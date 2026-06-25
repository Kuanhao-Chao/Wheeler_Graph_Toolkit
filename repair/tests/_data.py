"""Shared fixtures/data for the repair pytest suite (canonical graphs + verified optima).

Self-contained sys.path setup so it imports cleanly whether pytest collects it or a test module
does `from _data import ...`. All expected values were computed and cross-checked against the
brute-force oracle + exhaustive folder (see EXPECTED)."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(ROOT, "verify"), os.path.join(ROOT, "repair")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import brute_oracle as bo  # noqa: E402
import dfa  # noqa: E402

# Canonical graphs (edge lists; string labels). Cover: WG chain, the classic 4-node non-WG,
# diamond (cross-origin merge), single/parallel edges, multi-source, nondeterministic original,
# deep chain, wide fan-out.
GRAPHS = {
    "t_chain":      [("a", "b", "x"), ("b", "c", "x")],
    "t_nonwg":      [("s", "n1", "a"), ("s", "n2", "b"), ("n1", "n3", "b"), ("n2", "n3", "a")],
    "diamond":      [("s", "a", "x"), ("s", "b", "y"), ("a", "t", "z"), ("b", "t", "z")],
    "single_edge":  [("a", "b", "x")],
    "parallel_dup": [("a", "b", "x"), ("a", "b", "x")],
    "multi_source": [("s1", "m", "a"), ("s2", "m", "a"), ("m", "t", "b")],
    "nondet":       [("r", "a", "x"), ("r", "b", "x"), ("a", "c", "y"), ("b", "c", "z")],
    "deep_chain":   [("v%d" % i, "v%d" % (i + 1), "a") for i in range(6)],
    "wide_fanout":  [("r", "a", "a"), ("r", "b", "b"), ("r", "c", "c")],
}

# Verified expected values (trie size, determinism, #Nerode classes, #origin classes, exact
# min-size nodes, exact min-edits nodes, edits = node duplications, oracle Wheeler verdict).
EXPECTED = {
    "t_chain":      dict(trie=3, det=True,  nerode=3, origin=3, min_size=3, min_edits=3, edits=0, wg=True),
    "t_nonwg":      dict(trie=5, det=True,  nerode=4, origin=4, min_size=5, min_edits=5, edits=1, wg=False),
    "diamond":      dict(trie=5, det=True,  nerode=3, origin=4, min_size=4, min_edits=4, edits=0, wg=True),
    "single_edge":  dict(trie=2, det=True,  nerode=2, origin=2, min_size=2, min_edits=2, edits=0, wg=True),
    "parallel_dup": dict(trie=2, det=False, nerode=2, origin=2, min_size=2, min_edits=2, edits=0, wg=True),
    "multi_source": dict(trie=3, det=True,  nerode=3, origin=3, min_size=3, min_edits=3, edits=0, wg=True),
    "nondet":       dict(trie=4, det=False, nerode=3, origin=3, min_size=4, min_edits=4, edits=1, wg=False),
    "deep_chain":   dict(trie=7, det=True,  nerode=7, origin=7, min_size=7, min_edits=7, edits=0, wg=True),
    "wide_fanout":  dict(trie=4, det=True,  nerode=2, origin=4, min_size=4, min_edits=4, edits=0, wg=True),
}


def build(edges, int_mode=False):
    """Return a dict with the determinized trie + label rank + graph structure for `edges`."""
    nodes = sorted({t for t, _, _ in edges} | {h for _, h, _ in edges})
    out_adj = {n: [] for n in nodes}
    indeg = {n: 0 for n in nodes}
    for (u, v, l) in edges:
        out_adj[u].append((l, v))
        indeg[v] += 1
    sources = [n for n in nodes if indeg[n] == 0]
    rank = bo.rank_labels(edges, int_mode)
    T = dfa.determinize(sources, out_adj)
    return dict(T=T, label_rank=rank, nodes=nodes, sources=sources, out_adj=out_adj, edges=edges)


def write_dot(edges, path):
    """Write an edge list to a DOT file in the recognizer's contract."""
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (u, v, l) in edges:
            f.write(f"\t{u} -> {v} [ label = {l} ];\n")
        f.write("}\n")
