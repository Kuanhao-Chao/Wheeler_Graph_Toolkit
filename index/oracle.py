"""Brute-force ground truth for Wheeler-graph pattern queries.

Independent of the FM-index: it just follows labeled edges. For a pattern P, `reachable` returns the
set of nodes that are the end of some walk spelling P from any start node (i.e., the states reachable
by reading P). `count` is its size. The index in `wg_index.py` must agree with this on every pattern.
"""


def parse_dot(text):
    """Return (nodes:set[int], edges:list[(tail,head,label)]) from a recognizer/relabeled DOT whose
    node ids are integers (Wheeler order)."""
    import re
    edge_re = re.compile(r"(\w+)\s*->\s*(\w+)\s*\[\s*label\s*=\s*(\w+)\s*\]")
    nodes, edges = set(), []
    for line in text.splitlines():
        m = edge_re.search(line.replace(" ", "")) or edge_re.search(line)
        if m:
            t, h, lab = int(m.group(1)), int(m.group(2)), m.group(3)
            nodes.update((t, h))
            edges.append((t, h, lab))
    return nodes, edges


def reachable(nodes, edges, pattern):
    """Set of nodes reachable by a walk spelling `pattern` from any start node."""
    cur = set(nodes)
    by_label = {}
    for t, h, lab in edges:
        by_label.setdefault(lab, []).append((t, h))
    for c in pattern:
        nxt = set()
        for t, h in by_label.get(c, ()):
            if t in cur:
                nxt.add(h)
        cur = nxt
        if not cur:
            break
    return cur


def count(nodes, edges, pattern):
    return len(reachable(nodes, edges, pattern))
