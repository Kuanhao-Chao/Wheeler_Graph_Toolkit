"""AUDITOR B -- r-index phi / toehold / locate_phi / recover_pos under sample='runs'.

Gates the r-index (sample='runs') path against three INDEPENDENT grounds:
  * ISA = inverse(SA) built here  -> phi(p) == SA[(ISA[p]-1) % n] for EVERY p
  * SA == build_sa_brute(T)       -> recover_pos(i) == SA[i] for EVERY i
  * brute substring scan          -> locate_phi occ set == locate(rate) == brute
  * index.locate_oracle.locate_brute (genomic ground truth) on real yeast data

No source is edited; this file is green. Any real defect would be marked
`# BUG(file:function):` + xfail/skip so it can be flipped on after a fix.
"""
import bisect
import os
import random
import sys

import pytest

sys.path.insert(0, "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph")

from index.suffix_index import (  # noqa: E402
    SuffixIndex,
    build_sa_brute,
    as_tuples,
)

YEAST_FA = ("/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph/"
            "data/multiseq_alignment/yeast/fasta/chrI_blk00000_s6.fa")
YEAST_COORDS = YEAST_FA.replace(".fa", ".coords.json")


# --------------------------------------------------------------------- helpers (independent grounds)
def isa_of(SA):
    n = len(SA)
    isa = [0] * n
    for i, p in enumerate(SA):
        isa[p] = i
    return isa


def brute_occ(seqs, P):
    """Transparent brute substring scan: set of (doc, local_pos)."""
    res = set()
    if not P:
        return res
    m = len(P)
    for d, s in enumerate(seqs):
        for i in range(len(s) - m + 1):
            if s[i:i + m] == P:
                res.add((d, i))
    return res


def core_set(hits):
    return {(h["record_idx"], h["ungapped_pos"]) for h in hits}


def all_substrings(seqs, maxlen=4):
    pats = set()
    for s in seqs:
        for ln in range(1, maxlen + 1):
            for i in range(len(s) - ln + 1):
                pats.add(s[i:i + ln])
    pats |= {"A", "C", "G", "T", "AA", "ACGT", "Z", "N", ""}
    return pats


# --------------------------------------------------------------------- the per-instance gate
def _check_instance(seqs, s):
    idx = SuffixIndex(seqs, s=s, sample="runs")
    idx_rate = SuffixIndex(seqs, s=s, sample="rate")
    n = idx.n
    SA = idx.SA

    # SA itself is the transparent brute cyclic-rotation order
    assert SA == build_sa_brute(idx.T), ("SA mismatch", seqs)

    isa = isa_of(SA)

    # GATE 1: phi(p) == SA[(ISA[p]-1) % n] for every p (incl. the cyclic-wrap branch p at SA-rank 0).
    for p in range(n):
        got = idx.phi(p)
        exp = SA[(isa[p] - 1) % n]
        assert got == exp, ("phi", seqs, p, got, exp)
        # exercise the bisect k==-1 cyclic branch whenever it is actually reachable
        k = bisect.bisect_right(idx._phi_keys, p) - 1
        if k == -1:
            # smallest phi key > p -> wrap to last pair; verified equal above already.
            pass

    # GATE 2: recover_pos(i) == SA[i] for EVERY i (untested elsewhere since locate dispatches to phi)
    for i in range(n):
        assert idx.recover_pos(i) == SA[i], ("recover_pos", seqs, i)

    # GATE 3: toehold == SA[hi-1] for every nonempty range; locate_phi == locate(rate) == brute
    for P in all_substrings(seqs):
        if P:
            lo, hi, toe = idx._backward_toehold(P)
            if hi > lo:
                assert toe == SA[hi - 1], ("toehold", seqs, P, toe, SA[hi - 1])
        runs_set = core_set(idx.locate(P))          # dispatches to locate_phi under 'runs'
        phi_set = core_set(idx.locate_phi(P)) if P else set()
        rate_set = core_set(idx_rate.locate(P))
        bset = brute_occ(seqs, P)
        assert runs_set == rate_set == bset, ("locate", seqs, P, runs_set, rate_set, bset)
        if P:
            assert phi_set == bset, ("locate_phi", seqs, P, phi_set, bset)
    return idx


# --------------------------------------------------------------------- random property sweep
def _rand_seqs(rng):
    ndoc = rng.randint(1, 4)
    out = []
    for _ in range(ndoc):
        L = rng.randint(0, 12)
        mode = rng.random()
        if mode < 0.25:
            out.append("".join(rng.choice("ACGT") if rng.random() > 0.6 else "A" for _ in range(L)))
        elif mode < 0.4:
            out.append("A" * L)                      # pure homopolymer -> few runs, many occ
        else:
            out.append("".join(rng.choice("ACGT") for _ in range(L)))
    return out


