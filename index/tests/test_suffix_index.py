"""Gates for the tagged suffix Wheeler index (index/suffix_index.py): exact species+position locate.

SA/BWT/DOC/C/rank == a transparent brute reference; recover_pos == SA for every sample rate; locate ==
the independent brute oracle (index/locate_oracle) AND == the existing occ-map locate; forward
convention; the reference species cross-checked against the real sacCer3 genome. Run under python3; the
De Bruijn generator + genome fetch are shelled to / cached via myenv as in test_locate.py.
"""
import glob
import json
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import suffix_index as sx       # noqa: E402
from index import locate as loc            # noqa: E402
from index import locate_oracle as lor     # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402

YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "chrI_*.fa")))
GENOME = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "genome", "chrI.fa")
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
HAVE_REC = os.path.exists(REC)


# --------------------------------------------------------------------------- SA/BWT/DOC vs brute ref
def _brute_bwt_doc(T, doc):
    n = len(T)
    sa = sx.build_sa_brute(T)
    bwt = [T[(sa[i] - 1) % n] for i in range(n)]
    docarr = [doc[sa[i]] for i in range(n)]
    return sa, bwt, docarr


def test_sa_bwt_doc_c_rank_vs_brute():
    rng = random.Random(3)
    for _ in range(120):
        seqs = ["".join(rng.choice("ACGT") for _ in range(rng.randint(0, 14)))
                for _ in range(rng.randint(1, 5))]
        if sum(len(s) for s in seqs) == 0:
            continue
        T, doc, _ds, _a = sx.build_text(seqs)
        idx = sx.SuffixIndex(seqs, coords=None, s=rng.choice([1, 2, 4]))
        bsa, bbwt, bdoc = _brute_bwt_doc(T, doc)
        assert idx.SA == bsa and idx.BWT == bbwt and idx.DOC == bdoc
        # C[c] and rank from prefix arrays match direct counts over BWT
        for c in range(idx.sigma):
            assert idx.C[c] == sum(1 for x in T if x < c)
            for i in (0, idx.n // 2, idx.n):
                assert idx._rank(c, i) == idx.BWT[:i].count(c)


def test_recover_pos_equals_sa_all_sample_rates():
    rng = random.Random(5)
    for _ in range(60):
        seqs = ["".join(rng.choice("ACGT") for _ in range(rng.randint(1, 16)))
                for _ in range(rng.randint(1, 4))]
        for s in (1, 2, 3, 5, 8):
            idx = sx.SuffixIndex(seqs, coords=None, s=s)
            assert all(idx.recover_pos(i) == idx.SA[i] for i in range(idx.n))


def test_locate_equals_brute_scan_and_sample_invariant():
    rng = random.Random(7)
    for _ in range(120):
        seqs = ["".join(rng.choice("ACGT") for _ in range(rng.randint(0, 16)))
                for _ in range(rng.randint(1, 5))]
        if sum(len(s) for s in seqs) == 0:
            continue
        pats = set()
        for u in seqs:
            for m in range(1, 5):
                for p in range(len(u) - m + 1):
                    pats.add(u[p:p + m])
        pats |= {"Z", "ACGTACGT", "TTTTT", ""}
        ref = None
        for s in (1, 2, 4, 8):
            idx = sx.SuffixIndex(seqs, coords=None, s=s)
            res = {}
            for P in pats:
                res[P] = {(h["record_idx"], h["ungapped_pos"]) for h in idx.locate(P)}
                truth = {(di, p) for di, u in enumerate(seqs)
                         for p in range(len(u) - len(P) + 1) if P and u[p:p + len(P)] == P}
                assert res[P] == truth, (seqs, P)
            if ref is None:
                ref = res
            else:
                assert res == ref                 # SA-sample invariance


def test_forward_convention():
    # the suffix index indexes FORWARD sequences: locate('ACG') finds forward ACG (contrast the
    # De Bruijn index which queries reverse(P)).
    idx = sx.SuffixIndex(["TTACGTT"], coords=None, s=1)
    assert {h["ungapped_pos"] for h in idx.locate("ACG")} == {2}
    assert idx.locate("GCA") == []               # reverse is NOT found


# --------------------------------------------------------------------------- synthetic genomic (± strand)
def test_synthetic_both_strands_multihit(tmp_path):
    seqs = ["ACGACGAC", "ACGACGAC"]              # spA(+), spB(-)
    coords = [
        {"fasta_id": "spA", "src": "spA.chr", "start": 100, "size": 8, "strand": "+", "srcSize": 1000},
        {"fasta_id": "spB", "src": "spB.ctg", "start": 50, "size": 8, "strand": "-", "srcSize": 200},
    ]
    idx = sx.SuffixIndex(seqs, coords=coords, s=2)
    got = sx.as_tuples(idx.locate("ACG"))
    expected = {
        ("spA", "spA.chr", 100, 103, "+"), ("spA", "spA.chr", 103, 106, "+"),
        ("spB", "spB.ctg", 147, 150, "-"), ("spB", "spB.ctg", 144, 147, "-"),
    }
    assert got == expected
    # write a FASTA so the independent oracle reads the same content
    fa = os.path.join(str(tmp_path), "syn.fa")
    with open(fa, "w") as f:
        f.write(">spA\nACGACGAC\n>spB\nACGACGAC\n")
    for P in ("ACG", "ACGA", "AC", "A", "TTTT", "zzz"):
        assert sx.as_tuples(idx.locate(P)) == lor.locate_brute(fa, coords, P)


# --------------------------------------------------------------------------- real chrI blocks vs oracle
def _coords_for(fa):
    return json.load(open(fa.replace(".fa", ".coords.json")))


@pytest.mark.skipif(not YEAST_FA, reason="needs yeast FASTA")
@pytest.mark.parametrize("fa", YEAST_FA[:6])
def test_suffix_locate_vs_oracle_real_block(fa):
    a, l = 2, -1
    coords = _coords_for(fa)
    idx = sx.SuffixIndex.from_fasta(fa, a=a, l=l, coords=coords, s=4)
    seqs = [_ungap_cap(s, l) for _id, s in read_fasta(fa)[:a]]
    rng = random.Random(hash(fa) & 0xffff)
    pats = set()
    for u in seqs:
        for m in (1, 3, 6, 9):
            if len(u) >= m:
                j = rng.randint(0, len(u) - m); pats.add(u[j:j + m])
    pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(2, 7))) for _ in range(30)}
    pats |= {"ZZZ", "N", ""}
    saw = False
    for P in pats:
        got = sx.as_tuples(idx.locate(P))
        truth = lor.locate_brute(fa, coords, P, a=a, l=l)
        assert got == truth, (fa, P)
        saw = saw or bool(truth)
    assert saw


