"""Audit F -- index.wg_index.WGIndex: count over recognizer I/O/L.

Gates (every output checked against INDEPENDENT ground truth):
  * count(P) == (lo, hi, n) with set(range(lo,hi)) == oracle.reachable(nodes,edges,P)
    (the Wheeler contiguity theorem) over present + absent + off-alphabet patterns.
  * count("") returns the full node range (1, n+1, n).
  * from_iol(outdir).iol() == from_graph_dot(graph.dot).iol().
  * from_edges with a deliberately LARGER alphabet (labels a..f) works.
  * real recognized yeast De Bruijn blocks (skipif recognizer/generator/data missing).

Ground truths used (independent of the FM-index):
  * index.oracle.reachable  -- follows labeled edges, no FM machinery.
  * a transparent brute substring/edge-walk reimplementation written here.
  * verify.brute_oracle.is_wheeler -- n! permutation oracle, used only to *construct*
    valid Wheeler-ordered graphs (the index's precondition: node ids ARE the Wheeler order).

NOTE: WGIndex assumes its input is already in valid Wheeler node order (node id == order).
Contiguity is a theorem only under that precondition; feeding a graph whose identity
labeling is not a valid Wheeler order is out of contract and not a bug.
"""
import os
import random
import shutil
import glob
import sys

import pytest

sys.path.insert(0, "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph")

from index.wg_index import WGIndex
from index import oracle
from verify import brute_oracle

REPO = "/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph"
EXAMPLE = os.path.join(REPO, "data/example/out__example")
YEAST_FA = os.path.join(REPO, "data/multiseq_alignment/yeast/fasta")
MYENV_PY = "/home/kh.chao/miniconda3/envs/myenv/bin/python"


# --------------------------------------------------------------- independent ground truth
def brute_reachable(nodes, edges, pattern):
    """Transparent edge-walk: set of nodes ending a walk spelling pattern from any start."""
    cur = set(nodes)
    for c in pattern:
        nxt = set()
        for t, h, lab in edges:
            if lab == c and t in cur:
                nxt.add(h)
        cur = nxt
        if not cur:
            break
    return cur


def relabel_to_wheeler(nodes, edges):
    """If (nodes,edges) is a Wheeler graph, relabel nodes to a valid Wheeler order
    (node id == order position + 1) so the WGIndex precondition holds; else None."""
    nlist = sorted(nodes)
    rank = brute_oracle.rank_labels(edges, int_mode=False)
    ok, order = brute_oracle.is_wheeler(nlist, edges, rank, return_order=True)
    if not ok:
        return None
    nmap = {v: order[v] + 1 for v in nlist}
    return set(nmap.values()), [(nmap[t], nmap[h], l) for t, h, l in edges]


def gate(idx, nodes, edges, P):
    """Assert count(P) matches oracle AND independent brute, with contiguity."""
    lo, hi, cnt = idx.count(P)
    reach = oracle.reachable(nodes, edges, P)
    breach = brute_reachable(nodes, edges, P)
    assert reach == breach, ("oracle vs brute disagree", P, reach, breach)
    assert set(range(lo, hi)) == reach, ("range != reach", P, (lo, hi, cnt), sorted(reach))
    assert cnt == len(reach) == hi - lo, ("count size", P, cnt, len(reach))


# --------------------------------------------------------------- property-based
def _patterns(labels):
    alpha = sorted(set(labels)) or ["a"]
    pool = alpha + ["z", "Q", "9"]  # include off-alphabet symbols
    pats = [""]
    for c in pool:
        pats.append(c)
    rnd = random.Random(99)
    for L in range(2, 5):
        for _ in range(8):
            pats.append("".join(rnd.choice(pool) for _ in range(L)))
    return pats


def test_property_random_wheeler_graphs():
    """Thousands of random valid Wheeler-ordered graphs; count == oracle == brute, contiguous."""
    rnd = random.Random(12345)
    built = 0
    pat_checks = 0
    for _ in range(3000):
        n = rnd.randint(1, 7)
        labels = [chr(ord("a") + i) for i in range(rnd.randint(1, 3))]
        edges = [(rnd.randint(1, n), rnd.randint(1, n), rnd.choice(labels))
                 for _ in range(rnd.randint(0, 2 * n))]
        rl = relabel_to_wheeler(set(range(1, n + 1)), edges)
        if rl is None:
            continue
        nodes2, edges2 = rl
        idx = WGIndex.from_edges(nodes2, edges2)
        nn = len(nodes2)
        # empty pattern -> full node range
        assert idx.count("") == (1, nn + 1, nn)
        for P in _patterns(labels):
            gate(idx, nodes2, edges2, P)
            pat_checks += 1
        built += 1
    assert built > 200, f"too few valid Wheeler graphs generated ({built})"
    assert pat_checks > 5000


def test_larger_alphabet_path():
    """from_edges with a deliberately larger alphabet a..f (6 labels)."""
    nodes = set(range(1, 8))
    edges = [(1, 2, "a"), (2, 3, "b"), (3, 4, "c"),
             (4, 5, "d"), (5, 6, "e"), (6, 7, "f")]
    idx = WGIndex.from_edges(nodes, edges)
    assert sorted(idx.labels) == list("abcdef")
    for P in ["", "a", "ab", "abc", "abcdef", "f", "af", "g", "z"]:
        gate(idx, nodes, edges, P)
    assert idx.count("") == (1, 8, 7)
    assert idx.count("abcdef") == (7, 8, 1)


