#!/usr/bin/env python3
"""
style.py -- one visual language for every WGT report figure.

Imported by plot_report.py and plot_limit.py. Resolves the prior palette collision (blue meant BOTH
"new binary" and "WG verdict"; red meant BOTH "pre-4.1" and "non-WG") by giving each semantic axis a
disjoint, colorblind-aware palette:

  * BINARIES (generations)  -> sequential PURPLE ramp; darker = newer/better. Never a verdict color.
  * VERDICTS (WG / non-WG)  -> categorical teal / orange. Never a binary color.
  * GENERATORS (MSA builds) -> categorical blue / orange / green.
  * REFERENCE / walls       -> neutral grays.

Use apply_style() once at import, then pull colors/labels from the dicts and helpers below.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# --------------------------------------------------------------------------- palettes
# Binary generations: light -> dark purple == older -> newer.
# Two-way comparison: v1.0.0 (the last stable GitHub release, 2023, dense O(E^2)) vs the current work
# (sparse encodings + lazy/CEGAR). The `pre41` key == v1.0.0's encoding (verified identical structure),
# so it doubles as the OLD slot; `pre42` is the dropped intermediate (kept only so stray refs don't crash).
BIN = {
    "pre41": "#9e9ac8",   # v1.0.0 (2023) -- light
    "pre42": "#6a51a3",   # (intermediate; unused in the two-way report)
    "new":   "#3f007d",   # current (this work) -- dark
}
BIN_LABEL = {
    "pre41": "v1.0.0 (2023, dense)",
    "pre42": "pre-4.2 (intermediate)",
    "new":   "current (sparse + lazy)",
}

# Verdicts: categorical, distinct from the purple ramp.
VERDICT = {
    "WG":  "#1b9e77",   # teal-green   (Wheeler / SAT)
    "nonWG": "#d95f02",  # orange       (non-Wheeler / UNSAT)
}
VERDICT_LABEL = {"WG": "Wheeler", "nonWG": "non-Wheeler"}

# Generators (MSA constructions).
GEN_COLOR = {
    "debruijn": "#1f78b4",
    "revdet":   "#ff7f00",
    "trie":     "#33a02c",
}

# Per-graph-type accents (4 biological corpora) -- hue by generator, kept consistent with GEN_COLOR.
TYPE_COLOR = {
    "DeBruijnG_DNA": "#1f78b4",
    "DeBruijnG_AA":  "#6baed6",
    "RevDetG_DNA":   "#e6550d",
    "RevDetG_AA":    "#fd8d3c",
}
TYPE_LABEL = {
    "DeBruijnG_DNA": "De Bruijn DNA",
    "DeBruijnG_AA":  "De Bruijn AA",
    "RevDetG_DNA":   "RevDet DNA",
    "RevDetG_AA":    "RevDet AA",
}

# Limit-test algorithms: same binary => same color as the §4 figures.
ALGO_STYLE = {
    "smt":      ("#2166ac", "-",  "o", "default SMT"),
    "full":     (BIN["new"], "-",  "s", "full-range (this work)"),
    "full-old": (BIN["pre41"], "--", "s", "full-range (v1.0.0)"),
    "perm":     ("#7f7f7f", "-.", "^", "permutation"),
    "exp":      ("#bdbdbd", ":",  "D", "exponential ref."),
    # clean two-way (v1.0.0 vs current) algos
    "old-default": (BIN["pre41"], "--", "o", "v1.0.0 default (vanilla z3)"),
    "new-lazy":    (BIN["new"],   "-",  "o", "current default (lazy/CEGAR)"),
    "new-smt":     ("#2166ac",    ":",  "o", "current vanilla z3 (-s smt)"),
    "old-f":       (BIN["pre41"], "--", "s", "v1.0.0 full-range (dense)"),
    "new-f":       (BIN["new"],   "-",  "s", "current full-range (sparse)"),
}

# Reference / annotation neutrals.
REF_GRAY   = "#666666"     # y=x, 1x lines
WALL_GRAY  = "#444444"     # solver/timeout walls (dashed)
WALL_LS    = (0, (6, 4))
BAND_TEAL  = "#1b9e77"     # real-MSA size band
GRID_ALPHA = 0.25


def apply_style():
    """Set shared rcParams. Call once after importing pyplot in the plotting module."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.titleweight": "semibold",
        "axes.labelsize": 11,
        "axes.labelweight": "medium",
        "legend.fontsize": 9,
        "legend.frameon": False,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.grid": True,
        "grid.alpha": GRID_ALPHA,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })


# --------------------------------------------------------------------------- helpers
def binary_label(key):
    return BIN_LABEL.get(key, key)


def verdict_label(key):
    return VERDICT_LABEL.get(key, key)


def panel_tag(ax, letter, loc=(-0.08, 1.04), fontsize=14):
    """Vector panel letter in axis-fraction coords (replaces compose_figs.py's painted strip)."""
    ax.text(loc[0], loc[1], f"({letter})", transform=ax.transAxes,
            fontsize=fontsize, fontweight="bold", va="bottom", ha="right")


def one_line(ax, y=1.0, label="1× (no change)", color=REF_GRAY):
    """Horizontal reference line at a speedup of 1x."""
    ax.axhline(y, color=color, lw=1.0, ls="--", zorder=1)
    ax.text(0.99, y, " " + label, transform=ax.get_yaxis_transform(),
            ha="right", va="bottom", fontsize=8, color=color)


def diagonal(ax, color=REF_GRAY):
    """y = x reference for scatter (uses current limits)."""
    lo = min(ax.get_xlim()[0], ax.get_ylim()[0])
    hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([lo, hi], [lo, hi], color=color, lw=1.0, ls="--", zorder=1)


def breakeven_band(ax, lo=0.98, hi=1.02, color=REF_GRAY):
    """Shade the 'within wall-clock noise' band around 1x so break-even bars sit visibly inside it."""
    ax.axhspan(lo, hi, color=color, alpha=0.12, zorder=0)


def legend_binaries(ax, keys=("pre41", "new"), **kw):
    handles = [plt.Line2D([], [], color=BIN[k], lw=3, label=binary_label(k)) for k in keys]
    ax.legend(handles=handles, **kw)
