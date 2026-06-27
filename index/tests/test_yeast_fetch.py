"""Phase 1 gate: MAF -> per-block FASTA parsing, on an in-memory fixture (no network)."""
import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from pipeline import yeast_fetch as yf  # noqa: E402

# Minimal MAF fixture: 2 blocks. Block 1 = 3 species x 13 cols (one gap each in seqs 2,3);
# block 2 = 2 species x 5 cols. (MAF requires equal row lengths within a block.)
FIXTURE_MAF = """##maf version=1 scoring=multiz
a score=23262.0
s sacCer3.chrI  0 13 + 230218 ACGTACGTACGTA
s sacPar.chr1  10 12 + 200000 ACGT-CGTACGTA
s sacMik.chr1  20 12 + 190000 ACGTACGT-CGTA

a score=5000.0
s sacCer3.chrI 20 5 + 230218 GGCCA
s sacPar.chr1  40 4 + 200000 GGC-A
"""


def _blocks():
    return list(yf.iter_blocks(io.StringIO(FIXTURE_MAF)))


def test_block_count_and_dims():
    blocks = _blocks()
    assert len(blocks) == 2
    b1 = yf.block_records(blocks[0])
    b2 = yf.block_records(blocks[1])
    assert len(b1) == 3 and len(b1[0][1]) == 13
    assert len(b2) == 2 and len(b2[0][1]) == 5


def test_species_ids_and_uniqueness():
    b1 = yf.block_records(_blocks()[0])
    ids = [rid for rid, _ in b1]
    assert ids == ["sacCer3", "sacPar", "sacMik"]
    assert len(set(ids)) == len(ids)  # unique within block


def test_rows_roundtrip_gapped_sequence():
    # The FASTA row must equal the MAF gapped row (uppercased), char-for-char.
    b1 = yf.block_records(_blocks()[0])
    assert b1[0] == ("sacCer3", "ACGTACGTACGTA")
    assert b1[1] == ("sacPar", "ACGT-CGTACGTA")
    assert b1[2] == ("sacMik", "ACGTACGT-CGTA")


def test_block_ok_filters():
    b1 = yf.block_records(_blocks()[0])
    assert yf.block_ok(b1, min_species=2, min_cols=8, max_cols=2000)
    assert not yf.block_ok(b1, min_species=4, min_cols=8, max_cols=2000)  # too few species
    assert not yf.block_ok(b1, min_species=2, min_cols=20, max_cols=2000)  # too narrow vs min_cols
    # a block with a non-DNA residue (N) is rejected
    bad = [("a", "ACGTN"), ("b", "ACGTA")]
    assert not yf.block_ok(bad, min_species=2, min_cols=4, max_cols=2000)


def test_write_blocks_to_disk(tmp_path):
    man = yf.write_blocks(io.StringIO(FIXTURE_MAF), str(tmp_path), chrom="chrI",
                          min_species=2, min_cols=4, max_cols=2000)
    assert len(man) == 2
    # files exist and contain the expected FASTA content for block 1
    p0 = man[0]["path"]
    assert os.path.exists(p0)
    text = open(p0).read()
    assert ">sacCer3\nACGTACGTACGTA\n" in text
    assert ">sacPar\nACGT-CGTACGTA\n" in text
    assert man[0]["n_species"] == 3 and man[0]["cols"] == 13
    assert man[1]["n_species"] == 2 and man[1]["cols"] == 5


def test_block_coords_matches_maf_annotations():
    # block 1: sacCer3 @0/13/+, sacPar @10/12/+, sacMik @20/12/+ (srcSizes 230218/200000/190000)
    c1 = yf.block_coords(_blocks()[0])
    assert [c["fasta_id"] for c in c1] == ["sacCer3", "sacPar", "sacMik"]
    assert [c["src"] for c in c1] == ["sacCer3.chrI", "sacPar.chr1", "sacMik.chr1"]
    assert (c1[0]["start"], c1[0]["size"], c1[0]["strand"], c1[0]["srcSize"]) == (0, 13, "+", 230218)
    assert (c1[1]["start"], c1[1]["size"], c1[1]["strand"]) == (10, 12, "+")
    assert (c1[2]["start"], c1[2]["size"], c1[2]["strand"]) == (20, 12, "+")
    c2 = yf.block_coords(_blocks()[1])
    assert (c2[0]["start"], c2[0]["size"]) == (20, 5) and (c2[1]["start"], c2[1]["size"]) == (40, 4)


def test_coords_sidecar_written_and_joins_by_record_index(tmp_path):
    import json
    man = yf.write_blocks(io.StringIO(FIXTURE_MAF), str(tmp_path), chrom="chrI",
                          min_species=2, min_cols=4, max_cols=2000)
    side = os.path.join(str(tmp_path), man[0]["stem"] + ".coords.json")
    assert os.path.exists(side)
    coords = json.load(open(side))
    recs = yf.block_records(_blocks()[0])
    # one coord entry per FASTA record, same order/ids -> joinable by record index
    assert len(coords) == len(recs)
    assert [c["fasta_id"] for c in coords] == [rid for rid, _ in recs]
    # uncapped: ungapped length of each FASTA row == the MAF 'size' field
    for c, (_rid, seq) in zip(coords, recs):
        assert len(seq.replace("-", "")) == c["size"]
    # reference start in the filename matches coords[0].start
    assert man[0]["stem"].split("_s")[-1] == str(coords[0]["start"])
