#!/usr/bin/env python3
"""plot_index_report.py -- figures for the Wheeler-graph INDEX technical report.

Six figures, one visual language (style.py: ACCENT violet = the suffix index, gray = De Bruijn baseline).
Every number traces to benchmark/report_figs/verify_index_report_numbers.py (must be all-PASS).
Source PNGs use an FI* prefix (no collision with the recognizer report's F*). Render with:
  ~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/plot_index_report.py
"""
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt        # noqa: E402
import numpy as np                     # noqa: E402
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch  # noqa: E402

import style as S                      # noqa: E402
from style import ACCENT, BASE_C, BASE_EDGE  # noqa: E402

S.apply_style()
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data")
OUT = HERE
REVDET = "#b0a8c0"   # third neutral for RevDet (still in the violet/gray family, not a new hue)


def _load(n):
    return json.load(open(os.path.join(DATA, n)))


def _save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def _scorecard_panel(ax, title, big, sub, color=ACCENT):
    ax.axis("off")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=6)
    ax.text(0.5, 0.62, big, transform=ax.transAxes, ha="center", va="center",
            fontsize=25, fontweight="bold", color=color)
    ax.text(0.5, 0.26, sub, transform=ax.transAxes, ha="center", va="center",
            fontsize=10.5, color="#333333", linespacing=1.5)


# --------------------------------------------------------------------------- 1. HERO scorecard
def fig_hero():
    res = _load("genome_resolution.json")["summary"]
    g = _load("suffix_genome_scaling.json")["aggregate"]
    rt = _load("suffix_router.json")
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.5))
    _scorecard_panel(axes[0], "Resolution",
                     "100%",
                     "correct species set\n(653/653 multi-species queries)\n"
                     f"0 false positives  vs  De Bruijn {int(res['debruijn_native_species_rate']*100)}% "
                     f"/ {res['debruijn_superset_fp']} FP")
    _scorecard_panel(axes[1], "Scale  (whole yeast genome)",
                     "44,063",
                     "alignment blocks · 43.4 M nodes\n"
                     f"built in {g['total_build_s']:.0f} s · {g['total_ondisk_mb']:.0f} MB on disk")
    _scorecard_panel(axes[2], "Speed  &  correctness",
                     f"{rt['speedup_routed_vs_touchall']:.0f}×",
                     f"routed locate {g['median_routed_ms']:.1f} ms\n"
                     "0 mismatches over >4 M audited cases")
    fig.suptitle("A queryable Wheeler-graph pangenome index: native species + position, validated whole-genome",
                 fontsize=12.5, fontweight="semibold", y=1.04)
    fig.text(0.5, -0.02,
             "Honest trade: the suffix index is ~1.2× larger than the De Bruijn graph "
             f"({res['median_nodes']['suffix']} vs {res['median_nodes']['debruijn']} median nodes/block) "
             "— it buys exact, native species-and-position resolution.",
             ha="center", fontsize=9.5, color="#555555", style="italic")
    fig.tight_layout()
    _save(fig, "FIhero.png")


