"""Correctness gate for the C++ succinct FM-index (index/cpp/wg_index.cpp).

The C++ engine must agree, query-for-query, with BOTH the Python WGIndex (index/wg_index.py) and the
independent brute oracle (index/oracle.py) -- on the committed example, real yeast De Bruijn blocks,
and random complete / d-NFA Wheeler graphs, over present + absent patterns. This is what lets the C++
index stand in for the verified Python one at genome scale.

Run under python3 (no z3 needed). The C++ binary is built once via `make` in index/cpp.
"""
import glob
import os
import random
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import oracle  # noqa: E402
from index.wg_index import WGIndex  # noqa: E402
from pipeline import msa_to_index as m2i  # noqa: E402

CPP_DIR = os.path.join(ROOT, "index", "cpp")
CPP_BIN = os.path.join(CPP_DIR, "wg_index")
YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "*.fa")))
HAVE_REC = os.path.exists(m2i.REC)
EXAMPLE = os.path.join(ROOT, "data", "example", "out__example")
# the De Bruijn generator needs Biopython; shell it via the myenv interpreter regardless of the runner
PY_BIO = os.environ.get("WGT_PY_BIO", os.path.expanduser("~/miniconda3/envs/myenv/bin/python"))


@pytest.fixture(scope="session")
def cpp_bin():
    r = subprocess.run(["make", "-s"], cwd=CPP_DIR, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(CPP_BIN):
        pytest.skip(f"C++ index build failed: {r.stderr[:200]}")
    return CPP_BIN


def cpp_batch(binary, outdir, patterns):
    """Run the C++ binary over a list of (non-empty) patterns -> {pattern: (lo, hi, n)}."""
    qfile = os.path.join(outdir, "_q.txt")
    with open(qfile, "w") as fh:
        for p in patterns:
            if p:                       # the empty pattern is handled separately (--query "")
                fh.write(p + "\n")
    r = subprocess.run([binary, outdir, "--queries", qfile], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = {}
    for line in r.stdout.splitlines():
        t = line.split()
        if len(t) >= 4:
            out[t[0]] = (int(t[-3]), int(t[-2]), int(t[-1]))
    return out


def cpp_one(binary, outdir, pattern):
    r = subprocess.run([binary, outdir, "--query", pattern], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    lo, hi, n = r.stdout.split()
    return int(lo), int(hi), int(n)


# --------------------------------------------------------------------------- committed example
@pytest.mark.skipif(not os.path.isdir(EXAMPLE), reason="committed example output absent")
def test_cpp_example(cpp_bin):
    py = WGIndex.from_iol(EXAMPLE)
    for p in ("a", "b", "aa", "ab", "ba", "z"):
        assert cpp_one(cpp_bin, EXAMPLE, p) == py.count(p), p
    # empty pattern: whole node range
    assert cpp_one(cpp_bin, EXAMPLE, "") == py.count("")


# --------------------------------------------------------------------------- C++ == Python == oracle
def _check_cpp(cpp_bin, outdir, rng, n_random=120, max_len=6):
    gdot = os.path.join(outdir, "graph.dot")
    nodes, edges = oracle.parse_dot(open(gdot).read())
    py = WGIndex.from_iol(outdir)
    alpha = sorted({lab for _t, _h, lab in edges})

    adj = {}
    for t, h, lab in edges:
        adj.setdefault(t, []).append((lab, h))
    present = []
    for _ in range(40):
        v = rng.choice(sorted(nodes)); s = []
        for _ in range(rng.randint(1, max_len)):
            if v not in adj:
                break
            lab, h = rng.choice(adj[v]); s.append(lab); v = h
        if s:
            present.append("".join(s))
    pats = present + ["".join(rng.choice(alpha) for _ in range(rng.randint(1, max_len)))
                      for _ in range(n_random)]
    pats = [p for p in pats if p]

    cpp = cpp_batch(cpp_bin, outdir, pats)
    saw_hit = False
    for p in pats:
        c = cpp[p]
        lo, hi, n = py.count(p)
        truth = oracle.reachable(nodes, edges, p)
        assert c == (lo, hi, n), (outdir, p, "cpp", c, "py", (lo, hi, n))
        assert n == len(truth) and set(range(lo, hi)) == truth, (outdir, p, (lo, hi, n), sorted(truth))
        saw_hit = saw_hit or n > 0
    assert saw_hit, "expected at least one present pattern"


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC), reason="needs yeast FASTA + recognizer")
@pytest.mark.parametrize("fa", YEAST_FA[:6])
def test_cpp_vs_oracle_real_yeast(cpp_bin, fa, tmp_path):
    r = m2i.process_block(fa, k=4, l=40, a=2, work=str(tmp_path), py=PY_BIO)
    assert r["verdict"] == 1 and r["outdir"]
    _check_cpp(cpp_bin, r["outdir"], random.Random(hash(fa) & 0xffff))


@pytest.mark.skipif(not HAVE_REC, reason="needs recognizer")
@pytest.mark.parametrize("kind,args", [
    ("complete", ["-n", "10", "-e", "16", "-l", "3"]),
    ("dnfa", ["-n", "12", "-e", "18", "-l", "3"]),
    ("complete", ["-n", "14", "-e", "20", "-l", "4"]),
    ("dnfa", ["-n", "16", "-e", "26", "-l", "4"]),
])
def test_cpp_vs_oracle_random_wg(cpp_bin, kind, args, tmp_path):
    gen = os.path.join(ROOT, "generator", "Random_generator",
                       "gen_complete_WG.py" if kind == "complete" else "gen_d-nfa_WG.py")
    dot = os.path.join(str(tmp_path), f"rand_{kind}.dot")
    rr = subprocess.run([sys.executable, gen, "-o", dot] + args, capture_output=True, text=True)
    if rr.returncode != 0 or not os.path.exists(dot):
        pytest.skip(f"random WG gen failed: {rr.stderr[:160]}")
    res = m2i.recognize(dot, str(tmp_path), write=True)
    if res["verdict"] != 1 or not res["outdir"]:
        pytest.skip("generated graph not recognized as Wheeler")
    _check_cpp(cpp_bin, res["outdir"], random.Random(1234))
