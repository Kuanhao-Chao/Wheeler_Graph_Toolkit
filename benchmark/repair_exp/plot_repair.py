#!/usr/bin/env python3
"""
plot_repair.py -- comprehensive analysis figure for minimal Wheeler-graph repair.

Reads benchmark/repair_exp/data/{corpus_random,corpus_revdet,corpus_wg,scaling}.csv and renders a
6-panel figure covering the four analysis facets:
  (A) scaling      : repair wall time vs trie size, per method (log-log).
  (B) ceilings     : largest trie each method decides within budget (bar).
  (C) memory       : peak RSS vs trie size, per method.
  (D) type x alpha : trie-vs-minimal size reduction by graph type/alphabet.
  (E) edits        : minimal repair node-duplications (#splits) distribution by category.
  (F) optimality   : refine (and greedy) vs the exact Z3 optimum -- points on the diagonal.

Render with ~/miniconda3/envs/spliceai/bin/python. Reuses report_figs/style.py.
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "report_figs"))
import style as S  # noqa: E402
S.apply_style()

DATA = os.path.join(HERE, "data")
MCOL = {"trie": S.BIN["pre41"], "greedy": S.BIN["pre42"], "refine": S.BIN["new"], "exact": "#000000"}
MLAB = {"trie": "trie (existing)", "greedy": "greedy", "refine": "refine (this work)", "exact": "exact (Z3)"}


def load(name):
    p = os.path.join(DATA, name)
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    rnd = [r for r in load("corpus_random.csv")]
    rev = [r for r in load("corpus_revdet.csv")]
    wg = [r for r in load("corpus_wg.csv")]
    scal = load("scaling.csv")
    corpus = rnd + rev + wg
    print(f"loaded corpus: {len(rnd)} random + {len(rev)} revdet + {len(wg)} wg; scaling rows {len(scal)}")

    fig, ax = plt.subplots(2, 3, figsize=(16, 9.5))

    # (A) scaling: wall vs trie per method
    a = ax[0, 0]
    for m in ("trie", "refine", "greedy", "exact"):
        pts = [(num(r["trie_nodes"]), num(r["wall_s"])) for r in scal
               if r["method"] == m and r["status"] == "DECIDED" and num(r["trie_nodes"]) and num(r["wall_s"]) is not None]
        pts = [(t, max(w, 1e-4)) for t, w in pts if t]
        if pts:
            pts.sort()
            a.plot([t for t, _ in pts], [w for _, w in pts], "o-", color=MCOL[m], ms=4, label=MLAB[m])
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlabel("trie size (path-string count)"); a.set_ylabel("repair wall time (s)")
    a.set_title("(A) Scaling: time vs trie size")
    a.legend(fontsize=8, loc="upper left")

    # (B) ceilings: max trie decided per method
    b = ax[0, 1]
    ceil = {}
    for m in ("exact", "greedy", "refine", "trie"):
        dec = [num(r["trie_nodes"]) for r in scal if r["method"] == m and r["status"] == "DECIDED" and num(r["trie_nodes"])]
        ceil[m] = max(dec) if dec else 0
    ms = ["exact", "greedy", "refine", "trie"]
    b.bar(range(len(ms)), [ceil[m] for m in ms], color=[MCOL[m] for m in ms])
    for i, m in enumerate(ms):
        b.text(i, ceil[m], f" {int(ceil[m])}", ha="center", va="bottom", fontsize=9)
    b.set_xticks(range(len(ms))); b.set_xticklabels([MLAB[m].split()[0] for m in ms], fontsize=8)
    b.set_yscale("log"); b.set_ylabel("largest trie decided in budget")
    b.set_title("(B) Per-method ceiling")

    # (C) memory: RSS vs trie
    c = ax[0, 2]
    for m in ("trie", "refine", "greedy", "exact"):
        pts = [(num(r["trie_nodes"]), num(r["rss_kb"])) for r in scal
               if r["method"] == m and r["status"] == "DECIDED" and num(r["trie_nodes"]) and num(r["rss_kb"])]
        if pts:
            pts.sort()
            c.plot([t for t, _ in pts], [k / 1024 for _, k in pts], "o-", color=MCOL[m], ms=4, label=MLAB[m])
    c.set_xscale("log")
    c.set_xlabel("trie size"); c.set_ylabel("peak RSS (MB)")
    c.set_title("(C) Memory vs trie size")
    c.legend(fontsize=8, loc="upper left")

    # (D) type x alphabet reduction (trie / refine size)
    d = ax[1, 0]
    cats = []
    def cat_key(r):
        t, al = r["type"], r["alphabet"]
        return f"{t}\n{al}" if al else t
    groups = {}
    for r in corpus:
        if r["verdict_in"] != "nonWG":
            continue
        red = num(r["trie_size"]) / num(r["refine_size"]) if num(r["refine_size"]) else None
        if red:
            groups.setdefault(cat_key(r), []).append(red)
    keys = sorted(groups, key=lambda k: -np.median(groups[k]))
    if keys:
        d.boxplot([groups[k] for k in keys], labels=keys, showfliers=False)
        d.axhline(1.0, color=S.REF_GRAY, lw=1)
        d.set_ylabel("size reduction  trie / minimal (×)")
        d.set_title("(D) Reduction by type × alphabet (non-WG)")
        d.tick_params(axis="x", labelsize=7)

    # (E) edits distribution by category
    e = ax[1, 1]
    egroups = {}
    for r in corpus:
        if r["verdict_in"] != "nonWG" or r["refine_edits"] == "":
            continue
        egroups.setdefault(cat_key(r), []).append(int(r["refine_edits"]))
    keys2 = sorted(egroups, key=lambda k: -np.median(egroups[k]))
    if keys2:
        e.boxplot([egroups[k] for k in keys2], labels=keys2, showfliers=False)
        e.set_ylabel("minimal repair: node duplications (#splits)")
        e.set_title("(E) Edits to repair, by category")
        e.tick_params(axis="x", labelsize=7)

    # (F) optimality: refine/greedy vs exact
    f = ax[1, 2]
    rx = [(num(r["exact_size"]), num(r["refine_size"])) for r in corpus
          if num(r["exact_size"]) and num(r["refine_size"])]
    gx = [(num(r["exact_size"]), num(r["greedy_size"])) for r in corpus
          if num(r["exact_size"]) and num(r["greedy_size"])]
    if rx:
        f.scatter([a_ for a_, _ in rx], [b_ for _, b_ in rx], s=26, c=MCOL["refine"], label="refine", alpha=0.7)
    if gx:
        f.scatter([a_ for a_, _ in gx], [b_ for _, b_ in gx], s=18, c=MCOL["greedy"], marker="x", label="greedy", alpha=0.7)
    allv = [v for pair in rx + gx for v in pair]
    if allv:
        mx = max(allv) + 1
        f.plot([0, mx], [0, mx], color=S.REF_GRAY, ls="--", lw=1, label="= exact optimum")
        agree = sum(1 for a_, b_ in rx if a_ == b_)
        f.set_title(f"(F) Optimality: heuristic vs exact (refine={agree}/{len(rx)} optimal)")
    f.set_xlabel("exact optimum nodes"); f.set_ylabel("heuristic nodes")
    f.legend(fontsize=8, loc="upper left")

    fig.suptitle("Comprehensive minimal Wheeler-graph repair benchmark "
                 "(faster refine algorithm; correctness-verified)", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = os.path.join(HERE, "Frepair_comprehensive.png")
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
