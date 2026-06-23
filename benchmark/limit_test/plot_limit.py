#!/usr/bin/env python3
"""
plot_limit.py -- figures for the WGT scalability limit test (reads limit_test.py output).

Produces, under <results>/plots/:
  size_vs_time__<family>.png   -- median wall time vs graph size (log-y), one line per algorithm,
                                  with the timeout T drawn as a horizontal line (its crossing = limit).
  limits_bar.png               -- largest decided/repaired n per algorithm, grouped by family
                                  (THRESHOLD solid, CAPPED hatched, UNREACHED = lower-bound arrow).
  old_vs_new_f__<family>.png   -- OLD vs NEW `-f` overlay (the Phase-4.2 max-size gain), if both ran.

Usage:  python3 benchmark/limit_test/plot_limit.py [--results DIR]
"""

import argparse
import csv
import json
import os
from collections import defaultdict

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "report_figs"))
import style as S  # noqa: E402
S.apply_style()

ALGO_STYLE = {  # one visual language with the §4 figures: same binary => same color
    "smt":      ("#2166ac", "o", "default SMT"),
    "perm":     ("#7f7f7f", "s", "permutation"),
    "full":     (S.BIN["new"], "^", "full -f (this work)"),
    "full-old": (S.BIN["pre42"], "v", "full -f (pre-4.2)"),
    "exp":      ("#bdbdbd", "D", "exponential ref."),
    "wheelerize": ("#8c564b", "P", "repair (wheelerize)"),
}


def load_runs(results):
    path = os.path.join(results, "raw", "runs.jsonl")
    runs = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    runs.append(json.loads(line))
                except ValueError:
                    pass
    return runs


def load_summary(results):
    path = os.path.join(results, "summary", "limit_summary.csv")
    rows = []
    if not os.path.exists(path):
        return rows   # summary is written only at run completion; raw-based figures still render
    with open(path) as fh:
        header = fh.readline().strip().split(",")
        for line in fh:
            rows.append(dict(zip(header, line.strip().split(","))))
    return rows


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def curves(runs):
    """(family, algo) -> sorted list of (n, median_wall) over DECISIVE replicate runs."""
    agg = defaultdict(lambda: defaultdict(list))
    for r in runs:
        if r.get("measured_n") is None or r.get("wall") is None:
            continue
        if r.get("klass") != "DECISIVE":
            continue
        agg[(r["family"], r["algo"])][r["measured_n"]].append(r["wall"])
    out = {}
    for key, by_n in agg.items():
        out[key] = sorted((n, median(ws)) for n, ws in by_n.items())
    return out


def families_in(runs):
    return sorted({r["family"] for r in runs})


def algos_in(runs, family):
    return [a for a in ALGO_STYLE if any(r["algo"] == a and r["family"] == family for r in runs)]


def load_bio_band(bio_csv):
    """Real-MSA graph-size band (min, median, max nodes) from the practicality CSV, or None."""
    if not bio_csv or not os.path.exists(bio_csv):
        return None
    ns = []
    with open(bio_csv) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                ns.append(int(float(row["nodes"])))
            except (ValueError, KeyError):
                pass
    if not ns:
        return None
    ns.sort()
    return (ns[0], median(ns), ns[-1])


def plot_size_vs_time(runs, T, outdir, bio_band=None):
    cv = curves(runs)
    for family in families_in(runs):
        fig, ax = plt.subplots(figsize=(8, 5.5))
        plotted = False
        for algo in algos_in(runs, family):
            pts = cv.get((family, algo), [])
            if not pts:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            color, marker, label = ALGO_STYLE[algo]
            ax.plot(xs, ys, marker=marker, color=color, label=label, lw=1.6, ms=5)
            plotted = True
        if not plotted:
            plt.close(fig)
            continue
        if bio_band:
            lo, med, hi = bio_band
            ax.axvspan(lo, hi, color=S.BAND_TEAL, alpha=0.10, zorder=0,
                       label=f"real MSA graphs (n={lo}–{hi:.0f})")
            ax.axvline(med, color=S.BAND_TEAL, ls=":", lw=1.2, alpha=0.8)
        if T:
            ax.axhline(T, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1, label=f"timeout T={T:g}s")
        ax.set_yscale("log")
        ax.set_xscale("log", base=2)
        ax.set_xlabel("graph size  (nodes, log₂)")
        ax.set_ylabel("median wall time per decision (s, log)")
        ax.set_title(f"Scalability: {family} family  (decision time vs size)")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=8)
        p = os.path.join(outdir, f"size_vs_time__{family}.png")
        fig.tight_layout()
        fig.savefig(p, dpi=300)
        plt.close(fig)
        print(f"wrote {p}")


