#!/usr/bin/env python3
"""
style.py -- one visual language for every WGT report figure.

Imported by plot_report.py and plot_limit.py. One rule, enforced everywhere, so a reader decodes the
palette once and never again:

  * VERSION (v1.0.0 vs current)  -> v1.0.0 = neutral GRAY (the baseline), current = one BOLD VIOLET
    accent. This pair appears in EVERY two-version figure and means nothing else.
  * VERDICT (Wheeler / non-WG)   -> categorical TEAL / ORANGE. Only ever a verdict; never a version.
    (Safe because version is gray/violet, so teal never collides with "current".)
  * FAMILY (complete / dnfa)     -> line style + marker (solid-o / dashed-s), never a third hue.
  * GENERATORS (MSA builds)      -> categorical blue / orange / green.
  * REFERENCE / walls            -> neutral grays.

Memory convention (locked): GNU `time -v` reports KiB; convert with /1024 -> "MB", /1024^2 -> "GB"
(binary, written loosely MB/GB). Keeps the iconic 56 MB and is consistent across micro + lazy tables.

Use apply_style() once at import, then pull colors/labels from the dicts and helpers below.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# --------------------------------------------------------------------------- palettes
# VERSION: v1.0.0 = neutral gray baseline; current = bold violet accent. Locked across all figures.
BIN = {
    "pre41": "#9097a1",   # v1.0.0 (2023, dense)            -- neutral gray baseline
    "pre42": "#6a51a3",   # (intermediate; unused two-way)  -- kept so stray refs don't crash
    "new":   "#3f007d",   # current (this work)             -- bold violet accent
}
BIN_LABEL = {
    "pre41": "v1.0.0 (2023)",
    "pre42": "pre-4.2 (intermediate)",
    "new":   "current (this work)",
}
BASE_C  = BIN["pre41"]    # alias: the baseline version
ACCENT  = BIN["new"]      # alias: the current/headline version
BASE_EDGE = "#5f656e"     # darker edge for gray bars on white

# Verdicts: categorical, disjoint from the version pair.
VERDICT = {
    "WG":  "#1b9e77",    # teal-green   (Wheeler / SAT)
    "nonWG": "#d95f02",  # orange       (non-Wheeler / UNSAT)
}
VERDICT_LABEL = {"WG": "Wheeler", "nonWG": "non-Wheeler"}

# Families on the synthetic worst-case ladder: encode by line style + marker, never a new hue.
FAMILY_STYLE = {"complete": ("-", "o"), "dnfa": ((0, (5, 3)), "s")}
FAMILY_LABEL = {"complete": "complete", "dnfa": "d-NFA"}

# Generators (MSA constructions).
GEN_COLOR = {"debruijn": "#1f78b4", "revdet": "#ff7f00", "trie": "#33a02c"}

# Per-graph-type accents (4 biological corpora).
TYPE_COLOR = {
    "DeBruijnG_DNA": "#1f78b4", "DeBruijnG_AA": "#6baed6",
    "RevDetG_DNA":   "#e6550d", "RevDetG_AA":   "#fd8d3c",
}
TYPE_LABEL = {
    "DeBruijnG_DNA": "De Bruijn DNA", "DeBruijnG_AA": "De Bruijn AA",
    "RevDetG_DNA": "RevDet DNA", "RevDetG_AA": "RevDet AA",
}

# Limit-test algorithms: same version => same gray/violet as the report figures.
ALGO_STYLE = {
    "smt":      ("#2166ac", "-",  "o", "default SMT"),
    "full":     (BIN["new"], "-",  "s", "full-range (this work)"),
    "full-old": (BIN["pre41"], "--", "s", "full-range (v1.0.0)"),
    "perm":     ("#7f7f7f", "-.", "^", "permutation"),
    "exp":      ("#bdbdbd", ":",  "D", "exponential ref."),
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
WALL_FILL  = "#d9d9d9"     # shaded timeout/over-budget region
BAND_TEAL  = "#1b9e77"
GRID_ALPHA = 0.22

# Memory unit conversion (locked: GNU time KiB -> binary MB/GB).
def kib_to_mb(kib):  return kib / 1024.0
def kib_to_gb(kib):  return kib / 1024.0 / 1024.0


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
    """Shade the 'within wall-clock noise' band around 1x."""
    ax.axhspan(lo, hi, color=color, alpha=0.12, zorder=0)


def legend_binaries(ax, keys=("pre41", "new"), **kw):
    handles = [plt.Line2D([], [], color=BIN[k], lw=3, label=binary_label(k)) for k in keys]
    ax.legend(handles=handles, **kw)


def callout(ax, text, color=ACCENT, fontsize=22, xy=(0.5, 0.5), ha="center", va="center", weight="bold"):
    """Big headline number, centered in axis-fraction coords (for the hero scorecard)."""
    ax.text(xy[0], xy[1], text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=fontsize, fontweight=weight, color=color)


def gain_arrow(ax, x, y_lo, y_hi, text, color=ACCENT):
    """Vertical double-headed arrow between two y-values at x, labeled with the gain (data coords)."""
    ax.annotate("", xy=(x, y_hi), xytext=(x, y_lo),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.6))
    ax.text(x, (y_lo * y_hi) ** 0.5, " " + text, color=color, fontsize=9.5,
            fontweight="bold", ha="left", va="center")
