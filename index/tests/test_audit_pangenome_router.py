"""AUDITOR D -- PangenomeIndex w-mer prefilter + global router SOUNDNESS.

Adversarially audits index/pangenome_index.PangenomeIndex (_block_wmers, _survives, locate,
build_global, locate_routed). Every output is gated against TWO independent grounds:

  * index.locate_oracle.locate_brute  -- the locate ground truth (own ungap/cap + MAF transform)
  * a transparent brute reimplementation of the per-block w-mer set (decoded from idx.T)

Crux gates (for many real + synthetic + degenerate patterns):
  as_tuples(pg.locate(P)) == as_tuples(pg.locate_routed(P)) == union_over_blocks locate_brute(P)
  and: for EVERY block whose locate_brute(P) is nonempty, pg._survives(block,P,..) is True
       (the prefilter must NEVER drop a true container).

Adversarial w: w=1, w=2, w > every |P| (forces fallback), and a pattern whose w-mers route to an
empty candidate set (genome-absent / split across blocks). Runs green; no real bug was found.
"""
import sys, os, json, random, tempfile
sys.path.insert(0, "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph")
import pytest

from index.pangenome_index import PangenomeIndex, _block_wmers
from index.suffix_index import as_tuples
from index.locate_oracle import locate_brute
from index.faithful import read_fasta, _ungap_cap

ROOT = "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph"
FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
YEAST = sorted(__import__("glob").glob(os.path.join(FADIR, "chrI_*.fa")))
HAVE_YEAST = len(YEAST) >= 5


# ----------------------------------------------------------------- independent reimplementations
def brute_wmers(idx, w):
    """Transparent reference for _block_wmers: decode idx.T into per-document DNA strings (codes < a
    are separators), collect every length-w substring. Independent of the source's loop structure."""
    docs, cur = [], []
    for code in idx.T:
        if code < idx.a:
            docs.append("".join(cur)); cur = []
        else:
            cur.append("ACGT"[code - idx.a])
    if cur:
        docs.append("".join(cur))
    out = set()
    for d in docs:
        for i in range(len(d) - w + 1):
            out.add(d[i:i + w])
    return out


def oracle_union(fastas, P, a, l):
    """Ground-truth genome occurrence set = union of locate_brute over the blocks."""
    out = set()
    for fa in fastas:
        cp = fa.replace(".fa", ".coords.json")
        coords = json.load(open(cp)) if os.path.exists(cp) else None
        out |= locate_brute(fa, coords, P, a=a, l=l)
    return out


def gate_pattern(pg, fastas, P, a):
    """The full soundness gate for one pattern P. Returns nothing; asserts equality + no dropped
    container. Empty P is a defined no-op (locate returns [])."""
    loc = as_tuples(pg.locate(P))
    rou = as_tuples(pg.locate_routed(P))
    orc = oracle_union(fastas, P, a, -1)
    assert loc == orc, f"locate != oracle for {P!r}: {sorted(loc)} vs {sorted(orc)}"
    assert rou == orc, f"routed != oracle for {P!r}: {sorted(rou)} vs {sorted(orc)}"
    # the crux: never drop a true container
    for b in pg.blocks:
        cp = os.path.join(os.path.dirname(fastas[0]), b["stem"].replace(".fa", ".coords.json"))
        fa = os.path.join(os.path.dirname(fastas[0]), b["stem"])
        coords = json.load(open(cp)) if os.path.exists(cp) else None
        if P and locate_brute(fa, coords, P, a=a, l=-1):
            assert pg._survives(b, P, b["idx"]._encode(P)) is True, \
                f"_survives dropped a TRUE container: block {b['stem']} pattern {P!r}"


