#!/usr/bin/env python3
"""
plot_report.py -- figures for the WGT technical report (v1.0.0 vs current, lazy/CEGAR rebuild).

Six figures, three axes, one visual language (see style.py: version = gray/violet, verdict = teal/
orange, family = line style). Each figure is a SINGLE matplotlib figure (no post-hoc PNG gluing), so
panels share fonts, ticks, and DPI:

  HERO          rfig_hero          -- 3-axis scorecard with the headline numbers + honest-trade footer
  CORRECTNESS   rfig_correctness   -- false-accepts vs the brute-force oracle, per backend
  CAPABILITY    rfig_lazy_ceiling  -- THE headline: lazy/CEGAR moves the default-path ceiling (wall+RSS)
  PERFORMANCE   rfig_atoms         -- encoding size in atoms (the mechanism)
                rfig_performance   -- 2x2: -f scatter, setup/solve split, peak memory, per-type speedup
  PRACTICALITY  rfig_practicality  -- MSA Wheeler-rate, recognition <1 s, and DAG repair blow-up

All numbers trace to benchmark/report_figs/verify_report_numbers.py (run it; it must be all-PASS).
Render with:  ~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/plot_report.py
"""
import json
import os
import sys
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import numpy as np                # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

import style as S                 # noqa: E402
from style import BIN, VERDICT, ACCENT, BASE_C, BASE_EDGE  # noqa: E402

S.apply_style()

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LAZY = os.path.join(HERE, "..", "lazy_cegar")
OUT = HERE


# ----------------------------------------------------------------------------- loaders
def load_csv(path):
    if not os.path.exists(path):
        return None
    rows = []
    with open(path) as fh:
        header = fh.readline().strip().split(",")
        for line in fh:
            rows.append(dict(zip(header, line.rstrip("\n").split(","))))
    return rows


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _short(name):
    return (name.replace("Human_", "").replace("_orthologues", "")
                .replace("_DNA", "").replace("_AA", "").replace(".dot", ""))


def load_ftiming():
    """Two-way -f timing: ftiming_oldnew.raw.jsonl (pre41=v1.0.0, new=current) over all four corpora."""
    path = os.path.join(DATA, "ftiming_oldnew.raw.jsonl")
    if not os.path.exists(path):
        return []
    per_graph = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        tag = "AA" if "_AA/" in rec["dot"] else "DNA"
        g = per_graph.setdefault(rec["dot"], {"name": rec["name"], "edges": str(rec["edges"]),
                                              "_corpus": tag, "_timeout": 120.0})
        lab = rec["label"]
        g[f"{lab}_wall"] = ("" if rec.get("median_wall") is None else f"{rec['median_wall']:.6f}")
        g[f"{lab}_cpu"] = ("" if rec.get("median_cpu") is None else f"{rec['median_cpu']:.0f}")
        g[f"{lab}_status"] = rec.get("status", "")
        g[f"{lab}_verdict"] = ("" if rec.get("verdict") is None else str(rec["verdict"]))
    return list(per_graph.values())


def _metric(row, label, kind):
    st_ = row.get(f"{label}_status", "")
    v = fnum(row.get(f"{label}_{kind}"))
    if kind == "cpu" and v is not None:
        v = v / 1e6
    return v, st_


TYPE_FROM_DIR = {"DeBruijnG_DNA": "De Bruijn\nDNA", "DeBruijnG_AA": "De Bruijn\nAA",
                 "RevDetG_DNA": "RevDet\nDNA", "RevDetG_AA": "RevDet\nAA"}
TYPE_ORDER = ["De Bruijn\nDNA", "De Bruijn\nAA", "RevDet\nDNA", "RevDet\nAA"]


def load_ftiming_bytype():
    path = os.path.join(DATA, "ftiming_oldnew.raw.jsonl")
    if not os.path.exists(path):
        return None
    per_graph = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            dotpath = rec["dot"]
            gtype = next((TYPE_FROM_DIR[d] for d in TYPE_FROM_DIR if f"/{d}/" in dotpath), None)
            if gtype is None:
                continue
            g = per_graph.setdefault(dotpath, {"_type": gtype, "edges": rec["edges"], "_dot": dotpath})
            lab = rec["label"]
            g[f"{lab}_wall"] = rec.get("median_wall")
            g[f"{lab}_status"] = rec.get("status", "")
            if rec.get("verdict") is not None:
                g["new_verdict" if lab == "new" else f"{lab}_verdict"] = str(rec["verdict"])
    return list(per_graph.values())