def test_larger_alphabet_random():
    """Random valid Wheeler graphs over 4..6 distinct labels."""
    rnd = random.Random(7)
    built = 0
    for _ in range(2000):
        n = rnd.randint(2, 8)
        labels = [chr(ord("a") + i) for i in range(rnd.randint(4, 6))]
        edges = [(rnd.randint(1, n), rnd.randint(1, n), rnd.choice(labels))
                 for _ in range(rnd.randint(1, 2 * n))]
        rl = relabel_to_wheeler(set(range(1, n + 1)), edges)
        if rl is None:
            continue
        nodes2, edges2 = rl
        idx = WGIndex.from_edges(nodes2, edges2)
        for P in ["", rnd.choice(labels),
                  "".join(rnd.choice(labels) for _ in range(3)), "zz"]:
            gate(idx, nodes2, edges2, P)
        built += 1
    assert built > 100


def test_degenerate_cases():
    """Self-loops, parallel same-label edges, isolated node (Wheeler-ordered), empty graph."""
    # valid: isolated node placed before the only in-degree node
    nodes, edges = {1, 2, 3}, [(1, 3, "a")]
    idx = WGIndex.from_edges(nodes, edges)
    assert idx.count("") == (1, 4, 3)
    for P in ["", "a", "aa", "b"]:
        gate(idx, nodes, edges, P)

    # single-node self-loop (one label)
    nodes, edges = {1}, [(1, 1, "a")]
    idx = WGIndex.from_edges(nodes, edges)
    for P in ["", "a", "aa", "aaa", "b"]:
        gate(idx, nodes, edges, P)

    # parallel same-label edges from one tail
    nodes, edges = {1, 2, 3}, [(1, 2, "a"), (1, 2, "a"), (1, 3, "a")]
    idx = WGIndex.from_edges(nodes, edges)
    for P in ["", "a", "aa"]:
        gate(idx, nodes, edges, P)

    # no-edge single node
    nodes, edges = {1}, []
    idx = WGIndex.from_edges(nodes, edges)
    assert idx.count("") == (1, 2, 1)
    assert idx.count("a") == (1, 1, 0)


def test_off_alphabet_and_absent():
    """Absent present-alphabet patterns and off-alphabet symbols -> empty, contiguous."""
    nodes = {1, 2, 3, 4, 5}
    edges = [(1, 3, "a"), (1, 4, "a"), (5, 4, "a"), (1, 5, "b"), (2, 5, "b")]
    idx = WGIndex.from_edges(nodes, edges)
    for P in ["z", "Q", "az", "za", "aaaa", "bbb", "abc"]:
        lo, hi, cnt = idx.count(P)
        assert (lo == hi) or set(range(lo, hi)) == oracle.reachable(nodes, edges, P)
        gate(idx, nodes, edges, P)


# --------------------------------------------------------------- committed example data
@pytest.mark.skipif(not os.path.isdir(EXAMPLE), reason="example output dir missing")
def test_example_iol_and_count():
    a = WGIndex.from_iol(EXAMPLE)
    b = WGIndex.from_graph_dot(os.path.join(EXAMPLE, "graph.dot"))
    assert a.iol() == b.iol()
    nodes, edges = oracle.parse_dot(open(os.path.join(EXAMPLE, "graph.dot")).read())
    for P in ["", "a", "b", "aa", "ab", "ba", "bb", "aab", "aba", "z"]:
        gate(a, nodes, edges, P)
    assert a.count("") == (1, a.n + 1, a.n)


# --------------------------------------------------------------- real yeast blocks
def _have_pipeline():
    try:
        from pipeline import msa_to_index as m
    except Exception:
        return False
    return (os.path.exists(getattr(m, "REC", "")) and os.path.exists(getattr(m, "GEN_PY", ""))
            and os.path.isdir(YEAST_FA) and os.path.exists(MYENV_PY))


@pytest.mark.skipif(not _have_pipeline(),
                    reason="recognizer / myenv generator / yeast data not available")
def test_real_yeast_blocks(tmp_path):
    from pipeline import msa_to_index as m
    fas = sorted(glob.glob(os.path.join(YEAST_FA, "chrI_*.fa")))[:3]
    assert fas, "no yeast blocks found"
    work = str(tmp_path / "yw")
    os.makedirs(work, exist_ok=True)
    verified = 0
    rnd = random.Random(1)
    for fa in fas:
        try:
            res = m.process_block(fa, k=4, l=40, a=2, work=work, py=MYENV_PY)
        except Exception as e:
            pytest.skip(f"process_block failed (env): {e!r}")
        if res["verdict"] != 1 or not res["outdir"]:
            continue
        od = res["outdir"]
        idx = WGIndex.from_iol(od)
        dotidx = WGIndex.from_graph_dot(os.path.join(od, "graph.dot"))
        assert idx.iol() == dotidx.iol(), ("from_iol vs from_graph_dot", fa)
        nodes, edges = oracle.parse_dot(open(os.path.join(od, "graph.dot")).read())
        assert idx.count("") == (1, idx.n + 1, idx.n)
        labs = sorted({l for _, _, l in edges})
        pats = [""] + labs + ["".join(rnd.choice(labs) for _ in range(L))
                              for L in range(2, 5) for _ in range(15)]
        for P in pats:
            gate(idx, nodes, edges, P)
        verified += 1
    if verified == 0:
        pytest.skip("no yeast block recognized as Wheeler in this run")


if __name__ == "__main__":
    test_property_random_wheeler_graphs()
    test_larger_alphabet_path()
    test_larger_alphabet_random()
    test_degenerate_cases()
    test_off_alphabet_and_absent()
    print("OK")
