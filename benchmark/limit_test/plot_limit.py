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
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

ALGO_STYLE = {  # consistent colors/markers across figures
    "smt":      ("#1f77b4", "o", "default-SMT"),
    "perm":     ("#2ca02c", "s", "permutation"),
    "full":     ("#d62728", "^", "full -f (NEW)"),
    "full-old": ("#ff7f0e", "v", "full -f (OLD)"),
    "exp":      ("#9467bd", "D", "exponential (GT)"),
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


def plot_size_vs_time(runs, T, outdir):
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
        if T:
            ax.axhline(T, ls="--", color="gray", lw=1, label=f"timeout T={T:g}s")
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
    algos = [a for a in ALGO_STYLE if any(r["algo"] == a for r in summary)]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    width = 0.8 / max(1, len(families))
    x = np.arange(len(algos))
    for fi, family in enumerate(families):
        heights, hatches = [], []
        for algo in algos:
            row = next((r for r in summary if r["algo"] == algo and r["family"] == family), None)
            if row is None or row["limit_n"] in ("None", "", None):
                heights.append(0)
                hatches.append("")
                continue
            heights.append(float(row["limit_n"]))
            hatches.append("//" if row["kind"] == "CAPPED" else "")
        bars = ax.bar(x + fi * width, heights, width, label=family)
        for b, h in zip(bars, hatches):
            if h:
                b.set_hatch(h)
    ax.set_yscale("log")
    ax.set_xticks(x + width * (len(families) - 1) / 2)
    ax.set_xticklabels([ALGO_STYLE[a][2] for a in algos], rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("largest decided / repaired n  (log)")
    ax.set_title("Recognition & repair size limits  (hatched = capability cap, not timeout)")
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
                    marker=marker, color=color, label=label, lw=1.8, ms=5)
        if T:
            ax.axhline(T, ls="--", color="gray", lw=1, label=f"timeout T={T:g}s")
        ax.set_yscale("log")
        ax.set_xscale("log", base=2)
        ax.set_xlabel("graph size  (nodes, log₂)")
        ax.set_ylabel("median wall time (s, log)")
        ax.set_title(f"Phase-4.2 effect on `-f`: OLD vs NEW  ({family})")
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
    args = ap.parse_args()
    runs = load_runs(args.results)
    summary = load_summary(args.results)
    T = max((r["wall"] for r in runs if r.get("klass") == "TIMEOUT"), default=None)
    # better: read T from any summary row
    if summary:
        try:
            T = float(summary[0]["timeout_s"])
        except (ValueError, KeyError):
            pass
    outdir = os.path.join(args.results, "plots")
    os.makedirs(outdir, exist_ok=True)
    plot_size_vs_time(runs, T, outdir)
    plot_limits_bar(summary, outdir)
    plot_old_vs_new(runs, T, outdir)


if __name__ == "__main__":
    main()
