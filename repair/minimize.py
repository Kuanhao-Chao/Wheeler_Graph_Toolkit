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
# Fast heuristic: refine-from-coarse. Start at the coarsest legal partition (Nerode classes for
# min-size; origin classes for min-edits) and SPLIT toward the trie until Wheeler. The decision
# test is an in-process co-lexicographic order check: position each block by the min co-lex rank
# of its trie members' incoming strings (root = empty string = position 0, giving A1 for free).
# If that order satisfies the three axioms, a Wheeler witness exists (sound ACCEPT, any n); if it
# violates one, the offending head blocks tell us where to split. Every intermediate is lossless
# (a refinement of the gate, a coarsening of the always-Wheeler trie => termination). The result
# is a fast upper bound, tightened by a bounded merge-back cleanup.  Cost: O(s * t^2) in-process,
# ZERO subprocesses (s = splits needed, empirically ~1), vs the greedy's O(t^2) recognizer calls.
# --------------------------------------------------------------------------------------------
def colex_rank(T, label_rank):
    """trie id -> co-lex rank of its incoming string (co-lex compares the LAST label first).
    The empty-string root sorts first (rank 0), which makes the root block A1-first for free."""
    key = [tuple(label_rank[c] for c in reversed(T.string[t])) for t in range(T.n)]
    rank = [0] * T.n
    for r, t in enumerate(sorted(range(T.n), key=lambda t: key[t])):
        rank[t] = r
    return rank


def _block_pos(T, block_of, colex):
    """Position of each block = its rank (by minimum member co-lex) among all blocks."""
    mn = {}
    for t in range(T.n):
        b = block_of[t]
        if b not in mn or colex[t] < mn[b]:
            mn[b] = colex[t]
    return {b: i for i, b in enumerate(sorted(mn, key=lambda b: mn[b]))}


def _colex_check(T, block_of, colex, label_rank):
    """None if the quotient is Wheeler under the co-lex order; else (axiom, head1, head2)."""
    _, bedges, _, _ = dfa.quotient(T, block_of)
    if not bedges:
        return None
    bpos = _block_pos(T, block_of, colex)
    indeg = {}
    allb = set()
    for (u, v, _) in bedges:
        indeg[v] = indeg.get(v, 0) + 1
        allb.add(u)
        allb.add(v)
    zero = [b for b in allb if indeg.get(b, 0) == 0]
    posn = [b for b in allb if indeg.get(b, 0) > 0]
    if zero and posn and max(bpos[b] for b in zero) >= min(bpos[b] for b in posn):
        return ("A1", None, None)
    E = [(u, v, label_rank[l]) for (u, v, l) in bedges]
    for i in range(len(E)):
        u1, v1, a1 = E[i]
        for j in range(len(E)):
            if i == j:
                continue
            u2, v2, a2 = E[j]
            if a1 < a2 and not (bpos[v1] < bpos[v2]):
                return ("A2", v1, v2)
            if a1 == a2 and bpos[u1] < bpos[u2] and not (bpos[v1] <= bpos[v2]):
                return ("A3", v1, v2)
    return None


def wheeler_via_colex_order(T, block_of, colex, label_rank):
    """Public: (is_wheeler_under_colex, violation_or_None). A True is a sound Wheeler witness."""
    v = _colex_check(T, block_of, colex, label_rank)
    return (v is None), v


def _members(block_of, n):
    from collections import defaultdict
    m = defaultdict(list)
    for t in range(n):
        m[block_of[t]].append(t)
    return m


