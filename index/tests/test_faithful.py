"""Phase 2 gate: De Bruijn construction faithfully encodes the MSA.

Hard gates run on tiny/toy alignments (no external data). A conditional block also checks several real
yeast chrI blocks if Phase-1 data is present.
"""
import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import debruijn, faithful  # noqa: E402

YEAST_FA = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")


def _write(tmp_path, name, seqs):
    p = os.path.join(str(tmp_path), name)
    with open(p, "w") as fh:
        for i, s in enumerate(seqs):
            fh.write(f">s{i}\n{s}\n")
    return p


def test_reference_matches_observed_generator_tiny():
    # 'ACGTACG', k=3 (node length 2): the generator emitted exactly this graph (verified by hand).
    g = debruijn.build(["ACGTACG"], 3, seqLen=100, alnNum=1)
    assert g["source"] == 0  # '$' is BFS-root id 0
    assert g["edges"] == {(0, 1, "G"), (1, 2, "C"), (2, 3, "A"),
                          (3, 4, "T"), (4, 5, "G"), (5, 2, "C")}


def test_reference_equals_generator_single_seq(tmp_path):
    fa = _write(tmp_path, "one.fa", ["ACGTACG"])
    r = faithful.check_faithful(fa, k=3, l=100, a=1)
    assert r["edges_equal"], r
    assert r["decode_ok"], r
    assert r["ok"]


def test_reference_equals_generator_multi_seq(tmp_path):
    fa = _write(tmp_path, "multi.fa", ["ACGTACGT", "ACGTTCGT", "ACGAACGT"])
    r = faithful.check_faithful(fa, k=3, l=100, a=3)
    assert r["edges_equal"] and r["decode_ok"], r


def test_faithful_with_gaps_and_cap(tmp_path):
    # gaps must be stripped; seqLen cap must be honored (so the graph matches the reference exactly).
    fa = _write(tmp_path, "gap.fa", ["AC--GTAC-G", "ACG-GTACG-"])
    r = faithful.check_faithful(fa, k=4, l=6, a=2)
    assert r["edges_equal"] and r["decode_ok"], r


def test_decode_rejects_absent_pattern(tmp_path):
    # a string that is NOT the reverse of any encoded sequence is not spellable from the source
    fa = _write(tmp_path, "dec.fa", ["ACGTAC"])
    g = debruijn.build(["ACGTAC"], 3, seqLen=100, alnNum=1)
    assert faithful.spellable(g["edges"], g["source"], "CATGCA")      # reverse('ACGTAC') -> spellable
    assert not faithful.spellable(g["edges"], g["source"], "TTTTTT")  # absent


YEAST_BLOCKS = sorted(glob.glob(os.path.join(YEAST_FA, "*.fa")))[:8]


@pytest.mark.skipif(not YEAST_BLOCKS, reason="Phase-1 yeast FASTA not present (run pipeline/yeast_fetch.py)")
@pytest.mark.parametrize("fa", YEAST_BLOCKS)
def test_faithful_on_real_yeast_blocks(fa):
    # small cap so the graph stays small and the check is fast; both species, k=4.
    r = faithful.check_faithful(fa, k=4, l=40, a=2)
    assert r["edges_equal"], (fa, r)
    assert r["decode_ok"], (fa, r)