def _paired_ratio(r, old, new="new"):
    ov, nv = r.get(f"{old}_wall"), r.get(f"{new}_wall")
    if (r.get(f"{old}_status") == "DECISIVE" and r.get(f"{new}_status") == "DECISIVE"
            and ov and nv and nv > 0):
        return ov / nv
    return None


def load_atom_counts():
    rows = load_csv(os.path.join(DATA, "atom_counts.csv"))
    if not rows:
        return None
    for r in rows:
        for k in ("nodes", "edges", "labels", "pre41_total", "new_total",
                  "pre41_a2", "pre41_a3", "new_a2", "new_a3", "mean_DE", "frac_edges_block"):
            r[k] = fnum(r.get(k))
    return rows


def _lazy_rows():
    return (load_csv(os.path.join(LAZY, "results_lazy_old.csv")),
            load_csv(os.path.join(LAZY, "results_lazy_ceiling.csv")))


def _lazy_point(rows, fam, backend, n):
    for r in rows or []:
        if r.get("family") == fam and r.get("backend") == backend and r.get("n") == str(n):
            return r
    return None


# ============================================================ PANEL DRAWS
def draw_validation(ax):
    """Verdict agreement vs the independent brute-force oracle: corpora x deciders, 0 disagreements.
    A validation grid (the recognizer's SMT and permutation backends AND the rebuilt exponential
    reference all agree with the oracle on every decided graph) -- not a version comparison."""
    sm = json.load(open(os.path.join(DATA, "static_metrics.json")))["verdict_agreement"]
    corpora = ["REAL", "SYNTH"]
    deciders = ["SMT", "PERM", "EXP"]
    decider_disp = {"SMT": "recognizer\n(SMT / lazy)", "PERM": "recognizer\n(permutation)",
                    "EXP": "exponential\nreference"}
    teal = VERDICT["WG"]
    ax.set_xlim(-0.5, len(deciders) - 0.5); ax.set_ylim(-0.5, len(corpora) - 0.5)
    for i, cpr in enumerate(corpora):
        for j, dn in enumerate(deciders):
            agree = int(sm[cpr][dn][0]); decided = int(sm[cpr]["graphs"])
            ax.add_patch(plt.Rectangle((j - 0.46, i - 0.42), 0.92, 0.84, facecolor="white",
                                       edgecolor="#d9d9d9", lw=1.0, zorder=1))
            ax.add_patch(plt.Rectangle((j - 0.46, i - 0.42), 0.05, 0.84, facecolor=teal,
                                       edgecolor="none", zorder=2))
            ax.text(j, i + 0.10, f"{agree}/{decided}", ha="center", va="center",
                    fontsize=13, fontweight="bold", color="#222", zorder=3)
            ax.text(j, i - 0.22, "✓ agree", ha="center", va="center", fontsize=9, color=teal, zorder=3)
    ax.set_xticks(range(len(deciders))); ax.set_xticklabels([decider_disp[d] for d in deciders])
    ax.set_yticks(range(len(corpora)))
    ax.set_yticklabels([f"{c}\n({int(sm[c]['graphs'])} graphs)" for c in corpora])
    ax.invert_yaxis()
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0); ax.grid(False)
    ax.set_title(f"Verdict agreement vs the brute-force oracle — {sm['total_disagreements']} "
                 f"disagreements\n({sm['total_graphs']} graphs: {sm['total_wg']} Wheeler, "
                 f"{sm['total_nonwg']} non-Wheeler; every accepted order independently re-validated)",
                 fontsize=11)