def _split_block_colex(block_of, B, colex, next_id):
    """Split block B into two by co-lex order at the median; second half gets a fresh id."""
    members = sorted((t for t in range(len(block_of)) if block_of[t] == B), key=lambda t: colex[t])
    second = set(members[len(members) // 2:])
    return ([next_id if (block_of[t] == B and t in second) else block_of[t]
             for t in range(len(block_of))], next_id + 1)


def refine(T, label_rank, mode="size", cleanup=True, cleanup_max=64):
    """Refine-from-coarse minimal Wheeler repair (fast). Returns the same dict shape as exact().
    The optional merge-back cleanup is O(blocks^4); it is skipped when the refined partition has
    more than `cleanup_max` blocks (where it both rarely helps and would dominate runtime)."""
    if mode == "size":
        class_of, ncls = dfa.nerode_classes(T)
    elif mode == "edits":
        class_of, ncls = dfa.origin_classes(T)
    else:
        raise ValueError(mode)
    if not T.edges:
        return {"nodes": 1, "block_of": [0] * T.n, "method": f"refine-{mode}",
                "edits": 0 if mode == "edits" else None}

    colex = colex_rank(T, label_rank)
    block_of = list(class_of)
    next_id = max(block_of) + 1
    for _ in range(T.n + 2):                     # bounded by reaching the trie (always Wheeler)
        viol = _colex_check(T, block_of, colex, label_rank)
        if viol is None:
            break
        _, h1, h2 = viol
        mem = _members(block_of, T.n)
        B = next((b for b in (h1, h2) if b is not None and len(mem.get(b, [])) >= 2), None)
        if B is None:                            # split any non-singleton (guarantees progress)
            cand = [b for b, m in mem.items() if len(m) >= 2]
            if not cand:
                break                            # already the trie: cannot happen with a violation
            B = max(cand, key=lambda b: len(mem[b]))
        block_of, next_id = _split_block_colex(block_of, B, colex, next_id)

    if cleanup and len(set(block_of)) <= cleanup_max:
        block_of = _merge_back(T, block_of, class_of, colex, label_rank)
    nb = len(set(block_of))
    out = {"nodes": nb, "block_of": block_of, "method": f"refine-{mode}"}
    if mode == "edits":
        out["edits"] = nb - ncls
    return out


def _merge_back(T, block_of, class_of, colex, label_rank):
    """Bounded cleanup: merge refinement-created blocks within a gate class when the merge stays
    Wheeler (co-lex test). Only touches the few blocks refinement produced -- cheap."""
    from collections import defaultdict
    cls_of_block = {}
    for t in range(T.n):
        cls_of_block.setdefault(block_of[t], class_of[t])
    changed = True
    while changed:
        changed = False
        by_class = defaultdict(list)
        for b in set(block_of):
            by_class[cls_of_block[b]].append(b)
        for blist in by_class.values():
            done = False
            for i in range(len(blist)):
                for j in range(i + 1, len(blist)):
                    trial = [blist[i] if x == blist[j] else x for x in block_of]
                    if _colex_check(T, trial, colex, label_rank) is None:
                        block_of = trial
                        changed = done = True
                        break
                if done:
                    break
            if done:
                break
    return block_of


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


def repair(T, label_rank, mode, method, timeout_ms=10000):
    """Dispatch one (method, mode) repair over a prebuilt trie. method in {exact,greedy,refine}."""
    if method == "exact":
        return exact(T, label_rank, mode, timeout_ms)
    if method == "greedy":
        return greedy(T, label_rank, mode)
    if method == "refine":
        return refine(T, label_rank, mode)
    raise ValueError(method)


if __name__ == "__main__":
    import argparse
    import json
    import time
    ap = argparse.ArgumentParser(description="Minimal Wheeler-graph repair (exact Z3 / greedy / refine).")
    ap.add_argument("dot")
    ap.add_argument("--int", action="store_true")
    ap.add_argument("--method", choices=["exact", "greedy", "refine"], default=None,
                    help="run ONE method (both objectives); default runs exact (both) verbosely")
    ap.add_argument("--mode", choices=["size", "edits", "both"], default="both")
    ap.add_argument("--out", default=None, help="write the repaired DOT here (first mode)")
    ap.add_argument("--json", action="store_true", help="machine-readable output (for the benchmark)")
    ap.add_argument("--timeout-ms", type=int, default=10000)
    args = ap.parse_args()

    nodes, sources, out_adj, edges = dfa.build_graph(args.dot)
    if not dfa.is_acyclic(nodes, out_adj):
        raise SystemExit("input is cyclic; out of scope for lossless node-splitting repair")
    label_rank = bo.rank_labels(edges, args.int)
    T = dfa.determinize(sources, out_adj)
    modes = ["size", "edits"] if args.mode == "both" else [args.mode]
    method = args.method or "exact"

    res = {}
    for m in modes:
        t0 = time.time()
        r = repair(T, label_rank, m, method, args.timeout_ms)
        res[m] = {"nodes": r["nodes"], "edits": r.get("edits"), "seconds": round(time.time() - t0, 4)}
        if args.out and m == modes[0]:
            write_repair(T, r["block_of"], args.out)

    if args.json:
        print(json.dumps({"dot": args.dot, "method": method, "in_nodes": len(nodes),
                          "in_edges": len(edges), "trie_nodes": T.n, "modes": res}))
    else:
        print(f"input    : {len(nodes)} nodes, {len(edges)} edges   (method={method})")
        print(f"trie     : {T.n} nodes")
        for m in modes:
            tag = "min-size " if m == "size" else "min-edits"
            extra = f"  ({res[m]['edits']} duplications)" if m == "edits" else ""
            print(f"{tag}: {res[m]['nodes']} nodes{extra}   [{res[m]['seconds']}s]")
        if args.out:
            print(f"wrote {args.out}")
