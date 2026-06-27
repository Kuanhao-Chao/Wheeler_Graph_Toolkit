"""Phase A gate: RevDet -> minimal repair -> index, on real yeast blocks.

Reuses the repair module's own correctness gate (`repair/verify_repair.py`: recognizer accepts +
path-strings preserved + labels preserved) and checks the FM-index against the brute oracle on the
repaired Wheeler graph (count AND node-range, present + absent patterns). Runs under python3 (z3).
"""
import glob
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "repair"))

from index import oracle              # noqa: E402
from index.wg_index import WGIndex    # noqa: E402

HAVE_Z3 = True
try:
    import z3  # noqa: F401
    import verify_repair as vr        # noqa: E402
    from pipeline import revdet_to_index as r2i  # noqa: E402
except Exception:                     # noqa: BLE001
    HAVE_Z3 = False

YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "*.fa")))
HAVE_REC = os.path.exists(os.path.join(ROOT, "recognizer", "bin", "recognizer_linux"))
NEED = HAVE_Z3 and YEAST_FA and HAVE_REC


def _index_matches_oracle(outdir, rng, n_random=80, max_len=6):
    gdot = os.path.join(outdir, "graph.dot")
    nodes, edges = oracle.parse_dot(open(gdot).read())
    idx = WGIndex.from_iol(outdir)
    # constructor cross-check: recognizer I/O/L == rebuilt-from-graph.dot
    assert idx.iol() == WGIndex.from_edges(nodes, edges).iol()
    alpha = sorted({lab for _t, _h, lab in edges})
    adj = {}
    for t, h, lab in edges:
        adj.setdefault(t, []).append((lab, h))
    present, saw = [], False
    for _ in range(40):
        v, s = rng.choice(sorted(nodes)), []
        for _ in range(rng.randint(1, max_len)):
            if v not in adj:
                break
            lab, h = rng.choice(adj[v]); s.append(lab); v = h
        if s:
            present.append("".join(s))
    pats = present + ["".join(rng.choice(alpha) for _ in range(rng.randint(1, max_len)))
                      for _ in range(n_random)]
    for p in pats:
        lo, hi, n = idx.count(p)
        truth = oracle.reachable(nodes, edges, p)
        assert n == len(truth) and set(range(lo, hi)) == truth, (outdir, p, (lo, hi, n), sorted(truth))
        saw = saw or n > 0
    assert saw


@pytest.mark.skipif(not NEED, reason="needs z3 + yeast FASTA + recognizer")
@pytest.mark.parametrize("fa", YEAST_FA[:5])
def test_revdet_repair_index_yeast(fa, tmp_path):
    rec, idx = r2i.process_block(fa, l=40, a=2, work=str(tmp_path))
    assert rec["ok"], rec
    # RevDet was non-Wheeler and got repaired to a Wheeler graph that is indexed
    assert idx is not None and rec["wheeler_nodes"] == idx.n

    # repair correctness + losslessness (recognizer accepts; path-strings + labels preserved)
    in_dot = rec["revdet_dot"]
    out_dot = rec["to_index_dot"]
    if rec.get("repaired"):
        ok, res = vr.verify(in_dot, out_dot, int_mode=False)
        assert res["strings_preserved"], (fa, res)   # lossless: same path-string set
        assert res["labels_preserved"], (fa, res)
        assert res["recognizer"], (fa, res)          # output is a Wheeler graph
        assert ok, (fa, res)

    # index correctness vs the brute oracle on the repaired Wheeler graph
    _index_matches_oracle(rec["outdir"], random.Random(hash(fa) & 0xffff))


@pytest.mark.skipif(not NEED, reason="needs z3 + yeast FASTA + recognizer")
def test_revdet_query_present_and_absent(tmp_path):
    import dfa
    from repair import wheelerize as wz
    fa = YEAST_FA[0]
    rec, idx = r2i.process_block(fa, l=40, a=2, work=str(tmp_path))
    assert rec["ok"] and idx is not None
    # a genuine substring of what RevDet spells must be found (forward; no reversal)
    nodes, sources, out_adj, edges = dfa.build_graph(rec["revdet_dot"])
    spelled = max(("".join(p) for p in wz.path_strings(sources, out_adj)), key=len)
    present = spelled[8:14]
    gnodes, gedges = oracle.parse_dot(open(os.path.join(rec["outdir"], "graph.dot")).read())
    assert idx.count(present)[2] == oracle.count(gnodes, gedges, present)
    assert idx.count(present)[2] > 0                 # a real spelled substring is found (forward)
    assert idx.count("ZZZZZZ")[2] == 0               # absent
