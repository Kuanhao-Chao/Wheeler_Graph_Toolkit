"""End-to-end integration over the adversarial battery: for every canonical graph, the three
methods agree with the brute-force optimum and produce verified, lossless Wheeler graphs.

Also includes a small randomized differential as a property-based smoke test (kept tiny so the
suite stays fast; the full fuzzing lives in repair/test_minimize.py)."""

import random

import pytest

import _data
import dfa
import minimize as mz
import exhaustive_fold as ex
import brute_oracle as bo

NAMES = list(_data.GRAPHS)


@pytest.mark.parametrize("name", NAMES)
def test_full_pipeline(name):
    b = _data.build(_data.GRAPHS[name])
    T, rank = b["T"], b["label_rank"]
    L_in = dfa.path_strings(b["sources"], b["out_adj"])
    in_labels = dfa.label_set(b["edges"])

    rs = mz.exact(T, rank, "size")["nodes"]
    re = mz.exact(T, rank, "edits")["nodes"]
    if T.n <= 9:                                   # cross-check against the brute-force optimum
        assert ex.min_size(T, rank)[0] == rs
        assert ex.min_edits(T, rank)[0] == re
    assert rs <= re                                # min-size never exceeds min-edits

    for method in ("exact", "greedy", "refine"):
        for mode in ("size", "edits"):
            r = mz.repair(T, rank, mode, method)
            assert r["nodes"] >= (rs if mode == "size" else re)   # never beats the optimum
            _, bedges, qs, qadj = dfa.quotient(T, r["block_of"])
            if bedges:
                qn = [str(x) for x in sorted({y for e in bedges for y in (e[0], e[1])})]
                ed = [(str(a), str(c), l) for (a, c, l) in bedges]
                assert bo.is_wheeler(qn, ed, rank)                # output is Wheeler
                assert {a for (_, _, a) in bedges} <= in_labels    # no new labels
            assert dfa.path_strings(qs, qadj) == L_in              # lossless


def _gen_dag(rng, n, nl):
    labs = list("abc"[:nl])
    return [(f"v{i}", f"v{j}", rng.choice(labs))
            for i in range(n) for j in range(i + 1, n) if rng.random() < 0.5]


def test_small_random_differential():
    rng = random.Random(20240625)
    checked = 0
    for _ in range(120):
        edges = _gen_dag(rng, rng.randint(3, 6), rng.randint(1, 3))
        if not edges:
            continue
        b = _data.build(edges)
        T, rank = b["T"], b["label_rank"]
        if T.n > 8:
            continue
        for mode in ("size", "edits"):
            opt = mz.exact(T, rank, mode)["nodes"]
            assert ex.exhaustive_min(
                T, (dfa.nerode_classes if mode == "size" else dfa.origin_classes)(T)[0], rank)[0] == opt
            for method in ("greedy", "refine"):
                r = mz.repair(T, rank, mode, method)
                assert r["nodes"] >= opt
                _, bedges, qs, qadj = dfa.quotient(T, r["block_of"])
                assert dfa.path_strings(qs, qadj) == dfa.path_strings(b["sources"], b["out_adj"])
        checked += 1
    assert checked >= 30, f"too few non-trivial random graphs checked ({checked})"