# ----------------------------------------------------------------- synthetic block writer
def _write_block(d, name, seqs, rng):
    fa = os.path.join(d, name + ".fa")
    with open(fa, "w") as f:
        for i, s in enumerate(seqs):
            f.write(">sp%d\n%s\n" % (i, s))
    coords = []
    for i, s in enumerate(seqs):
        ung = len(s.replace("-", ""))
        strand = rng.choice("++-")                 # exercise both transform branches
        srcSize = rng.randint(ung + 5, ung + 500)
        start = rng.randint(0, srcSize - ung) if srcSize > ung else 0
        coords.append({"fasta_id": "sp%d" % i, "src": "sp%d.ctg" % i, "start": start,
                       "size": ung, "strand": strand, "srcSize": srcSize})
    json.dump(coords, open(fa.replace(".fa", ".coords.json"), "w"))
    return fa


def _rand_seq(rng, L, skew):
    if skew == "homo":
        return rng.choice("ACGT") * L
    if skew == "AT":
        return "".join(rng.choice("AT") for _ in range(L))
    return "".join(rng.choice("ACGT") for _ in range(L))


# =================================================================== TESTS

@pytest.mark.parametrize("w", [1, 2, 3, 4, 8, 20])
def test_block_wmers_matches_brute(w, tmp_path):
    """_block_wmers == transparent reimplementation across skew/homopolymer/short docs."""
    rng = random.Random(7 * w + 1)
    for t in range(15):
        seqs = [_rand_seq(rng, rng.randint(0, 14), rng.choice([None, "homo", "AT"]))
                for _ in range(rng.randint(1, 4))]
        fa = _write_block(str(tmp_path), f"w{w}t{t}", seqs, rng)
        pg = PangenomeIndex([fa], a=4, l=-1, s=2, w=w)
        for b in pg.blocks:
            assert b["wmers"] == brute_wmers(b["idx"], w)


def test_property_synthetic_soundness(tmp_path):
    """120 random multi-block configs: locate == routed == oracle, and _survives never drops a true
    container. Varies #docs, lengths (incl. empty), alphabet skew, w in {1,2,3,4,8,20}, s, ± strand."""
    rng = random.Random(99)
    configs = 0
    for trial in range(120):
        a = rng.randint(1, 4)
        fastas, allseqs = [], []
        for bi in range(rng.randint(1, 6)):
            seqs = [_rand_seq(rng, rng.randint(0, 14), rng.choice([None, None, "homo", "AT"]))
                    for _ in range(rng.randint(1, a))]
            allseqs.extend(seqs)
            fastas.append(_write_block(str(tmp_path), f"t{trial}b{bi}", seqs, rng))
        w = rng.choice([1, 2, 3, 4, 8, 20])
        s = rng.choice([1, 2, 4, 8])
        pg = PangenomeIndex(fastas, a=a, l=-1, s=s, w=w).build_global()
        configs += 1
        # wmers reference
        for b in pg.blocks:
            assert b["wmers"] == brute_wmers(b["idx"], w)
        # patterns: present substrings + absent + off-alpha + degenerate
        pats = set()
        for u in allseqs:
            for _ in range(4):
                if not u:
                    continue
                L = rng.randint(1, len(u)); st = rng.randint(0, len(u) - L)
                pats.add(u[st:st + L])
        pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(1, 10))) for _ in range(15)}
        pats |= {"GGGGGGGGGGGGGGGGGGGG", "ZQ", "ACGTN", "N", "AAAA", "A", "AC", ""}
        for P in pats:
            gate_pattern(pg, fastas, P, a)
    assert configs == 120


def test_empty_pattern_is_noop(tmp_path):
    rng = random.Random(3)
    fa = _write_block(str(tmp_path), "e0", ["ACGTACGT", "TTTT"], rng)
    pg = PangenomeIndex([fa], a=4, l=-1, s=2, w=4).build_global()
    assert as_tuples(pg.locate("")) == set()
    assert as_tuples(pg.locate_routed("")) == set()


