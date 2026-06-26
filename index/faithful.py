"""Phase 2 gate: prove the De Bruijn graph faithfully represents the MSA.

Two independent checks per alignment:
  (1) EDGE-SET EQUALITY — the actual generator's emitted DOT has exactly the labeled edges the
      transparent reference (`index/debruijn.py`) builds. This proves the generator builds the De
      Bruijn graph this code understands.
  (2) SEQUENCE ROUND-TRIP — for each input sequence, the construction's walk from the `$` source
      spells the reverse of that (ungapped, capped) sequence, and every edge of that walk is present.
      This proves the reference (hence the generator) actually encodes the input sequences.

Together: indexing the graph == indexing the MSA's sequence content (a pattern P read forward on the
graph corresponds to reverse(P) occurring in some sequence).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GEN_DIR = os.path.join(ROOT, "generator", "DeBruijnGraph_generator")
GEN_PY = os.path.join(GEN_DIR, "DeBruijnGraph_generator.py")

sys.path.insert(0, ROOT)
from index import debruijn  # noqa: E402

_EDGE_RE = re.compile(r"^\s*S?(\w+)\s*->\s*S?(\w+)\s*\[\s*label\s*=\s*(\w+)\s*\]\s*;")


def parse_dot_edges(text):
    """Parse 'A -> B [label=x];' lines (generator 'S0 -> S1' or recognizer '1 -> 3' forms).
    Returns (edges:set[(tail,head,label)], nodes:set). tail/head are kept as strings (ids)."""
    edges, nodes = set(), set()
    for line in text.splitlines():
        m = _EDGE_RE.match(line.replace(" ", "") if "label=" in line.replace(" ", "") else line)
        if not m:
            m = _EDGE_RE.match(line)
        if m:
            t, h, lab = m.group(1), m.group(2), m.group(3)
            edges.add((t, h, lab))
            nodes.update((t, h))
    return edges, nodes


def read_fasta(path):
    """Ordered [(id, seq)] via the stdlib (FASTA order == the order the generator reads)."""
    recs, rid, buf = [], None, []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if rid is not None:
                    recs.append((rid, "".join(buf)))
                rid, buf = line[1:].strip(), []
            elif line:
                buf.append(line)
    if rid is not None:
        recs.append((rid, "".join(buf)))
    return recs


def run_generator(fasta, k, l, a, out_dot, py=None):
    """Run the real De Bruijn generator (subprocess, from its own dir) and return its DOT edge set."""
    py = py or sys.executable
    r = subprocess.run([py, GEN_PY, "-o", out_dot, "-k", str(k), "-l", str(l), "-a", str(a),
                        os.path.abspath(fasta)],
                       cwd=GEN_DIR, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(out_dot):
        raise RuntimeError(f"generator failed: {r.stderr.strip()[:300]}")
    edges_str, _ = parse_dot_edges(open(out_dot).read())
    # generator ids are integers in 'S<id>' form -> normalize to int tuples
    return {(int(t), int(h), lab) for (t, h, lab) in edges_str}


def _adj(edges):
    """label-adjacency {tail: {label: [heads]}} from a set of (tail,head,label) int edges."""
    out = {}
    for t, h, lab in edges:
        out.setdefault(t, {}).setdefault(lab, []).append(h)
    return out


def spellable(edges, source, pattern):
    """Is `pattern` spellable by a walk starting at `source`, following edge labels (DFS)? This is a
    genuine decode of the graph, independent of how it was built."""
    adj = _adj(edges)
    stack = [(source, 0)]
    seen = set()
    while stack:
        node, i = stack.pop()
        if i == len(pattern):
            return True
        if (node, i) in seen:
            continue
        seen.add((node, i))
        for h in adj.get(node, {}).get(pattern[i], []):
            stack.append((h, i + 1))
    return False


def _ungap_cap(seq, seqLen):
    u = seq.replace("-", "").upper()
    return u[:(len(u) if (seqLen == -1 or seqLen > len(u)) else seqLen)]


def check_faithful(fasta, k, l, a, py=None, work_dot=None):
    """Run both faithfulness checks. Returns a result dict with ok/details; raises only on tool error."""
    seqs = [s for _id, s in read_fasta(fasta)][:a]
    g = debruijn.build(seqs, k, seqLen=l, alnNum=a)
    work_dot = work_dot or (os.path.splitext(fasta)[0] + ".genref.dot")
    gen_edges = run_generator(fasta, k, l, a, work_dot, py=py)

    # (1) edge-set equality: the generator builds exactly the reference De Bruijn graph
    edges_equal = (g["edges"] == gen_edges)

    # (2) decode: on the GENERATOR's graph, reverse(each input sequence) is spellable from the $ source
    #     (source = node 0 under the generator's BFS-from-$ numbering). Non-circular: walks the emitted
    #     graph, recovering sequence content the construction's reverse spelling produced.
    decode_ok = True
    for s in seqs:
        u = _ungap_cap(s, l)
        if u and not spellable(gen_edges, g["source"], u[::-1]):
            decode_ok = False
    return {
        "fasta": os.path.basename(fasta), "k": k, "l": l, "a": a,
        "n_nodes": g["n"], "n_edges": len(g["edges"]),
        "edges_equal": edges_equal, "decode_ok": decode_ok,
        "ok": edges_equal and decode_ok,
        "only_ref": len(g["edges"] - gen_edges), "only_gen": len(gen_edges - g["edges"]),
    }
