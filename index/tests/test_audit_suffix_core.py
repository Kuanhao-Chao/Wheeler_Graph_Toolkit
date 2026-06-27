"""AUDITOR A — SuffixIndex core (suffix_index.py): build_text / build_sa / build_bwt /
C[] / _rank / lf / recover_pos / backward_search / count.

Every output is gated against an INDEPENDENT brute reimplementation written here
(brute suffix sort, brute BWT/DOC/C/rank, brute substring-scan count) plus the
module's own transparent reference build_sa_brute. No assertion trusts the index alone.

Result: no defects found in the SuffixIndex core. The whole file runs green.
Run: ~/miniconda3/envs/myenv/bin/python -m pytest test_audit_suffix_core.py -q
"""
import os
import random
import sys

import pytest

sys.path.insert(0, "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph")

from index.suffix_index import (  # noqa: E402
    SuffixIndex, build_text, build_sa, build_sa_brute, build_bwt, dna_code,
)

ALPH = "ACGT"
YEAST_FA = ("/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph/"
            "data/multiseq_alignment/yeast/fasta/chrI_blk00000_s6.fa")


# --------------------------------------------------------------------------- independent brutes
def brute_count(seqs, P):
    """Substring-scan occurrence count of P across the (ungapped) docs. P uppercased to match
    the index's _encode(P.upper())."""
    P = P.upper()
    if P == "":
        return 0
    return sum(s[i:i + len(P)] == P
               for s in seqs for i in range(len(s) - len(P) + 1))


def isa_of(SA):
    isa = [0] * len(SA)
    for i, p in enumerate(SA):
        isa[p] = i
    return isa


def all_core_gates(seqs, s, patterns):
    """Assert every SuffixIndex core field/method against an independent ground truth.
    Returns the built index."""
    idx = SuffixIndex(seqs, s=s, sample="rate")
    T, n = idx.T, idx.n

    # build_text: T = S_0 sep_0 S_1 sep_1 ...; sep_i = i; A=a..T=a+3
    code = dna_code(len(seqs))
    exp_T, exp_doc, exp_ds = [], [], []
    for i, sq in enumerate(seqs):
        exp_ds.append(len(exp_T))
        for ch in sq:
            exp_T.append(code[ch]); exp_doc.append(i)
        exp_T.append(i); exp_doc.append(i)
    assert idx.T == exp_T
    assert idx.doc == exp_doc
    assert idx.doc_start == exp_ds
    assert idx.a == len(seqs)
    assert idx.n == len(exp_T)

    # SA == transparent brute (cyclic-rotation sort) == prefix-doubling build_sa
    sab = build_sa_brute(T)
    assert idx.SA == sab
    assert build_sa(T) == sab

    # BWT[i] == T[(SA[i]-1) % n]
    assert idx.BWT == ([T[(idx.SA[i] - 1) % n] for i in range(n)] if n else [])
    assert idx.BWT == build_bwt(T, idx.SA)

    # DOC[i] == doc[SA[i]]
    assert idx.DOC == [idx.doc[idx.SA[i]] for i in range(n)]

    # C[c] == #symbols < c in T
    for c in range(idx.sigma):
        assert idx.C[c] == sum(1 for x in T if x < c)

    # _rank(c,i) == BWT[:i].count(c)
    for c in range(idx.sigma):
        for i in range(n + 1):
            assert idx._rank(c, i) == idx.BWT[:i].count(c)

    # lf(i) == ISA[(SA[i]-1) % n]
    isa = isa_of(idx.SA)
    for i in range(n):
        assert idx.lf(i) == isa[(idx.SA[i] - 1) % n]

    # recover_pos(i) == SA[i] for ALL i (LF walk to nearest rate sample)
    for i in range(n):
        assert idx.recover_pos(i) == idx.SA[i]

    # count(P) == hi-lo == brute substring-scan count
    for P in patterns:
        lo, hi = idx.backward_search(P)
        assert hi >= lo
        bc = brute_count(seqs, P)
        assert (hi - lo) == bc
        assert idx.count(P) == bc
    return idx


# --------------------------------------------------------------------------- property-based
def _sample_rates(n):
    # s in {1,2,4,8, n, n+5, 2n}; large s => only SA pos 0 sampled (O(n) recover walk)
    return {1, 2, 4, 8, max(1, n), n + 5, max(1, 2 * n)}


