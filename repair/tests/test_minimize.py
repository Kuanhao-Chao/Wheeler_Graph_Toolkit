"""Unit tests for repair/minimize.py (exact, greedy, refine, dispatch, z3 recognizer)."""

import pytest

import _data
import dfa
import minimize as mz
import brute_oracle as bo

NAMES = list(_data.GRAPHS)


@pytest.mark.parametrize("name", NAMES)
def test_exact_matches_expected(name):
    b = _data.build(_data.GRAPHS[name])
    T, rank = b["T"], b["label_rank"]
    exp = _data.EXPECTED[name]
    assert mz.exact(T, rank, "size")["nodes"] == exp["min_size"]
    re = mz.exact(T, rank, "edits")
    assert re["nodes"] == exp["min_edits"]
    assert re["edits"] == exp["edits"]


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("method", ["greedy", "refine"])
def test_heuristic_never_below_exact_and_optimal_here(name, method):
    b = _data.build(_data.GRAPHS[name])
    T, rank = b["T"], b["label_rank"]
    fn = getattr(mz, method)
    for mode in ("size", "edits"):
        ex = mz.exact(T, rank, mode)["nodes"]
        h = fn(T, rank, mode)["nodes"]
        assert h >= ex                       # a heuristic must never beat the optimum
        assert h == ex                       # on these fixtures both heuristics are optimal


@pytest.mark.parametrize("name", NAMES)
def test_min_size_le_min_edits(name):
    b = _data.build(_data.GRAPHS[name])
    T, rank = b["T"], b["label_rank"]
    assert mz.exact(T, rank, "size")["nodes"] <= mz.exact(T, rank, "edits")["nodes"]


@pytest.mark.parametrize("name", NAMES)
def test_every_output_is_wheeler_and_lossless(name):
    b = _data.build(_data.GRAPHS[name])
    T, rank = b["T"], b["label_rank"]
    L_in = dfa.path_strings(b["sources"], b["out_adj"])
    for method in ("exact", "greedy", "refine"):
        for mode in ("size", "edits"):
            r = mz.repair(T, rank, mode, method)
            _, bedges, qs, qadj = dfa.quotient(T, r["block_of"])
            if bedges:
                qn = [str(x) for x in sorted({y for e in bedges for y in (e[0], e[1])})]
                ed = [(str(a), str(c), l) for (a, c, l) in bedges]
                assert bo.is_wheeler(qn, ed, rank), f"{name}/{method}/{mode} not Wheeler"
            assert dfa.path_strings(qs, qadj) == L_in, f"{name}/{method}/{mode} changed language"


@pytest.mark.parametrize("name", NAMES)
def test_is_wheeler_z3_agrees_with_oracle(name):
    b = _data.build(_data.GRAPHS[name])
    assert mz.is_wheeler_z3(b["nodes"], b["edges"], b["label_rank"]) == \
        bo.is_wheeler(b["nodes"], b["edges"], b["label_rank"])


def test_refine_matches_greedy_on_midsize():
    # a graph whose trie is bigger than the input but still tractable: refine == greedy here
    import glob
    import subprocess
    rec = _data.os.path.join(_data.ROOT, "recognizer", "bin", "recognizer_linux")
    for f in glob.glob(_data.os.path.join(_data.ROOT, "data/graph/RevDetGraph/**/*.dot"), recursive=True):
        nodes, sources, out_adj, edges = mz.dfa.build_graph(f)
        if not (10 <= len(nodes) <= 25) or not dfa.is_acyclic(nodes, out_adj):
            continue
        if subprocess.run([rec, f], capture_output=True).returncode != 255:
            continue
        rank = bo.rank_labels(edges, False)
        try:
            T = dfa.determinize(sources, out_adj, max_nodes=4000)
        except RuntimeError:
            continue
        if T.n > 60:                         # keep the slow greedy bounded for one test graph
            continue
        for mode in ("size", "edits"):
            assert mz.refine(T, rank, mode)["nodes"] == mz.greedy(T, rank, mode)["nodes"]
        return  # one suitable graph is enough
    pytest.skip("no suitable mid-size RevDet graph found")
