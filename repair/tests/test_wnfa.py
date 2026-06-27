"""Gates for the incremental Wheeler-NFA repair (repair/wnfa.py). Run under python3 (z3 + recognizer)."""
import glob
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPAIR = os.path.dirname(HERE)
ROOT = os.path.dirname(REPAIR)
sys.path.insert(0, REPAIR)
sys.path.insert(0, ROOT)

import wnfa                          # noqa: E402
import verify_repair as vr          # noqa: E402
from wheelerize import path_strings  # noqa: E402
from index import oracle            # noqa: E402
from index.wg_index import WGIndex  # noqa: E402
from pipeline import msa_to_index as m2i  # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
HAVE_REC = os.path.exists(REC)
YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "*.fa")))
PY_BIO = wnfa.m2i  # marker; RevDet generator shelled via revdet path below


def _write_dot(edges, path):
    with open(path, "w") as f:
        f.write("strict digraph  {\n")
        for (t, h, l) in edges:
            f.write(f"\t{t} -> {h} [label={l}];\n")
        f.write("}\n")


# ----------------------------------------------------------------- split primitive: language-preserving
def test_split_preserves_language(tmp_path):
    # diamond-ish DAG: node 3 has two in-edges (from 1 and 2); splitting it must keep path-strings.
    edges = [(0, 1, "a"), (0, 2, "b"), (1, 3, "c"), (2, 3, "c"), (3, 4, "d")]
    p = os.path.join(str(tmp_path), "g.dot"); _write_dot(edges, p)
    N, S, E = wnfa.load_int(p)
    out0, _ = wnfa._mut(N, E)
    before = path_strings(S, out0)
    # split node (id of original "3") by its two in-edges into two groups
    v = sorted(N)[3]
    n_before = len(N)
    in_edges = [e for e in E if e[1] == v]
    assert len(in_edges) == 2
    N2, E2 = wnfa.split_node_by_inedges(N, E, v, [0, 1])
    out1, inn1 = wnfa._mut(N2, E2)
    src1 = [u for u in N2 if not inn1[u]]
    after = path_strings(src1, out1)
    assert before == after                       # language preserved
    assert len(N2) == n_before + 1               # exactly one new node (one split into two copies)


@pytest.mark.skipif(not HAVE_REC, reason="recognizer needed")
def test_split_preserves_language_random():
    rng = random.Random(7)
    for _ in range(15):
        n = rng.randint(5, 9)
        edges = set()
        for u in range(n):
            for v in range(u + 1, n):              # DAG: only forward edges
                if rng.random() < 0.45:
                    edges.add((u, v, rng.choice("ab")))
        edges = sorted(edges)
        if not edges:
            continue
        N = set(range(n))
        before = path_strings([u for u in N if all(e[1] != u for e in edges)], wnfa._mut(N, edges)[0])
        # pick a node with >=2 in-edges
        inn = wnfa._mut(N, edges)[1]
        cand = [u for u in N if len(inn[u]) >= 2]
        if not cand:
            continue
        v = cand[0]
        assign = [rng.randint(0, 1) for _ in inn[v]]
        if len(set(assign)) < 2:
            assign[0] = 0; assign[-1] = 1
        N2, E2 = wnfa.split_node_by_inedges(set(N), list(edges), v, assign)
        out1, inn1 = wnfa._mut(N2, E2)
        after = path_strings([u for u in N2 if not inn1[u]], out1)
        assert before == after


# ----------------------------------------------------------------- end-to-end on yeast RevDet
def _revdet_dot(fa, l, a, work):
    import subprocess
    gen = os.path.join(ROOT, "generator", "RevDetGraph_generator")
    out = os.path.join(work, "rd.dot")
    r = subprocess.run([os.path.expanduser("~/miniconda3/envs/myenv/bin/python"),
                        os.path.join(gen, "RevDetGraph_generator.py"),
                        "-o", out, "-l", str(l), "-a", str(a), os.path.abspath(fa)],
                       cwd=gen, capture_output=True, text=True, timeout=120)
    return out if (r.returncode == 0 and os.path.exists(out)) else None


@pytest.mark.skipif(not (HAVE_REC and YEAST_FA), reason="recognizer + yeast FASTA needed")
@pytest.mark.parametrize("fa", YEAST_FA[:4])
def test_wnfa_repair_yeast_verified(fa, tmp_path):
    rd = _revdet_dot(fa, 40, 2, str(tmp_path))
    assert rd, "RevDet build failed"
    rec = wnfa.repair(rd, str(tmp_path))
    assert rec["ok"]
    # lossless: path-string set preserved
    assert wnfa.lossless(rd, rec)
    # write the repaired DOT and run the repair module's 5-invariant verifier (Wheeler + lossless + labels)
    outp = os.path.join(str(tmp_path), "wnfa_out.dot")
    wnfa.write_dot(rec["edges"], outp)
    ok, res = vr.verify(rd, outp, int_mode=False)
    assert res["recognizer"] and res["strings_preserved"] and res["labels_preserved"], (fa, res)
    # index correctness on the repaired (possibly nondeterministic) Wheeler graph: count == oracle
    r2 = m2i.recognize(outp, str(tmp_path), write=True)
    assert r2["verdict"] == 1 and r2["outdir"]
    nodes, edges = oracle.parse_dot(open(os.path.join(r2["outdir"], "graph.dot")).read())
    idx = WGIndex.from_iol(r2["outdir"])
    rng = random.Random(hash(fa) & 0xffff)
    alpha = sorted({l for _t, _h, l in edges})
    adj = {}
    for t, h, l in edges:
        adj.setdefault(t, []).append((l, h))
    pats = []
    for _ in range(30):                            # present patterns by random walk
        v, s = rng.choice(sorted(nodes)), []
        for _ in range(rng.randint(1, 6)):
            if v not in adj:
                break
            l, h = rng.choice(adj[v]); s.append(l); v = h
        if s:
            pats.append("".join(s))
    pats += ["".join(rng.choice(alpha) for _ in range(rng.randint(1, 6))) for _ in range(60)]
    saw = False
    for p in pats:
        lo, hi, n = idx.count(p)
        truth = oracle.reachable(nodes, edges, p)
        assert n == len(truth) and set(range(lo, hi)) == truth, (fa, p, (lo, hi, n), sorted(truth))
        saw = saw or n > 0
    assert saw
