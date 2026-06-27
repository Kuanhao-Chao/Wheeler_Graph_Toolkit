"""Correctness gate for the C++ suffix-index port (index/cpp/wg_suffix.cpp).

C++ locate must equal BOTH the Python SuffixIndex (index/suffix_index.py) and the brute oracle
(index/locate_oracle.py) -- core (record_idx, ungapped_pos) and genomic (species, src, gstart, gend,
strand, incl. - strand) -- on synthetic blocks and real yeast blocks. Built once via `make`. Run under
python3.
"""
import glob
import json
import os
import random
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import suffix_index as sx       # noqa: E402
from index import locate_oracle as lor     # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402

CPP_DIR = os.path.join(ROOT, "index", "cpp")
CPP_BIN = os.path.join(CPP_DIR, "wg_suffix")
YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "chrI_*.fa")))


@pytest.fixture(scope="session")
def cpp_bin():
    r = subprocess.run(["make", "-s", "wg_suffix"], cwd=CPP_DIR, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(CPP_BIN):
        pytest.skip(f"C++ suffix build failed: {r.stderr[:300]}")
    return CPP_BIN


def _cpp_batch(binary, fa, a, l, s, patterns, coords=None):
    """Run --queries; parse the grouped output -> {pattern: set(...)} (pairs, or genomic tuples)."""
    qf = os.path.join(os.path.dirname(fa), "_sq.txt")
    with open(qf, "w") as fh:
        for p in patterns:
            if p:
                fh.write(p + "\n")
    cmd = [binary, fa, "--a", str(a), "--l", str(l), "--s", str(s)]
    if coords:
        cmd += ["--coords", coords]
    cmd += ["--queries", qf]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out, cur = {}, None
    for line in r.stdout.splitlines():
        if line.startswith("# "):
            cur = line[2:]; out[cur] = set()
        elif line.strip():
            if coords:
                t = line.split("\t"); out[cur].add((t[0], t[1], int(t[2]), int(t[3]), t[4]))
            else:
                a2, b2 = line.split(); out[cur].add((int(a2), int(b2)))
    return out


def _check(cpp_bin, fa, a, l, s, coords_path, patterns):
    coords = json.load(open(coords_path)) if coords_path else None
    cpp_core = _cpp_batch(cpp_bin, fa, a, l, s, patterns)
    cpp_gen = _cpp_batch(cpp_bin, fa, a, l, s, patterns, coords=coords_path) if coords_path else None
    for P in patterns:
        if not P:
            continue
        idx = sx.SuffixIndex.from_fasta(fa, a=a, l=l, coords=coords, s=s)
        py_core = {(h["record_idx"], h["ungapped_pos"]) for h in
                   sx.SuffixIndex.from_fasta(fa, a=a, l=l, coords=None, s=s).locate(P)}
        assert cpp_core.get(P, set()) == py_core, ("core", fa, P)
        if coords_path:
            py_gen = sx.as_tuples(idx.locate(P))
            truth = lor.locate_brute(fa, coords, P, a=a, l=l)
            assert cpp_gen.get(P, set()) == py_gen == truth, ("genomic", fa, P)


# --------------------------------------------------------------------------- synthetic (both strands)
def test_cpp_suffix_synthetic_both_strands(cpp_bin, tmp_path):
    fa = os.path.join(str(tmp_path), "syn.fa")
    with open(fa, "w") as f:
        f.write(">spA\nACGACGAC\n>spB\nACGACGAC\n")
    coords = [
        {"fasta_id": "spA", "src": "spA.chr", "start": 100, "size": 8, "strand": "+", "srcSize": 1000},
        {"fasta_id": "spB", "src": "spB.ctg", "start": 50, "size": 8, "strand": "-", "srcSize": 200},
    ]
    cpath = os.path.join(str(tmp_path), "syn.coords.json")
    json.dump(coords, open(cpath, "w"))
    _check(cpp_bin, fa, 2, -1, 2, cpath, ["ACG", "ACGA", "AC", "A", "TTTT", "ZZZ"])


# --------------------------------------------------------------------------- real chrI blocks
@pytest.mark.skipif(not YEAST_FA, reason="needs yeast FASTA")
@pytest.mark.parametrize("fa", YEAST_FA[:6])
@pytest.mark.parametrize("s", [1, 4])
def test_cpp_suffix_vs_python_oracle(cpp_bin, fa, s):
    a, l = 2, -1
    coords_path = fa.replace(".fa", ".coords.json")
    seqs = [_ungap_cap(seq, l) for _id, seq in read_fasta(fa)[:a]]
    rng = random.Random(hash(fa) & 0xffff)
    pats = set()
    for u in seqs:
        for m in (1, 3, 6, 9, len(u)):
            if 1 <= m <= len(u):
                pats.add(u[rng.randint(0, len(u) - m):][:m])
    pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(2, 7))) for _ in range(25)}
    pats |= {"ZZZ", "N"}
    _check(cpp_bin, fa, a, l, s, coords_path if os.path.exists(coords_path) else None, sorted(pats))


@pytest.mark.skipif(not YEAST_FA, reason="needs yeast FASTA")
def test_cpp_suffix_info_parity(cpp_bin):
    fa = YEAST_FA[7]
    r = subprocess.run([cpp_bin, fa, "--a", "2", "--l", "-1", "--s", "4", "--info"],
                       capture_output=True, text=True)
    kv = dict(tok.split("=") for tok in r.stdout.split())
    idx = sx.SuffixIndex.from_fasta(fa, a=2, l=-1, s=4)
    assert (int(kv["n"]), int(kv["r"]), int(kv["n_samples"]), int(kv["sigma"]), int(kv["a"])) == \
           (idx.n, idx.r, idx.n_samples, idx.sigma, idx.a)
