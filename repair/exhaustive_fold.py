#!/usr/bin/env python3
"""
exhaustive_fold.py -- INDEPENDENT brute-force optimum for minimal Wheeler-graph repair.

This is the ground-truth optimizer used to VERIFY the Z3 solver (repair/minimize.py). It shares
no logic with the Z3 encoding: it simply enumerates every legal fold of the trie and asks the
brute oracle (verify/brute_oracle.py) whether each quotient is a Wheeler graph, keeping the one
with the fewest nodes.

Legal folds (a partition of the trie's nodes where every block lies inside one equivalence class):
  * min-size : blocks inside Nerode (right-language) classes  -> merges preserve L(G).
  * min-edits: blocks inside origin classes (same subset state) -> no cross-original merges.

Because it is exponential (Bell numbers x n! in the oracle), it is for TINY tries only
(default cap 9 nodes). Its output is the provable optimum the Z3 solver must match.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, HERE)
import brute_oracle as bo  # noqa: E402
import dfa  # noqa: E402


def set_partitions(items):
    """Yield every set partition of `items` as a list of blocks (lists)."""
    items = list(items)
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for parts in set_partitions(rest):
        # put `first` into each existing block...
        for i in range(len(parts)):
            yield parts[:i] + [[first] + parts[i]] + parts[i + 1:]
        # ...or into a new block of its own
        yield [[first]] + parts


def within_class_partitions(class_of, n):
    """Yield global block_of arrays (list trie-id -> block-id) ranging over all partitions that
    merge only WITHIN a class (no block spans two classes)."""
    from itertools import product
    groups = {}
    for t in range(n):
        groups.setdefault(class_of[t], []).append(t)
    class_ids = sorted(groups)
    per_class = [list(set_partitions(groups[c])) for c in class_ids]
    for combo in product(*per_class):
        block_of = [None] * n
        bid = 0
        for blocks in combo:
            for block in blocks:
                for t in block:
                    block_of[t] = bid
                bid += 1
        yield block_of


def quotient_is_wheeler(T, block_of, label_rank):
    """Build the quotient graph and decide Wheeler-ness with the brute oracle."""
    blocks, bedges, _, _ = dfa.quotient(T, block_of)
    if not bedges:
        return True  # no edges -> vacuously Wheeler (empty/edge-free graph)
    nodes = sorted({b for e in bedges for b in (e[0], e[1])})
    nodes = [str(b) for b in nodes]
    edges = [(str(bt), str(bh), a) for (bt, bh, a) in bedges]
    return bo.is_wheeler(nodes, edges, label_rank)


def exhaustive_min(T, class_of, label_rank, max_nodes=9):
    """Smallest #blocks over all within-class folds of T that are Wheeler. Returns
    (min_blocks, witness_block_of) or (None, None) if too large to enumerate."""
    if T.n > max_nodes:
        return None, None
    best = None
    best_block = None
    for block_of in within_class_partitions(class_of, T.n):
        nb = len(set(block_of))
        if best is not None and nb >= best:
            continue  # cannot improve
        if quotient_is_wheeler(T, block_of, label_rank):
            best = nb
            best_block = list(block_of)
    return best, best_block


def min_size(T, label_rank, max_nodes=9):
    cls, _ = dfa.nerode_classes(T)
    return exhaustive_min(T, cls, label_rank, max_nodes)


def min_edits(T, label_rank, max_nodes=9):
    cls, noc = dfa.origin_classes(T)
    nb, block = exhaustive_min(T, cls, label_rank, max_nodes)
    edits = None if nb is None else nb - noc
    return nb, edits, block, noc


def repair_optima(path, int_mode=False, max_nodes=9):
    """Convenience: load a DOT, return a dict of exhaustive optima (trie/min-size/min-edits)."""
    nodes, sources, out_adj, edges = dfa.build_graph(path)
    label_rank = bo.rank_labels(edges, int_mode)
    T = dfa.determinize(sources, out_adj)
    sz_blocks, sz_block = min_size(T, label_rank, max_nodes)
    ed_blocks, ed_edits, ed_block, noc = min_edits(T, label_rank, max_nodes)
    return {
        "in_nodes": len(nodes), "in_edges": len(edges),
        "trie_nodes": T.n, "origin_classes": noc,
        "min_size_nodes": sz_blocks, "min_size_block": sz_block,
        "min_edits_nodes": ed_blocks, "min_edits": ed_edits, "min_edits_block": ed_block,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Exhaustive brute-force minimal Wheeler repair (tiny graphs).")
    ap.add_argument("dot")
    ap.add_argument("--int", action="store_true")
    ap.add_argument("--max-nodes", type=int, default=9)
    args = ap.parse_args()
    r = repair_optima(args.dot, args.int, args.max_nodes)
    print(f"input        : {r['in_nodes']} nodes, {r['in_edges']} edges")
    print(f"trie         : {r['trie_nodes']} nodes  (origin classes = {r['origin_classes']})")
    print(f"min-size  WG : {r['min_size_nodes']} nodes")
    print(f"min-edits WG : {r['min_edits_nodes']} nodes  ({r['min_edits']} duplications)")
