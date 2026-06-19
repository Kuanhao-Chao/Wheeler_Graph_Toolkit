#!/usr/bin/env python3
"""
brute_oracle.py -- a trivially-correct, brute-force Wheeler-graph decision oracle.

This is GROUND TRUTH for verifying the WGT recognizer. It shares no code or logic
with the recognizer or the exponential baseline, so it is an independent check.

A directed edge-labeled graph G = (V, E) with a label rank on edges is a *Wheeler graph*
iff there exists a total order `pi` on V (a bijection V -> {0,1,...,n-1}) such that:

  (A1) every node with in-degree 0 precedes every node with in-degree > 0;
  (A2) for edges e1=(u1,v1,a1) and e2=(u2,v2,a2):  a1 < a2  =>  pi(v1) < pi(v2);
  (A3) for edges e1=(u1,v1,a) and e2=(u2,v2,a) with the SAME label:
                 pi(u1) < pi(u2)  =>  pi(v1) <= pi(v2).

We decide membership by brute force: enumerate ALL n! total orders and test the three
axioms directly. ACCEPT iff some order satisfies all of them. This is exponential and is
intended only for small n (default cap n <= 9), which is exactly where recognizer bugs are
findable and where exhaustive ground truth is feasible.

Input: a DOT file in the recognizer's contract. We replicate the recognizer's parsing
(wg.cpp:106-128) so the two tools always see the SAME graph:
  - nodes are inferred ONLY from edges (standalone node declarations are ignored);
  - edge lines, after whitespace removal, match  (\\w+)->(\\w+)\\[label=(\\w+)\\];
  - label rank: distinct label strings sorted lexicographically (default), or distinct
    integers sorted numerically with --int (matches recognizer's default vs -i).

Output (stdout), one line: "<verdict>\\t<num_nodes>\\t<path>"
  verdict = 1  if G IS a Wheeler graph
  verdict = 0  if G is NOT a Wheeler graph
  verdict = -1 if G could not be decided (too many nodes for the cap)  -> see --max-n
Exit code mirrors verdict for convenience (1 / 0 / 2), but parse stdout, not the exit code.
"""

import argparse
import re
import sys
from itertools import permutations

EDGE_RE = re.compile(r"(\w+)->(\w+)\[label=(\w+)\];")


def parse_dot(path):
    """Return (nodes, edges) where nodes is a sorted list of node names inferred
    ONLY from edges, and edges is a list of (tail, head, label_str) tuples.
    Mirrors recognizer/src/wg.cpp:106-128."""
    edges = []
    node_set = set()
    with open(path) as fh:
        for line in fh:
            # recognizer erases ' '; we erase all whitespace (equivalent for the
            # space-delimited DOT the generators emit, and more robust to tabs).
            stripped = re.sub(r"\s+", "", line)
            m = EDGE_RE.search(stripped)
            if m:
                tail, head, label = m.group(1), m.group(2), m.group(3)
                edges.append((tail, head, label))
                node_set.add(tail)
                node_set.add(head)
    return sorted(node_set), edges


def rank_labels(edges, int_mode):
    """Map each distinct label string to an integer rank, matching the recognizer:
    lexicographic over strings (default) or numeric over ints (--int)."""
    labels = {e[2] for e in edges}
    if int_mode:
        ordered = sorted(labels, key=lambda s: int(s))
    else:
        ordered = sorted(labels)
    return {lab: i for i, lab in enumerate(ordered)}


def is_wheeler(nodes, edges, label_rank, return_order=False):
    """Brute-force decide Wheeler-ness. Returns True/False (or (bool, order) if
    return_order). `order` is a dict node->position for the first satisfying order."""
    n = len(nodes)

    # Encode edges as (tail_idx, head_idx, label_rank) over node indices 0..n-1.
    idx = {name: i for i, name in enumerate(nodes)}
    E = [(idx[t], idx[h], label_rank[l]) for (t, h, l) in edges]

    # in-degree per node index (for A1).
    indeg = [0] * n
    for (_, h, _) in E:
        indeg[h] += 1
    zero_in = [i for i in range(n) if indeg[i] == 0]
    pos_in = [i for i in range(n) if indeg[i] > 0]

    # Empty graph (no nodes) is vacuously Wheeler. Do NOT shortcut n==1: a single node can carry
    # self-loops, and two self-loops with different labels violate A2 (a<b needs pos(v)<pos(v)).
    # n==1 falls through to the permutation loop below (one trivial order, but axioms still checked).
    if n == 0:
        return (True, {}) if return_order else True

    # Enumerate every assignment of nodes to positions. perm[i] = position of node i.
    base = list(range(n))
    for perm in permutations(base):
        # A1: all zero-in-degree nodes precede all positive-in-degree nodes.
        if zero_in and pos_in:
            if max(perm[i] for i in zero_in) >= min(perm[i] for i in pos_in):
                continue

        ok = True
        # A2 + A3: check every ordered pair of edges.
        for i in range(len(E)):
            u1, v1, a1 = E[i]
            for j in range(len(E)):
                if i == j:
                    continue
                u2, v2, a2 = E[j]
                if a1 < a2:
                    if not (perm[v1] < perm[v2]):  # A2
                        ok = False
                        break
                elif a1 == a2:
                    if perm[u1] < perm[u2] and not (perm[v1] <= perm[v2]):  # A3
                        ok = False
                        break
            if not ok:
                break

        if ok:
            if return_order:
                return True, {nodes[i]: perm[i] for i in range(n)}
            return True

    return (False, None) if return_order else False


def main():
    ap = argparse.ArgumentParser(description="Brute-force Wheeler-graph oracle (ground truth).")
    ap.add_argument("dot", help="input DOT file")
    ap.add_argument("--int", action="store_true",
                    help="treat labels as integers when ranking (matches recognizer -i)")
    ap.add_argument("--max-n", type=int, default=9,
                    help="refuse graphs with more nodes than this (default 9; n! blows up)")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print the satisfying order (if any) and graph stats to stderr")
    args = ap.parse_args()

    nodes, edges = parse_dot(args.dot)
    label_rank = rank_labels(edges, args.int)
    n = len(nodes)

    if args.verbose:
        print(f"nodes={n} edges={len(edges)} labels={len(label_rank)} "
              f"rank={label_rank}", file=sys.stderr)

    if n > args.max_n:
        print(f"-1\t{n}\t{args.dot}")
        if args.verbose:
            print(f"UNDECIDED: n={n} exceeds --max-n={args.max_n}", file=sys.stderr)
        sys.exit(2)

    verdict, order = is_wheeler(nodes, edges, label_rank, return_order=True)
    print(f"{1 if verdict else 0}\t{n}\t{args.dot}")
    if args.verbose:
        if verdict:
            print(f"WHEELER; order={order}", file=sys.stderr)
        else:
            print("NOT_WHEELER", file=sys.stderr)
    sys.exit(1 if verdict else 0)


if __name__ == "__main__":
    main()
