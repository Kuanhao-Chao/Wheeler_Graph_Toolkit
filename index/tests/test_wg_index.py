"""Phase 3 gates: the Wheeler-graph FM-index (count/backward search).

  * exact hand-checked example + load from the committed example I/O/L;
  * index.count == brute oracle, and the index node-range == the oracle's reachable set (contiguous),
    over present + absent patterns, on real yeast blocks and random Wheeler graphs (through the real
    recognizer);
  * from_graph_dot I/O/L == the recognizer's emitted I/O/L (label-order consistency);
  * a biological end-to-end demo on a real yeast block.
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

YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "*.fa")))
HAVE_REC = os.path.exists(m2i.REC)
EXAMPLE = os.path.join(ROOT, "data", "example", "out__example")


# --------------------------------------------------------------------------- exact / committed
def test_example_exact_from_edges():
    # the worked example graph (Wheeler order 1..5)
    nodes = {1, 2, 3, 4, 5}
    edges = [(1, 3, "a"), (1, 4, "a"), (5, 4, "a"), (1, 5, "b"), (2, 5, "b")]
    idx = WGIndex.from_edges(nodes, edges)
    assert idx.iol() == ("1101001001", "0001011101", "aabba")
    assert idx.count("a") == (3, 5, 2)
    assert idx.count("b") == (5, 6, 1)
    assert idx.count("ab") == (3, 3, 0)        # no b-edge leaves {3,4}
    assert idx.count("z")[2] == 0              # label not in graph


@pytest.mark.skipif(not os.path.isdir(EXAMPLE), reason="committed example output absent")
def test_from_iol_matches_from_dot_example():
    a = WGIndex.from_iol(EXAMPLE)
    b = WGIndex.from_graph_dot(os.path.join(EXAMPLE, "graph.dot"))
    assert a.iol() == b.iol() == ("1101001001", "0001011101", "aabba")
    for p in ("a", "b", "ab", "aa", "ba"):
        assert a.count(p) == b.count(p)


# --------------------------------------------------------------------------- index == oracle helper
def _check_index_vs_oracle(outdir, rng, n_random=120, max_len=6):
    """Full agreement check on a recognized graph's output dir."""
    gdot = os.path.join(outdir, "graph.dot")
    nodes, edges = oracle.parse_dot(open(gdot).read())
    # constructors agree (recognizer I/O/L == rebuilt-from-graph.dot I/O/L)
    idx_iol = WGIndex.from_iol(outdir)
    idx_dot = WGIndex.from_edges(nodes, edges)
    assert idx_iol.iol() == idx_dot.iol(), outdir
    idx = idx_iol
    alpha = sorted({lab for _t, _h, lab in edges})

    # present patterns: walk random paths to get guaranteed-present label strings
    adj = {}
    for t, h, lab in edges:
        adj.setdefault(t, []).append((lab, h))
    present = []
    for _ in range(40):
        v = rng.choice(sorted(nodes))
        s = []
        for _ in range(rng.randint(1, max_len)):
            if v not in adj:
                break
            lab, h = rng.choice(adj[v])
            s.append(lab); v = h
        if s:
            present.append("".join(s))

    pats = present + ["".join(rng.choice(alpha) for _ in range(rng.randint(1, max_len)))
                      for _ in range(n_random)]
    saw_hit = False
    for p in pats:
        lo, hi, n = idx.count(p)
        truth = oracle.reachable(nodes, edges, p)
        assert n == len(truth), (outdir, p, (lo, hi, n), sorted(truth))
        # the index range must be exactly the oracle's reachable set (contiguous interval)
        assert set(range(lo, hi)) == truth, (outdir, p, (lo, hi), sorted(truth))
        saw_hit = saw_hit or n > 0
    assert saw_hit, "expected at least one present pattern"


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC), reason="needs yeast FASTA + recognizer")
@pytest.mark.parametrize("fa", YEAST_FA[:6])
def test_index_vs_oracle_real_yeast(fa, tmp_path):
    r = m2i.process_block(fa, k=4, l=40, a=2, work=str(tmp_path))
    assert r["verdict"] == 1 and r["outdir"]
    _check_index_vs_oracle(r["outdir"], random.Random(hash(fa) & 0xffff))


@pytest.mark.skipif(not HAVE_REC, reason="needs recognizer")
@pytest.mark.parametrize("kind,args", [
    ("complete", ["-n", "10", "-e", "16", "-l", "3"]),
    ("dnfa", ["-n", "12", "-e", "18", "-l", "3"]),
    ("complete", ["-n", "14", "-e", "20", "-l", "4"]),
])
def test_index_vs_oracle_random_wg(kind, args, tmp_path):
    gen = os.path.join(ROOT, "generator", "Random_generator",
                       "gen_complete_WG.py" if kind == "complete" else "gen_d-nfa_WG.py")
    dot = os.path.join(str(tmp_path), f"rand_{kind}.dot")
    rr = subprocess.run([sys.executable, gen, "-o", dot] + args, capture_output=True, text=True)
    if rr.returncode != 0 or not os.path.exists(dot):
        pytest.skip(f"random WG gen failed: {rr.stderr[:160]}")
    res = m2i.recognize(dot, str(tmp_path), write=True)
    if res["verdict"] != 1 or not res["outdir"]:
        pytest.skip("generated graph not recognized as Wheeler (unexpected but skip)")
    _check_index_vs_oracle(res["outdir"], random.Random(1234))


# --------------------------------------------------------------------------- biological end-to-end demo
@pytest.mark.skipif(not (YEAST_FA and HAVE_REC), reason="needs yeast FASTA + recognizer")
def test_yeast_end_to_end_query(tmp_path):
    """A k-mer that occurs in the alignment (queried as its reverse, per the construction) is found;
    a fabricated absent k-mer is not. Both match the oracle."""
    from index import faithful
    fa = YEAST_FA[0]
    r = m2i.process_block(fa, k=5, l=60, a=2, work=str(tmp_path))
    assert r["verdict"] == 1 and r["outdir"]
    idx = WGIndex.from_iol(r["outdir"])
    nodes, edges = oracle.parse_dot(open(os.path.join(r["outdir"], "graph.dot")).read())

    seqs = [s for _id, s in faithful.read_fasta(fa)][:2]
    u = faithful._ungap_cap(seqs[0], 60)
    present = u[10:16]                  # a 6-mer that occurs in sequence 0
    q = present[::-1]                   # paths spell reverse(seq), so query the reverse
    lo, hi, n = idx.count(q)
    assert n > 0, (present, q)
    assert n == oracle.count(nodes, edges, q)
    assert set(range(lo, hi)) == oracle.reachable(nodes, edges, q)

    absent = "ZZZZZZ"                    # not over the DNA alphabet -> definitely absent
    assert idx.count(absent)[2] == 0 == oracle.count(nodes, edges, absent)
