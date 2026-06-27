"""AUDITOR C — genomic coordinate transform / strand / alphabet boundaries.

Adversarial audit of index.locate.transform as exercised through
index.suffix_index.SuffixIndex.locate(P) when coords are supplied, plus the
off-alphabet / case-folding handling on both the query and the input rows.

Every assertion is gated against an INDEPENDENT ground truth:
  * index.locate_oracle.locate_brute  (its OWN inlined ungap/cap + transform),
  * a transparent brute substring scan reimplemented here (brute_substr_set),
  * hand-computed exact tuples for the '-' strand (catch a transform off-by-one),
  * the real sacCer3 chrI genome for the '+' transform (when the data is present).

Run: ~/miniconda3/envs/myenv/bin/python -m pytest test_audit_locate_strand.py -q
"""
import glob
import json
import os
import random
import sys

import pytest

sys.path.insert(0, "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph")
ROOT = "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph"

from index.suffix_index import SuffixIndex, as_tuples          # noqa: E402
from index.faithful import _ungap_cap, read_fasta              # noqa: E402
from index.locate import transform                             # noqa: E402
from index import locate_oracle                                # noqa: E402

YEAST_FA_DIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
GENOME = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "genome", "chrI.fa")
HAS_YEAST = os.path.isdir(YEAST_FA_DIR) and bool(glob.glob(os.path.join(YEAST_FA_DIR, "chrI_*.coords.json")))
HAS_GENOME = os.path.isfile(GENOME)


# --------------------------------------------------------------------------- helpers
def write_fasta(path, rows):
    with open(path, "w") as fh:
        for i, r in enumerate(rows):
            fh.write(">row%d\n%s\n" % (i, r))


def brute_substr_set(rows, coords, P):
    """Fully independent brute reimplementation of locate (NOT the named oracle):
    upper-case query (mirrors the documented contract), scan every ungapped row,
    apply the MAF +/- coordinate math inline."""
    P = P.upper()
    out = set()
    m = len(P)
    if m == 0:
        return out
    for i, r in enumerate(rows):
        u = _ungap_cap(r, -1)
        c = coords[i]
        for pos in range(len(u) - m + 1):
            if u[pos:pos + m] == P:
                st, strand, srcSize = c["start"], c["strand"], c["srcSize"]
                if strand == "-":
                    out.add((c["fasta_id"], c["src"], srcSize - (st + pos + m), srcSize - (st + pos), "-"))
                else:
                    out.add((c["fasta_id"], c["src"], st + pos, st + pos + m, "+"))
    return out


def make_coords(rows, rng):
    coords = []
    for i, r in enumerate(rows):
        u = _ungap_cap(r, -1)
        strand = rng.choice(["+", "-"])
        start = rng.randint(0, 50)
        srcSize = start + len(u) + rng.randint(0, 100)   # sane: keeps + coords >= 0
        coords.append({"fasta_id": "sp%d" % (i % 3), "src": "src%d" % i, "start": start,
                       "size": len(u), "strand": strand, "srcSize": srcSize})
    return coords


def gather_patterns(rows, rng, maxlen=5):
    pats = set()
    for r in rows:
        u = _ungap_cap(r, -1)
        for L in range(1, min(maxlen, len(u)) + 1):
            for s in range(0, len(u) - L + 1):
                pats.add(u[s:s + L])
    for _ in range(8):
        L = rng.randint(1, 5)
        pats.add("".join(rng.choice("ACGT") for _ in range(L)))
    return list(pats)


# --------------------------------------------------------------------------- property-based
def test_property_locate_matches_two_independent_grounds(tmp_path):
    """Random multi-document DNA (varied #docs, lengths, alphabet skew, homopolymers, gaps),
    both sample modes, several SA rates: index == locate_brute oracle == transparent brute."""
    ncases = 0
    for trial in range(120):
        rng = random.Random(trial)
        ndocs = rng.randint(1, 5)
        rows = []
        for _ in range(ndocs):
            L = rng.randint(0, 14)
            if rng.random() < 0.3:
                rows.append(rng.choice("ACGT") * L)                      # homopolymer
            else:
                alpha = rng.choice(["ACGT", "AC", "AT", "ACG", "A"])     # alphabet skew
                row = "".join(rng.choice(alpha) for _ in range(L))
                if rng.random() < 0.3 and L > 0:                         # interleave gaps
                    row = "-".join(row[i:i + 1] for i in range(len(row)))
                rows.append(row)
        fa = str(tmp_path / ("t%d.fa" % trial))
        write_fasta(fa, rows)
        coords = make_coords(rows, rng)
        seqs = [_ungap_cap(r, -1) for r in rows]
        pats = gather_patterns(rows, rng)
        for sample in ("rate", "runs"):
            for s in (1, 2, 8):
                idx = SuffixIndex(seqs, coords=coords, s=s, sample=sample)
                for P in pats:
                    got = as_tuples(idx.locate(P))
                    exp_oracle = locate_oracle.locate_brute(fa, coords, P, l=None)
                    exp_brute = brute_substr_set(rows, coords, P)
                    assert got == exp_oracle, (sample, s, P, rows, coords)
                    assert got == exp_brute, (sample, s, P, rows, coords)
                    ncases += 1
    assert ncases > 5000