def draw_mechanism_compression(ax):
    """How little the lazy/CEGAR default builds: A3 constraints materialized vs the full O(n^2) pair
    universe, across n. The built curve stays ~linear (a few thousand) while the universe grows
    quadratically (hundreds of millions); at n=32,768 it is 3,835 of 402,722,292 (~99.999% never built)."""
    cur = load_csv(os.path.join(LAZY, "results_lazy_ceiling.csv"))
    for fam in ("complete", "dnfa"):
        ls, mk = S.FAMILY_STYLE[fam]
        uni, built = [], []
        for r in cur or []:
            if r.get("family") != fam or r.get("backend") != "lazy" or r.get("verdict") != "WG":
                continue
            n = fnum(r.get("n")); pu = fnum(r.get("pair_universe")); ma = fnum(r.get("materialized_a3"))
            if n and pu and ma:
                uni.append((n, pu)); built.append((n, ma))
        uni.sort(); built.sort()
        if uni:
            xs, ys = zip(*uni)
            ax.plot(xs, ys, marker=mk, ms=4, lw=2.0, color=BASE_C, ls=ls,
                    label=f"full $O(n^2)$ A3 universe — {S.FAMILY_LABEL[fam]}")
        if built:
            xs, ys = zip(*built)
            ax.plot(xs, ys, marker=mk, ms=4, lw=2.4, color=ACCENT, ls=ls,
                    label=f"A3 actually built (lazy) — {S.FAMILY_LABEL[fam]}")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("graph size  n  (nodes, log)")
    ax.set_ylabel("within-label (A3) constraints (log)")
    ax.set_title("(A) The lazy default builds almost none of the $O(n^2)$ formula")
    ax.annotate("n=32,768: 3,835 built\nof 402,722,292\n(~99.999% never built)",
                xy=(32768, 3835), xytext=(2200, 9e6), fontsize=8.5, color=ACCENT, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.2))
    ax.text(0.03, 0.06, "lazy/CEGAR converges in ≈5–8 rounds at every size",
            transform=ax.transAxes, fontsize=7.8, color="#555", style="italic")
    ax.legend(fontsize=7.4, loc="upper left")
    ax.grid(True, which="both", alpha=0.22)