def test_random_property_runs_index():
    rng = random.Random(20240627)
    for _ in range(1500):
        seqs = _rand_seqs(rng)
        s = rng.choice([1, 2, 3, 8])
        _check_instance(seqs, s)


# --------------------------------------------------------------------- explicit degenerate / extreme
@pytest.mark.parametrize("seqs,s", [
    (["A"], 1),                                       # single doc, |T| tiny
    (["", ""], 2),                                    # all-empty docs (only separators)
    (["ACGT"], 8),                                    # single doc, s >> n (irrelevant for runs)
    (["AAAAAAAA"], 2),                                # homopolymer, |occ| large for "A"
    (["AAAA", "AAAA", "AAAA"], 4),                    # "A" in every doc -> large occ set
    (["AAAAAAAA", "TTTTTTTT"], 1),                    # two homopolymers, many run heads overall
    (["ACGTACGTACGT"], 3),                            # periodic
    (["A", "C", "G", "T"], 1),                        # 4 single-char docs
    (["ACACACAC", "CACACACA"], 2),                    # overlapping period-2
    (["GATTACA", "TACAGAT", "ACAGATT"], 8),           # mixed
])
def test_degenerate_and_extreme(seqs, s):
    _check_instance(seqs, s)


def test_single_char_pattern_every_doc():
    # |P|=1 substring present in every doc -> max occ; runs/rate/brute must agree exactly
    seqs = ["AAGAA", "TAAAT", "CAAAC"]
    idx = SuffixIndex(seqs, s=2, sample="runs")
    idx_rate = SuffixIndex(seqs, s=2, sample="rate")
    for P in ["A", "C", "G", "T"]:
        assert core_set(idx.locate(P)) == core_set(idx_rate.locate(P)) == brute_occ(seqs, P)


def test_wrap_branch_min_phi_key_is_zero():
    """The bisect k==-1 cyclic-wrap branch in phi() is UNREACHABLE in practice: text position 0
    always sits at a BWT run head (its BWT symbol is the unique largest separator sep_{a-1},
    which occurs once -> always its own run), so 0 is always a phi key and min(_phi_keys)==0.
    This documents that the wrap branch is dead code (not a bug); phi is still proven correct for
    every p by test_random_property_runs_index / the per-instance gate."""
    rng = random.Random(11)
    for _ in range(3000):
        seqs = _rand_seqs(rng)
        idx = SuffixIndex(seqs, s=2, sample="runs")
        if idx.n == 0:
            continue
        assert min(idx._phi_keys) == 0


# --------------------------------------------------------------------- real yeast genomic ground truth
_have_yeast = os.path.exists(YEAST_FA) and os.path.exists(YEAST_COORDS)


@pytest.mark.skipif(not _have_yeast, reason="yeast block fasta / coords not present")
def test_yeast_genomic_runs_vs_brute_oracle():
    import json
    from index.locate_oracle import locate_brute
    from index.faithful import read_fasta, _ungap_cap

    coords = json.load(open(YEAST_COORDS))
    a, l = 4, 200
    idx_runs = SuffixIndex.from_fasta(YEAST_FA, a=a, l=l, coords=coords, s=8, sample="runs")
    idx_rate = SuffixIndex.from_fasta(YEAST_FA, a=a, l=l, coords=coords, s=8, sample="rate")

    SA = idx_runs.SA
    assert SA == build_sa_brute(idx_runs.T)
    n = idx_runs.n
    isa = isa_of(SA)
    for p in range(n):
        assert idx_runs.phi(p) == SA[(isa[p] - 1) % n]
    for i in range(n):
        assert idx_runs.recover_pos(i) == SA[i]

    recs = read_fasta(YEAST_FA)[:a]
    rows = [_ungap_cap(seq, l) for _id, seq in recs]
    rng = random.Random(5)
    pats = set()
    for r in rows:
        for ln in (1, 3, 6, 12):
            if len(r) >= ln:
                for _ in range(15):
                    i = rng.randint(0, len(r) - ln)
                    pats.add(r[i:i + ln])
    pats |= {"A", "C", "G", "T", "ACGT", "NNN"}

    for P in pats:
        lo, hi, toe = idx_runs._backward_toehold(P)
        if hi > lo:
            assert toe == SA[hi - 1], (P, toe, SA[hi - 1])
        runs_t = as_tuples(idx_runs.locate_phi(P))
        rate_t = as_tuples(idx_rate.locate(P))
        brute = locate_brute(YEAST_FA, coords, P, a=a, l=l)
        assert runs_t == rate_t == brute, (P, len(runs_t), len(rate_t), len(brute))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