# --------------------------------------------------------------------------- real-genome cross-check
# --------------------------------------------------------------------------- P2: recognizer certification
@pytest.mark.skipif(not HAVE_REC, reason="recognizer needed")
@pytest.mark.parametrize("seqs", [
    ["AC", "AG"], ["ACG", "ACG"], ["ACGACG", "ACGTAC"],
    ["ACGTACGTAACC", "ACGTACGTAACG", "ACGTACGAAACC"],
])
def test_suffix_order_is_a_wheeler_order(seqs, tmp_path):
    sys.path.insert(0, os.path.join(ROOT, "verify"))
    from verify import suffix_wheeler_cert as cert
    idx = sx.SuffixIndex(seqs, coords=None, s=1)
    res = cert.certify(idx, str(tmp_path))
    assert res["sa_order_is_wheeler"], res                 # the SA-rank order satisfies the axioms
    if res["brute_wheeler"] is not None:                   # n<=9: brute force agrees
        assert res["brute_wheeler"]
    assert res["recognizer_verdict"] == 1                  # the recognizer independently accepts
    assert res["recognizer_order_valid"]
    assert res["recognizer_iso_to_sa_rank"]                # ... and its order IS the suffix-array rank


@pytest.mark.skipif(not (YEAST_FA and os.path.exists(GENOME)),
                    reason="needs yeast FASTA + cached sacCer3 genome")
def test_located_reference_matches_real_genome():
    from pipeline.yeast_fetch import read_genome_fasta
    chrI = read_genome_fasta(GENOME)
    assert len(chrI) == 230218
    a, l = 2, -1
    checked = 0
    for fa in YEAST_FA[:30]:
        coords = _coords_for(fa)
        ref = read_fasta(fa)[0]
        if ref[0] != "sacCer3":
            continue
        idx = sx.SuffixIndex.from_fasta(fa, a=a, l=l, coords=coords, s=4)
        u = _ungap_cap(ref[1], -1)
        if len(u) < 12:
            continue
        for m in (5, 8, 12):
            P = u[7:7 + m]
            for h in idx.locate(P):
                if h["species"] == "sacCer3":
                    assert h["strand"] == "+" and chrI[h["gstart"]:h["gend"]] == P, (P, h)
                    checked += 1
    assert checked > 0
