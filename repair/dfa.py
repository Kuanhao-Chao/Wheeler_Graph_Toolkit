#!/usr/bin/env python3
"""
dfa.py -- shared front-end for minimal Wheeler-graph repair (Phase 5.2).

Given an edge-labeled DAG G, this module builds the common substrate the minimal-repair
solvers (repair/minimize.py) operate on:

  * determinize G into the TRIE T = the prefix tree of its path-string language L(G)
    (subset construction; one node per distinct incoming string -- same construction as
    repair/wheelerize.build_trie, extended to also record each trie node's incoming string
    and its `origin` = the SET of original nodes it represents);
  * compute right-language / Nerode classes on T (acyclic DFA minimization), so a MERGE of
    two trie nodes is language-preserving IFF they share a class;
  * build quotient graphs from a partition of T's nodes, plus language / label utilities.

Two repair objectives are quotients of T:
  - min-size : merge trie nodes with EQUAL right-language (Nerode-respecting). Smallest
               deterministic Wheeler graph spelling L(G).
  - min-edits: merge trie nodes with EQUAL origin set (origin-respecting), i.e. fewest
               node-duplications of the (determinized) original. Since same-origin trie
               nodes always share a right-language, origin-respecting => Nerode-respecting,
               so min-size <= size(min-edits).

Reuses verify/brute_oracle.py (parser, label ranks) and repair/wheelerize.py utilities.
DAG inputs only (cycles -> infinite language). Read-only with respect to the input graph.
"""

import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, HERE)
import brute_oracle as bo  # noqa: E402
from wheelerize import build_graph, path_strings, is_acyclic  # noqa: E402


class Trie:
    """Determinized prefix tree of L(G). Node ids are 0..n-1; root is 0 (empty string)."""
    __slots__ = ("string", "origin", "out", "edges", "n", "root")

    def __init__(self):
        self.string = []   # id -> tuple of label strings (the unique incoming string)
        self.origin = []   # id -> frozenset(original node names) it represents (subset state)
        self.out = []      # id -> dict {label_str: head_id}  (deterministic by construction)
        self.edges = []    # list of (tail_id, head_id, label_str)
        self.n = 0
        self.root = 0


def determinize(sources, out_adj, max_nodes=200000):
    """Subset-construction trie of the path-string language. Mirrors wheelerize.build_trie
    but records per-node string + origin set so we can fold it later."""
    T = Trie()
    string_id = {(): 0}
    T.string.append(())
    T.origin.append(frozenset(sources))
    T.out.append({})
    states = {(): frozenset(sources)}
    q = deque([()])
    while q:
        w = q.popleft()
        wid = string_id[w]
        S = states[w]
        nxt = {}
        for u in S:
            for (a, v) in out_adj[u]:
                nxt.setdefault(a, set()).add(v)
        for a in sorted(nxt):
            nw = w + (a,)
            if nw not in string_id:
                nid = len(string_id)
                string_id[nw] = nid
                T.string.append(nw)
                T.origin.append(frozenset(nxt[a]))
                T.out.append({})
                states[nw] = frozenset(nxt[a])
                q.append(nw)
                if len(string_id) > max_nodes:
                    raise RuntimeError(f"trie too large (> {max_nodes} states); aborting")
            hid = string_id[nw]
            T.out[wid][a] = hid
            T.edges.append((wid, hid, a))
    T.n = len(string_id)
    return T


def nerode_classes(T):
    """Right-language equivalence classes on T (acyclic DFA minimization).
    Two trie nodes are equivalent iff they spell the same set of continuation strings.
    Returns (class_of: list[int], num_classes). class_of[t] is t's class id.

    The trie is a DAG and every node's string is strictly longer than its parent's, so
    processing nodes by DECREASING string length guarantees children are signed before
    parents. sig(t) = frozenset of (label, sig(child)); equal sig <=> equal right-language."""
    sig = [None] * T.n
    for t in sorted(range(T.n), key=lambda i: len(T.string[i]), reverse=True):
        sig[t] = frozenset((a, sig[h]) for (a, h) in T.out[t].items())
    classes = {}
    class_of = [0] * T.n
    for t in range(T.n):
        if sig[t] not in classes:
            classes[sig[t]] = len(classes)
        class_of[t] = classes[sig[t]]
    return class_of, len(classes)


def origin_classes(T):
    """Origin equivalence classes on T: two trie nodes share a class iff identical origin
    set (subset state). For a deterministic original these are singletons {v}, so a class =
    one original node; merging within a class = NOT duplicating that node. Returns
    (class_of, num_classes)."""
    classes = {}
    class_of = [0] * T.n
    for t in range(T.n):
        key = T.origin[t]
        if key not in classes:
            classes[key] = len(classes)
        class_of[t] = classes[key]
    return class_of, len(classes)


