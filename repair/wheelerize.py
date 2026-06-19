#!/usr/bin/env python3
"""
wheelerize.py -- string-preserving Wheeler-graph repair for DAGs, by node splitting (Phase 5.1).

Given a directed edge-labeled DAG, produce a Wheeler graph that spells EXACTLY the same set of
path-strings (the label strings of paths starting at source nodes, prefix-closed). Strategy: unfold
the DAG into the TRIE of its path-strings -- each trie node is a distinct path-string, and there is
an edge  w --a--> w·a  whenever some source-path spells w·a.

Why this always works for a DAG:
  * A trie is ALWAYS a Wheeler graph: order each node by the co-lexicographic order of its (unique)
    incoming string. Axiom checks:
      - roots-first: the root's incoming string is empty (co-lex smallest);
      - label axiom (a<b ⇒ head earlier): co-lex compares the last char first, so w·a < w'·b;
      - same-label axiom (u<u' ⇒ v≤v'): co-lex(w·a) vs co-lex(w'·a) reduces to co-lex(w) vs co-lex(w').
  * It preserves the path-string set by construction.
So node-splitting repair always succeeds on a DAG. The trie can be larger than the input (worst
case exponential); shrinking it (subset/DFA minimization while staying Wheeler) is future work.

Cyclic graphs are out of scope here (unfolding would be infinite) -> reported; the lossy edge-edit
fallback is a separate path (not yet implemented).

Verification (always run): the output is checked to (a) be accepted by the recognizer, (b) be
accepted by the brute oracle when small enough, and (c) spell the same path-string set as the input.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "verify"))
import brute_oracle as bo  # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")


def build_graph(path):
    """Return (sources, out_adj, edges, label_int) for the input DOT."""
    nodes, edges = bo.parse_dot(path)
    out_adj = {n: [] for n in nodes}
    indeg = {n: 0 for n in nodes}
    for (u, v, l) in edges:
        out_adj[u].append((l, v))
        indeg[v] += 1
    sources = [n for n in nodes if indeg[n] == 0]
    return nodes, sources, out_adj, edges


def is_acyclic(nodes, out_adj):
    """Kahn-style topological check."""
    indeg = {n: 0 for n in nodes}
    for u in nodes:
        for (_, v) in out_adj[u]:
            indeg[v] += 1
    queue = [n for n in nodes if indeg[n] == 0]
    seen = 0
    while queue:
        u = queue.pop()
        seen += 1
        for (_, v) in out_adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return seen == len(nodes)


def path_strings(sources, out_adj, max_nodes=200000):
    """All path-strings from sources (prefix-closed), as a set of label-tuples.
    Also returns the set of (string) trie-nodes reachable. Bounded for a DAG."""
    strings = set()
    # stack of (current_node, string_so_far)
    stack = [(s, ()) for s in sources]
    seen_pairs = set((s, ()) for s in sources)
    while stack:
        node, w = stack.pop()
        strings.add(w)
        for (a, v) in out_adj[node]:
            nw = w + (a,)
            if (v, nw) not in seen_pairs:
                seen_pairs.add((v, nw))
                stack.append((v, nw))
                if len(seen_pairs) > max_nodes:
                    raise RuntimeError(f"trie too large (> {max_nodes} states); aborting")
    return strings


def build_trie(sources, out_adj, max_nodes=200000):
    """Build the trie of path-strings. Returns (trie_edges, num_nodes).
    trie node id = index of its string; edges are (tail_id, head_id, label)."""
    # state of a trie node = the SET of original nodes reachable by that exact string.
    # trie nodes are keyed by the STRING (so it is a tree, guaranteed Wheeler), with `states`
    # used only to compute outgoing transitions.
    from collections import deque
    string_id = {(): 0}
    states = {(): frozenset(sources)}
    trie_edges = []
    q = deque([()])
    while q:
        w = q.popleft()
        S = states[w]
        # gather transitions by label
        nxt = {}
        for u in S:
            for (a, v) in out_adj[u]:
                nxt.setdefault(a, set()).add(v)
        for a in sorted(nxt):
            nw = w + (a,)
            if nw not in string_id:
                string_id[nw] = len(string_id)
                states[nw] = frozenset(nxt[a])
                q.append(nw)
                if len(string_id) > max_nodes:
                    raise RuntimeError(f"trie too large (> {max_nodes} states); aborting")
            trie_edges.append((string_id[w], string_id[nw], a))
    return trie_edges, len(string_id)


def write_trie_dot(trie_edges, path):
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (u, v, a) in trie_edges:
            f.write(f"\tN{u} -> N{v} [ label = {a} ];\n")
        f.write("}\n")


def recognizer_accepts(path, int_labels):
    args = [REC, path] + (["-i"] if int_labels else [])
    rc = subprocess.run(args, capture_output=True).returncode
    return rc == 1


def main():
    ap = argparse.ArgumentParser(description="String-preserving Wheelerization of a DAG (trie unfolding).")
    ap.add_argument("dot", help="input DOT (a DAG)")
    ap.add_argument("-o", "--out", default=None, help="output DOT for the repaired Wheeler graph")
    ap.add_argument("--int", action="store_true", help="labels are integers (recognizer -i)")
    ap.add_argument("--max-nodes", type=int, default=200000)
    args = ap.parse_args()

    nodes, sources, out_adj, edges = build_graph(args.dot)
    print(f"input: {len(nodes)} nodes, {len(edges)} edges, {len(sources)} source(s)")

    if not is_acyclic(nodes, out_adj):
        print("INPUT IS CYCLIC -> string-preserving node-splitting is not finite here.")
        print("Use the lossy edge-edit fallback (not yet implemented). Aborting.")
        sys.exit(2)

    try:
        trie_edges, n_trie = build_trie(sources, out_adj, args.max_nodes)
    except RuntimeError as e:
        print(f"ABORT: {e}")
        sys.exit(3)

    out_path = args.out or (os.path.splitext(args.dot)[0] + ".wheelerized.dot")
    write_trie_dot(trie_edges, out_path)
    print(f"output: {n_trie} nodes, {len(trie_edges)} edges  ->  {out_path}")
    print(f"node blow-up: {len(nodes)} -> {n_trie}  ({n_trie/max(1,len(nodes)):.2f}x)")

    # ---- Verification ----
    ok = True

    # (a) recognizer accepts the result as a Wheeler graph. Trie labels are the original labels;
    # if they are integers use -i, else default.
    rec_ok = recognizer_accepts(out_path, args.int)
    print(f"[verify] recognizer says Wheeler: {rec_ok}")
    ok &= rec_ok

    # (b) brute oracle accepts (only if small enough for n!).
    o_nodes, o_edges = bo.parse_dot(out_path)
    if len(o_nodes) <= 9:
        rank = bo.rank_labels(o_edges, int_mode=args.int)
        oracle_ok = bo.is_wheeler(o_nodes, o_edges, rank)
        print(f"[verify] brute oracle says Wheeler: {oracle_ok}")
        ok &= oracle_ok
    else:
        print(f"[verify] brute oracle skipped (output has {len(o_nodes)} nodes > 9)")

    # (c) path-string set preserved.
    in_strings = path_strings(sources, out_adj, args.max_nodes)
    _, o_sources, o_out, _ = build_graph(out_path)
    out_strings = path_strings(o_sources, o_out, args.max_nodes)
    preserved = (in_strings == out_strings)
    print(f"[verify] path-string set preserved: {preserved} "
          f"(|input strings|={len(in_strings)}, |output strings|={len(out_strings)})")
    if not preserved:
        only_in = list(in_strings - out_strings)[:5]
        only_out = list(out_strings - in_strings)[:5]
        print(f"         sample only-in-input:  {only_in}")
        print(f"         sample only-in-output: {only_out}")
    ok &= preserved

    print("RESULT:", "OK -- repaired to a Wheeler graph, strings preserved. ✓" if ok else "FAILED ✗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
