"""AUDITOR E -- DAWG (suffix automaton) exactness audit.

Focus: index.dawg.DAWG -- count, locate, edges, Wheeler-ness.

Every assertion is gated against an INDEPENDENT ground truth:
  * a transparent brute substring scan written here (brute_occ);
  * index.locate_oracle.locate_brute for genomic coords;
  * verify.brute_oracle.is_wheeler (all-perms, n<=9) for Wheeler-ness.

Run:  ~/miniconda3/envs/myenv/bin/python -m pytest test_audit_dawg.py -q
"""
import sys, os, random, itertools, json

REPO = "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph"
sys.path.insert(0, REPO)

import pytest

from index.dawg import DAWG
from index.faithful import read_fasta, _ungap_cap
from index.locate_oracle import locate_brute
from index.suffix_index import as_tuples
from verify import brute_oracle


# --------------------------------------------------------------------------- ground truth helpers
def brute_occ(seqs, P):
    """Independent brute substring scan -> set{(doc_idx, pos)}. Empty pattern -> empty set."""
    P = P.upper()
    m = len(P)
    out = set()
    if m == 0:
        return out
    for i, s in enumerate(seqs):
        s = s.upper()
        for pos in range(len(s) - m + 1):
            if s[pos:pos + m] == P:
                out.add((i, pos))
    return out


def dawg_locate_set(d, P):
    return {(h["record_idx"], h["ungapped_pos"]) for h in d.locate(P)}


def all_subs(seqs, maxlen):
    subs = set()
    for s in seqs:
        for L in range(1, min(maxlen, len(s)) + 1):
            for i in range(len(s) - L + 1):
                subs.add(s[i:i + L])
    return subs


def _check(seqs, pats):
    d = DAWG(seqs)
    for P in pats:
        if P == "":          # empty pattern semantics are degenerate (see test_empty_pattern_count_quirk)
            assert d.locate(P) == []
            continue
        bo = brute_occ(seqs, P)
        assert d.count(P) == len(bo), (seqs, P, d.count(P), len(bo))
        assert dawg_locate_set(d, P) == bo, (seqs, P)


# --------------------------------------------------------------------------- 1. property: random multi-doc
def test_count_locate_random_multidoc():
    random.seed(7)
    cases = 0
    for _ in range(1500):
        ndocs = random.randint(1, 4)
        mode = random.random()
        seqs = []
        for _ in range(ndocs):
            L = random.randint(0, 14)
            if mode < 0.25:
                alpha = random.choice(["A", "AC", "ACG", "ACGT"])   # alphabet skew
            elif mode < 0.5:
                alpha = "A" * random.randint(1, 3) + "C"            # homopolymer skew
            else:
                alpha = "ACGT"
            seqs.append("".join(random.choice(alpha) for _ in range(L)))
        if all(len(s) == 0 for s in seqs):
            continue
        pats = list(all_subs(seqs, 6))
        pats += ["".join(random.choice("ACGT") for _ in range(random.randint(1, 4))) for _ in range(3)]
        pats += ["", "N", "AN", "X", "ACGTN"]                       # empty + off-alphabet (misses)
        _check(seqs, pats)
        cases += len(pats)
    assert cases > 10000


# --------------------------------------------------------------------------- 2. adversarial clone-forcing
@pytest.mark.parametrize("seqs", [
    ["ACGCGCG"], ["ACGACGACG"], ["AAAA"], ["ACGCGCGCG"], ["ACGACGACGACG"],
    ["CGCGCGCG"], ["ACACAC"], ["ACGCGCG", "ACGACGACG"], ["AAAAA", "AAA"],
    ["ACGTACGTACGT"], ["GCGCGCGC", "CGCGCG"], ["TATATA"], ["ACGACG", "CGACGA"],
    ["ACGCGCGCGCG"], ["AGAGAGAG"], ["ACGACGTACG"], ["ACGCG"], ["ACGACG"],
])
def test_adversarial_clone_states(seqs):
    # Repeat-heavy strings force suffix-automaton CLONE states; locate must still be exact.
    pats = list(all_subs(seqs, 11)) + ["", "N", "ZZ"]
    _check(seqs, pats)


