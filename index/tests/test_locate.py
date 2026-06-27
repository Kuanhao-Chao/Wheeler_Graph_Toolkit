"""Gates for LOCATE (index/locate.py): query a string -> exact (species, src, genomic, strand)
occurrences, verified against the independent brute oracle (index/locate_oracle.py).

Covers: a synthetic block with hand-computed coordinates (both strands, multi-hit, |P|<K/=K/>K);
real chrI blocks through the FM prefilter; the consistency gate tying occ_map to the De Bruijn k-mers.
The router + real-genome cross-check live alongside (L3). Run under python3; the De Bruijn generator
is shelled to myenv.
"""
import glob
import json
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import debruijn                  # noqa: E402
from index import locate as loc             # noqa: E402
from index import locate_oracle as lor      # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402
from pipeline import msa_to_index as m2i     # noqa: E402

YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "chrI_*.fa")))
HAVE_REC = os.path.exists(m2i.REC)
PY_BIO = os.environ.get("WGT_PY_BIO", os.path.expanduser("~/miniconda3/envs/myenv/bin/python"))


# --------------------------------------------------------------------------- synthetic: hand-computed
def test_synthetic_both_strands_multihit(tmp_path):
    # spA(+): "ACGACGAC" at start 100; spB(-): same seq at start 50, srcSize 200.
    fa = os.path.join(str(tmp_path), "syn.fa")
    with open(fa, "w") as f:
        f.write(">spA\nACGACGAC\n>spB\nACGACGAC\n")
    coords = [
        {"fasta_id": "spA", "src": "spA.chr", "start": 100, "size": 8, "strand": "+", "srcSize": 1000},
        {"fasta_id": "spB", "src": "spB.ctg", "start": 50, "size": 8, "strand": "-", "srcSize": 200},
    ]
    k = 4                                     # K = 3
    sample = loc.build_locate_sample(fa, k, a=None, l=-1)

    # P = "ACG" (m == K): spA pos 0,3 (+); spB pos 0,3 (-)
    hits = loc.locate_shard("ACG", sample, coords, count_fn=None)
    got = loc.as_tuples(hits)
    expected = {
        ("spA", "spA.chr", 100, 103, "+"),
        ("spA", "spA.chr", 103, 106, "+"),
        ("spB", "spB.ctg", 147, 150, "-"),    # 200-(50+0+3)=147 .. 200-(50+0)=150
        ("spB", "spB.ctg", 144, 147, "-"),    # 200-(50+3+3)=144 .. 200-(50+3)=147
    }
    assert got == expected
    assert got == lor.locate_brute(fa, coords, "ACG")     # oracle agrees too

    # |P| > K and |P| < K, plus absent -> all agree with the oracle
    for P in ("ACGA", "AC", "A", "TTTT", "zzz"):
        assert loc.as_tuples(loc.locate_shard(P, sample, coords)) == lor.locate_brute(fa, coords, P)


# --------------------------------------------------------------------------- committed example block
def test_example_block_consistency():
    # the example De Bruijn graph isn't yeast; just check occ-map keys tie to the k-mer set (k=4).
    fa = os.path.join(ROOT, "data", "multiseq_alignment", "appendix", "a1.fa")
    if not os.path.exists(fa):
        pytest.skip("appendix toy alignment absent")
    k = 4
    seqs = [s for _id, s in read_fasta(fa)]
    g = debruijn.build(seqs, k, seqLen=-1, alnNum=None)
    sample = loc.build_locate_sample(fa, k, a=None, l=-1)
    kmer_nodes = {km for km in g["kmer2id"] if "$" not in km}
    assert set(sample["occ"].keys()) == kmer_nodes