def draw_lazy(ax, metric):
    old, cur = _lazy_rows()
    is_mem = (metric == "rss_kb")
    conv = S.kib_to_mb if is_mem else (lambda v: v)
    series = [("pre41", old, "smt", "complete"), ("pre41", old, "smt", "dnfa"),
              ("new", cur, "lazy", "complete"), ("new", cur, "lazy", "dnfa")]
    for ver, rows, backend, fam in series:
        ls, mk = S.FAMILY_STYLE[fam]
        pts = []
        for r in rows or []:
            if r.get("backend") != backend or r.get("family") != fam or r.get("verdict") != "WG":
                continue
            n = fnum(r.get("n")); v = fnum(r.get(metric))
            if n and v:
                pts.append((n, conv(v)))
        pts.sort()
        if pts:
            xs, ys = zip(*pts)
            lab = f"{S.binary_label(ver)} — {S.FAMILY_LABEL[fam]}"
            ax.plot(xs, ys, marker=mk, ms=4, lw=2.0, color=BIN[ver], ls=ls, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("graph size  n  (nodes, log)")
    # v1.0.0 timeout wall + headline gain arrow at n=2816 (complete)
    o = _lazy_point(old, "complete", "smt", 2816)
    c = _lazy_point(cur, "complete", "lazy", 2816)
    if o and c:
        ov = conv(fnum(o[metric])); cv = conv(fnum(c[metric]))
        ax.axvspan(2816, ax.get_xlim()[1] if ax.get_xlim()[1] > 2816 else 5000,
                   color=S.WALL_FILL, alpha=0.5, zorder=0)
        gain = (fnum(o[metric]) / fnum(c[metric]))
        S.gain_arrow(ax, 2816, cv, ov, f"≈{gain:.0f}×")
    if is_mem:
        ax.set_ylabel("peak resident set size (MB, log)")
        ax.set_title("(B) Peak memory — 7.3 GB → 56 MB at n=2,816  (≈133× lighter)")
    else:
        ax.set_ylabel("wall-clock time (s, log)")
        ax.set_title("(A) Recognition time — 488 s → 0.9 s at n=2,816  (≈554× faster)")
    ax.text(0.97, 0.05, "shaded: v1.0.0 times out\n(600 s budget)", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=7.5, color=S.WALL_GRAY)
    ax.legend(fontsize=7.6, loc="upper left")
    ax.grid(True, which="both", alpha=0.22)


def draw_scatter(ax, kind="cpu"):
    rows = load_ftiming()
    cap = max(r["_timeout"] for r in rows)
    wg_x, wg_y, nw_x, nw_y, to_x, to_y = [], [], [], [], [], []
    for r in rows:
        ov, ost = _metric(r, "pre41", kind)
        nv, nst = _metric(r, "new", kind)
        if ost == "DECISIVE" and nst == "DECISIVE" and ov and nv:
            if r.get("new_verdict") == "1":
                wg_x.append(ov); wg_y.append(nv)
            else:
                nw_x.append(ov); nw_y.append(nv)
        elif ost == "TIMEOUT" and nst == "DECISIVE" and nv:
            to_y.append(nv); to_x.append(cap)
    if wg_x:
        ax.scatter(wg_x, wg_y, s=15, alpha=0.55, color=VERDICT["WG"], edgecolors="none",
                   label=f"Wheeler ({len(wg_x)})")
    if nw_x:
        ax.scatter(nw_x, nw_y, s=15, alpha=0.55, color=VERDICT["nonWG"], edgecolors="none",
                   label=f"non-Wheeler ({len(nw_x)})")
    if to_x:
        ax.scatter(to_x, to_y, s=42, marker="^", facecolors="none", edgecolors="#222",
                   linewidths=1.2, label=f"v1.0.0 timed out, current finished ({len(to_x)})")
    lo, hi = 1e-3, cap * 1.5
    ax.plot([lo, hi], [lo, hi], "--", color=S.REF_GRAY, lw=1, label="y = x")
    ax.axvline(cap, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1, alpha=0.7)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("v1.0.0 (2023) CPU-time per decision (s, log)")
    ax.set_ylabel("current — CPU-time per decision (s, log)")
    ax.set_title("(A) Per-graph -f time — below y=x is faster (≈all 444 graphs)")
    ax.legend(fontsize=7.6, loc="upper left")
    ax.grid(True, which="both", alpha=0.2)


def draw_setup_solve(ax):
    rows = load_csv(os.path.join(DATA, "micro_oldnew.setup_solve.csv"))
    graphs = []
    for r in rows:
        key = (r["name"], r["edges"])
        if key not in graphs:
            graphs.append(key)
    labels = ["pre41", "new"]
    ng = len(graphs); bw = 0.8 / len(labels); x = np.arange(ng)
    for li, lab in enumerate(labels):
        setups, solves = [], []
        for (name, edges) in graphs:
            rec = next((r for r in rows if r["name"] == name and r["binary"] == lab), None)
            setups.append((fnum(rec["setup_med"]) if rec else 0) or 0)
            solves.append((fnum(rec["solve_med"]) if rec else 0) or 0)
        off = (li - (len(labels) - 1) / 2) * bw
        c = BIN[lab]
        ax.bar(x + off, solves, bw, color=c, label=S.binary_label(lab))
        ax.bar(x + off, setups, bw, bottom=solves, color=c, alpha=0.4, hatch="////",
               edgecolor="white", linewidth=0)
    phase_handles = [Patch(facecolor="#999", label="z3 solve (solid)"),
                     Patch(facecolor="#999", alpha=0.4, hatch="////", label="encoding setup (hatched)")]
    gen_leg = ax.legend(loc="upper right", fontsize=8.5, title="version")
    ax.add_artist(gen_leg)
    ax.legend(handles=phase_handles, loc="upper center", fontsize=8.5)
    big = max(range(ng), key=lambda i: int(graphs[i][1]))
    ax.annotate("setup ≈14× smaller\n→ total ≈2× faster", xy=(big, 0.5),
                xytext=(big - 1.4, ax.get_ylim()[1] * 0.72), fontsize=8.5, color="#333", ha="center",
                arrowprops=dict(arrowstyle="->", color="#333", lw=1))
    short = [f"{_short(n)}\n(e={e})" for (n, e) in graphs]
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=7.5)
    ax.set_ylabel("wall time (s)")
    ax.set_title("(B) -f setup vs solve — sparsification collapses encoding setup")
    ax.grid(True, axis="y", alpha=0.25)