# --------------------------------------------------------------------------- 3. empty / off-alphabet
def test_empty_and_offalpha_locate():
    d = DAWG(["ACGACG", "CGT"])
    assert d.locate("") == []
    assert d.locate("N") == []          # off-alphabet
    assert d.locate("X") == []
    assert d.locate("ACGTN") == []
    assert d.count("N") == 0
    assert d.count("ZZZ") == 0
    # a non-occurring but in-alphabet pattern
    assert d.locate("TTTT") == []
    assert d.count("TTTT") == 0


# --------------------------------------------------------------------------- 4. empty-pattern count (FIXED)
def test_empty_pattern_count_matches_locate():
    # Audit finding, FIXED: DAWG.count now guards P=="" -> 0, so count("")==len(locate(""))==0,
    # consistent with SuffixIndex.count("").
    d = DAWG(["ACGACG", "CGT"])
    assert d.count("") == len(d.locate("")) == 0


def test_empty_pattern_behavior_fixed():
    # After the audit fix, count("")==0 and locate("")==[] (was: count returned len(T)).
    d = DAWG(["ACGACG", "CGT"])
    assert d.count("") == 0
    assert d.locate("") == []


# --------------------------------------------------------------------------- 5. Wheeler-ness on tiny DAWGs
def test_dawg_is_wheeler_small():
    tested = 0
    for total in range(1, 6):                       # single-doc strings length 1..5
        for combo in itertools.product("ACGT", repeat=total):
            d = DAWG(["".join(combo)])
            edges = [(str(u), str(w), lab) for (u, w, lab) in d.edges()]
            nodes = sorted({e[0] for e in edges} | {e[1] for e in edges})
            if len(nodes) > 8:                      # keep n! brute oracle feasible
                continue
            lr = brute_oracle.rank_labels(edges, int_mode=True)
            assert brute_oracle.is_wheeler(nodes, edges, lr), "".join(combo)
            tested += 1
    assert tested > 1000


@pytest.mark.parametrize("seqs", [
    ["AC", "GT"], ["A", "C", "G"], ["ACG", "CGT"], ["AA", "AA"],
    ["ACGCG"], ["ACGACG"], ["AC", "AC"], ["A", "A", "A"],
])
def test_dawg_is_wheeler_small_multidoc(seqs):
    d = DAWG(seqs)
    edges = [(str(u), str(w), lab) for (u, w, lab) in d.edges()]
    nodes = sorted({e[0] for e in edges} | {e[1] for e in edges})
    if len(nodes) > 9:
        pytest.skip("too many states for brute Wheeler oracle")
    lr = brute_oracle.rank_labels(edges, int_mode=True)
    assert brute_oracle.is_wheeler(nodes, edges, lr), seqs


# --------------------------------------------------------------------------- 6. genomic locate w/ coords (yeast)
YEAST_FA = os.path.join(REPO, "data/multiseq_alignment/yeast/fasta/chrI_blk00000_s6.fa")
YEAST_CJ = YEAST_FA[:-3] + ".coords.json"


@pytest.mark.skipif(not (os.path.exists(YEAST_FA) and os.path.exists(YEAST_CJ)),
                    reason="yeast block / coords sidecar not present")
def test_genomic_locate_yeast_block():
    coords = json.load(open(YEAST_CJ))
    a = len(coords)
    l = -1
    seqs = [_ungap_cap(seq, l) for _id, seq in read_fasta(YEAST_FA)[:a]]
    d = DAWG(seqs, coords=coords)
    random.seed(3)
    pats = list(all_subs(seqs, 6))
    random.shuffle(pats)
    pats = pats[:300] + ["NNN", "ACGTACGTACGTACGTACGT"]   # include misses
    for P in pats:
        got = as_tuples(d.locate(P))
        want = locate_brute(YEAST_FA, coords, P, a=a, l=l)
        assert got == want, (P, got, want)


# --------------------------------------------------------------------------- 7. C++ binary parity (gap note)
WG_SUFFIX = os.path.join(REPO, "index/cpp/wg_suffix")


@pytest.mark.skipif(not os.path.exists(WG_SUFFIX),
                    reason="C++ wg_suffix not built (cd index/cpp && make -s wg_suffix); DAWG is a "
                           "Python-only module -- no C++ DAWG counterpart, so no parity gate here")
def test_cpp_placeholder():
    # Intentionally a no-op skip target: the C++ wg_suffix is the suffix-FM index, not the DAWG;
    # there is no C++ DAWG to compare against. Documented gap.
    pass