def test_adversarial_routing(tmp_path):
    """The named extreme routing cases, checked against locate + oracle with stats inspection."""
    rng = random.Random(0)
    def mk(name, seqs):
        return _write_block(str(tmp_path), name, seqs, rng)
    f0 = mk("b0", ["AAAACCCC"])
    f1 = mk("b1", ["GGGGTTTT"])
    fastas = [f0, f1]
    pg = PangenomeIndex(fastas, a=1, l=-1, s=2, w=4).build_global()

    # (A) split w-mers: TTTT in b1 but TTTA/TTAA/TAAA in no block -> intersection empty -> absent
    st = {}
    rou = as_tuples(pg.locate_routed("TTTTAAAA", st))
    assert rou == as_tuples(pg.locate("TTTTAAAA")) == oracle_union(fastas, "TTTTAAAA", 1, -1) == set()
    assert st["candidates"] == 0

    # (B) genome-present, len>=w: routed touches exactly its container, equals oracle (1 hit)
    st2 = {}
    rou2 = as_tuples(pg.locate_routed("AAAACCCC", st2))
    assert rou2 == as_tuples(pg.locate("AAAACCCC")) == oracle_union(fastas, "AAAACCCC", 1, -1)
    assert len(rou2) == 1 and st2["candidates"] == 1

    # (C) a w-mer in NO block (genome-absent DNA, len>=w) -> empty candidate set, empty result
    st3 = {}
    assert as_tuples(pg.locate_routed("CGCGCGCG", st3)) == set() and st3["candidates"] == 0
    assert oracle_union(fastas, "CGCGCGCG", 1, -1) == set()

    # (D) off-alphabet, len>=w: w-mers never in gmap -> empty; matches locate + oracle
    assert as_tuples(pg.locate_routed("ZZZZ")) == as_tuples(pg.locate("ZZZZ")) == set()

    # (E) w larger than every |P|: |P|<w forces locate_routed -> locate fallback (still sound)
    for P in ["AAA", "ACCC", "GGG", "TTT"]:
        assert as_tuples(pg.locate_routed(P)) == as_tuples(pg.locate(P)) == \
               oracle_union(fastas, P, 1, -1)


def test_w_larger_than_all_patterns(tmp_path):
    """w huge (>= every document & pattern length): every query falls back to locate, still exact."""
    rng = random.Random(11)
    fastas, allseqs = [], []
    for bi in range(4):
        seqs = [_rand_seq(rng, rng.randint(1, 10), None) for _ in range(rng.randint(1, 3))]
        allseqs.extend(seqs)
        fastas.append(_write_block(str(tmp_path), f"big{bi}", seqs, rng))
    pg = PangenomeIndex(fastas, a=3, l=-1, s=4, w=1000).build_global()
    pats = set()
    for u in allseqs:
        for _ in range(3):
            L = rng.randint(1, len(u)); st = rng.randint(0, len(u) - L)
            pats.add(u[st:st + L])
    pats |= {"ACGTACGT", "ZZ", "GGGG"}
    for P in pats:
        gate_pattern(pg, fastas, P, 3)


@pytest.mark.skipif(not HAVE_YEAST, reason="yeast chrI fasta blocks not present")
@pytest.mark.parametrize("w", [1, 2, 8, 13, 200])
def test_real_chrI_blocks(w):
    """25 real chrI MAF blocks (a=4): locate == routed == oracle, and the prefilter never drops a true
    container, over real substrings (multi-species) + absent + off-alpha + degenerate patterns."""
    fastas = YEAST[:25]
    pg = PangenomeIndex(fastas, a=4, l=-1, s=4, w=w).build_global()
    for b in pg.blocks:
        assert b["wmers"] == brute_wmers(b["idx"], w)

    seqs = []
    for fa in fastas:
        for _id, s in read_fasta(fa)[:4]:
            seqs.append(_ungap_cap(s, -1))
    rng = random.Random(2024 + w)
    pats = set()
    tries = 0
    while len(pats) < 40 and tries < 4000:
        tries += 1
        s = rng.choice(seqs)
        if len(s) < 1:
            continue
        L = rng.randint(1, min(30, len(s)))
        st = rng.randint(0, len(s) - L)
        pats.add(s[st:st + L])
    pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(1, 25))) for _ in range(20)}
    pats |= {"GGGGGGGGGGGG", "ACGTACGTACGTACGT", "ZZZZ", "ACGTN", "N", "A", "AC", "ACG",
             "CACACCCACAC"}
    for P in pats:
        gate_pattern(pg, fastas, P, 4)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