def quotient(T, block_of):
    """Merge trie nodes by the partition `block_of` (list: trie id -> block id, any hashable).
    Returns (blocks_sorted, bedges_sorted, sources, out_adj) for the quotient graph, where
    bedges are deduped (block_tail, block_head, label) triples (parallel edges collapse)."""
    bedges = set()
    for (u, h, a) in T.edges:
        bedges.add((block_of[u], block_of[h], a))
    blocks = sorted(set(block_of))
    indeg = {b: 0 for b in blocks}
    out_adj = {b: [] for b in blocks}
    for (bt, bh, a) in bedges:
        out_adj[bt].append((a, bh))
        indeg[bh] += 1
    sources = [b for b in blocks if indeg[b] == 0]
    return blocks, sorted(bedges), sources, out_adj


def write_quotient_dot(blocks, bedges, path, prefix="Q"):
    """Write a quotient graph to DOT in the recognizer's contract. Block ids are renamed to
    contiguous Q0,Q1,... so node names are always \\w+."""
    idx = {b: i for i, b in enumerate(sorted(blocks))}
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (bt, bh, a) in bedges:
            f.write(f"\t{prefix}{idx[bt]} -> {prefix}{idx[bh]} [ label = {a} ];\n")
        f.write("}\n")
    return idx


def is_deterministic(out_adj):
    """True iff no node has two out-edges with the same label (forward-deterministic). For
    such graphs the trie's origin sets are singletons and 'min-edits vs the original' is
    exactly 'vs the input'; otherwise min-edits is measured vs the determinized graph."""
    for u, lst in out_adj.items():
        seen = set()
        for (a, _) in lst:
            if a in seen:
                return False
            seen.add(a)
    return True


def label_set(edges):
    """The set of distinct label strings -- the rank space. Must be identical input vs output
    or A2 comparisons change meaning (silent-failure guard)."""
    return {e[2] for e in edges}


def quotient_strings(sources, out_adj, max_nodes=200000):
    """Path-string set of a quotient (sources, out_adj). Thin wrapper over path_strings."""
    return path_strings(sources, out_adj, max_nodes)


# --------------------------------------------------------------------------------------------
# Self-test gate (Step 1): determinize a DOT, verify the trie and the minimal DFA preserve the
# language and the label set, and that the minimal DFA is a DAG.
# --------------------------------------------------------------------------------------------
def _selftest(path, int_mode=False):
    nodes, sources, out_adj, edges = build_graph(path)
    print(f"input: {len(nodes)} nodes, {len(edges)} edges, {len(sources)} source(s), "
          f"deterministic={is_deterministic(out_adj)}, acyclic={is_acyclic(nodes, out_adj)}")
    L_in = path_strings(sources, out_adj)
    labels_in = label_set(edges)

    T = determinize(sources, out_adj)
    print(f"trie: {T.n} nodes, {len(T.edges)} edges")

    # identity quotient == the trie itself: must preserve L and labels
    blocks, bedges, qs, qadj = quotient(T, list(range(T.n)))
    L_trie = path_strings(qs, qadj)
    labels_trie = {a for (_, _, a) in bedges}
    assert L_trie == L_in, f"TRIE changed language! lost={list(L_in-L_trie)[:3]} gained={list(L_trie-L_in)[:3]}"
    assert labels_trie <= labels_in and (labels_trie == labels_in or len(L_in) <= 1), \
        f"TRIE label set changed: {labels_in} -> {labels_trie}"
    print(f"  [gate] trie preserves L ({len(L_in)} strings) and labels: OK")

    # minimal DFA (Nerode quotient): preserves L, identical labels, still a DAG
    cls, ncls = nerode_classes(T)
    mblocks, mbedges, ms, madj = quotient(T, cls)
    L_min = path_strings(ms, madj)
    labels_min = {a for (_, _, a) in mbedges}
    assert L_min == L_in, "minimal DFA changed the language!"
    assert labels_min == labels_trie, "minimal DFA changed the label set!"
    mnodes = sorted({b for e in mbedges for b in (e[0], e[1])} | set(mblocks))
    is_dag = is_acyclic(mnodes, madj)
    print(f"  minimal DFA: {ncls} classes, {len(mbedges)} edges, DAG={is_dag}")
    assert is_dag, "minimal DFA is not a DAG (unexpected for a finite language)!"
    print(f"  [gate] minimal DFA preserves L and labels and is a DAG: OK")

    oc, noc = origin_classes(T)
    print(f"  origin classes: {noc} (== input nodes for a deterministic graph: "
          f"{noc == len(nodes) if is_deterministic(out_adj) else 'n/a'})")
    print("SELFTEST OK")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="dfa.py self-test / inspector")
    ap.add_argument("dot")
    ap.add_argument("--int", action="store_true")
    args = ap.parse_args()
    _selftest(args.dot, args.int)
