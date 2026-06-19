#!/usr/bin/env python3
"""
check_order.py -- validate ONE given node order against the 3 Wheeler axioms.

The brute oracle (brute_oracle.py) searches all n! orders and is limited to n<=9. But to settle a
backend DISAGREEMENT we don't need to search: a backend that says "Wheeler" produces a concrete
order (the recognizer writes it via -w to out__<stem>/nodes.txt). Checking whether that SINGLE order
satisfies the axioms is O(E^2) and works for ANY n. If the order is valid, the graph IS a Wheeler
graph (a witness exists) regardless of what any other backend says.

Axioms (same as brute_oracle.py:9-14), for edges e1=(u1,v1,a1), e2=(u2,v2,a2) and a position map pi:
  (A1) every in-degree-0 node precedes every in-degree-positive node;
  (A2) a1 < a2            => pi(v1) < pi(v2);
  (A3) a1 == a2, pi(u1) < pi(u2) => pi(v1) <= pi(v2).

Usage:
  python3 verify/check_order.py graph.dot order.txt [--int]
    order.txt: lines "<node_name>\\t<position>" (e.g. the recognizer's nodes.txt). Only the relative
    order of the positions matters; they need not be 1..n.
Exit code: 0 = order is a valid Wheeler order; 1 = it violates an axiom; 2 = bad input.
"""

import argparse
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute_oracle as bo  # noqa: E402


def parse_order(path):
    """Return dict node_name -> position (int). Accepts '<name>\\t<pos>' or '<name> <pos>'."""
    pos = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            pos[parts[0]] = int(parts[1])
    return pos


def check(nodes, edges, label_rank, pos):
    """Return (ok, reason). pos: node->position. Validates A1/A2/A3 on this single order."""
    # all nodes must be positioned, distinctly
    missing = [n for n in nodes if n not in pos]
    if missing:
        return False, f"order missing {len(missing)} node(s), e.g. {missing[:3]}"
    used = [pos[n] for n in nodes]
    if len(set(used)) != len(used):
        return False, "order positions are not distinct"

    # in-degrees (count self-loops too, matching the oracle)
    indeg = {n: 0 for n in nodes}
    for (_, h, _) in edges:
        indeg[h] += 1
    zero_in = [n for n in nodes if indeg[n] == 0]
    pos_in = [n for n in nodes if indeg[n] > 0]

    # A1: every in-degree-0 node precedes every in-degree-positive node.
    if zero_in and pos_in:
        if max(pos[n] for n in zero_in) >= min(pos[n] for n in pos_in):
            return False, "A1: an in-degree-0 node does not precede all in-degree-positive nodes"

    # encode edges as (tail, head, rank)
    E = [(u, v, label_rank[l]) for (u, v, l) in edges]

    # A2 + A3 over ordered pairs
    for i in range(len(E)):
        u1, v1, a1 = E[i]
        for j in range(len(E)):
            if i == j:
                continue
            u2, v2, a2 = E[j]
            if a1 < a2:
                if not (pos[v1] < pos[v2]):
                    return False, (f"A2: label {a1}<{a2} but pos(head {v1})={pos[v1]} "
                                   f">= pos(head {v2})={pos[v2]}")
            elif a1 == a2:
                if pos[u1] < pos[u2] and not (pos[v1] <= pos[v2]):
                    return False, (f"A3: same label {a1}, pos(tail {u1})<pos(tail {u2}) but "
                                   f"pos(head {v1})={pos[v1]} > pos(head {v2})={pos[v2]}")
    return True, "valid Wheeler order"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dot")
    ap.add_argument("order", help="node->position file (e.g. recognizer nodes.txt)")
    ap.add_argument("--int", action="store_true", help="rank labels numerically (recognizer -i)")
    args = ap.parse_args()

    nodes, edges = bo.parse_dot(args.dot)
    label_rank = bo.rank_labels(edges, int_mode=args.int)
    pos = parse_order(args.order)

    ok, reason = check(nodes, edges, label_rank, pos)
    print(f"{'VALID' if ok else 'INVALID'}: {reason}")
    print(f"  nodes={len(nodes)} edges={len(edges)} labels={len(label_rank)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
