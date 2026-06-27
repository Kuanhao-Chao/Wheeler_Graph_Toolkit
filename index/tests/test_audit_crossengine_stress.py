"""AUDITOR H -- cross-engine determinism stress for the tagged suffix index.

Catch-all: over random multi-document DNA and over real chrI yeast blocks (a in {2,4}) with >=500
generated patterns (present real substrings of varied length + random DNA + off-alphabet), the
occurrence set {(record_idx, ungapped_pos)} must be IDENTICAL across:
  * index.suffix_index.SuffixIndex sample='rate', s=1
  * index.suffix_index.SuffixIndex sample='rate', s=4
  * index.suffix_index.SuffixIndex sample='runs'
  * index.dawg.DAWG
  * a transparent brute substring scan (the independent ground truth written here).
And the genomic occurrence set index.suffix_index.as_tuples(locate(P)) must equal
index.locate_oracle.locate_brute(...). Any single disagreement is a bug with a minimal witness.

Run: ~/miniconda3/envs/myenv/bin/python -m pytest test_audit_crossengine_stress.py -q
"""
import glob
import json
import os
import random
import sys

import pytest

ROOT = "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph"
sys.path.insert(0, ROOT)

from index import suffix_index as sx          # noqa: E402
from index import locate_oracle as lor        # noqa: E402
from index.dawg import DAWG                    # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402

YEAST_FA = sorted(glob.glob(os.path.join(
    ROOT, "data", "multiseq_alignment", "yeast", "fasta", "chrI_*.fa")))
HAVE_YEAST = len(YEAST_FA) > 0


# --------------------------------------------------------------------------- helpers
def brute_scan(seqs, P):
    """Independent ground truth: set of (record_idx, ungapped_pos) where P occurs (plain scan)."""
    P = P.upper()
    out = set()
    m = len(P)
    if m == 0:
        return out
    for i, s in enumerate(seqs):
        for pos in range(len(s) - m + 1):
            if s[pos:pos + m] == P:
                out.add((i, pos))
    return out


def core_set(hits):
    return {(h["record_idx"], h["ungapped_pos"]) for h in hits}


def build_core_engines(seqs):
    return {
        "rate_s1": sx.SuffixIndex(seqs, coords=None, s=1, sample="rate"),
        "rate_s4": sx.SuffixIndex(seqs, coords=None, s=4, sample="rate"),
        "runs":    sx.SuffixIndex(seqs, coords=None, s=4, sample="runs"),
        "dawg":    DAWG(seqs, coords=None),
    }


def gen_patterns(seqs, rng, n):
    """Present real substrings of varied length + random DNA + off-alphabet/empty."""
    pats = []
    text = [s for s in seqs if s]
    maxlen = max((len(s) for s in text), default=1)
    for _ in range(n):
        r = rng.random()
        if text and r < 0.55:
            s = rng.choice(text)
            L = rng.randint(1, min(len(s), 20))
            st = rng.randint(0, len(s) - L)
            pats.append(s[st:st + L])
        elif r < 0.85:
            L = rng.randint(1, max(2, min(12, maxlen)))
            pats.append("".join(rng.choice("ACGT") for _ in range(L)))
        else:
            pats.append(rng.choice(["N", "ACGTN", "ACNGT", "X",
                                    rng.choice("ACGT") * rng.randint(1, 5)]))
    return pats


