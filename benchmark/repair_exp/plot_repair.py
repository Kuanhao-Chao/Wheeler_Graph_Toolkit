#!/usr/bin/env python3
"""
plot_repair.py -- figures for minimal Wheeler-graph repair (Phase 5).

Reads benchmark/repair_exp/data/repair_{revdet,random}.csv and renders a 4-panel figure:
  (A) Repaired size vs input size: trie (existing) blows up; minimal repair stays near the input.
  (B) Pareto -- min-size vs min-edits per graph (min-size <= min-edits, on/above the diagonal).
  (C) Size reduction of the minimal repair over the trie (ECDF) + node-duplication distribution.
  (D) Optimality -- greedy vs exact (Z3) where exact is feasible: greedy lands on the optimum.

Render with ~/miniconda3/envs/spliceai/bin/python (matplotlib). Reuses report_figs/style.py.
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
TRIE_C = S.BIN["pre41"]      # existing trie repair (light purple, the baseline)
SIZE_C = S.BIN["new"]        # minimal min-size (dark purple, this work)
EDIT_C = S.GEN_COLOR["revdet"]  # min-edits accent (orange)
EXACT_C = "#000000"


def load(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    rows = []
    for r in csv.DictReader(open(path)):
        if r.get("verdict_in") != "nonWG":
            continue
        def gi(k):
            v = r.get(k, "")
            return int(v) if v not in ("", None) else None
        rows.append({
            "in": gi("in_nodes"), "trie": gi("trie_nodes"),
            "gsize": gi("greedy_size"), "gedit_n": gi("greedy_edits_nodes"),
            "gedit": gi("greedy_edits"), "exsize": gi("exact_size"),
            "exedit": gi("exact_edits"), "verify": gi("verify_ok"),
        })
    return rows


def main():
    rev = load("repair_revdet.csv")
    rnd = load("repair_random.csv")
    allr = rev + rnd
    if not allr:
        print("no data yet; run run_repair_corpus.py first")
        return
    nfail = sum(1 for r in allr if r["verify"] == 0)
    print(f"loaded {len(allr)} non-WG graphs ({len(rev)} RevDet, {len(rnd)} random); "
          f"verify failures = {nfail}")

    fig, ax = plt.subplots(2, 2, figsize=(11, 9))

    # (A) repaired size vs input size
    a = ax[0, 0]
    for rows, mk, lab in ((rev, "o", "RevDet (gene)"), (rnd, "^", "random")):
        if not rows:
            continue
        x = [r["in"] for r in rows]
        a.scatter(x, [r["trie"] for r in rows], s=18, c=TRIE_C, marker=mk, alpha=0.55)
        a.scatter(x, [r["gsize"] for r in rows], s=18, c=SIZE_C, marker=mk, alpha=0.8)
    mx = max(r["trie"] for r in allr) + 2
    a.plot([0, mx], [0, mx], color=S.REF_GRAY, lw=1, ls="--", label="y = x (no change)")
    a.scatter([], [], c=TRIE_C, marker="s", label="trie repair (existing)")
    a.scatter([], [], c=SIZE_C, marker="s", label="minimal repair (min-size)")
    a.set_xlabel("input nodes")
    a.set_ylabel("repaired nodes")
    a.set_title("Repaired size: trie blows up, minimal stays near input")
    a.legend(fontsize=8, loc="upper left")
    S.panel_tag(a, "A")

    # (B) Pareto: min-size vs min-edits
    b = ax[0, 1]
    for rows, mk, c in ((rev, "o", EDIT_C), (rnd, "^", "#999999")):
        if not rows:
            continue
        b.scatter([r["gsize"] for r in rows], [r["gedit_n"] for r in rows],
                  s=20, marker=mk, c=c, alpha=0.7,
                  label=("RevDet" if rows is rev else "random"))
    mx = max(r["gedit_n"] for r in allr) + 2
    b.plot([0, mx], [0, mx], color=S.REF_GRAY, lw=1, ls="--", label="min-size = min-edits")
    b.set_xlabel("min-size nodes")
    b.set_ylabel("min-edits nodes")
    b.set_title("Pareto: min-size ≤ min-edits (closest-to-input costs a little)")
    b.legend(fontsize=8, loc="upper left")
    S.panel_tag(b, "B")

    # (C) reduction ECDF (split by source) + edits distribution
    c = ax[1, 0]
    for rows, col, lab in ((rev, EDIT_C, "RevDet (gene)"), (rnd, "#999999", "random")):
        if not rows:
            continue
        red = sorted(r["trie"] / r["gsize"] for r in rows if r["gsize"])
        ys = np.arange(1, len(red) + 1) / len(red)
        c.step(red, ys, where="post", color=col, lw=2.2, label=lab)
        med = red[len(red) // 2]
        c.axvline(med, color=col, ls=S.WALL_LS, lw=1.0)
        c.text(med, 0.10 if rows is rev else 0.02, f" {med:.2f}×", color=col, fontsize=9)
    c.axvline(1.0, color=S.REF_GRAY, lw=1)
    c.set_xlabel("size reduction  trie / minimal  (×)")
    c.set_ylabel("fraction of graphs ≤ x")
    c.set_title("Minimal repair is much smaller than the trie")
    c.legend(fontsize=8, loc="lower right")
    S.panel_tag(c, "C")
    # inset: node-duplication (min-edits) distribution
    ins = c.inset_axes([0.55, 0.18, 0.4, 0.5])
    eds = [r["gedit"] for r in allr if r["gedit"] is not None]
    if eds:
        ins.hist(eds, bins=range(0, max(eds) + 2), color=EDIT_C, alpha=0.85, align="left")
        ins.set_title("min-edits (splits)", fontsize=8)
        ins.tick_params(labelsize=7)

    # (D) optimality: greedy vs exact
    d = ax[1, 1]
    ex = [(r["gsize"], r["exsize"], r["gedit_n"], r["exedit"]) for r in allr
          if r["exsize"] is not None]
    if ex:
        gs = [e[0] for e in ex]
        es = [e[1] for e in ex]
        ge = [e[2] for e in ex]
        ee = [e[3] for e in ex]
        d.scatter(es, gs, s=26, c=SIZE_C, marker="o", alpha=0.7, label="min-size")
        d.scatter(ee, ge, s=26, c=EDIT_C, marker="s", alpha=0.6, label="min-edits")
        mx = max(max(gs), max(es)) + 1
        d.plot([0, mx], [0, mx], color=S.REF_GRAY, lw=1, ls="--", label="greedy = exact")
        agree = sum(1 for e in ex if e[0] == e[1] and e[2] == e[3])
        d.set_title(f"Greedy matches the Z3 optimum ({agree}/{len(ex)} graphs)")
        d.set_xlabel("exact optimum nodes (Z3)")
        d.set_ylabel("greedy nodes")
        d.legend(fontsize=8, loc="upper left")
    else:
        d.text(0.5, 0.5, "no exact data", ha="center")
    S.panel_tag(d, "D")

    fig.suptitle("Minimal-change Wheeler-graph repair (lossless node-splitting)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = os.path.join(HERE, "Frepair_minimal.png")
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