# --------------------------------------------------------------------------- real chrI blocks + prefilter
def _coords_for(fa):
    return json.load(open(fa.replace(".fa", ".coords.json")))


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC), reason="needs yeast FASTA + recognizer")
@pytest.mark.parametrize("fa", YEAST_FA[:5])
def test_locate_vs_oracle_real_block(fa, tmp_path):
    k, a, l = 4, 2, -1
    coords = _coords_for(fa)
    r = m2i.process_block(fa, k=k, l=(10_000_000), a=a, work=str(tmp_path), py=PY_BIO)
    assert r["verdict"] == 1 and r["outdir"]
    from index.wg_index import WGIndex
    count_fn = WGIndex.from_iol(r["outdir"]).count
    sample = loc.build_locate_sample(fa, k, a=a, l=l)

    # consistency: occ-map keys == De Bruijn (k-1)-mers (minus $-containing)
    seqs = [s for _id, s in read_fasta(fa)][:a]
    g = debruijn.build(seqs, k, seqLen=-1, alnNum=a)
    assert set(sample["occ"].keys()) == {km for km in g["kmer2id"] if "$" not in km}

    # present patterns (real substrings, various lengths incl. multi-hit), absent, off-alphabet
    rng = random.Random(hash(fa) & 0xffff)
    us = [_ungap_cap(s, -1) for s in seqs]
    pats = set()
    for u in us:
        for m in (2, 3, 4, 6, 9):
            if len(u) >= m:
                j = rng.randint(0, len(u) - m)
                pats.add(u[j:j + m])
    pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(2, 7))) for _ in range(30)}
    pats |= {"ZZZ", "N", ""}
    saw_hit = False
    for P in pats:
        got = loc.as_tuples(loc.locate_shard(P, sample, coords, count_fn))
        truth = lor.locate_brute(fa, coords, P, a=a, l=l)
        assert got == truth, (fa, P, sorted(got), sorted(truth))
        saw_hit = saw_hit or bool(truth)
    assert saw_hit

    # the FM prefilter is SOUND: a real substring is never skipped (count(reverse(P))>0)
    for u in us[:1]:
        if len(u) >= 5:
            P = u[1:6]
            assert count_fn(P[::-1])[2] > 0


# --------------------------------------------------------------------------- L3: router across shards
def _shard_fastas(gli, fadir):
    return [(os.path.join(fadir, sh["stem"] + ".fa"), sh["coords"]) for sh in gli.shards]


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC), reason="needs yeast FASTA + recognizer")
def test_router_locate_vs_oracle(tmp_path):
    from index import genome_index as gi
    fadir = os.path.dirname(YEAST_FA[0])
    k, a, l = 4, 2, -1
    man = gi.build_shards(YEAST_FA[:15], k=k, l=10_000_000, a=a, work=str(tmp_path), py_bio=PY_BIO)
    shards = man["shards"]
    assert len(shards) >= 8
    gli = loc.GenomeLocateIndex(shards, fadir, k=k, a=a, l=l, engine="py")
    shard_fc = _shard_fastas(gli, fadir)

    def oracle_union(P):
        out = set()
        for fa, coords in shard_fc:
            out |= lor.locate_brute(fa, coords, P, a=a, l=l)
        return out

    rng = random.Random(99)
    pats = set()
    for fa, _c in shard_fc[:6]:
        for u in (_ungap_cap(s, -1) for _id, s in read_fasta(fa)[:a]):
            if len(u) >= 8:
                j = rng.randint(0, len(u) - 6)
                pats.add(u[j:j + 6])
    pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(3, 7))) for _ in range(20)}
    pats |= {"ZZZ"}
    saw_multi = False
    for P in pats:
        hits = gli.locate(P)
        assert loc.as_tuples(hits) == oracle_union(P), (P, sorted(loc.as_tuples(hits)))
        # router output is dedup'd and sorted
        keys = [(h["species"], h["src"], h["gstart"], h["gend"], h["strand"]) for h in hits]
        assert len(keys) == len(set(keys))
        assert keys == sorted(keys, key=lambda t: (t[0], t[1], t[2], t[3]))
        saw_multi = saw_multi or len(hits) >= 2
    assert saw_multi


# --------------------------------------------------------------------------- L3: real-genome cross-check
GENOME = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "genome", "chrI.fa")


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC and os.path.exists(GENOME)),
                    reason="needs yeast FASTA + recognizer + cached sacCer3 genome")
def test_located_reference_coords_match_real_genome(tmp_path):
    from index import genome_index as gi
    from pipeline.yeast_fetch import read_genome_fasta
    chrI = read_genome_fasta(GENOME)
    assert len(chrI) == 230218                      # == the MAF srcSize for sacCer3.chrI
    fadir = os.path.dirname(YEAST_FA[0])
    k, a, l = 4, 2, -1
    man = gi.build_shards(YEAST_FA[:25], k=k, l=10_000_000, a=a, work=str(tmp_path), py_bio=PY_BIO)
    gli = loc.GenomeLocateIndex(man["shards"], fadir, k=k, a=a, l=l, engine="py")

    # real reference k-mers of various lengths -> every located sacCer3 hit must be literally in chrI
    rng = random.Random(7)
    checked = 0
    for fa, coords in _shard_fastas(gli, fadir)[:25]:
        ref = read_fasta(fa)[0]                      # the reference row is first
        if ref[0] != "sacCer3":
            continue
        u = _ungap_cap(ref[1], -1)
        for m in (5, 8, 12):
            if len(u) < m:
                continue
            P = u[rng.randint(0, len(u) - m):][:m]
            for h in gli.locate(P):
                if h["species"] == "sacCer3":
                    assert h["strand"] == "+"
                    assert chrI[h["gstart"]:h["gend"]] == P, (P, h)
                    checked += 1
    assert checked > 0
