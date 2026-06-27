"""Incremental Wheeler-NFA repair (trie-free, language-preserving).

Make a non-Wheeler DAG (e.g. a RevDet column automaton) into a Wheeler graph by splitting nodes ONLY
where no Wheeler order can exist -- keeping nondeterminism (same-label branching) rather than
determinizing to the exponential path-string trie. The aim is a graph small enough to beat the
deterministic min-repair (and ideally De Bruijn); the existing FM-index already queries nondeterministic
Wheeler graphs.

Mechanism (heuristic split + the C++ recognizer as ground truth):
  * per-node min/max incoming-string co-lex key by topological DP (no string enumeration -- one key per
    node, length = path depth);
  * obstruction: adjacent nodes (by min-key) whose co-lex [min,max] intervals interleave can't be totally
    ordered -> split the straddling node by partitioning its in-edges around the conflict;
  * `split_node_by_inedges` duplicates the node per in-edge group, each copy keeping ALL out-edges
    (language-preserving; nondeterminism kept);
  * loop until the recognizer accepts; bounded, with a determinization fallback (`minimize.refine`) so it
    always returns a verified Wheeler graph (worst case = the trie).

Run under python3 (z3 for the fallback; recognizer binary). Correctness is guaranteed by verification
(repair/verify_repair.py + index/oracle.py), not by the heuristic being provably minimal.
"""
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import dfa                       # noqa: E402  (re-exports build_graph/is_acyclic/path_strings)
import minimize as mz           # noqa: E402
import brute_oracle as bo       # noqa: E402
from wheelerize import path_strings  # noqa: E402
from pipeline import msa_to_index as m2i  # noqa: E402  (recognize())


# ----------------------------------------------------------------- graph load / io (int node ids)
def load_int(dot):
    nodes, sources, out_adj, edges = dfa.build_graph(dot)
    idmap = {name: i for i, name in enumerate(sorted(nodes, key=str))}
    E = [(idmap[u], idmap[v], l) for (u, v, l) in edges]
    N = set(idmap.values())
    S = [idmap[s] for s in sources]
    return N, S, E


def write_dot(E, path):
    with open(path, "w") as f:
        f.write("strict digraph  {\n")
        for (t, h, l) in sorted(set(E)):
            f.write(f"\t{t} -> {h} [label={l}];\n")
        f.write("}\n")


def _mut(N, E):
    out = {u: [] for u in N}
    inn = {u: [] for u in N}
    for (t, h, l) in E:
        out[t].append((l, h))
        inn[h].append((l, t))
    return out, inn


