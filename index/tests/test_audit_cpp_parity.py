"""AUDITOR G -- C++ wg_suffix parity incl. block-rank (BLOCK=64) boundaries.

Adversarial parity gate for index/cpp/wg_suffix.cpp against:
  * the Python SuffixIndex (index/suffix_index.py, sample='rate'), AND
  * an independent brute substring scan written here + index/locate_oracle.locate_brute
    (the genomic ground truth, with its own inlined ungap/cap + transform).

Focus: the block-rank prefix table (rankpre, BLOCK=64) and the rate-sampled SA.
We construct multi-string texts whose |T| (= sum(len(doc)) + a, one distinct separator
per doc) is EXACTLY 64, 128, 192 so backward_search's first rnk() call lands on a block
boundary (i = n in {64,128,192}); we sweep SA sample rates s in {1, n, n+5}; and we check
--info (n, r, n_samples, sigma, a) parity.

NOTE (documented non-bug): the C++ port implements ONLY sample='rate' (no 'runs'/phi mode).
Correctness of 'runs' is transitive elsewhere (Py runs == Py rate == C++ rate == oracle); the
absence of a 'runs' mode in C++ is a feature gap, not a defect, so this file never asks C++
for it.

Run: ~/miniconda3/envs/myenv/bin/python -m pytest test_audit_cpp_parity.py -q
"""
import glob
import json
import os
import random
import subprocess
import sys

import pytest

sys.path.insert(0, "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph")
from index import suffix_index as sx          # noqa: E402
from index import locate_oracle as lor        # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402

ROOT = "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph"
CPP_DIR = os.path.join(ROOT, "index", "cpp")
CPP_BIN = os.path.join(CPP_DIR, "wg_suffix")
YEAST = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast",
                                      "fasta", "chrI_*.fa")))
DNA = "ACGT"


