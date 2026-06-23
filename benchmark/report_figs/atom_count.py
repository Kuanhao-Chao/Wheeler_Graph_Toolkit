#!/usr/bin/env python3
"""
atom_count.py -- analytical SMT-atom counter for the -f (full_range_search) encoding.

Counts, WITHOUT running z3, the number of `s.add(...)` assertions each recognizer generation would
emit under `-f`, directly from a DOT graph's structure. This makes the asymptotic claim of Phases
4.1/4.2 measurable (atoms, not inferred from wall time):

    A2 (cross-group, smt.cpp:56-91)
      pre41 (dense)  : one head-pair constraint per cross-label edge pair  = sum_{i<j} E_i*E_j
      pre42/new (sparse): per group 2*E_l head brackets + 1 (lo<=hi), chain L-1  = 2E + 2L - 1
    A3 (within-group, smt.cpp:95-195)
      pre41/pre42/new-fallback (pairwise): one conjoined add per (i<j) edge pair = sum_l C(E_l,2)
      new block (smt.cpp:133-161), fires iff  2*D_l < E_l  AND  D_l(D_l-1)+2E_l < E_l(E_l-1):
                     per group 2*E_l brackets + 2*C(D_l,2) inter-key = 2E_l + D_l(D_l-1)
    baseline (range + distinct, smt.cpp:33-53): IDENTICAL across all three generations (n range
      bounds + one distinct() per non-singleton range group). Reported separately; it cancels in
      every OLD-vs-NEW comparison. Under -f the ranges are {roots:[1,R]} and {rest:[R+1,n]}.

E = edges, L = distinct labels, E_l = edges in label group l, T_l/H_l = distinct tails/heads in l,
D_l = min(T_l, H_l). Validated against `recognizer_linux_instr -f -v` (prints s.assertions().size()).

Usage:
  python3 benchmark/report_figs/atom_count.py \
      --corpus data/graph/SMT_vs_RHSMT/{DeBruijnG_DNA,DeBruijnG_AA,RevDetG_DNA,RevDetG_AA} \
      --out benchmark/report_figs/data/atom_counts.csv
"""
import argparse
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

EDGE_RE = re.compile(r"(\w+)->(\w+)\[label=(\w+)\]")


def parse_dot(path):
    """Return list of (tail, head, label). Mirrors wg.cpp: strip spaces, match \\w+ tokens."""
    edges = []
    with open(path) as fh:
        for line in fh:
            if "->" not in line:
                continue
            m = EDGE_RE.search(line.replace(" ", ""))
            if m:
                edges.append((m.group(1), m.group(2), m.group(3)))
    return edges


def comb2(x):
    return x * (x - 1) // 2


def guard_fires(E_l, D_l):
    """smt.cpp:133 -- block A3 fires iff 2*D < E and D(D-1)+2E < E(E-1)."""
    return (2 * D_l < E_l) and (D_l * (D_l - 1) + 2 * E_l < E_l * (E_l - 1))


