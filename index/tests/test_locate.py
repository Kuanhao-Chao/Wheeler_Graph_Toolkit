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
