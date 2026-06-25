#!/usr/bin/env python3
"""
test_minimize.py -- property-based + adversarial correctness tests for minimal WG repair.

Two layers:
  1. DIFFERENTIAL (the optimality proof): for many random small DAGs, assert the Z3 exact
     optima (repair/minimize.exact) EQUAL the independent brute-force optima
     (repair/exhaustive_fold), for BOTH objectives, and that min-size <= min-edits.
  2. INVARIANTS (the correctness proof): every repaired quotient must (a) be Wheeler per the
     brute oracle, (b) spell the EXACT same path-string set as the input, (c) keep the same
     label set. (The C++ recognizer invariant is added in repair/verify_repair.py for any-n.)

Plus a fixed ADVERSARIAL battery (already-WG, single node, parallel edges, deep chain, wide
fan-out, multi-source, nondeterministic original, the classic 4-node non-WG).

Run under python3 (z3). Exits nonzero on any failure.
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, HERE)
import brute_oracle as bo  # noqa: E402
import dfa  # noqa: E402
import minimize as mz  # noqa: E402
import exhaustive_fold as ex  # noqa: E402

LABS = "abcdefghij"


def graph_from_edges(edges):
    nodes = sorted({t for (t, _, _) in edges} | {h for (_, h, _) in edges})
    out_adj = {n: [] for n in nodes}
    indeg = {n: 0 for n in nodes}
    for (u, v, l) in edges:
        out_adj[u].append((l, v))
        indeg[v] += 1
    sources = [n for n in nodes if indeg[n] == 0]
    return nodes, sources, out_adj


def gen_random_dag(rng, n, nl, prob=0.45, int_mode=False):
    """Random labeled DAG: edges only i->j with i<j (acyclic), labels from first nl symbols
    (letters for string mode, digits for int mode so rank_labels --int can parse them)."""
    labs = [str(k) for k in range(nl)] if int_mode else list(LABS[:nl])
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < prob:
                edges.append((f"v{i}", f"v{j}", rng.choice(labs)))
    return edges


def check_output(T, block_of, label_rank, in_strings, in_labels):
    """Per-output invariants on a quotient (oracle-decidable size). Returns (ok, reason)."""
    blocks, bedges, qs, qadj = dfa.quotient(T, block_of)
    # (a) Wheeler per brute oracle
    if bedges:
        nodes = [str(b) for b in sorted({b for e in bedges for b in (e[0], e[1])})]
        edges = [(str(bt), str(bh), a) for (bt, bh, a) in bedges]
        if not bo.is_wheeler(nodes, edges, label_rank):
            return False, "output NOT Wheeler per oracle"
    # (b) path-string set preserved
    out_strings = dfa.path_strings(qs, qadj)
    if out_strings != in_strings:
        return False, (f"path-string set changed "
                       f"(lost {list(in_strings - out_strings)[:2]}, "
                       f"gained {list(out_strings - in_strings)[:2]})")
    # (c) label set preserved
    out_labels = {a for (_, _, a) in bedges}
    if bedges and out_labels != in_labels:
        return False, f"label set changed {in_labels} -> {out_labels}"
    return True, "ok"


def diff_one(edges, int_mode=False, timeout_ms=10000, max_trie=8):
    """One differential + invariant check. Returns (status, detail). status in
    {OK, SKIP, FAIL}."""
    nodes, sources, out_adj = graph_from_edges(edges)
    if not edges:
        return "SKIP", "no edges"
    label_rank = bo.rank_labels(edges, int_mode)
    in_labels = {a for (_, _, a) in edges}
    try:
        T = dfa.determinize(sources, out_adj, max_nodes=10000)
    except RuntimeError:
        return "SKIP", "trie too large"
    if T.n > max_trie:
        return "SKIP", f"trie {T.n} > {max_trie}"
    in_strings = dfa.path_strings(sources, out_adj)

    # exhaustive optima (ground truth)
    ms_x, _ = ex.min_size(T, label_rank, max_nodes=max_trie)
    me_x, me_x_edits, _, noc = ex.min_edits(T, label_rank, max_nodes=max_trie)

    # exact Z3 optima
    rs = mz.exact(T, label_rank, "size", timeout_ms)
    re = mz.exact(T, label_rank, "edits", timeout_ms)

    # 1. optimality: exact == exhaustive
    if rs["nodes"] != ms_x:
        return "FAIL", f"min-size mismatch: exact={rs['nodes']} exhaustive={ms_x}"
    if re["nodes"] != me_x:
        return "FAIL", f"min-edits mismatch: exact={re['nodes']} exhaustive={me_x}"
    if re["edits"] != me_x_edits:
        return "FAIL", f"min-edits edits mismatch: exact={re['edits']} exhaustive={me_x_edits}"
    # 2. consistency: min-size <= size(min-edits)
    if rs["nodes"] > re["nodes"]:
        return "FAIL", f"min-size {rs['nodes']} > min-edits {re['nodes']} (violates lower bound)"
    # 3. invariants on both exact outputs
    for tag, r in (("size", rs), ("edits", re)):
        ok, why = check_output(T, r["block_of"], label_rank, in_strings, in_labels)
        if not ok:
            return "FAIL", f"{tag} output invariant: {why}"

    # 4. greedy heuristic: must be Wheeler + lossless, and no better than the exact optimum
    gs = mz.greedy(T, label_rank, "size", int_mode)
    ge = mz.greedy(T, label_rank, "edits", int_mode)
    if gs["nodes"] < rs["nodes"]:
        return "FAIL", f"greedy-size {gs['nodes']} < exact {rs['nodes']} (impossible)"
    if ge["nodes"] < re["nodes"]:
        return "FAIL", f"greedy-edits {ge['nodes']} < exact {re['nodes']} (impossible)"
    for tag, r in (("greedy-size", gs), ("greedy-edits", ge)):
        ok, why = check_output(T, r["block_of"], label_rank, in_strings, in_labels)
        if not ok:
            return "FAIL", f"{tag} output invariant: {why}"

    gap_s = gs["nodes"] - rs["nodes"]
    gap_e = ge["nodes"] - re["nodes"]
    return "OK", (f"size={rs['nodes']}(g+{gap_s}) edits={re['nodes']}({re['edits']},g+{gap_e}) "
                  f"trie={T.n}")


def run_random(n_iter, seed=1, int_mode=False):
    rng = random.Random(seed)
    counts = {"OK": 0, "SKIP": 0, "FAIL": 0}
    fails = []
    nontrivial = 0
    for i in range(n_iter):
        n = rng.randint(2, 6)
        nl = rng.randint(1, 3)
        edges = gen_random_dag(rng, n, nl, int_mode=int_mode)
        status, detail = diff_one(edges, int_mode)
        counts[status] += 1
        if status == "OK":
            nontrivial += 1
        if status == "FAIL":
            fails.append((edges, detail))
            if len(fails) <= 5:
                print(f"  FAIL seed#{i}: {detail}\n    edges={edges}")
    print(f"random: OK={counts['OK']} SKIP={counts['SKIP']} FAIL={counts['FAIL']} "
          f"(checked {nontrivial} non-trivial)")
    return counts["FAIL"], fails


# ----- adversarial battery -----
ADVERSARIAL = {
    "classic_nonwg": [("s", "n1", "a"), ("s", "n2", "b"), ("n1", "n3", "b"), ("n2", "n3", "a")],
    "already_wg_chain": [("a", "b", "x"), ("b", "c", "x")],
    "single_edge": [("a", "b", "x")],
    "parallel_dup": [("a", "b", "x"), ("a", "b", "x")],  # duplicate edge
    "deep_chain": [(f"v{i}", f"v{i+1}", "a") for i in range(6)],
    "wide_fanout": [("r", "a", "a"), ("r", "b", "b"), ("r", "c", "c")],
    "multi_source": [("s1", "m", "a"), ("s2", "m", "a"), ("m", "t", "b")],
    "nondet_same_label": [("r", "a", "x"), ("r", "b", "x"), ("a", "c", "y"), ("b", "c", "z")],
    "diamond": [("s", "a", "x"), ("s", "b", "y"), ("a", "t", "z"), ("b", "t", "z")],
}


def run_adversarial(int_mode=False):
    nfail = 0
    for name, edges in ADVERSARIAL.items():
        status, detail = diff_one(edges, int_mode)
        flag = "ok " if status != "FAIL" else "FAIL"
        print(f"  [{flag}] {name:18s} {status}: {detail}")
        if status == "FAIL":
            nfail += 1
    return nfail


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--int", action="store_true")
    args = ap.parse_args()
    # The adversarial battery uses letter labels, so run it only in string mode.
    f1 = 0
    if not args.int:
        print("=== adversarial battery ===")
        f1 = run_adversarial(args.int)
    print(f"=== random differential ({args.n} graphs, seed {args.seed}) ===")
    f2, _ = run_random(args.n, args.seed, args.int)
    total = f1 + f2
    print(f"\nTOTAL FAILURES: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