def test_property_random_multidoc():
    random.seed(1)
    cases = 0
    for _ in range(400):
        ndocs = random.randint(1, 4)
        seqs = []
        for _ in range(ndocs):
            L = random.randint(0, 8)
            if random.random() < 0.2:                # homopolymer / skew
                seqs.append(random.choice(ALPH) * L)
            else:
                seqs.append("".join(random.choice(ALPH) for _ in range(L)))
        pats = set()
        for sq in seqs:
            if sq:
                for _ in range(3):
                    a = random.randint(0, len(sq)); b = random.randint(a, len(sq))
                    pats.add(sq[a:b])
        for _ in range(3):
            pats.add("".join(random.choice(ALPH) for _ in range(random.randint(1, 5))))
        pats.add("N")                                # off-alphabet -> 0
        pats = [p for p in pats if p]
        n = sum(len(x) for x in seqs) + ndocs
        for s in _sample_rates(n):
            all_core_gates(seqs, s, pats)
            cases += 1
    assert cases > 1000


def test_property_longer_seqs_all_sample_rates():
    random.seed(7)
    for _ in range(60):
        seqs = ["".join(random.choice(ALPH) for _ in range(random.randint(5, 40)))
                for _ in range(random.randint(1, 3))]
        n = sum(len(x) for x in seqs) + len(seqs)
        pats = []
        for sq in seqs:
            for _ in range(8):
                L = random.randint(1, 6)
                a = random.randint(0, max(0, len(sq) - L))
                pats.append(sq[a:a + L])
        for s in (1, 3, n, 2 * n + 3):               # incl. s>=n (single sample) & s>2n
            all_core_gates(seqs, s, pats)


# --------------------------------------------------------------------------- degenerate / extreme
@pytest.mark.parametrize("seqs", [
    [""],            # single empty doc -> T == [sep_0]
    ["", ""],        # sum(len)==0, every doc empty
    ["A"],           # a=1 single doc, |P|=1
    ["A" * 200],     # homopolymer
    ["AT", "AT"],    # two-doc identical seqs
    ["AAAA", "AAAA"],
    ["ACGTACGT"],
    ["GGGT", "ACCC"],  # cross-doc: 'TA','CG' wrap must NOT match (separator between docs)
])
def test_degenerate_and_extreme(seqs):
    pats = ["A", "AA", "AAA", "AT", "TA", "CG", "ACGT", "AAAA", "ACGTACGT", "T", "GG", "N"]
    n = sum(len(x) for x in seqs) + len(seqs)
    for s in _sample_rates(n):
        all_core_gates(seqs, s, pats)


def test_pattern_longer_than_block():
    idx = SuffixIndex(["ACGT"], s=4)
    assert idx.count("ACGTACGT") == 0     # |P| > block length
    assert idx.count("ACGTA") == 0
    assert idx.count("AC") == 1
    assert idx.count("ACGT") == 1


def test_homopolymer_large_sample_rate():
    # s >> n => only text pos 0 sampled, recover_pos is a full O(n) LF walk
    idx = SuffixIndex(["A" * 200], s=10 ** 6)
    assert idx.n_samples == 1
    for i in range(idx.n):
        assert idx.recover_pos(i) == idx.SA[i]
    assert idx.count("A" * 5) == 196      # 200-5+1


def test_offalphabet_and_empty_pattern():
    idx = SuffixIndex(["ACGT"])
    # off-alphabet -> _encode None -> empty range
    assert idx.backward_search("N") == (0, 0)
    assert idx.count("ANG") == 0
    # empty pattern: documented behavior count('')==0 (locate also returns []); NOT a bug,
    # an intentional convention (an empty P would otherwise "occur" n times).
    assert idx.count("") == 0
    assert idx.backward_search("") == (0, 0)


def test_empty_seqs_a0_documented():
    """seqs=[] gives a=0 (separators would collide with DNA codes) but there is no text, so the
    index is an empty, non-crashing degenerate instance. Documented, not exercised as a real index."""
    idx = SuffixIndex([], s=4)
    assert idx.n == 0 and idx.a == 0
    assert idx.SA == [] and idx.BWT == []
    assert idx.count("A") == 0


def test_lowercase_pattern_encoding():
    idx = SuffixIndex(["ACGTACGT"], s=4)
    assert idx.count("acgt") == idx.count("ACGT") == 2


# --------------------------------------------------------------------------- real yeast data
@pytest.mark.skipif(not os.path.exists(YEAST_FA), reason="yeast block fasta absent")
def test_yeast_from_fasta_core():
    from index.faithful import read_fasta, _ungap_cap
    idx = SuffixIndex.from_fasta(YEAST_FA, a=3, l=120, s=8)
    assert idx.SA == build_sa_brute(idx.T)
    for i in range(0, idx.n, 25):
        assert idx.recover_pos(i) == idx.SA[i]
    seqs = [_ungap_cap(s, 120) for _id, s in read_fasta(YEAST_FA)[:3]]
    for P in ["A", "ACG", "TT", "GATC", "ACGTACGT"]:
        assert idx.count(P) == brute_count(seqs, P)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