# --------------------------------------------------------------------------- boundary block
def _boundary_block():
    # doc0 '+' start=0 (start boundary); doc1 '-' small srcSize (reverse edges);
    # doc2 '+' homopolymer. Hand-computable '-' tuples below.
    rows = ["ACGTACGT", "ACGT", "GGGG"]
    coords = [
        {"fasta_id": "spA", "src": "cA", "start": 0, "size": 8, "strand": "+", "srcSize": 100},
        {"fasta_id": "spB", "src": "cB", "start": 2, "size": 4, "strand": "-", "srcSize": 10},
        {"fasta_id": "spC", "src": "cC", "start": 5, "size": 4, "strand": "+", "srcSize": 50},
    ]
    return rows, coords


def test_transform_minus_strand_handcomputed():
    """Hand-derived '-' strand tuples for doc1 ACGT, start=2, srcSize=10:
       P=ACGT pos0 m4 -> (10-(2+0+4), 10-(2+0)) = (4, 8)
       P=CG   pos1 m2 -> (10-(2+1+2), 10-(2+1)) = (5, 7)
       P=T    pos3 m1 -> (10-(2+3+1), 10-(2+3)) = (4, 5)   [pos = len-m, doc end]"""
    _rows, coords = _boundary_block()
    c = coords[1]
    assert transform(c, 0, 4) == (4, 8, "-")
    assert transform(c, 1, 2) == (5, 7, "-")
    assert transform(c, 3, 1) == (4, 5, "-")


@pytest.mark.parametrize("sample", ["rate", "runs"])
def test_boundary_tuples_exact_and_oracle(tmp_path, sample):
    rows, coords = _boundary_block()
    fa = str(tmp_path / "bound.fa")
    write_fasta(fa, rows)
    seqs = [_ungap_cap(r, -1) for r in rows]
    idx = SuffixIndex(seqs, coords=coords, s=2, sample=sample)

    acgt = as_tuples(idx.locate("ACGT"))
    assert acgt == locate_oracle.locate_brute(fa, coords, "ACGT", l=None)
    # multi-hit: doc0 pos0 (+,start=0 boundary) and pos4 (+,doc end) plus doc1 (- strand)
    assert ("spA", "cA", 0, 4, "+") in acgt          # pos=0, start=0
    assert ("spA", "cA", 4, 8, "+") in acgt          # pos=len-m (doc end)
    assert ("spB", "cB", 4, 8, "-") in acgt          # hand-computed - tuple

    assert ("spB", "cB", 5, 7, "-") in as_tuples(idx.locate("CG"))
    assert ("spB", "cB", 4, 5, "-") in as_tuples(idx.locate("T"))     # - strand at doc end


# --------------------------------------------------------------------------- off-alphabet
@pytest.mark.parametrize("sample", ["rate", "runs"])
@pytest.mark.parametrize("P", ["N", "n", "Z", "z", "NN", "ACN", "AXT", " ", "*", ""])
def test_off_alphabet_empty(tmp_path, sample, P):
    """Genuinely off-alphabet (or empty) queries -> no hits, count 0. 'n' upper-cases to 'N'
    which is still off-alphabet, so it stays empty."""
    rows, coords = _boundary_block()
    seqs = [_ungap_cap(r, -1) for r in rows]
    idx = SuffixIndex(seqs, coords=coords, s=2, sample=sample)
    assert idx.locate(P) == []
    assert idx.count(P) == 0


@pytest.mark.parametrize("sample", ["rate", "runs"])
@pytest.mark.parametrize("P", ["acg", "acgt", "gggg", "Ac", "cGt"])
def test_lowercase_query_is_case_folded_like_oracle(tmp_path, sample, P):
    """NOTE (documented non-bug): SuffixIndex._encode does P.upper(), and locate_oracle.locate_brute
    also upper-cases P. So a lowercase in-alphabet query is NOT off-alphabet -- it matches its
    upper-case form, and index == oracle. (The naive reading 'lowercase -> []' is only true when the
    upper-cased pattern is absent; the ground-truth-anchored invariant is index == oracle.)"""
    rows, coords = _boundary_block()
    fa = str(tmp_path / "lc.fa")
    write_fasta(fa, rows)
    seqs = [_ungap_cap(r, -1) for r in rows]
    idx = SuffixIndex(seqs, coords=coords, s=2, sample=sample)
    assert as_tuples(idx.locate(P)) == locate_oracle.locate_brute(fa, coords, P, l=None)