def draw_memory(ax):
    rows = load_csv(os.path.join(DATA, "micro_oldnew.mem.csv"))
    graphs = []
    for r in rows:
        if r["name"] not in graphs:
            graphs.append(r["name"])
    x = np.arange(len(graphs)); bw = 0.38
    for li, lab in enumerate(("pre41", "new")):
        vals = []
        for g in graphs:
            rec = next((r for r in rows if r["name"] == g and r["binary"] == lab), None)
            vals.append(S.kib_to_mb((fnum(rec["peak_rss_kb"]) if rec else 0) or 0))
        ax.bar(x + (li - 0.5) * bw, vals, bw, color=BIN[lab],
               edgecolor=(BASE_EDGE if lab == "pre41" else "none"), label=S.binary_label(lab))
    ax.set_xticks(x); ax.set_xticklabels([_short(g) for g in graphs], fontsize=7.5)
    ax.set_ylabel("peak resident set size (MB)")
    ax.set_title("(C) Peak memory — the honest ~1.8× space-for-time trade")
    ax.annotate("k=5: block fires\n(D/E≈0.27) → ~1.8×", xy=(1, 1180), xytext=(0.2, 950),
                fontsize=8, color="#333",
                arrowprops=dict(arrowstyle="->", color="#333", lw=1))
    ax.annotate("k=4: block off\n→ ≈equal", xy=(3, 60), xytext=(2.5, 430), fontsize=8, color="#333",
                arrowprops=dict(arrowstyle="->", color="#333", lw=1))
    ax.legend(loc="upper right", fontsize=8.5)
    ax.grid(True, axis="y", alpha=0.25)


def draw_type_speedup(ax):
    rows = load_ftiming_bytype()
    vstyle = [("Wheeler", "1", VERDICT["WG"]), ("non-Wheeler", "-1", VERDICT["nonWG"])]
    alphabet = {"De Bruijn\nDNA": "4-letter", "RevDet\nDNA": "4-letter",
                "De Bruijn\nAA": "20-letter", "RevDet\nAA": "20-letter"}
    types = [t for t in TYPE_ORDER if any(r["_type"] == t for r in rows)]
    x = np.arange(len(types)); bw = 0.38
    S.breakeven_band(ax, 1 - 0.02, 1 + 0.02)
    for vi, (vlabel, vval, color) in enumerate(vstyle):
        meds, ns = [], []
        for t in types:
            ratios = [v for v in (_paired_ratio(r, "pre41") for r in rows
                      if r["_type"] == t and r.get("new_verdict") == vval) if v]
            meds.append(float(np.median(ratios)) if ratios else 0.0); ns.append(len(ratios))
        off = (vi - 0.5) * bw
        bars = ax.bar(x + off, meds, bw, color=color, label=vlabel)
        for b, m, n in zip(bars, meds, ns):
            if n:
                ax.text(b.get_x() + b.get_width() / 2, m + 0.03, f"{m:.2f}×\nn={n}",
                        ha="center", va="bottom", fontsize=7.5)
    S.one_line(ax, 1.0, "1× (no change)")
    ax.set_xticks(x); ax.set_xticklabels(types, fontsize=9)
    for xi, t in zip(x, types):
        ax.text(xi, -0.16, alphabet[t], transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=7.5, color="#777", style="italic")
    ax.set_ylabel("median -f speedup  (v1.0.0 / current; >1 = faster)")
    ax.set_title("(D) Per-type speedup — faster on every type, no regression")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.margins(y=0.20)


def draw_atoms_scatter(ax):
    rows = load_atom_counts()
    sub = sorted((r for r in rows if r["type"] == "DeBruijnG_DNA"), key=lambda r: r["edges"])
    E = np.array([r["edges"] for r in sub], float)
    for lab in ("pre41", "new"):
        tot = np.array([r[f"{lab}_total"] for r in sub], float)
        m = (E > 0) & (tot > 0)
        ax.scatter(E[m], tot[m], s=11, alpha=0.40, color=BIN[lab], edgecolors="none")
        b, a = np.polyfit(np.log(E[m]), np.log(tot[m]), 1)
        xs = np.array([E[m].min(), E[m].max()])
        ax.plot(xs, np.exp(a) * xs ** b, color=BIN[lab], lw=2.4,
                label=f"{S.binary_label(lab)}   $\\propto E^{{{b:.2f}}}$")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("edges (log)"); ax.set_ylabel("SMT assertions (A2+A3, log)")
    ax.set_title("(B) Full-range atoms: dense $E^{2}$ → sparse $E^{1.6}$\n(De Bruijn DNA, block fires)")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.grid(True, which="both", alpha=0.2)