def _toposort(N, out):
    indeg = {u: 0 for u in N}
    for u in N:
        for (_l, v) in out[u]:
            indeg[v] += 1
    q = deque([u for u in N if indeg[u] == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for (_l, v) in out[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return order


def _colex_keys(N, inn, order, lr):
    """min/max incoming-string co-lex key per node (co-lex = reversed string; key = (label_rank, parent
    key...)). DAG topo DP; one key per node (no enumeration)."""
    mink, maxk = {}, {}
    for v in order:
        ins = inn[v]
        if not ins:                       # source: empty incoming string (sorts first, A1)
            mink[v] = (); maxk[v] = ()
        else:
            mink[v] = min((lr[l],) + mink[u] for (l, u) in ins)
            maxk[v] = max((lr[l],) + maxk[u] for (l, u) in ins)
    return mink, maxk


def _find_split(N, inn, mink, maxk, lr):
    """Pick a node whose co-lex interval interleaves its neighbour's; return (v, assign) where assign[i]
    is the group (0/1) of v's i-th in-edge (in inn[v] order)."""
    order = sorted(N, key=lambda v: (mink[v], v))
    for i in range(len(order) - 1):
        a, b = order[i], order[i + 1]
        if len(inn[a]) >= 2 and maxk[a] > mink[b]:        # a straddles b's start
            assign = [0 if ((lr[l],) + mink[u]) < mink[b] else 1 for (l, u) in inn[a]]
            if 0 in assign and 1 in assign:
                return a, assign
    return None, None


def _fallback_split(N, inn):
    """Progress guarantee: split the max-in-degree node by predecessor (a determinization step)."""
    cand = [v for v in N if len(inn[v]) >= 2]
    if not cand:
        return None, None
    v = max(cand, key=lambda v: len(inn[v]))
    preds = {}
    for (_l, u) in inn[v]:
        preds.setdefault(u, len(preds))
    if len(preds) < 2:                                    # one predecessor, many labels -> split by label
        labs = {}
        assign = [labs.setdefault(l, len(labs)) for (l, _u) in inn[v]]
    else:
        assign = [preds[u] for (_l, u) in inn[v]]
    return (v, assign) if len(set(assign)) >= 2 else (None, None)


def split_node_by_inedges(N, E, v, assign):
    """Duplicate v per in-edge group (assign[i] for v's i-th in-edge, E-scan order); each copy keeps ALL
    of v's out-edges (language-preserving). Returns (N, newE). Mutates N (adds copies)."""
    in_edges = [e for e in E if e[1] == v]
    out_edges = [e for e in E if e[0] == v]
    assert len(assign) == len(in_edges)
    ng = max(assign) + 1
    fresh = max(N) + 1
    copy = [v] + [fresh + k for k in range(ng - 1)]       # group 0 reuses v
    for c in copy[1:]:
        N.add(c)
    newE = [e for e in E if e[0] != v and e[1] != v]      # edges untouched by v
    for gi, e in zip(assign, in_edges):                   # redirect in-edges to their copy
        newE.append((e[0], copy[gi], e[2]))
    for e in out_edges:                                   # duplicate out-edges to every copy
        for c in copy:
            newE.append((c, e[1], e[2]))
    return N, sorted(set(newE))


def is_nondeterministic(E):
    seen = set()
    for (t, _h, l) in E:
        if (t, l) in seen:
            return True
        seen.add((t, l))
    return False


def _recognize(E, work):
    p = os.path.join(work, "wnfa_cur.dot")
    write_dot(E, p)
    return m2i.recognize(p, work, write=False)["verdict"], p


# ----------------------------------------------------------------- the repair
def repair(dot, work, max_rounds=None):
    """Returns a record: {ok, edges, nodes, splits, rounds, nondet, fallback, dot}."""
    os.makedirs(work, exist_ok=True)
    N, S, E = load_int(dot)
    out0, _ = _mut(N, E)
    if not dfa.is_acyclic(N, out0):
        raise ValueError("input is cyclic; out of scope")
    lr = bo.rank_labels(E, False)
    max_rounds = max_rounds or (6 * len(N) + 20)
    splits = 0
    for rnd in range(1, max_rounds + 1):
        verdict, curdot = _recognize(E, work)
        if verdict == 1:
            return {"ok": True, "edges": E, "nodes": sorted(N), "splits": splits, "rounds": rnd,
                    "nondet": is_nondeterministic(E), "fallback": False, "dot": curdot}
        out, inn = _mut(N, E)
        order = _toposort(N, out)
        mink, maxk = _colex_keys(N, inn, order, lr)
        v, assign = _find_split(N, inn, mink, maxk, lr)
        if v is None:
            v, assign = _fallback_split(N, inn)
        if v is None:
            break
        N, E = split_node_by_inedges(N, E, v, assign)
        splits += 1
    # determinization fallback: always Wheeler (the trie quotient)
    return _determinize_fallback(dot, work, splits)


def _determinize_fallback(dot, work, splits):
    nodes, sources, out_adj, edges = dfa.build_graph(dot)
    lr = bo.rank_labels(edges, False)
    T = dfa.determinize(sources, out_adj)
    r = mz.refine(T, lr, mode="size")
    outp = os.path.join(work, "wnfa_fallback.dot")
    mz.write_repair(T, r["block_of"], outp)
    N, S, E = load_int(outp)
    return {"ok": True, "edges": E, "nodes": sorted(N), "splits": splits, "rounds": -1,
            "nondet": is_nondeterministic(E), "fallback": True, "dot": outp}


def lossless(dot, rec):
    """Path-string set preserved between the input DOT and the repaired edges?"""
    N0, S0, E0 = load_int(dot)
    out0, _ = _mut(N0, E0)
    before = path_strings(S0, out0)
    N1 = set(rec["nodes"]); E1 = rec["edges"]
    out1, inn1 = _mut(N1, E1)
    src1 = [u for u in N1 if not inn1[u]]
    after = path_strings(src1, out1)
    return before == after


if __name__ == "__main__":
    import argparse
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("dot")
    ap.add_argument("--work", default=None)
    args = ap.parse_args()
    work = args.work or tempfile.mkdtemp(prefix="wnfa_")
    rec = repair(args.dot, work)
    N0, _, E0 = load_int(args.dot)
    print(f"input: {len(N0)} nodes, {len(E0)} edges")
    print(f"repaired: {len(rec['nodes'])} nodes, {len(rec['edges'])} edges  "
          f"splits={rec['splits']} rounds={rec['rounds']} nondet={rec['nondet']} "
          f"fallback={rec['fallback']}")
    print(f"lossless={lossless(args.dot, rec)}")