# --------------------------------------------------------------------------- build / run helpers
@pytest.fixture(scope="session")
def cpp_bin():
    r = subprocess.run(["make", "-s", "wg_suffix"], cwd=CPP_DIR,
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(CPP_BIN):
        pytest.skip(f"C++ wg_suffix build failed: {r.stderr[:300]}")
    return CPP_BIN


def _write_fa(path, seqs):
    with open(path, "w") as fh:
        for i, s in enumerate(seqs):
            fh.write(f">r{i}\n{s}\n")


def _cpp_locate(binary, fa, a, l, s, pat, coords_path=None):
    cmd = [binary, fa, "--a", str(a), "--l", str(l), "--s", str(s)]
    if coords_path:
        cmd += ["--coords", coords_path]
    cmd += ["--locate", pat]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = set()
    for line in r.stdout.splitlines():
        if line.startswith("# ") or not line.strip():
            continue
        if coords_path:
            t = line.split("\t")
            out.add((t[0], t[1], int(t[2]), int(t[3]), t[4]))
        else:
            x, y = line.split()
            out.add((int(x), int(y)))
    return out


def _cpp_queries(binary, fa, a, l, s, pats, coords_path=None):
    """Parse grouped --queries output -> {pattern: set(...)}."""
    qf = os.path.join(os.path.dirname(fa), "_audit_q.txt")
    with open(qf, "w") as fh:
        for p in pats:
            if p:
                fh.write(p + "\n")
    cmd = [binary, fa, "--a", str(a), "--l", str(l), "--s", str(s)]
    if coords_path:
        cmd += ["--coords", coords_path]
    cmd += ["--queries", qf]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out, cur = {}, None
    for line in r.stdout.splitlines():
        if line.startswith("# "):
            cur = line[2:]
            out[cur] = set()
        elif line.strip():
            if coords_path:
                t = line.split("\t")
                out[cur].add((t[0], t[1], int(t[2]), int(t[3]), t[4]))
            else:
                x, y = line.split()
                out[cur].add((int(x), int(y)))
    return out


def _cpp_info(binary, fa, a, l, s):
    r = subprocess.run([binary, fa, "--a", str(a), "--l", str(l), "--s", str(s), "--info"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return {k: v for k, v in (tok.split("=") for tok in r.stdout.split() if "=" in tok)}


# --------------------------------------------------------------------------- ground truth
def _py_core(seqs, s, pat):
    idx = sx.SuffixIndex(seqs, coords=None, s=s)
    return {(h["record_idx"], h["ungapped_pos"]) for h in idx.locate(pat)}


def _brute_core(seqs, l, pat):
    """Independent brute substring scan over ungapped/capped rows -> {(record_idx, pos)}."""
    pat = pat.upper()
    m = len(pat)
    out = set()
    if m == 0:
        return out
    for i, s in enumerate(seqs):
        u = _ungap_cap(s, l)
        for p in range(len(u) - m + 1):
            if u[p:p + m] == pat:
                out.add((i, p))
    return out


def _rand_seq(rng, n, weights=None):
    return "".join(rng.choices(DNA, weights=weights, k=n)) if n > 0 else ""


# --------------------------------------------------------------------------- |T| = 64/128/192 gate
def _seqs_total(rng, total, a):
    """a rows (no gaps) with sum(len)+a == total  (each row contributes one separator)."""
    body = total - a
    lens = [body // a] * a
    for i in range(body % a):
        lens[i] += 1
    return [_rand_seq(rng, L) for L in lens]


@pytest.mark.skipif(not os.path.exists(CPP_DIR), reason="no cpp dir")
@pytest.mark.parametrize("total", [64, 128, 192])
def test_block_boundary_locate_and_info(cpp_bin, tmp_path, total):
    """|T| exactly on the BLOCK=64 boundary: locate + --info parity, s in {1, n, n+5}."""
    rng = random.Random(1000 + total)
    for a in (1, 2, 3, 4):
        if total - a < a:
            continue
        seqs = _seqs_total(rng, total, a)
        assert sum(len(s) for s in seqs) + a == total
        idx0 = sx.SuffixIndex(seqs, s=8)
        assert idx0.n == total                       # first rnk() lands at i == total (block edge)
        n = idx0.n

        pats = set()
        for s in seqs:
            for L in (1, 2, 3, 4):
                for p in range(len(s) - L + 1):
                    pats.add(s[p:p + L])
        for _ in range(30):
            pats.add(_rand_seq(rng, rng.randint(1, 5)))
        pats |= {"N", "ACGTN"}

        for s_samp in (1, n, n + 5):
            fa = os.path.join(str(tmp_path), f"t{total}_a{a}_s{s_samp}.fa")
            _write_fa(fa, seqs)

            info = _cpp_info(cpp_bin, fa, a, -1, s_samp)
            pidx = sx.SuffixIndex(seqs, s=s_samp)
            assert int(info["n"]) == pidx.n
            assert int(info["r"]) == pidx.r
            assert int(info["n_samples"]) == pidx.n_samples
            assert int(info["sigma"]) == pidx.sigma
            assert int(info["a"]) == pidx.a

            for pat in pats:
                cpp = _cpp_locate(cpp_bin, fa, a, -1, s_samp, pat)
                py = _py_core(seqs, s_samp, pat)
                brute = _brute_core(seqs, -1, pat)
                assert cpp == py == brute, (total, a, s_samp, pat, cpp, py, brute)


# --------------------------------------------------------------------------- multi-block (n > 192)
@pytest.mark.skipif(not os.path.exists(CPP_DIR), reason="no cpp dir")
def test_multiblock_and_sample_extremes(cpp_bin, tmp_path):
    """n spanning many BLOCK=64 blocks (and n not a multiple of 64); s in {1, 8, n, n+5}."""
    rng = random.Random(42)
    for trial in range(12):
        a = rng.randint(2, 4)
        seqs = [_rand_seq(rng, rng.randint(60, 120)) for _ in range(a)]
        fa = os.path.join(str(tmp_path), f"mb{trial}.fa")
        _write_fa(fa, seqs)
        n = sx.SuffixIndex(seqs, s=8).n
        pats = set()
        for s in seqs:
            for _ in range(12):
                L = rng.randint(1, 8)
                p = rng.randint(0, len(s) - L)
                pats.add(s[p:p + L])
        for s_samp in (1, 8, n, n + 5):
            grouped = _cpp_queries(cpp_bin, fa, a, -1, s_samp, list(pats))
            for pat in pats:
                cpp = grouped.get(pat, set())
                py = _py_core(seqs, s_samp, pat)
                brute = _brute_core(seqs, -1, pat)
                assert cpp == py == brute, (trial, s_samp, pat, cpp, py, brute)


# --------------------------------------------------------------------------- property-based fuzz
@pytest.mark.skipif(not os.path.exists(CPP_DIR), reason="no cpp dir")
def test_property_random_multidoc(cpp_bin, tmp_path):
    """Random multi-doc DNA: vary #docs, lengths, skew, homopolymers, gaps, caps."""
    rng = random.Random(2024)
    for trial in range(120):
        a = rng.randint(1, 5)
        style = rng.choice(["uniform", "skew", "homo", "gappy", "short"])
        seqs = []
        for _ in range(a):
            if style == "homo":
                s = "".join(rng.choice(DNA) * rng.randint(1, 8) for _ in range(rng.randint(1, 6)))
            elif style == "skew":
                s = _rand_seq(rng, rng.randint(1, 30), weights=[10, 1, 1, 1])
            elif style == "gappy":
                base = _rand_seq(rng, rng.randint(5, 30))
                s = "".join(ch + ("-" * rng.randint(0, 2) if rng.random() < 0.3 else "")
                            for ch in base)
            elif style == "short":
                s = _rand_seq(rng, rng.randint(1, 3))
            else:
                s = _rand_seq(rng, rng.randint(1, 30))
            seqs.append(s)
        l = rng.choice([-1, -1, 5, 10])
        s_samp = rng.choice([1, 2, 4, 8])
        fa = os.path.join(str(tmp_path), f"p{trial}.fa")
        _write_fa(fa, seqs)

        uca = [_ungap_cap(s, l) for s in seqs]
        pats = set()
        for u in uca:
            for _ in range(6):
                if not u:
                    continue
                L = rng.randint(1, min(6, len(u)))
                p = rng.randint(0, len(u) - L)
                pats.add(u[p:p + L])
        for _ in range(6):
            pats.add(_rand_seq(rng, rng.randint(1, 5)))
        pats |= {"N"}

        # empty pattern: C++ must emit no hits
        assert _cpp_locate(cpp_bin, fa, a, l, s_samp, "") == set()

        idx = sx.SuffixIndex.from_fasta(fa, a=a, l=l, coords=None, s=s_samp)
        for pat in pats:
            cpp = _cpp_locate(cpp_bin, fa, a, l, s_samp, pat)
            py = {(h["record_idx"], h["ungapped_pos"]) for h in idx.locate(pat)}
            brute = _brute_core(seqs, l, pat)
            assert cpp == py == brute, (seqs, l, s_samp, pat, cpp, py, brute)


# --------------------------------------------------------------------------- genomic on real yeast
@pytest.mark.skipif(not YEAST, reason="no yeast chrI fasta")
@pytest.mark.skipif(not os.path.exists(CPP_DIR), reason="no cpp dir")
def test_genomic_real_chrI(cpp_bin):
    """--coords genomic tuples on real chrI blocks == Python == locate_brute (both strands)."""
    rng = random.Random(7)
    strands = set()
    checked = 0
    for fa in YEAST[:30]:
        cp = fa[:-3] + ".coords.json"
        if not os.path.exists(cp):
            continue
        coords = json.load(open(cp))
        a = len(coords)
        for c in coords:
            strands.add(c["strand"])
        l, s = -1, 8
        recs = read_fasta(fa)[:a]
        uca = [_ungap_cap(seq, l) for _, seq in recs]
        pats = set()
        for u in uca:
            for _ in range(5):
                if len(u) < 3:
                    continue
                L = rng.randint(3, min(12, len(u)))
                p = rng.randint(0, len(u) - L)
                pats.add(u[p:p + L])
        if not pats:
            continue
        grouped = _cpp_queries(cpp_bin, fa, a, l, s, list(pats), coords_path=cp)
        idx = sx.SuffixIndex.from_fasta(fa, a=a, l=l, coords=coords, s=s)
        for pat in pats:
            cpp = grouped.get(pat, set())
            py = sx.as_tuples(idx.locate(pat))
            truth = lor.locate_brute(fa, coords, pat, a=a, l=l)
            assert cpp == py == truth, (fa, pat, cpp, py, truth)
            checked += 1
    assert checked > 0
    assert strands == {"+", "-"}, f"expected both strands exercised, got {strands}"
