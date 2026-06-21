#!/usr/bin/env python3
"""
fasta_to_wg.py -- turnkey "MSA -> Wheeler graph" pipeline for WGT.

Given a multiple-sequence-alignment (MSA) FASTA, build a graph from it with one of WGT's three
constructions, hand it to the recognizer, and report whether it is a Wheeler graph (with size and
timing). This is a thin wrapper that chains the existing generators and recognizer -- it adds no new
graph logic.

The three constructions (all under generator/):
  * debruijn : the order-(k-1) De Bruijn graph of the sequences' k-mers, with identical k-mers merged
               into one node and each edge labelled by the incoming character. Compact; Wheeler-ness
               depends on k and the sequences (~half of real gene MSAs at small k).
  * revdet   : the reverse-deterministic column automaton -- parse the alignment columns and merge
               states so that, reading backwards, each (state,label) has one predecessor. Tends to be
               a Wheeler graph (~80% of real gene MSAs) because the column order supplies a valid order.
  * trie     : the prefix tree of the (ungapped) sequences. Rarely a Wheeler graph (converging paths
               break axioms A2/A3), but a useful stress input.

A Wheeler graph admits a total node order satisfying: (A1) in-degree-0 nodes first; (A2) a smaller
edge label forces an earlier head; (A3) equal label + earlier tail forces a not-later head. Deciding
existence is NP-complete; WGT's recognizer makes it fast with a renaming heuristic + SMT/permutation.

Usage:
  python3 pipeline/fasta_to_wg.py MSA.fa --generator debruijn -k 5 -l 200 -a 8
  python3 pipeline/fasta_to_wg.py MSA.fa --generator revdet -l 100 -a 10 --backend f --keep-dot out.dot
  python3 pipeline/fasta_to_wg.py MSA.fa --generator trie -a 6 --tsv      # machine-readable row
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
GEN = {
    "debruijn": ("DeBruijnGraph_generator", "DeBruijnGraph_generator.py"),
    "revdet":   ("RevDetGraph_generator", "RevDetGraph_generator.py"),
    "trie":     ("Trie_generator", "Trie_generator.py"),
}
VERDICT = {1: "Wheeler graph", -1: "NOT a Wheeler graph", 0: "undecided (solver returned unknown)"}

# The generators need Biopython on top of a *working* numpy. The base conda python has a broken
# numpy, and many envs lack Bio, so probe for a capable interpreter (override with --gen-python or
# $WGT_GEN_PYTHON). The first that imports Bio + a working numpy.ndarray wins.
_GEN_PY_CANDIDATES = [
    os.environ.get("WGT_GEN_PYTHON"),
    sys.executable,
    "/home/kh.chao/miniconda3/envs/python3.7/bin/python",
    "/home/kh.chao/miniconda3/envs/py3.8/bin/python",
    "/home/kh.chao/miniconda3/envs/liftofftools/bin/python",
    "python3",
]
_PROBE = "import numpy,Bio; _=numpy.ndarray"


def find_gen_python(override=None):
    for cand in ([override] if override else []) + _GEN_PY_CANDIDATES:
        if not cand:
            continue
        try:
            if subprocess.run([cand, "-c", _PROBE], capture_output=True).returncode == 0:
                return cand
        except (OSError, FileNotFoundError):
            continue
    sys.stderr.write("[fasta_to_wg] no Python with Biopython + working numpy found "
                     "(set --gen-python or $WGT_GEN_PYTHON).\n")
    sys.exit(2)


def build_graph(genpy, fasta, generator, k, l, a, outdot):
    """Invoke the chosen generator (from its own dir, so its sibling node.py imports resolve)."""
    gdir, gscript = GEN[generator]
    cwd = os.path.join(ROOT, "generator", gdir)
    cmd = [genpy, gscript, "-o", os.path.abspath(outdot)]
    if generator == "debruijn":
        cmd += ["-k", str(k)]
    cmd += ["-l", str(l), "-a", str(a), os.path.abspath(fasta)]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(outdot):
        sys.stderr.write(f"[fasta_to_wg] generator failed:\n{r.stdout}\n{r.stderr}\n")
        sys.exit(2)


def graph_size(dot):
    """Count nodes (distinct endpoints) and edges from a `A -> B [label=x];` DOT."""
    edge_re = re.compile(r"(\w+)\s*->\s*(\w+)\s*\[label=")
    nodes, edges = set(), 0
    with open(dot) as fh:
        for line in fh:
            m = edge_re.search(line.replace(" ", ""))
            if m:
                nodes.add(m.group(1)); nodes.add(m.group(2)); edges += 1
    return len(nodes), edges


def recognize(dot, backend, timeout):
    """Run the recognizer; return (verdict:int|None, nodes:int|None, wall:float, status:str)."""
    cmd = [REC, dot, "-b"] + (["-f"] if backend == "f" else [])
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, None, timeout, "TIMEOUT"
    wall = time.perf_counter() - t0
    last = None
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            last = parts
    if last is None:
        return None, None, wall, "ERR"
    try:
        return int(last[0]), int(last[1]), wall, "OK"
    except (ValueError, IndexError):
        return None, None, wall, "ERR"


def main():
    ap = argparse.ArgumentParser(description="MSA FASTA -> graph -> Wheeler-graph verdict (turnkey).")
    ap.add_argument("fasta", help="input MSA FASTA")
    ap.add_argument("--generator", choices=list(GEN), default="debruijn")
    ap.add_argument("-k", "--kmer", type=int, default=5, help="k-mer length (debruijn only)")
    ap.add_argument("-l", "--seqlen", type=int, default=-1, help="sequence-length cap (-1 = full)")
    ap.add_argument("-a", "--alnnum", type=int, default=4, help="number of sequences to use")
    ap.add_argument("--backend", choices=["default", "f"], default="default",
                    help="default = heuristic+SMT (production); f = full-range SMT (no heuristic)")
    ap.add_argument("--timeout", type=float, default=600.0, help="recognizer wall timeout (s)")
    ap.add_argument("--keep-dot", default=None, help="write the DOT here instead of a temp file")
    ap.add_argument("--tsv", action="store_true", help="emit one machine-readable TSV row")
    ap.add_argument("--gen-python", default=None, help="Python with Biopython+numpy for the generator")
    args = ap.parse_args()

    genpy = find_gen_python(args.gen_python)

    if not os.path.exists(REC):
        sys.stderr.write(f"[fasta_to_wg] recognizer not found at {REC} (build it first).\n")
        sys.exit(2)

    tmp = None
    if args.keep_dot:
        outdot = args.keep_dot
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".dot", delete=False)
        outdot = tmp.name
        tmp.close()

    try:
        build_graph(genpy, args.fasta, args.generator, args.kmer, args.seqlen, args.alnnum, outdot)
        nodes, edges = graph_size(outdot)
        verdict, rec_nodes, wall, status = recognize(outdot, args.backend, args.timeout)
        name = os.path.basename(args.fasta)
        vstr = VERDICT.get(verdict, status)
        if args.tsv:
            print("\t".join(str(x) for x in
                  [name, args.generator, args.kmer, args.seqlen, args.alnnum,
                   nodes, edges, verdict if verdict is not None else status, f"{wall:.4f}"]))
        else:
            print(f"MSA:        {name}")
            print(f"generator:  {args.generator}"
                  + (f"  k={args.kmer}" if args.generator == 'debruijn' else "")
                  + f"  l={args.seqlen}  a={args.alnnum}")
            print(f"graph:      {nodes} nodes, {edges} edges  ({outdot})")
            print(f"backend:    {'full-range SMT (-f)' if args.backend=='f' else 'heuristic + SMT (default)'}")
            print(f"verdict:    {vstr}")
            print(f"time:       {wall*1000:.1f} ms wall")
    finally:
        if tmp is not None and not args.keep_dot and os.path.exists(outdot):
            os.unlink(outdot)


if __name__ == "__main__":
    main()