# --------------------------------------------------------------------------- random property stress
def test_crossengine_core_random():
    """All four engines agree with the brute substring scan on {(record_idx, ungapped_pos)}."""
    rng = random.Random(12345)
    queries = 0
    for _ in range(300):
        ndocs = rng.randint(1, 5)
        seqs = []
        for _ in range(ndocs):
            L = rng.randint(0, 18)
            mode = rng.random()
            if mode < 0.3:                    # alphabet skew
                seqs.append("".join(rng.choice("AC") for _ in range(L)))
            elif mode < 0.5:                  # homopolymer
                seqs.append(rng.choice("ACGT") * L)
            else:
                seqs.append("".join(rng.choice("ACGT") for _ in range(L)))
        if sum(len(s) for s in seqs) == 0:
            continue
        eng = build_core_engines(seqs)
        for P in gen_patterns(seqs, rng, 30):
            queries += 1
            truth = brute_scan(seqs, P)
            for name, e in eng.items():
                got = core_set(e.locate(P))
                assert got == truth, (
                    f"{name} disagreement: seqs={seqs} P={P!r} expected={truth} got={got}")
                # count agrees with the locate cardinality for non-empty patterns
                if P != "":
                    assert e.count(P) == len(truth), (
                        f"{name} count: seqs={seqs} P={P!r} "
                        f"expected={len(truth)} got={e.count(P)}")
    assert queries >= 500


def test_offalpha_and_absent_empty_everywhere():
    """Off-alphabet / absent patterns -> empty occurrence set on every engine."""
    seqs = ["ACGTACGT", "ACGTT", "GGGG"]
    eng = build_core_engines(seqs)
    for P in ["N", "X", "ACGTN", "n", "ACNGT", "TTTTTTTTTTTT", "CCCCC"]:
        truth = brute_scan(seqs, P)
        for name, e in eng.items():
            assert core_set(e.locate(P)) == truth, f"{name} P={P!r}"


def test_empty_pattern_locate_is_empty_on_all_engines():
    """locate('') is [] on every engine (the deliverable contract holds even though count differs)."""
    seqs = ["ACGT", "AC"]
    eng = build_core_engines(seqs)
    for name, e in eng.items():
        assert e.locate("") == [], f"{name} locate('') should be []"


def test_empty_pattern_count_consistent_across_engines():
    # Audit finding, FIXED: DAWG.count("") now returns 0, matching SuffixIndex.count("").
    seqs = ["ACGT", "AC"]
    sxi = sx.SuffixIndex(seqs)
    dawg = DAWG(seqs)
    assert sxi.count("") == dawg.count("") == 0


# --------------------------------------------------------------------------- real yeast stress
@pytest.mark.skipif(not HAVE_YEAST, reason="yeast chrI fasta blocks not present")
def test_crossengine_real_yeast_core_and_genomic():
    """Real chrI blocks, a in {2,4}, >=500 patterns: core sets agree across all engines AND
    as_tuples(locate(P)) == locate_brute(...) genomic ground truth."""
    rng = random.Random(999)
    queries = 0
    blocks_used = 0
    for fa in YEAST_FA[:120]:
        cj = fa.replace(".fa", ".coords.json")
        if not os.path.exists(cj):
            continue
        coords = json.load(open(cj))
        recs = read_fasta(fa)
        for a in (2, 4):
            if len(recs) < a:
                continue
            seqs = [_ungap_cap(s, -1) for _id, s in recs[:a]]
            if sum(len(s) for s in seqs) == 0:
                continue
            blocks_used += 1
            core = build_core_engines(seqs)
            gen_engines = {
                "rate_s1": sx.SuffixIndex(seqs, coords=coords, s=1, sample="rate"),
                "rate_s4": sx.SuffixIndex(seqs, coords=coords, s=4, sample="rate"),
                "runs":    sx.SuffixIndex(seqs, coords=coords, s=4, sample="runs"),
                "dawg":    DAWG(seqs, coords=coords),
            }
            for P in gen_patterns(seqs, rng, 8):
                queries += 1
                truth = brute_scan(seqs, P)
                for name, e in core.items():
                    assert core_set(e.locate(P)) == truth, (
                        f"core {name} fa={os.path.basename(fa)} a={a} P={P!r}")
                gtruth = lor.locate_brute(fa, coords, P, a=a, l=-1)
                for name, e in gen_engines.items():
                    got = sx.as_tuples(e.locate(P))
                    assert got == gtruth, (
                        f"genomic {name} fa={os.path.basename(fa)} a={a} P={P!r} "
                        f"expected={gtruth} got={got}")
        if queries >= 700:
            break
    assert blocks_used > 0
    assert queries >= 500