def count_atoms(edges):
    """Return a dict of atom counts mirroring smt.cpp under -f."""
    by_label = defaultdict(list)
    nodes = set()
    for t, h, lab in edges:
        by_label[lab].append((t, h))
        nodes.add(t)
        nodes.add(h)
    E = len(edges)
    L = len(by_label)
    n = len(nodes)
    # Validated exactly against recognizer_linux_instr (s.assertions().size()): under -f the shared
    # range+distinct baseline is exactly n+1 (n range bounds + one distinct() over the big group).
    baseline = n + 1

    # ---- A2 ----
    sum_El2 = sum(len(es) ** 2 for es in by_label.values())
    a2_pre41 = (E * E - sum_El2) // 2          # sum_{i<j} E_i*E_j
    a2_sparse = 2 * E + 2 * L - 1 if L > 0 else 0   # pre42 and new

    # ---- A3 ----
    a3_pairwise = 0          # pre41, pre42
    a3_new = 0               # new (block where it fires, else pairwise)
    fired_groups = 0
    fired_edges = 0
    de_ratios = []
    for lab, es in by_label.items():
        E_l = len(es)
        tails = {t for t, h in es}
        heads = {h for t, h in es}
        T_l, H_l = len(tails), len(heads)
        D_l = min(T_l, H_l)
        a3_pairwise += comb2(E_l)
        if E_l > 1:
            de_ratios.append(D_l / E_l)
        if guard_fires(E_l, D_l):
            a3_new += 2 * E_l + D_l * (D_l - 1)
            fired_groups += 1
            fired_edges += E_l
        else:
            a3_new += comb2(E_l)

    mean_DE = sum(de_ratios) / len(de_ratios) if de_ratios else float("nan")
    return {
        "edges": E, "labels": L, "nodes": n, "baseline": baseline,
        "pre41_a2": a2_pre41, "pre41_a3": a3_pairwise,
        "pre42_a2": a2_sparse, "pre42_a3": a3_pairwise,
        "new_a2": a2_sparse, "new_a3": a3_new,
        "new_guard_fired_groups": fired_groups,
        "frac_edges_block": (fired_edges / E) if E else 0.0,
        "mean_DE": mean_DE,
        # A2+A3 only (the part that changed between generations):
        "pre41_total": a2_pre41 + a3_pairwise,
        "pre42_total": a2_sparse + a3_pairwise,
        "new_total": a2_sparse + a3_new,
        # full z3 assertion count (baseline + A2 + A3) -- matches s.assertions().size() exactly:
        "new_total_z3": baseline + a2_sparse + a3_new,
    }


def typ(path):
    for t in ("DeBruijnG_DNA", "DeBruijnG_AA", "RevDetG_DNA", "RevDetG_AA"):
        if t in path:
            return t
    return "?"


def iter_dots(corpus_dirs):
    for d in corpus_dirs:
        dd = d if os.path.isabs(d) else os.path.join(ROOT, d)
        if not os.path.isdir(dd):
            print(f"  (skip non-dir {dd})", file=sys.stderr)
            continue
        for f in sorted(os.listdir(dd)):
            if f.endswith(".dot"):
                yield os.path.join(dd, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="comma list of dot directories")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cols = ["dot", "type", "nodes", "edges", "labels", "baseline",
            "pre41_a2", "pre41_a3", "pre42_a2", "pre42_a3", "new_a2", "new_a3",
            "new_guard_fired_groups", "frac_edges_block", "mean_DE",
            "pre41_total", "pre42_total", "new_total", "new_total_z3"]
    rows = []
    for dot in iter_dots(args.corpus.split(",")):
        edges = parse_dot(dot)
        if not edges:
            continue
        c = count_atoms(edges)
        c["dot"] = dot
        c["type"] = typ(dot)
        rows.append(c)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as out:
        out.write(",".join(cols) + "\n")
        for c in rows:
            out.write(",".join(
                f"{c[k]:.4f}" if k in ("frac_edges_block", "mean_DE") else str(c[k])
                for k in cols) + "\n")
    print(f"wrote {args.out}  ({len(rows)} graphs)")
    # quick per-type summary
    bytype = defaultdict(list)
    for c in rows:
        bytype[c["type"]].append(c)
    for t, cs in sorted(bytype.items()):
        import statistics
        es = [c["edges"] for c in cs]
        red41 = statistics.median(c["pre41_total"] / max(1, c["new_total"]) for c in cs)
        de = statistics.median(c["mean_DE"] for c in cs if c["mean_DE"] == c["mean_DE"])
        fe = statistics.median(c["frac_edges_block"] for c in cs)
        print(f"  {t:14s} n={len(cs):3d}  edges {min(es)}..{max(es)}  "
              f"atom-reduction(pre41/new) med={red41:.1f}x  mean_DE med={de:.2f}  "
              f"frac_edges_block med={fe:.2f}")


if __name__ == "__main__":
    main()
