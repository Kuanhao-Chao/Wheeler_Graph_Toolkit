#!/usr/bin/env python3
"""
msa_practicality.py -- how practical is "MSA -> Wheeler graph" on real gene MSAs?

Sweeps every Ensembl ortholog MSA under data/multiseq_alignment/ over the three constructions
(De Bruijn at several k, reverse-deterministic, trie) and a couple of (l, a) settings, and records
for each: MSA dimensions (n_seqs x aligned length), resulting graph size (nodes, edges), the
recognizer verdict, and the default-backend recognition wall time. Output is a CSV that answers:
  * how graph size scales with MSA dimensions and k,
  * how often each construction yields a Wheeler graph (the Wheeler-rate by generator),
  * how fast recognition is on real biological graphs (the "instant in practice" claim),
  * the largest practical MSA.

Recognition uses the production default backend (heuristic + SMT). Wall times are taken on a possibly
loaded host, so treat them as upper bounds; the qualitative conclusion (sub-second) is load-robust.

Usage:
  python3 pipeline/msa_practicality.py --out benchmark/report_figs/data/msa_practicality.csv
  python3 pipeline/msa_practicality.py --alphabets DNA --max-genes 40 --out ...csv
"""
import argparse
import csv
import glob
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fasta_to_wg as f2w  # noqa: E402

FASTA_BASE = os.path.join(ROOT, "data", "multiseq_alignment", "Ensembl_REST", "fasta")


def msa_dims(path):
    """(#sequences, aligned length of first record)."""
    n, first_len = 0, 0
    seq = []
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                if n == 1:
                    first_len = sum(len(s) for s in seq)
                n += 1
                seq = []
            else:
                if n == 1:
                    seq.append(line.strip())
    if n == 1:
        first_len = sum(len(s) for s in seq)
    return n, first_len


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--alphabets", default="DNA,AA")
    ap.add_argument("--max-genes", type=int, default=0, help="0 = all")
    ap.add_argument("--kmers", default="3,5,7", help="De Bruijn k values to sweep")
    ap.add_argument("--alns", default="4,8", help="alignment counts (a) to sweep")
    ap.add_argument("--seqlen", type=int, default=300,
                    help="per-sequence length cap (l). Caps trie/revdet graph size; -1 = full.")
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args()

    genpy = f2w.find_gen_python()
    kmers = [int(x) for x in args.kmers.split(",")]
    alns = [int(x) for x in args.alns.split(",")]

    fastas = []
    for alpha in args.alphabets.split(","):
        d = os.path.join(FASTA_BASE, alpha)
        for fa in sorted(glob.glob(os.path.join(d, "*.fa"))):
            fastas.append((alpha, fa))
    if args.max_genes:
        fastas = fastas[:args.max_genes]

    # Build the (generator, k) x a job list. De Bruijn sweeps k; revdet/trie have no k.
    jobs = []
    for k in kmers:
        for a in alns:
            jobs.append(("debruijn", k, a))
    for gen in ("revdet", "trie"):
        for a in alns:
            jobs.append((gen, 0, a))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fields = ["gene", "alphabet", "n_seqs", "aln_len", "generator", "k", "l", "a",
              "nodes", "edges", "verdict", "wall_s"]
    n_done = 0
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for alpha, fa in fastas:
            gene = os.path.basename(fa)[:-3]
            n_seqs, aln_len = msa_dims(fa)
            for gen, k, a in jobs:
                if a > n_seqs:
                    continue
                tmp = os.path.join("/tmp", f"msaprac_{os.getpid()}.dot")
                try:
                    f2w.build_graph(genpy, fa, gen, k, args.seqlen, a, tmp)
                    nodes, edges = f2w.graph_size(tmp)
                    verdict, _, wall, status = f2w.recognize(tmp, "default", args.timeout)
                    v = verdict if verdict is not None else status
                except SystemExit:
                    nodes = edges = ""; v = "GEN_FAIL"; wall = 0.0
                finally:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
                w.writerow({"gene": gene, "alphabet": alpha, "n_seqs": n_seqs, "aln_len": aln_len,
                            "generator": gen, "k": k, "l": args.seqlen, "a": a,
                            "nodes": nodes, "edges": edges, "verdict": v, "wall_s": f"{wall:.4f}"})
                fh.flush()
                n_done += 1
            print(f"[{gene} ({alpha}, {n_seqs} seqs x {aln_len})] {len(jobs)} jobs done "
                  f"({n_done} total)", flush=True)
    print(f"wrote {args.out}  ({n_done} rows)")


if __name__ == "__main__":
    main()