# --------------------------------------------------------------------------- mixed-case input rows
def test_mixedcase_rows_are_uppercased_via_from_fasta(tmp_path):
    """Mixed-case FASTA rows must be upper-cased on ingest (read_fasta/_ungap_cap). The index built
    from such a file must equal the oracle (which independently upper-cases the same rows)."""
    rows = ["acgtACGT", "AcGtAcGt", "GgGg"]
    coords = [
        {"fasta_id": "spA", "src": "cA", "start": 0, "size": 8, "strand": "+", "srcSize": 100},
        {"fasta_id": "spB", "src": "cB", "start": 3, "size": 8, "strand": "-", "srcSize": 40},
        {"fasta_id": "spC", "src": "cC", "start": 1, "size": 4, "strand": "+", "srcSize": 50},
    ]
    fa = str(tmp_path / "mixed.fa")
    write_fasta(fa, rows)
    idx = SuffixIndex.from_fasta(fa, coords=coords)
    for P in ["ACGT", "acgt", "GG", "Ac", "gGgG"]:
        assert as_tuples(idx.locate(P)) == locate_oracle.locate_brute(fa, coords, P, l=None)


def test_constructor_requires_uppercase_acgt_rows():
    """Input contract: the raw constructor does NOT case-fold rows (build_text indexes ACGT only);
    lowercase / non-ACGT rows raise KeyError. Use from_fasta (which _ungap_cap's) for case folding."""
    with pytest.raises(KeyError):
        SuffixIndex(["acgt"], coords=None)
    with pytest.raises(KeyError):
        SuffixIndex(["ACGN"], coords=None)


# --------------------------------------------------------------------------- real yeast data
def _yeast_blocks(limit):
    out = []
    for cj in sorted(glob.glob(os.path.join(YEAST_FA_DIR, "chrI_*.coords.json")))[:limit]:
        out.append((cj.replace(".coords.json", ".fa"), cj))
    return out


@pytest.mark.skipif(not HAS_YEAST, reason="yeast block FASTA/coords not present")
def test_real_yeast_blocks_match_oracle():
    """Real MAF blocks (including '-' strand records) -> index == locate_brute oracle."""
    rng = random.Random(0)
    n_blocks = 0
    for fa, cj in _yeast_blocks(6):
        coords = json.load(open(cj))
        idx = SuffixIndex.from_fasta(fa, coords=coords, s=4)
        seqs = [_ungap_cap(s, -1) for _id, s in read_fasta(fa)]
        pats = set()
        for u in seqs:
            for _ in range(20):
                if len(u) < 3:
                    continue
                L = rng.randint(1, 8)
                st = rng.randint(0, len(u) - L)
                pats.add(u[st:st + L])
        for P in pats:
            assert as_tuples(idx.locate(P)) == locate_oracle.locate_brute(fa, coords, P, l=None)
        n_blocks += 1
    assert n_blocks > 0


@pytest.mark.skipif(not (HAS_YEAST and HAS_GENOME), reason="yeast blocks + sacCer3 genome required")
def test_plus_transform_against_real_genome():
    """Strongest independent anchor for the '+' transform: for sacCer3 (always '+') the index's
    (gstart, gend) on a sub-pattern must slice exactly that pattern out of the real chrI sequence."""
    genome = "".join(l.strip() for l in open(GENOME) if not l.startswith(">")).upper()
    checked = 0
    for fa, cj in _yeast_blocks(8):
        coords = json.load(open(cj))
        recs = read_fasta(fa)
        idx = SuffixIndex.from_fasta(fa, coords=coords)
        for i, r in enumerate(coords):
            if r["fasta_id"] != "sacCer3":
                continue
            seq = _ungap_cap(recs[i][1], -1)
            if len(seq) < 8:
                continue
            assert genome[r["start"]:r["start"] + len(seq)] == seq      # whole-record anchor
            P = seq[2:7]
            for h in idx.locate(P):
                if h["record_idx"] == i and h["strand"] == "+":
                    assert genome[h["gstart"]:h["gend"]] == P           # sub-pattern transform anchor
                    checked += 1
                    break
        if checked >= 3:
            break
    assert checked > 0
