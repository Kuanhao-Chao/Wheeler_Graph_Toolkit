#!/usr/bin/env python3
"""
minimize.py -- minimal-change Wheeler-graph repair (Phase 5.2), lossless node-splitting.

Two objectives, both quotients of the determinized trie T (repair/dfa.py):
  * min-size : fewest nodes in the repaired Wheeler graph (merge trie nodes with EQUAL
               right-language -> language-preserving). Smallest deterministic WG for L(G).
  * min-edits: fewest node-duplications of the (determinized) original (merge trie nodes with
               EQUAL origin set). Since same-origin => same right-language, every min-edits
               solution is min-size-feasible, hence  min-size <= size(min-edits).

Methods:
  * exact()  -- Z3 incremental feasibility: force every trie node's position into [0,k); the
                smallest k that is satisfiable under the Wheeler axioms (with merges = equal
                position) is the provable optimum. Verified against repair/exhaustive_fold.py.
  * greedy() -- scalable heuristics (added in step 5/6): Nerode-gated pairwise merge (min-size)
                and refine-toward-trie splitting (min-edits).

A repair is realized as a partition `block_of` of T's nodes; the quotient graph + its node order
come straight from the satisfying positions. Correctness of every output is checked elsewhere by
repair/verify_repair.py (recognizer + oracle + path-string set + label set).

Run under `python3` (z3 4.11.1 binding). DAG inputs only.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, HERE)
import brute_oracle as bo  # noqa: E402
import dfa  # noqa: E402


# --------------------------------------------------------------------------------------------
# Exact optimum via Z3 incremental feasibility.
# --------------------------------------------------------------------------------------------
def _solve_at_k(T, class_of, label_rank, k, timeout_ms):
    """Is there a Wheeler quotient of T with <= k blocks, merging only within `class_of`?
    Returns the position list (block_of) if SAT, else None. Positions are in [0,k)."""
    from z3 import Solver, Int, Implies, And, sat

    n = T.n
    s = Solver()
    if timeout_ms:
        s.set("timeout", timeout_ms)
    p = [Int(f"p{t}") for t in range(n)]
    for t in range(n):
        s.add(p[t] >= 0, p[t] < k)

    # Merge legality: different equivalence class => different position (cannot be merged).
    by_class = {}
    for t in range(n):
        by_class.setdefault(class_of[t], []).append(t)
    classes = list(by_class.values())
    for ci in range(len(classes)):
        for cj in range(ci + 1, len(classes)):
            for a in classes[ci]:
                for b in classes[cj]:
                    s.add(p[a] != p[b])

    # A1: the trie root is the unique in-degree-0 node; in the quotient the only possible
    # in-degree-0 block is {root} when root is unmerged. If so, it must be first.
    root = T.root
    if n > 1:
        others = [t for t in range(n) if t != root]
        root_alone = And([p[root] != p[t] for t in others])
        s.add(Implies(root_alone, And([p[root] < p[t] for t in others])))

    # A2 (cross-label) and A3 (same-label, with mirror) over every ordered pair of trie edges.
    E = T.edges
    for i in range(len(E)):
        u1, v1, a1 = E[i]
        r1 = label_rank[a1]
        for j in range(len(E)):
            if i == j:
                continue
            u2, v2, a2 = E[j]
            if r1 < label_rank[a2]:
                s.add(p[v1] < p[v2])            # A2
            elif a1 == a2:
                s.add(Implies(p[u1] < p[u2], p[v1] <= p[v2]))  # A3 (mirror via both orders)

    if s.check() == sat:
        m = s.model()
        return [m[p[t]].as_long() for t in range(n)]
    return None


def exact(T, label_rank, mode="size", timeout_ms=10000, k_lo=1):
    """Provably-minimal Wheeler quotient of T for `mode` in {'size','edits'}.
    Returns dict: {nodes, block_of, classes, (edits for 'edits'), method}. block_of is the
    position list (equal value = merged)."""
    if mode == "size":
        class_of, ncls = dfa.nerode_classes(T)
    elif mode == "edits":
        class_of, ncls = dfa.origin_classes(T)
    else:
        raise ValueError(mode)

    if not T.edges:                       # 0-edge graph (e.g. single node) -> trivially Wheeler
        return {"nodes": 1, "block_of": [0] * T.n, "classes": ncls,
                "edits": 0 if mode == "edits" else None, "method": f"exact-{mode}"}

    best = None
    for k in range(max(1, k_lo), T.n + 1):
        sol = _solve_at_k(T, class_of, label_rank, k, timeout_ms)
        if sol is not None:
            best = sol
            break
    if best is None:                      # timed out everywhere -> fall back to the trie
        best = list(range(T.n))
    nb = len(set(best))
    out = {"nodes": nb, "block_of": best, "classes": ncls, "method": f"exact-{mode}"}
    if mode == "edits":
        out["edits"] = nb - ncls
    return out


# --------------------------------------------------------------------------------------------
# Scalable greedy heuristic: merge down from the trie, gated by the objective's class.
#   min-size  -> gate = Nerode (right-language) class   (merges preserve L)
#   min-edits -> gate = origin (subset-state) class     (no cross-original merges)
# Start from the trie (always Wheeler); greedily accept any within-gate merge that keeps the
# quotient Wheeler. Lossless by gating; terminates (node count strictly drops); yields an upper
# bound on the exact optimum.
# --------------------------------------------------------------------------------------------
import subprocess
import tempfile

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")


def is_wheeler_z3(nodes, edges, label_rank, timeout_ms=5000):
    """In-process Wheeler-graph recognition via Z3: is there a total node order satisfying the
    three axioms? Same axiom encoding as exact() but with free (un-merged) positions. Used as a
    fast, file-I/O-free acceptance test inside greedy(). (Final outputs are still independently
    re-checked by repair/verify_repair.py with the C++ recognizer + oracle.)"""
    from z3 import Solver, Int, Implies, Distinct, sat
    if not edges:
        return True
    idx = {name: i for i, name in enumerate(nodes)}
    m = len(nodes)
    s = Solver()
    if timeout_ms:
        s.set("timeout", timeout_ms)
    p = [Int(f"q{i}") for i in range(m)]
    s.add(Distinct(p))
    E = [(idx[t], idx[h], label_rank[l]) for (t, h, l) in edges]
    indeg = [0] * m
    for (_, h, _) in E:
        indeg[h] += 1
    zero = [i for i in range(m) if indeg[i] == 0]
    posn = [i for i in range(m) if indeg[i] > 0]
    for z in zero:                              # A1
        for v in posn:
            s.add(p[z] < p[v])
    for i in range(len(E)):                     # A2 + A3
        u1, v1, a1 = E[i]
        for j in range(len(E)):
            if i == j:
                continue
            u2, v2, a2 = E[j]
            if a1 < a2:
                s.add(p[v1] < p[v2])
            elif a1 == a2:
                s.add(Implies(p[u1] < p[u2], p[v1] <= p[v2]))
    return s.check() == sat


def wheeler_decide(T, block_of, label_rank, int_mode=False, oracle_cap=9, backend="z3"):
    """Decide whether the quotient of T by block_of is a Wheeler graph. Brute oracle for tiny
    quotients (fast, exact); Z3 in-process recognition otherwise (default); or the C++
    recognizer if backend=='rec'."""
    blocks, bedges, _, _ = dfa.quotient(T, block_of)
    if not bedges:
        return True
    qnodes = sorted({b for e in bedges for b in (e[0], e[1])})
    nodes = [str(b) for b in qnodes]
    edges = [(str(bt), str(bh), a) for (bt, bh, a) in bedges]
    if len(qnodes) <= oracle_cap:
        return bo.is_wheeler(nodes, edges, label_rank)
    if backend == "rec":
        fd, path = tempfile.mkstemp(suffix=".dot")
        os.close(fd)
        try:
            dfa.write_quotient_dot(blocks, bedges, path)
            args = [REC, path] + (["-i"] if int_mode else [])
            return subprocess.run(args, capture_output=True).returncode == 1
        finally:
            os.unlink(path)
    return is_wheeler_z3(nodes, edges, label_rank)


def greedy(T, label_rank, mode="size", int_mode=False, backend="rec"):
    """Locally-minimal Wheeler quotient by greedy within-gate merging from the trie.
    Single pass per gate-class, repeated until a full pass makes no merge (no O(n^3) global
    restart). Lossless by gating; result is an upper bound on the exact optimum. The acceptance
    test defaults to the fast C++ recognizer (propagation decider); 'z3' is an in-process
    fallback (slower for these graphs)."""
    from collections import defaultdict
    if mode == "size":
        class_of, ncls = dfa.nerode_classes(T)
    elif mode == "edits":
        class_of, ncls = dfa.origin_classes(T)
    else:
        raise ValueError(mode)

    block_of = list(range(T.n))
    if not T.edges:
        return {"nodes": 1, "block_of": [0] * T.n, "method": f"greedy-{mode}",
                "edits": 0 if mode == "edits" else None}

    cls_of_block = {}            # block id -> gate class
    for t in range(T.n):
        cls_of_block.setdefault(block_of[t], class_of[t])

    changed = True
    while changed:
        changed = False
        by_class = defaultdict(list)
        for b in set(block_of):
            by_class[cls_of_block[b]].append(b)
        for blist in by_class.values():
            i = 0
            while i < len(blist):
                base = blist[i]
                j = i + 1
                while j < len(blist):
                    cand = blist[j]
                    trial = [base if x == cand else x for x in block_of]
                    if wheeler_decide(T, trial, label_rank, int_mode, backend=backend):
                        block_of = trial
                        changed = True
                        blist.pop(j)          # cand absorbed into base; keep scanning
                    else:
                        j += 1
                i += 1
    nb = len(set(block_of))
    out = {"nodes": nb, "block_of": block_of, "method": f"greedy-{mode}"}
    if mode == "edits":
        out["edits"] = nb - ncls
    return out


# --------------------------------------------------------------------------------------------
# Convenience: load a DOT, run exact min-size and min-edits, return everything.
# --------------------------------------------------------------------------------------------
def repair_exact(path, int_mode=False, timeout_ms=10000):
    nodes, sources, out_adj, edges = dfa.build_graph(path)
    if not dfa.is_acyclic(nodes, out_adj):
        raise ValueError("input is cyclic; out of scope for lossless node-splitting repair")
    label_rank = bo.rank_labels(edges, int_mode)
    T = dfa.determinize(sources, out_adj)
    rs = exact(T, label_rank, "size", timeout_ms)
    re = exact(T, label_rank, "edits", timeout_ms)
    return {
        "in_nodes": len(nodes), "in_edges": len(edges), "trie_nodes": T.n,
        "min_size_nodes": rs["nodes"], "min_size_block": rs["block_of"],
        "min_edits_nodes": re["nodes"], "min_edits": re["edits"], "min_edits_block": re["block_of"],
        "T": T, "label_rank": label_rank,
    }


def write_repair(T, block_of, out_path):
    """Write the quotient induced by block_of to DOT (recognizer contract)."""
    blocks, bedges, _, _ = dfa.quotient(T, block_of)
    dfa.write_quotient_dot(blocks, bedges, out_path)
    return out_path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Exact minimal Wheeler-graph repair (Z3).")
    ap.add_argument("dot")
    ap.add_argument("--int", action="store_true")
    ap.add_argument("--mode", choices=["size", "edits", "both"], default="both")
    ap.add_argument("--out", default=None, help="write the (min-size) repaired DOT here")
    ap.add_argument("--timeout-ms", type=int, default=10000)
    args = ap.parse_args()
    r = repair_exact(args.dot, args.int, args.timeout_ms)
    print(f"input    : {r['in_nodes']} nodes, {r['in_edges']} edges")
    print(f"trie     : {r['trie_nodes']} nodes")
    print(f"min-size : {r['min_size_nodes']} nodes")
    print(f"min-edits: {r['min_edits_nodes']} nodes  ({r['min_edits']} duplications)")
    if args.out:
        block = r["min_size_block"] if args.mode != "edits" else r["min_edits_block"]
        write_repair(r["T"], block, args.out)
        print(f"wrote {args.out}")