def plot_limits_bar(summary, outdir):
    if not summary:
        print("limits_bar skipped (no summary yet; run still in progress)")
        return
    families = sorted({r["family"] for r in summary})
    fam_color = {"complete": "#1b9e77", "dnfa": "#2166ac", "random-dag": "#7f7f7f"}
    algos = [a for a in ALGO_STYLE if any(r["algo"] == a for r in summary)]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    width = 0.8 / max(1, len(families))
    x = np.arange(len(algos))
    for fi, family in enumerate(families):
        heights, hatches, kinds = [], [], []
        for algo in algos:
            row = next((r for r in summary if r["algo"] == algo and r["family"] == family), None)
            if row is None or row["limit_n"] in ("None", "", None):
                heights.append(0); hatches.append(""); kinds.append("")
                continue
            heights.append(float(row["limit_n"]))
            hatches.append("//" if row["kind"] == "CAPPED" else "")
            kinds.append(row["kind"])
        bars = ax.bar(x + fi * width, heights, width, label=family,
                      color=fam_color.get(family, "#888"))
        for b, h, k in zip(bars, hatches, kinds):
            if h:
                b.set_hatch(h)
            if k == "CAPPED":
                ax.text(b.get_x() + b.get_width() / 2, b.get_height(), "cap", ha="center",
                        va="bottom", fontsize=7, color=S.WALL_GRAY)
            elif k == "THRESHOLD":
                ax.text(b.get_x() + b.get_width() / 2, b.get_height(), "↑", ha="center",
                        va="bottom", fontsize=9, color=S.WALL_GRAY)
    ax.set_yscale("log")
    ax.set_xticks(x + width * (len(families) - 1) / 2)
    ax.set_xticklabels([ALGO_STYLE[a][2] for a in algos], rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("largest decided / repaired n  (log)")
    ax.set_title("Recognition & repair size limits  (cap = solver capability wall; ↑ = timeout-bounded)")
    ax.legend(title="family", fontsize=8)
    ax.grid(True, axis="y", which="both", alpha=0.25)
    p = os.path.join(outdir, "limits_bar.png")
    fig.tight_layout()
    fig.savefig(p, dpi=300)
    plt.close(fig)
    print(f"wrote {p}")


def plot_old_vs_new(runs, T, outdir):
    cv = curves(runs)
    for family in families_in(runs):
        new = cv.get((family, "full"), [])
        old = cv.get((family, "full-old"), [])
        if not new or not old:
            continue
        fig, ax = plt.subplots(figsize=(8, 5.5))
        for algo, pts in (("full-old", old), ("full", new)):
            color, marker, label = ALGO_STYLE[algo]
            ax.plot([p[0] for p in pts], [p[1] for p in pts],
                    marker=marker, color=color, label=label, lw=2.0, ms=5)
        # the shared z3 "unknown" ceiling: the largest n either curve reaches before z3 gives up
        wall_n = max([p[0] for p in new] + [p[0] for p in old])
        ax.axvline(wall_n, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1.2)
        ax.text(wall_n, ax.get_ylim()[1], " z3 returns unknown\n (solver wall, identical OLD/NEW)",
                ha="right", va="top", fontsize=8, color=S.WALL_GRAY)
        if T:
            ax.axhline(T, ls=(0, (1, 2)), color=S.WALL_GRAY, lw=1, alpha=0.6,
                       label=f"timeout T={T:g}s")
        ax.set_yscale("log")
        ax.set_xscale("log", base=2)
        ax.set_xlabel("graph size  (nodes, log₂)")
        ax.set_ylabel("median wall time (s, log)")
        ax.set_title(f"-f time, prior vs this work — {family}")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=8)
        p = os.path.join(outdir, f"old_vs_new_f__{family}.png")
        fig.tight_layout()
        fig.savefig(p, dpi=300)
        plt.close(fig)
        print(f"wrote {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "results"))
    ap.add_argument("--bio-csv", default=None,
                    help="practicality CSV (e.g. report_figs/data/msa_practicality.csv); "
                         "overlays the real-MSA graph-size band on size_vs_time figures")
    args = ap.parse_args()
    runs = load_runs(args.results)
    summary = load_summary(args.results)
    bio_band = load_bio_band(args.bio_csv)
    T = max((r["wall"] for r in runs if r.get("klass") == "TIMEOUT"), default=None)
    # better: read T from any summary row
    if summary:
        try:
            T = float(summary[0]["timeout_s"])
        except (ValueError, KeyError):
            pass
    outdir = os.path.join(args.results, "plots")
    os.makedirs(outdir, exist_ok=True)
    if bio_band:
        print(f"bio band: real-MSA graphs n={bio_band[0]}–{bio_band[2]:.0f} (median {bio_band[1]:.0f})")
    plot_size_vs_time(runs, T, outdir, bio_band=bio_band)
    plot_limits_bar(summary, outdir)
    plot_old_vs_new(runs, T, outdir)


if __name__ == "__main__":
    main()