def draw_atoms_composition(ax):
    rows = load_atom_counts()
    types = ["DeBruijnG_DNA", "DeBruijnG_AA", "RevDetG_DNA", "RevDetG_AA"]
    x = np.arange(len(types)); bw = 0.36
    for lab, off in (("pre41", -bw / 2), ("new", bw / 2)):
        a2 = [st.median([r[f"{lab}_a2"] for r in rows if r["type"] == t]) for t in types]
        a3 = [st.median([r[f"{lab}_a3"] for r in rows if r["type"] == t]) for t in types]
        base = BIN[lab]
        ax.bar(x + off, a2, bw, color=base, label=f"{S.binary_label(lab)}: A2 (cross-group)")
        ax.bar(x + off, a3, bw, bottom=a2, color=base, alpha=0.45, hatch="xx", edgecolor="white",
               label=f"{S.binary_label(lab)}: A3 (within-group)")
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels([S.TYPE_LABEL[t].replace(" ", "\n") for t in types], fontsize=8.5)
    ax.set_ylabel("median SMT assertions (log)")
    ax.set_title("(C) Where the atoms live: A2 vs A3, by type\n(current shrinks whichever dominates)")
    ax.legend(fontsize=7, loc="upper right", ncol=1)
    ax.grid(True, axis="y", which="both", alpha=0.2)


GEN_DISP = {"debruijn": "De Bruijn", "revdet": "RevDet", "trie": "Trie"}


def draw_wheeler_rate(ax):
    rows = load_csv(os.path.join(DATA, "msa_practicality.csv"))
    gens = [g for g in ("debruijn", "trie", "revdet") if any(r["generator"] == g for r in rows)]
    x = np.arange(len(gens)); wg_frac, labels = [], []
    for g in gens:
        gr = [r for r in rows if r["generator"] == g and r["verdict"] in ("1", "-1", "0")]
        tot = len(gr) or 1
        nwg = sum(1 for r in gr if r["verdict"] == "1")
        nnw = sum(1 for r in gr if r["verdict"] in ("-1", "0"))
        wg_frac.append(100 * nwg / tot); labels.append((nwg, nnw))
    ax.bar(x, wg_frac, 0.6, color=VERDICT["WG"], label="Wheeler")
    ax.bar(x, [100 - w for w in wg_frac], 0.6, bottom=wg_frac, color=VERDICT["nonWG"], label="not Wheeler")
    for xi, (nwg, nnw) in zip(x, labels):
        ax.text(xi, 50, f"{nwg} WG\n{nnw} non", ha="center", va="center", fontsize=8.5,
                color="white", fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([GEN_DISP[g] for g in gens])
    ax.set_ylabel("share of real MSAs (%)")
    ax.set_title("(A) Wheeler-rate by construction")
    ax.legend(fontsize=8.5, loc="lower center"); ax.set_ylim(0, 100)


def draw_recog_ecdf(ax):
    rows = load_csv(os.path.join(DATA, "msa_practicality.csv"))
    gens = [g for g in ("debruijn", "trie", "revdet") if any(r["generator"] == g for r in rows)]
    for g in gens:
        ms = sorted(fnum(r["wall_s"]) * 1000 for r in rows
                    if r["generator"] == g and fnum(r["wall_s"]) is not None)
        if not ms:
            continue
        ms = np.array(ms); y = np.arange(1, len(ms) + 1) / len(ms)
        ax.step(ms, y, where="post", color=S.GEN_COLOR[g], lw=2.0,
                label=f"{GEN_DISP[g]} (median {np.median(ms):.0f} ms)")
        ax.plot([np.median(ms)], [0.5], marker="o", ms=5, color=S.GEN_COLOR[g], zorder=5)
    ax.axvline(1000, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1.2)
    ax.text(1000, 0.05, " 1 s", fontsize=8.5, color=S.WALL_GRAY)
    ax.set_xscale("log")
    ax.set_xlabel("recognition wall time (ms, log)")
    ax.set_ylabel("fraction of MSAs (ECDF)")
    ax.set_title("(B) Every real graph decided in < 1 s")
    ax.legend(fontsize=8.0, loc="lower right"); ax.grid(True, which="both", alpha=0.2)


def draw_repair(ax):
    d = json.load(open(os.path.join(DATA, "repair_records.json")))
    recs = d["records"]
    ratios_rep = [r["ratio"] for r in recs if not r["was_wheeler"]]
    ratios_ok = [r["ratio"] for r in recs if r["was_wheeler"]]
    allr = ratios_rep + ratios_ok
    ax.axvspan(min(allr) * 0.95, 1.0, color=VERDICT["WG"], alpha=0.06)
    ax.axvspan(1.0, max(allr) * 1.05, color=VERDICT["nonWG"], alpha=0.06)
    bins = np.linspace(min(allr) * 0.95, max(allr) * 1.05, 30)
    ax.hist(ratios_ok, bins=bins, color=BASE_C, alpha=0.9,
            label=f"already Wheeler (n={len(ratios_ok)})")
    ax.hist(ratios_rep, bins=bins, color=VERDICT["WG"], alpha=0.85,
            label=f"needed repair (n={len(ratios_rep)})")
    ax.axvline(1.0, ls="--", color=S.REF_GRAY, lw=1)
    ax.text(0.985, ax.get_ylim()[1] * 0.9, "merging ←", ha="right", fontsize=8.5, color=VERDICT["WG"])
    ax.text(1.015, ax.get_ylim()[1] * 0.9, "→ splitting", ha="left", fontsize=8.5, color=VERDICT["nonWG"])
    ax.set_xlabel("node blow-up ratio  (output / input nodes)")
    ax.set_ylabel("DAGs")
    ax.set_title(f"(C) Repair: {d['repaired']}/{d['repaired']} succeed, 0 failures\n"
                 f"mean 0.87× (0.33–1.86×) over {d['total']} DAGs")
    ax.legend(fontsize=8.0); ax.grid(True, axis="y", alpha=0.25)


# ============================================================ HERO SCORECARD
def _hero_validation(ax):
    # Validation badge: the recognizer is checked against an independent oracle (0 disagreements),
    # not a v1.0.0-error comparison.
    ax.set_title("Correctness (validated)", fontsize=13, fontweight="bold", pad=16)
    bars = ax.bar([0, 1], [100, 100], 0.55, color=VERDICT["WG"], zorder=3)
    for b, lbl in zip(bars, ["931/931", "1,516/1,516"]):
        ax.text(b.get_x() + b.get_width() / 2, 102, lbl, ha="center", va="bottom",
                fontsize=8.5, color=VERDICT["WG"], fontweight="bold")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["real\ncorpora", "synthetic\ncorpora"], fontsize=9.5)
    ax.set_ylim(0, 175); ax.set_yticks([0, 50, 100]); ax.set_ylabel("agreement with the oracle (%)")
    S.callout(ax, "✓ 0 disagreements", color=ACCENT, fontsize=18, xy=(0.5, 0.90))
    ax.text(0.5, 0.80, "vs an independent brute-force oracle", transform=ax.transAxes, ha="center",
            fontsize=9, color="#555")
    ax.text(0.5, 0.72, "~18k oracle-checked graphs · every emitted order re-validated",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.6, color="#777")
    ax.grid(True, axis="y", alpha=0.2)


