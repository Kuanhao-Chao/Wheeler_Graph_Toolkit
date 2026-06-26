"""A transparent Python reference for WGT's De Bruijn MSA->graph construction.

It reproduces `generator/DeBruijnGraph_generator/DeBruijnGraph_generator.py` exactly — same node set
(the distinct (k-1)-mers, with a `$` sentinel), same reverse-built edges (`curr -> prev`, labeled with
the first character of the child/`prev` k-mer), and the same BFS-from-`$` integer node numbering — so
that:
  * faithfulness can be checked by *edge-set equality* against the generator's emitted DOT
    (`index/faithful.py`), proving the generator builds the graph this reference understands, and
  * every node carries its k-mer string (lost in the integer DOT), giving the index a biological
    interpretation (a query range of Wheeler nodes <-> a set of k-mers).

Convention recap (empirically pinned on a controlled input): a path from the `$` source spells the
*reverse* of an input sequence. So a pattern P read forward along graph edges corresponds to
reverse(P) appearing as a substring of an input sequence.
"""
from collections import deque, OrderedDict


def _prep(seq, seqLen):
    """Ungap, cap to seqLen (or full length), append the `$` sentinel. Returns (parsed_string, L)."""
    u = seq.replace("-", "").upper()
    L = len(u) if (seqLen == -1 or seqLen > len(u)) else seqLen
    return u[:L] + "$", L


def build(seqs, k_user, seqLen=-1, alnNum=None):
    """Build the De Bruijn graph of `seqs` exactly as the generator does.

    Returns a dict with:
      n            : node count
      id2kmer      : {node_id: kmer_string}
      kmer2id      : {kmer_string: node_id}
      edges        : set of (tail_id, head_id, label_char)   (label = head/prev kmer's first char)
      source       : node_id of the `$` node (always 0 under the generator's BFS)
    Mirrors the generator: node k-mer length is (k_user - 1); only the first `alnNum` sequences are
    used; sequences are ungapped, capped to seqLen, and `$`-terminated.
    """
    k = k_user - 1
    if alnNum is not None:
        seqs = seqs[:alnNum]
    parsed = [_prep(s, seqLen) for s in seqs]

    # node set = distinct k-mers over all (parsed) sequences
    kmers = set()
    for p, L in parsed:
        for i in range(L + 1):
            kmers.add(p[i:i + k])

    # adjacency: curr -> prev, children kept in first-insertion order, de-duplicated (strict digraph)
    children = OrderedDict((km, []) for km in kmers)
    childset = {km: set() for km in kmers}
    for p, L in parsed:
        prev = None
        for i in range(L + 1):
            curr = p[i:i + k]
            if prev is not None and prev not in childset[curr]:
                childset[curr].add(prev)
                children[curr].append(prev)
            prev = curr

    # BFS from "$" assigns integer ids in pop order (identical to the generator's bfs()).
    assert "$" in kmers, "every sequence is $-terminated, so '$' must be a node"
    kmer2id = {}
    visited = {"$"}
    q = deque(["$"])
    counter = 0
    while q:
        m = q.popleft()
        kmer2id[m] = counter
        counter += 1
        for c in children[m]:
            if c not in visited:
                visited.add(c)
                q.append(c)
    # (any node unreachable from '$' would be unnumbered; the construction guarantees reachability)
    assert len(kmer2id) == len(kmers), "all k-mers must be reachable from the $ source"

    id2kmer = {i: km for km, i in kmer2id.items()}
    edges = set()
    for curr_km, prevs in children.items():
        for prev_km in prevs:
            edges.add((kmer2id[curr_km], kmer2id[prev_km], prev_km[0]))
    return {"n": len(kmers), "id2kmer": id2kmer, "kmer2id": kmer2id,
            "edges": edges, "source": kmer2id["$"]}


def to_dot(g):
    """Render the reference graph in the generator's DOT form (for eyeballing / cross-checks)."""
    lines = ["strict digraph  {"]
    for t, h, lab in sorted(g["edges"]):
        lines.append(f"\tS{t} -> S{h} [ label = {lab} ];")
    lines.append("}")
    return "\n".join(lines) + "\n"