# --------------------------------------------------------------------------- 2. RESOLUTION
def fig_resolution():
    r = _load("genome_resolution.json")["summary"]
    fig, ax = plt.subplots(1, 3, figsize=(12.6, 3.8))
    methods = ["suffix\nindex", "De Bruijn", "RevDet"]
    cols = [ACCENT, BASE_C, REVDET]
    # (A) species-set correctness
    vals = [100, 0, np.nan]
    b = ax[0].bar(methods, [v if not np.isnan(v) else 0 for v in vals], color=cols, edgecolor=BASE_EDGE)
    ax[0].set_ylim(0, 108); ax[0].set_ylabel("correct species set (%)")
    ax[0].set_title("Native species resolution"); S.panel_tag(ax[0], "A")
    for rect, v in zip(b, vals):
        ax[0].text(rect.get_x() + rect.get_width() / 2, (v if not np.isnan(v) else 3) + 2,
                   "100%" if v == 100 else ("0%" if v == 0 else "n/a"), ha="center", fontweight="bold")
    # (B) superset false positives (fraction of recombinant controls accepted)
    fp = [r["suffix_fp"] / r["recombinants_total"] * 100, r["debruijn_superset_fp"] / r["recombinants_total"] * 100,
          r["revdet_superset_blocks"] / r["blocks"] * 100]
    b = ax[1].bar(methods, fp, color=cols, edgecolor=BASE_EDGE)
    ax[1].set_ylim(0, 112); ax[1].set_ylabel("recombinant controls accepted (%)")
    ax[1].set_title("Superset false positives"); S.panel_tag(ax[1], "B")
    for rect, lab in zip(b, [f"0/{r['recombinants_total']}", f"{r['debruijn_superset_fp']}/{r['recombinants_total']}",
                             f"{r['revdet_superset_blocks']}/{r['blocks']} blk"]):
        ax[1].text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 2, lab, ha="center", fontsize=9, fontweight="bold")
    # (C) median nodes per block
    nodes = [r["median_nodes"]["suffix"], r["median_nodes"]["debruijn"], r["median_nodes"]["revdet"]]
    b = ax[2].bar(methods, nodes, color=cols, edgecolor=BASE_EDGE)
    ax[2].set_ylabel("median nodes / block"); ax[2].set_title("Index size (compactness)")
    S.panel_tag(ax[2], "C")
    for rect, v in zip(b, nodes):
        ax[2].text(rect.get_x() + rect.get_width() / 2, v + 4, str(v), ha="center", fontweight="bold")
    fig.suptitle("Resolution × fidelity × size: 71 multi-species chrI blocks, 653 queries (vs the brute oracle)",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    _save(fig, "FIresolution.png")


# --------------------------------------------------------------------------- 3. MECHANISM (schematic)
def fig_mechanism():
    fig, ax = plt.subplots(figsize=(12.6, 4.2)); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 100)

    def box(x, y, w, h, text, fc, ec=BASE_EDGE, fs=10, tc="black", weight="normal"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4", fc=fc, ec=ec, lw=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, fontweight=weight)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                                     color="#555555", lw=1.6))

    # multi-string text with distinct separators
    ax.text(2, 92, "1.  multi-string text  (one block; distinct per-species separators $₀,$₁ < A<C<G<T)",
            fontsize=10.5, fontweight="bold")
    cells = list("ACGAC") + ["$₀"] + list("ACGTC") + ["$₁"]
    spe = ["sacCer3"] * 6 + ["sacPar"] * 6
    for i, (c, sp) in enumerate(zip(cells, spe)):
        sep = c.startswith("$")
        box(4 + i * 6.0, 78, 5.4, 8, c, "#efeafc" if not sep else "#dcdcdc", fs=11,
            tc=ACCENT if not sep else "#777777", weight="bold")
    ax.text(4 + 12 * 6.0 + 3, 82, "species = document array;  position = sampled suffix array",
            fontsize=9.5, color="#555555", va="center")

    arrow(50, 76, 50, 67)
    # backward search -> interval == occurrences
    box(10, 56, 80, 9, "2.  backward search of pattern P  →  half-open interval  [lo, hi)  ==  EXACTLY the occurrences of P",
        "#efeafc", ACCENT, fs=11, tc=ACCENT, weight="bold")
    ax.text(50, 51, "(a DNA pattern can never cross a separator, so every suffix in [lo,hi) lies in one species)",
            ha="center", fontsize=9, color="#555555")
    arrow(50, 50, 50, 41)
    # tag readout
    box(8, 28, 40, 11, "3a.  document array  →  WHICH species\n(sacCer3 / sacPar / sacKud / …)",
        "#e7f3ee", "#1b9e77", fs=10, tc="#0f6b4f")
    box(52, 28, 40, 11, "3b.  toehold + φ (r-index)  →  WHICH position\n→ genomic coordinate (± strand)",
        "#e7f3ee", "#1b9e77", fs=10, tc="#0f6b4f")
    arrow(28, 27, 28, 19); arrow(72, 27, 72, 19)
    box(20, 8, 60, 9, "every occurrence reported as  (species, source, gstart–gend, strand)  — multi-hit, exact",
        "#efeafc", ACCENT, fs=10.5, tc=ACCENT, weight="bold")
    # certificate inset
    ax.add_patch(FancyBboxPatch((6, 0.3), 88, 5.6, boxstyle="round,pad=0.3", fc="#f7f7f7", ec="#cccccc", lw=1))
    ax.text(50, 3.1, "Certificate: the recognizer independently accepts this graph; its Wheeler order IS the "
            "suffix-array rank\n(recognizer_iso_to_sa_rank = true; Gagie–Manzini–Sirén theorem).",
            ha="center", va="center", fontsize=8.3, color="#444444", style="italic", linespacing=1.4)
    ax.set_title("How a query resolves species + position over the multi-string BWT", fontsize=12.5, fontweight="bold")
    _save(fig, "FImechanism.png")


# --------------------------------------------------------------------------- 4. SCALE / SPEED / MEMORY
def fig_scale():
    g = _load("suffix_genome_scaling.json")
    pc = [r for r in g["per_chrom"] if "n_blocks" in r]
    blocks = np.array([r["n_blocks"] for r in pc]); build = np.array([r["build_s"] for r in pc])
    ondisk = np.array([r["ondisk_mb"] for r in pc])
    rows = list(csv.DictReader(open(os.path.join(DATA, "suffix_chrI_scaling.csv"))))
    fig, ax = plt.subplots(1, 3, figsize=(12.6, 3.9))
    # (A) per-chromosome linear scaling
    ax[0].scatter(blocks, build, s=34, color=ACCENT, zorder=3, label="build time")
    m, c = np.polyfit(blocks, build, 1)
    xs = np.array([blocks.min(), blocks.max()]); ax[0].plot(xs, m * xs + c, color=BASE_C, lw=1.2, ls="--")
    ax[0].set_xlabel("alignment blocks / chromosome"); ax[0].set_ylabel("build time (s)")
    ax[0].set_title("Per-chromosome build (linear)"); S.panel_tag(ax[0], "A")
    ax[0].annotate(f"17 chromosomes\n44,063 blocks\n{g['aggregate']['total_build_s']:.0f} s total",
                   xy=(0.04, 0.96), xycoords="axes fraction", va="top", fontsize=9, color="#444444")
    # (B) chrI a=4 s-tradeoff: on-disk (left) vs routed (right)
    a4 = sorted([r for r in rows if r["sample"] == "rate" and r["a"] == "4"], key=lambda r: int(r["s"]))
    sv = [int(r["s"]) for r in a4]; disk = [int(r["ondisk_arrays_kb"]) / 1024 for r in a4]
    rtd = [float(r["routed_ms"]) for r in a4]
    ax[1].plot(sv, disk, "-o", color=ACCENT, label="on-disk (MB)")
    ax[1].set_xlabel("SA-sample rate s (a=4)"); ax[1].set_ylabel("on-disk size (MB)", color=ACCENT)
    ax[1].set_xticks(sv); ax[1].set_title("chrI size ↔ speed knob"); S.panel_tag(ax[1], "B")
    ax2 = ax[1].twinx(); ax2.plot(sv, rtd, "--s", color="#1b9e77", label="routed locate (ms)")
    ax2.set_ylabel("routed locate (ms)", color="#1b9e77"); ax2.grid(False)
    # (C) on-disk vs in-mem + human projection
    ag = g["aggregate"]; hp = ag["human_projection"]
    labels = ["yeast\non-disk", "yeast\nin-mem (all)", "human\non-disk", "human\nin-mem (all)"]
    vals = [ag["total_ondisk_mb"] / 1024, ag["total_inmem_mb"] / 1024,
            hp["est_ondisk_gb"], hp["est_inmem_all_gb"]]
    cols = [ACCENT, BASE_C, ACCENT, BASE_C]
    b = ax[2].bar(labels, vals, color=cols, edgecolor=BASE_EDGE); ax[2].set_yscale("log")
    ax[2].set_ylabel("GB (log)"); ax[2].set_title("On-disk ≪ in-memory")
    ax[2].set_ylim(0.1, 1e4); S.panel_tag(ax[2], "C")
    for rect, v in zip(b, vals):
        ax[2].text(rect.get_x() + rect.get_width() / 2, v * 1.15,
                   f"{v:.1f}" if v < 100 else f"{v:.0f}", ha="center", fontsize=8.5, fontweight="bold")
    fig.suptitle("Scale, speed, and memory: whole yeast genome measured, human MSA projected (×262)",
                 fontsize=12, y=1.02); fig.tight_layout()
    _save(fig, "FIscale.png")


# --------------------------------------------------------------------------- 5. QUERY / LOCATE
def fig_query():
    rt = _load("suffix_router.json"); loc = _load("genome_chrI_locate.json")["overall"]
    ex = _load("genome_pangenome.json")["biological_example"]
    fig, ax = plt.subplots(1, 3, figsize=(12.6, 3.9))
    # (A) suffix router decomposition
    names = ["scan\nall blocks", "w-mer\nprefilter", "global\nrouted"]
    vals = [rt["touch_all_ms"], rt["wmer_prefilter_ms"], rt["routed_ms"]]
    b = ax[0].bar(names, vals, color=[BASE_C, "#6a51a3", ACCENT], edgecolor=BASE_EDGE)
    ax[0].set_yscale("log"); ax[0].set_ylabel("ms / query (log)")
    ax[0].set_title("Suffix router (chrI, 992 blocks)"); S.panel_tag(ax[0], "A")
    for rect, v in zip(b, vals):
        ax[0].text(rect.get_x() + rect.get_width() / 2, v * 1.3, f"{v:.3g}", ha="center", fontsize=9, fontweight="bold")
    ax[0].annotate(f"{rt['speedup_routed_vs_touchall']:.0f}×\nmedian {rt['median_survivors']:.0f}/992 survive",
                   xy=(2, vals[2]), xytext=(1.1, vals[0] * 0.4), fontsize=9.5, color=ACCENT, fontweight="bold",
                   arrowprops=dict(arrowstyle="->", color=ACCENT))
    # (B) De Bruijn locate baseline decomposition
    names = ["naive\nscan", "FM\nprefilter", "routed\nk-mer"]
    vals = [loc["naive_ms"], loc["fm_prefilter_ms"], loc["routed_ms"]]
    b = ax[1].bar(names, vals, color=[BASE_C, "#6a51a3", ACCENT], edgecolor=BASE_EDGE)
    ax[1].set_yscale("log"); ax[1].set_ylabel("ms / query (log)")
    ax[1].set_title("De Bruijn locate (baseline)"); S.panel_tag(ax[1], "B")
    for rect, v in zip(b, vals):
        ax[1].text(rect.get_x() + rect.get_width() / 2, v * 1.3, f"{v:.3g}", ha="center", fontsize=9, fontweight="bold")
    ax[1].annotate(f"{loc['speedup_routed_vs_naive']:.0f}×", xy=(2, vals[2]), xytext=(1.0, vals[0] * 0.4),
                   fontsize=11, color=ACCENT, fontweight="bold", arrowprops=dict(arrowstyle="->", color=ACCENT))
    # (C) worked example: species x position hit map
    sp = sorted(ex["species"]); ypos = {s: i for i, s in enumerate(sp)}
    for h in ex["hits"]:
        if h["species"] in ypos:
            ax[2].scatter(h["gstart"], ypos[h["species"]], s=44, color=ACCENT, zorder=3)
    ax[2].set_yticks(range(len(sp))); ax[2].set_yticklabels(sp)
    ax[2].set_xlabel("genomic position (bp)"); ax[2].set_ylim(-0.6, len(sp) - 0.4)
    ax[2].set_title(f"Query '{ex['pattern']}' → {ex['n_hits']} hits, {len(sp)} species"); S.panel_tag(ax[2], "C")
    fig.suptitle("Pattern matching: count / locate (species + genomic position), multi-hit", fontsize=12, y=1.02)
    fig.tight_layout()
    _save(fig, "FIquery.png")


# --------------------------------------------------------------------------- 6. AUDIT coverage
def fig_audit():
    # every count appears verbatim in index/AUDIT.md and is gated by verify_index_report_numbers.py
    dims = [("De Bruijn WGIndex (FM)", 2067185),    # dim F: 2,067,185 over 8,000 graphs
            ("coordinate transform", 1600000),       # dim C: ~1.6M cases
            ("φ / toehold assertions", 160000),      # dim B: >160k assertions
            ("C++ parity (exhaustive)", 27280),      # dim G: 27,280 cases
            ("cross-engine stress", 13858)]          # dim H: 11,088 + 2,770
    dims.sort(key=lambda d: d[1])
    fig, ax = plt.subplots(figsize=(11.5, 3.4))
    y = range(len(dims))
    ax.barh(list(y), [d[1] for d in dims], color=ACCENT, edgecolor=BASE_EDGE)
    ax.set_yticks(list(y)); ax.set_yticklabels([d[0] for d in dims]); ax.set_xscale("log")
    ax.set_xlabel("independently-verified cases / assertions (log)")
    ax.set_xlim(5e3, 1e7)
    for i, d in enumerate(dims):
        ax.text(d[1] * 1.18, i, f"{d[1]:,}", va="center", fontsize=9, fontweight="bold")
    ax.set_title("Adversarial audit: 8 algorithms · >4,000,000 cases vs independent oracles "
                 "(largest dimensions shown)\n1 bug found + fixed (DAWG.count('')), 0 mismatches at every scale",
                 fontsize=10.5)
    fig.tight_layout()
    _save(fig, "FIaudit.png")


def main():
    fig_hero(); fig_resolution(); fig_mechanism(); fig_scale(); fig_query(); fig_audit()


if __name__ == "__main__":
    main()