def _hero_capability(ax):
    ax.set_title("Capability (size ceiling)", fontsize=13, fontweight="bold", pad=16)
    ax.barh([1], [2816], color=BASE_C, edgecolor=BASE_EDGE, height=0.40, zorder=3)
    ax.barh([0], [32768], color=ACCENT, height=0.40, zorder=3)
    ax.text(2816, 1.30, "2,816 (timeout)", va="center", ha="center", fontsize=8.5, color=BASE_EDGE)
    ax.text(32768, 0.34, "≥32,768", va="center", ha="center", fontsize=9, color=ACCENT, fontweight="bold")
    ax.set_xscale("log"); ax.set_xlim(100, 130000); ax.set_ylim(-0.6, 1.9)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["current", "v1.0.0"], fontsize=10)
    ax.set_xlabel("largest graph decided, 600 s budget (nodes, log)")
    S.callout(ax, ">10×", color=ACCENT, fontsize=22, xy=(0.74, 0.86))
    ax.text(0.74, 0.74, "2,816 → ≥32,768 nodes", transform=ax.transAxes, ha="center",
            fontsize=8.6, color="#555")
    ax.grid(True, axis="x", which="both", alpha=0.2)


def _hero_performance(ax):
    ax.set_title("Performance (matched n=2,816)", fontsize=13, fontweight="bold", pad=16)
    groups = [("time", 488.4, 0.882, "488 s", "0.9 s"),
              ("memory", 7488.0, 56.4, "7.3 GB", "56 MB")]
    x = np.arange(len(groups)); bw = 0.34
    ax.bar(x - bw / 2, [g[1] for g in groups], bw, color=BASE_C, edgecolor=BASE_EDGE, label="v1.0.0", zorder=3)
    ax.bar(x + bw / 2, [g[2] for g in groups], bw, color=ACCENT, label="current", zorder=3)
    for xi, g in zip(x, groups):
        ax.text(xi - bw / 2, g[1] * 1.15, g[3], ha="center", va="bottom", fontsize=8.2, color=BASE_EDGE)
        ax.text(xi + bw / 2, g[2] * 1.15, g[4], ha="center", va="bottom", fontsize=8.2,
                color=ACCENT, fontweight="bold")
    ax.set_yscale("log"); ax.set_ylim(0.3, 5e5)
    ax.set_xticks(x); ax.set_xticklabels([g[0] for g in groups], fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    S.callout(ax, "≈554× · ≈133×", color=ACCENT, fontsize=17, xy=(0.5, 0.90))
    ax.text(0.5, 0.80, "faster  ·  lighter", transform=ax.transAxes, ha="center", fontsize=9.5, color="#555")
    ax.grid(True, axis="y", which="both", alpha=0.2)


def fig_hero():
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    _hero_validation(axes[0]); _hero_capability(axes[1]); _hero_performance(axes[2])
    fig.suptitle("The WGT recognizer: v1.0.0 (2023) vs the current lazy/CEGAR rebuild — "
                 "validated against an oracle, far more capable, and faster on the default path",
                 fontsize=13.5, y=1.02)
    fig.text(0.5, -0.02,
             "Honest trades:  full-range size ceiling (n=832) unchanged  ·  ≈1.8× peak RAM where the "
             "within-label block fires  ·  recognition remains NP-complete",
             ha="center", fontsize=9, color="#555", style="italic")
    _save(fig, "Fhero.png")


# ============================================================ FIGURES (single matplotlib figs)
def _save(fig, name):
    p = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {p}")


def fig_validation():
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    draw_validation(ax)
    _save(fig, "F2_validation.png")


def fig_lazy_ceiling():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    draw_lazy(axes[0], "wall"); draw_lazy(axes[1], "rss_kb")
    fig.suptitle("THE HEADLINE — lazy/CEGAR generates the within-label axiom on demand, moving the "
                 "default-path ceiling 2,816 → ≥32,768", fontsize=12.5)
    _save(fig, "Flazy_ceiling.png")


def fig_mechanism():
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.2))
    draw_mechanism_compression(axes[0]); draw_atoms_scatter(axes[1]); draw_atoms_composition(axes[2])
    fig.suptitle("Why the new algorithm is faster — the lazy default builds almost none of the "
                 "$O(n^2)$ formula, and the full-range encoding is sub-quadratic in atoms", fontsize=12.5)
    _save(fig, "Fmechanism.png")


def fig_performance():
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10.2))
    draw_scatter(axes[0][0]); draw_setup_solve(axes[0][1])
    draw_memory(axes[1][0]); draw_type_speedup(axes[1][1])
    fig.suptitle("Full-range performance — the sparser encoding is ≈14× cheaper to build and "
                 "1.3–1.9× faster end-to-end, at an honest ~1.8× peak-RAM trade", fontsize=12.5)
    _save(fig, "Fperformance.png")


def fig_practicality():
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.1))
    draw_wheeler_rate(axes[0]); draw_recog_ecdf(axes[1]); draw_repair(axes[2])
    fig.suptitle("Practicality on real data — 500 Ensembl MSA graphs decided in < 1 s; any non-Wheeler "
                 "DAG repairs into a Wheeler graph (path-strings preserved)", fontsize=12)
    _save(fig, "Fpracticality.png")


def main():
    figs = [
        ("hero", fig_hero),
        ("validation", fig_validation),
        ("lazy", fig_lazy_ceiling),
        ("performance", fig_performance),
        ("mechanism", fig_mechanism),
        ("practicality", fig_practicality),
    ]
    only = sys.argv[1:]
    for name, f in figs:
        if only and name not in only:
            continue
        try:
            f()
        except Exception as e:   # noqa: BLE001
            import traceback
            print(f"  !! {name} failed: {type(e).__name__}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
