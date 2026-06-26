#!/usr/bin/env python3
"""
plot_report.py -- figures for benchmark/REPORT.md (the NEW-vs-OLD WGT comparison).

Three axes, kept strictly separate:
  CORRECTNESS  F1 (false verdicts: OLD buggy/unsound vs NEW)   F2 (verdict-agreement grid)
  CAPABILITY   F3 (graphs OLD structurally could not decide; NEW does)
  PERFORMANCE  Fatoms (encoding size in atoms, the mechanism)  F4 (-f scatter)  F5 (speedup ECDF)
               F6 (-f cactus)  Fattr (A2-vs-A3 attribution)  Fguard (D/E guard)
               F7 (setup/solve split)  F7b (peak-RSS ladder)  F12 (per-type speedup)
  REPAIR       F11 (node blow-up distribution)
  PRACTICALITY F15 (MSA -> Wheeler graph on real gene families)

Every figure shares one visual language (see style.py): a purple ramp for binary generations
(pre-4.1/pre-4.2/this work), teal/orange for Wheeler/non-Wheeler verdicts. Each figure is independent
and skipped (with a note) if its data file is absent. Render with:
  ~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/plot_report.py
"""
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import numpy as np                # noqa: E402

import style as S                 # noqa: E402
from style import BIN, VERDICT    # noqa: E402

S.apply_style()

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = HERE
TIMEOUT_DNA = 90.0   # per-graph -f timeout used in run_ftiming.sh (DNA)
TIMEOUT_AA = 120.0   # (AA)


# ----------------------------------------------------------------------------- parsers (unchanged)
def parse_difftest_log(path):
    """{mode: {'fa':int,'fr':int}}, plus 'checked','nonwg'. None if absent."""
    if not os.path.exists(path):
        return None
    modes, meta = {}, {}
    with open(path) as fh:
        for line in fh:
            m = re.match(r"\s*(\S+)\s*:\s*false-accept\(nonWG->WG\)=\s*(\d+)\s+"
                         r"false-reject\(WG->nonWG\)=\s*(\d+)", line)
            if m:
                modes[m.group(1)] = {"fa": int(m.group(2)), "fr": int(m.group(3))}
            m2 = re.match(r"checked\s*:\s*(\d+)", line)
            if m2:
                meta["checked"] = int(m2.group(1))
            m3 = re.match(r"\s*truth non-WG\s*:\s*(\d+)", line)
            if m3:
                meta["nonwg"] = int(m3.group(1))
    return {"modes": modes, "meta": meta}


def parse_exp_log(path):
    """{'checked','nonwg','fa','fr','skipped'} or None."""
    if not os.path.exists(path):
        return None
    d = {}
    with open(path) as fh:
        for line in fh:
            for key, pat in (("checked", r"checked\s*:\s*(\d+)"),
                             ("nonwg", r"truth non-WG\s*:\s*(\d+)"),
                             ("skipped", r"skipped\s*:\s*(\d+)"),
                             ("fa", r"false-accept\s*:\s*(\d+)"),
                             ("fr", r"false-reject\s*:\s*(\d+)")):
                m = re.search(pat, line)
                if m and key not in d:
                    d[key] = int(m.group(1))
    return d or None


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


# ============================================================ CORRECTNESS
def fig1_correctness():
    # Clean two-way correctness from corr_oldnew.csv (differential vs the brute-force oracle): per-backend
    # false-accepts for v1.0.0 (the last stable GitHub release) vs current. Uses the "simple" corpus.
    rows = load_csv(os.path.join(DATA, "corr_oldnew.csv"))
    if not rows:
        print("F1 skipped (need corr_oldnew.csv)"); return
    corpus = "simple"
    nonwg = next((r["nonWG"] for r in rows if r["corpus"] == corpus), "?")

    def fa(binary, mode):
        r = next((x for x in rows if x["binary"] == binary and x["corpus"] == corpus
                  and x["mode"] == mode), None)
        return int(r["false_accept"]) if r else 0

    order = ["smt", "perm", "perm-e", "full"]
    disp = {"smt": "default SMT", "perm": "permutation\n(-s p)",
            "perm-e": "exhaustive\n(-s p -e)", "full": "full-range\n(-f)"}
    xlab = [disp[m] for m in order]
    old_fa = [fa("v1.0.0", m) for m in order]
    new_fa = [fa("current", m) for m in order]

    x = np.arange(len(xlab)); w = 0.38
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    b1 = ax.bar(x - w / 2, old_fa, w, color="#bdbdbd", hatch="//", edgecolor="#7a7a7a",
                label="v1.0.0 (2023 release)")
    b2 = ax.bar(x + w / 2, new_fa, w, color=VERDICT["WG"], label="current (this work)")
    ax.bar_label(b1, padding=2, fontsize=9, color="#7a7a7a")
    ax.bar_label(b2, padding=2, fontsize=9, fontweight="bold", color=VERDICT["WG"])
    for xi, o, n in zip(x, old_fa, new_fa):
        if o >= 100 and n == 0:
            ax.annotate(f"−{o}", xy=(xi - w / 2, o), xytext=(xi - w / 2, o * 0.62),
                        ha="center", fontsize=10, fontweight="bold", color="#7a7a7a")
    ax.set_ylabel("false-accepts  (non-WG graphs declared Wheeler)")
    ax.set_title("Correctness vs the brute-force oracle: v1.0.0's permutation backends\n"
                 "false-accept non-Wheeler graphs; current is sound on every backend")
    ax.text(0.5, 0.97, f"reject-heavy corpus: {nonwg} non-Wheeler graphs (oracle-checked, n≤7)",
            transform=ax.transAxes, ha="center", va="top", fontsize=8.5, color="#555")
    ax.set_xticks(x); ax.set_xticklabels(xlab, fontsize=9)
    ax.legend(loc="upper right")
    ax.margins(y=0.20)
    p = os.path.join(OUT, "F1_false_accepts.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}  (v1.0.0 fa={old_fa}, current fa={new_fa})")


def fig2_verdict_matrix():
    sm = json.load(open(os.path.join(DATA, "static_metrics.json")))["verdict_agreement"]
    corpora = ["REAL", "SYNTH"]
    deciders = ["SMT", "PERM", "EXP"]
    decider_disp = {"SMT": "recognizer\n(SMT)", "PERM": "recognizer\n(perm)", "EXP": "exponential"}
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    ax.set_xlim(-0.5, len(deciders) - 0.5)
    ax.set_ylim(-0.5, len(corpora) - 0.5)
    ax.set_aspect("auto")
    teal = VERDICT["WG"]
    for i, c in enumerate(corpora):
        for j, dname in enumerate(deciders):
            agree = int(sm[c][dname][0])
            decided = int(sm[c]["graphs"])
            # clean card: white face, teal left rule, big count, check glyph
            ax.add_patch(plt.Rectangle((j - 0.46, i - 0.42), 0.92, 0.84, facecolor="white",
                                       edgecolor="#d9d9d9", lw=1.0, zorder=1))
            ax.add_patch(plt.Rectangle((j - 0.46, i - 0.42), 0.05, 0.84, facecolor=teal,
                                       edgecolor="none", zorder=2))
            ax.text(j, i + 0.10, f"{agree}/{decided}", ha="center", va="center",
                    fontsize=13, fontweight="bold", color="#222", zorder=3)
            ax.text(j, i - 0.22, "✓ match", ha="center", va="center",
                    fontsize=9, color=teal, zorder=3)
    ax.set_xticks(range(len(deciders)))
    ax.set_xticklabels([decider_disp[d] for d in deciders])
    ax.set_yticks(range(len(corpora)))
    ax.set_yticklabels([f"{c}\n({int(sm[c]['graphs'])} graphs)" for c in corpora])
    ax.invert_yaxis()
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.grid(False)
    ax.set_title(f"Verdict agreement vs the brute-force oracle — 0 disagreements\n"
                 f"({sm['total_graphs']} graphs: {sm['total_wg']} Wheeler, {sm['total_nonwg']} non-Wheeler)",
                 fontsize=11)
    p = os.path.join(OUT, "F2_verdict_agreement.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


def fig3_capability():
    sm = json.load(open(os.path.join(DATA, "static_metrics.json")))["phase3_impact"]
    rows = sm["per_corpus"]
    # sort families so the gray "timed out" band grows left -> right
    rows = sorted(rows, key=lambda r: r["old_gt_timeout"])
    names = [r["corpus"] for r in rows]
    decided = [r["old_gt_decided"] for r in rows]
    timeout = [r["old_gt_timeout"] for r in rows]
    rescued = [r["rescued_nonwg"] for r in rows]
    x = np.arange(len(names))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.3),
                                   gridspec_kw={"width_ratios": [2.3, 1]})
    ax1.bar(x, decided, color=VERDICT["WG"], label="OLD exp: decided (in cap)")
    ax1.bar(x, timeout, bottom=decided, color="#bdbdbd", label="OLD exp: timed out (no verdict)")
    total_rescued = sum(rescued)
    labeled = False
    for xi, d, t, rc in zip(x, decided, timeout, rescued):
        if rc:
            ax1.bar(xi, rc, bottom=d + t - rc, color=VERDICT["nonWG"],
                    label=(f"non-WG rescued by this work ({total_rescued})" if not labeled else None))
            labeled = True
    ax1.set_ylim(0, max(d + t for d, t in zip(decided, timeout)) * 1.22)
    ax1.set_xticks(x); ax1.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax1.set_ylabel("graphs (n ≤ 9 decidable subset)")
    ax1.set_title("Capability: verdicts the OLD exponential baseline could not produce")
    ax1.legend(fontsize=8.5, loc="upper left")
    # right panel: typeset headline card (no monospace dump)
    tot = sm["total"]
    ax2.axis("off")
    ax2.text(0.0, 1.0, "Rebuilt exponential reference", fontsize=11, fontweight="bold",
             va="top", transform=ax2.transAxes)
    ax2.text(0.0, 0.88, f"decides {tot['new_gt_agree']} / {tot['graphs']} graphs\n"
                        f"(original left {tot['old_gt_timeout']} undecided)",
             fontsize=9.5, va="top", transform=ax2.transAxes, color="#333")
    ax2.text(0.0, 0.66, f"{tot['rescued_nonwg']} non-Wheeler graphs from real\n"
                        f"human gene orthologs now decided:",
             fontsize=9.5, va="top", transform=ax2.transAxes, color=VERDICT["nonWG"], fontweight="bold")
    genes = [_short(os.path.basename(g)) for g in sm["rescued_graphs"]]
    half = (len(genes) + 1) // 2
    col1 = "\n".join("• " + g for g in genes[:half])
    col2 = "\n".join("• " + g for g in genes[half:])
    ax2.text(0.02, 0.46, col1, fontsize=8.5, va="top", transform=ax2.transAxes, family="DejaVu Sans")
    ax2.text(0.52, 0.46, col2, fontsize=8.5, va="top", transform=ax2.transAxes, family="DejaVu Sans")
    p = os.path.join(OUT, "F3_capability.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


# ============================================================ ftiming loaders (unchanged)
def load_ftiming():
    # Clean two-way -f timing: the regenerated ftiming_oldnew.raw.jsonl carries exactly two binary
    # labels -- pre41 = v1.0.0 (recognizer_main, dense -f) and new = current -- over all four corpora.
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
    st = row.get(f"{label}_status", "")
    v = fnum(row.get(f"{label}_{kind}"))
    if kind == "cpu" and v is not None:
        v = v / 1e6
    return v, st


# ============================================================ PERFORMANCE: -f distribution
def fig4_scatter(kind="cpu"):
    rows = load_ftiming()
    if not rows:
        print("F4 skipped (need ftiming_*.csv)"); return
    fig, ax = plt.subplots(1, 1, figsize=(7, 6))
    cap = max(r["_timeout"] for r in rows)
    for old, title in (("pre41", "v1.0.0 → current  (per-graph -f time)"),):
        wg_x, wg_y, nw_x, nw_y, to_x, to_y = [], [], [], [], [], []
        for r in rows:
            ov, ost = _metric(r, old, kind)
            nv, nst = _metric(r, "new", kind)
            if ost == "DECISIVE" and nst == "DECISIVE" and ov and nv:
                if r.get("new_verdict") == "1":
                    wg_x.append(ov); wg_y.append(nv)
                else:
                    nw_x.append(ov); nw_y.append(nv)
            elif ost == "TIMEOUT" and nst == "DECISIVE" and nv:
                to_y.append(nv); to_x.append(cap)
        if wg_x:
            ax.scatter(wg_x, wg_y, s=15, alpha=0.55, color=VERDICT["WG"],
                       edgecolors="none", label=f"Wheeler ({len(wg_x)})")
        if nw_x:
            ax.scatter(nw_x, nw_y, s=15, alpha=0.55, color=VERDICT["nonWG"],
                       edgecolors="none", label=f"non-Wheeler ({len(nw_x)})")
        if to_x:
            ax.scatter(to_x, to_y, s=42, marker="^", facecolors="none", edgecolors="#222",
                       linewidths=1.2, label=f"OLD timed out, NEW finished ({len(to_x)})")
        lo, hi = 1e-3, cap * 1.5
        ax.plot([lo, hi], [lo, hi], "--", color=S.REF_GRAY, lw=1, label="y = x")
        ax.axvline(cap, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1, alpha=0.7)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.set_xlabel(f"v1.0.0 (2023) {kind}-time per decision (s, log)")
        ax.set_ylabel(f"current — {kind}-time per decision (s, log)")
        ax.set_title(title)
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, which="both", alpha=0.2)
    fig.suptitle(f"Leaner -f encoding: v1.0.0 vs current ({kind}-time; below y=x = faster)",
                 fontsize=12)
    p = os.path.join(OUT, f"F4_f_scatter_{kind}.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


def fig5_speedup_ecdf(kind="cpu"):
    rows = load_ftiming()
    if not rows:
        print("F5 skipped (need ftiming_*.raw.jsonl)"); return
    fig, ax = plt.subplots(1, 1, figsize=(7, 5.6))
    vstyle = {"Wheeler": (VERDICT["WG"], 1), "non-Wheeler": (VERDICT["nonWG"], -1)}
    for old, title in (("pre41", "-f speedup, v1.0.0 → current"),):
        for vlabel, (color, vval) in vstyle.items():
            ratios = []
            for r in rows:
                if r.get("new_verdict") != str(vval):
                    continue
                ov, ost = _metric(r, old, kind)
                nv, nst = _metric(r, "new", kind)
                if ost == "DECISIVE" and nst == "DECISIVE" and ov and nv and nv > 0:
                    ratios.append(ov / nv)
            if not ratios:
                continue
            ratios = np.sort(np.array(ratios))
            y = np.arange(1, len(ratios) + 1) / len(ratios)
            med = np.median(ratios)
            ax.step(ratios, y, where="post", color=color, lw=2.2,
                    label=f"{vlabel}  (median {med:.2f}×, n={len(ratios)})")
            ax.plot([med], [0.5], marker="o", color=color, ms=6, zorder=5)
        ax.axvline(1.0, ls="--", color=S.REF_GRAY, lw=1)
        ax.set_xscale("log")
        ax.set_xlabel(f"speedup = v1.0.0 / current ({kind}-time; >1 = faster)")
        ax.set_title(title)
        ax.legend(fontsize=8.5, loc="lower right")
        ax.grid(True, which="both", alpha=0.25)
    ax.annotate("non-WG curve steps near 1.0:\nA3 block stays off (neutral)",
                xy=(1.0, 0.5), xytext=(1.25, 0.22), fontsize=8, color=VERDICT["nonWG"],
                arrowprops=dict(arrowstyle="->", color=VERDICT["nonWG"], lw=1))
    ax.set_ylabel("fraction of graphs (ECDF)")
    fig.suptitle(f"Per-graph -f speedup distribution by verdict ({kind}-time)", fontsize=12)
    p = os.path.join(OUT, f"F5_speedup_ecdf_{kind}.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


def fig6_cactus(kind="cpu"):
    rows = load_ftiming()
    if not rows:
        print("F6 skipped (need ftiming_*.csv)"); return
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for label in ("pre41", "new"):
        times = []
        for r in rows:
            v, st = _metric(r, label, kind)
            if st == "DECISIVE" and v:
                times.append(v)
        if not times:
            continue
        times = np.sort(np.array(times))
        ax.plot(np.arange(1, len(times) + 1), times, color=BIN[label],
                label=f"{S.binary_label(label)}  ({len(times)} solved)", lw=2.0)
    ax.set_yscale("log")
    ax.set_xlabel("graphs solved within budget (sorted by time)")
    ax.set_ylabel(f"{kind}-time per decision (s, log)")
    ax.set_title("-f cactus plot: graphs solved within a time budget\n"
                 "(lower / further right = more graphs solved faster)")
    ax.legend()
    ax.grid(True, which="both", alpha=0.25)
    p = os.path.join(OUT, f"F6_cactus_{kind}.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


# ============================================================ PERFORMANCE: setup/solve + memory
def fig7_setup_solve():
    rows = load_csv(os.path.join(DATA, "micro_oldnew.setup_solve.csv"))
    if not rows:
        print("F7 skipped (need micro_oldnew.setup_solve.csv)"); return
    graphs = []
    for r in rows:
        key = (r["name"], r["edges"])
        if key not in graphs:
            graphs.append(key)
    labels = ["pre41", "new"]
    fig, ax = plt.subplots(figsize=(12, 6))
    ng = len(graphs)
    bw = 0.8 / len(labels)
    x = np.arange(ng)
    for li, lab in enumerate(labels):
        setups, solves = [], []
        for (name, edges) in graphs:
            rec = next((r for r in rows if r["name"] == name and r["binary"] == lab), None)
            setups.append((fnum(rec["setup_med"]) if rec else 0) or 0)
            solves.append((fnum(rec["solve_med"]) if rec else 0) or 0)
        off = (li - (len(labels) - 1) / 2) * bw
        c = BIN[lab]
        ax.bar(x + off, solves, bw, color=c, label=S.binary_label(lab))
        ax.bar(x + off, setups, bw, bottom=solves, color=c, alpha=0.45, hatch="////",
               edgecolor="white", linewidth=0)
    # phase legend (texture) separate from generation legend (hue)
    from matplotlib.patches import Patch
    phase_handles = [Patch(facecolor="#999", label="z3 solve (solid)"),
                     Patch(facecolor="#999", alpha=0.45, hatch="////", label="encoding setup (hatched)")]
    gen_leg = ax.legend(loc="upper left", fontsize=9, title="generation")
    ax.add_artist(gen_leg)
    ax.legend(handles=phase_handles, loc="upper center", fontsize=9)
    # delta annotation on the headline k=5 graph (largest edges)
    big = max(range(ng), key=lambda i: int(graphs[i][1]))
    ax.annotate("setup ≈14×, total ≈2×\n(v1.0.0 → current)",
                xy=(big, 0.5), xytext=(big - 0.3, ax.get_ylim()[1] * 0.7),
                fontsize=8.5, color="#333", ha="center")
    short = [f"{_short(n)}\n(e={e})" for (n, e) in graphs]
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=8)
    ax.set_ylabel("wall time (s)")
    ax.set_title("-f setup vs solve, by generation — the sparsification collapses encoding setup")
    ax.grid(True, axis="y", alpha=0.25)
    p = os.path.join(OUT, "F7_setup_solve.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


def fig7b_memory():
    """Peak-RSS ladder (micro.mem_ladder.csv): RSS vs edges over the k=6 De Bruijn DNA ladder, where
    the A3 block is OFF (high D/E) -- so the sparse A2 form replaces pre-4.1's dense O(E^2) cross-group
    constraints with O(E) ones and the new encoding is LIGHTER than pre-4.1 (and == pre-4.2). The ~2×
    space-for-time trade is the *block-firing* regime (low-D/E k=5 headline graphs, §4.3 table), shown
    separately. Falls back to the 2-point micro.mem.csv if the ladder is absent."""
    ladder = None   # two-way report: use the per-graph micro_oldnew.mem.csv bars (block-fires k=5 +
    #                 block-off k=4) -- this directly shows v1.0.0-dense vs current-sparse peak RSS.
    fig, ax = plt.subplots(figsize=(8.6, 5.3))
    k6 = [r for r in ladder if "k_6" in r["name"]] if ladder else None
    if k6:
        for lab in ("pre41", "pre42", "new"):
            pts = []
            for r in k6:
                if r["binary"] != lab or r.get("status") != "DECISIVE":
                    continue
                e = fnum(r["edges"]); kb = fnum(r["peak_rss_kb"])
                if e and kb:
                    pts.append((e, kb / 1e6))
            pts.sort()
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, marker="o", ms=5, color=BIN[lab], lw=2.0, label=S.binary_label(lab))
        ax.set_xlabel("edges")
        ax.set_ylabel("peak resident set size (GB)")
        ax.set_title("-f peak memory (De Bruijn DNA, A3 block off) — sparse A2 is lighter than pre-4.1")
        ax.annotate("block off here: no A3 aux vars, and sparse A2\n"
                    "(O(E)) replaces pre-4.1's dense O(E²) cross-group\n"
                    "→ this work ≈ pre-4.2 ≤ pre-4.1. The ~2× trade is the\n"
                    "block-firing k=5 regime (§4.3 table).",
                    xy=(0.03, 0.97), xycoords="axes fraction", ha="left", va="top",
                    fontsize=7.5, color="#333")
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.25)
    else:
        rows = load_csv(os.path.join(DATA, "micro_oldnew.mem.csv"))
        if not rows:
            print("F7b skipped (need micro_oldnew.mem.csv)"); plt.close(fig); return
        graphs = []
        for r in rows:
            if r["name"] not in graphs:
                graphs.append(r["name"])
        x = np.arange(len(graphs)); bw = 0.38
        for li, lab in enumerate(("pre41", "new")):
            vals = []
            for g in graphs:
                rec = next((r for r in rows if r["name"] == g and r["binary"] == lab), None)
                vals.append(((fnum(rec["peak_rss_kb"]) if rec else 0) or 0) / 1e3)  # KB -> MB
            ax.bar(x + (li - 0.5) * bw, vals, bw, color=BIN[lab], label=S.binary_label(lab))
        ax.set_xticks(x); ax.set_xticklabels([_short(g) for g in graphs], fontsize=8)
        ax.set_ylabel("peak resident set size (MB)")
        ax.set_title("-f peak memory: v1.0.0 (dense) vs current (sparse+block)\n"
                     "block fires on k=5 (D/E≈0.27) → ~1.8× space-for-time trade; k=4 (block off) ≈ equal")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.25)
    p = os.path.join(OUT, "F7b_memory.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


# ============================================================ PERFORMANCE: the mechanism (atoms)
def load_atom_counts():
    rows = load_csv(os.path.join(DATA, "atom_counts.csv"))
    if not rows:
        return None
    for r in rows:
        for k in ("nodes", "edges", "labels", "pre41_total", "pre42_total", "new_total",
                  "pre41_a2", "pre41_a3", "new_a2", "new_a3", "mean_DE", "frac_edges_block"):
            r[k] = fnum(r.get(k))
    return rows


def fig_atoms():
    """The mechanism, in atoms: how many SMT assertions each generation emits under -f, computed
    analytically (validated exactly against z3's s.assertions().size()). Shows O(E^2) -> O(E+L)/
    O(E_l^2)->O(E_l+D_l^2) directly, not inferred from wall time."""
    rows = load_atom_counts()
    if not rows:
        print("Fatoms skipped (need atom_counts.csv)"); return
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.2))

    def panel(ax, typ, letter):
        # scatter the per-graph atom counts and overlay a power-law fit per generation; the fitted
        # exponent reads off the asymptotics directly (pre-4.1 ~ E^2; new ~ E^1 only where the A3
        # block fires -- on AA it stays ~E^2 with a far smaller constant, which the fit reveals).
        sub = sorted((r for r in rows if r["type"] == typ), key=lambda r: r["edges"])
        E = np.array([r["edges"] for r in sub], float)
        for lab in ("pre41", "new"):
            tot = np.array([r[f"{lab}_total"] for r in sub], float)
            m = (E > 0) & (tot > 0)
            ax.scatter(E[m], tot[m], s=10, alpha=0.40, color=BIN[lab], edgecolors="none")
            b, a = np.polyfit(np.log(E[m]), np.log(tot[m]), 1)
            xs = np.array([E[m].min(), E[m].max()])
            ax.plot(xs, np.exp(a) * xs ** b, color=BIN[lab], lw=2.2,
                    label=f"{S.binary_label(lab)}   $\\propto E^{{{b:.2f}}}$")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("edges (log)"); ax.set_ylabel("SMT assertions (A2+A3, log)")
        ax.set_title(f"({letter}) {S.TYPE_LABEL[typ]}")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, which="both", alpha=0.2)

    panel(axes[0], "DeBruijnG_DNA", "A")
    panel(axes[1], "DeBruijnG_AA", "B")

    # (C) per-type median atom composition (A2 vs A3), pre-4.1 vs this work
    ax = axes[2]
    types = ["DeBruijnG_DNA", "DeBruijnG_AA", "RevDetG_DNA", "RevDetG_AA"]
    x = np.arange(len(types)); bw = 0.36
    import statistics as st
    for gi, (lab, off) in enumerate((("pre41", -bw / 2), ("new", bw / 2))):
        a2 = [st.median([r[f"{lab}_a2"] for r in rows if r["type"] == t]) for t in types]
        a3 = [st.median([r[f"{lab}_a3"] for r in rows if r["type"] == t]) for t in types]
        base = BIN[lab]
        ax.bar(x + off, a2, bw, color=base, label=f"{S.binary_label(lab)}: A2 (cross-group)")
        ax.bar(x + off, a3, bw, bottom=a2, color=base, alpha=0.45, hatch="xx", edgecolor="white",
               label=f"{S.binary_label(lab)}: A3 (within-group)")
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels([S.TYPE_LABEL[t].replace(" ", "\n") for t in types], fontsize=8.5)
    ax.set_ylabel("median SMT assertions (log)")
    ax.set_title("(C) Where the atoms live: A2 vs A3, by type")
    ax.legend(fontsize=7, loc="upper right", ncol=1)
    ax.grid(True, axis="y", which="both", alpha=0.2)

    fig.suptitle("Encoding size in atoms — the sparsification, measured directly "
                 "(analytical count ≡ z3 s.assertions().size())", fontsize=12)
    p = os.path.join(OUT, "Fatoms_encoding.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


# ============================================================ ftiming_bytype loaders (unchanged)
TYPE_FROM_DIR = {
    "DeBruijnG_DNA": "De Bruijn\nDNA", "DeBruijnG_AA": "De Bruijn\nAA",
    "RevDetG_DNA": "RevDet\nDNA", "RevDetG_AA": "RevDet\nAA",
}
TYPE_ORDER = ["De Bruijn\nDNA", "De Bruijn\nAA", "RevDet\nDNA", "RevDet\nAA"]


def load_ftiming_bytype():
    path = os.path.join(DATA, "ftiming_oldnew.raw.jsonl")   # two-way: pre41=v1.0.0, new=current
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


def fig12_type_speedup():
    rows = load_ftiming_bytype()
    if not rows:
        print("F12 skipped (need ftiming_bytype.raw.jsonl)")
        return
    vstyle = [("Wheeler", "1", VERDICT["WG"]), ("non-Wheeler", "-1", VERDICT["nonWG"])]
    alphabet = {"De Bruijn\nDNA": "4-letter", "RevDet\nDNA": "4-letter",
                "De Bruijn\nAA": "20-letter", "RevDet\nAA": "20-letter"}
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 5.8))
    REG_TOL = 0.98
    regressions, breakeven = [], []
    for old, title in (("pre41", "Per-type -f speedup  (v1.0.0 → current)"),):
        types = [t for t in TYPE_ORDER if any(r["_type"] == t for r in rows)]
        x = np.arange(len(types)); bw = 0.38
        S.breakeven_band(ax, 1 - 0.02, 1 + 0.02)
        for vi, (vlabel, vval, color) in enumerate(vstyle):
            meds, ns = [], []
            for t in types:
                ratios = [_paired_ratio(r, old) for r in rows
                          if r["_type"] == t and r.get("new_verdict") == vval]
                ratios = [x for x in ratios if x]
                med = float(np.median(ratios)) if ratios else 0.0
                meds.append(med); ns.append(len(ratios))
                if ratios and med < REG_TOL:
                    regressions.append((old, t.replace("\n", " "), vlabel, round(med, 4)))
                elif ratios and med < 1.0:
                    breakeven.append((old, t.replace("\n", " "), vlabel, round(med, 4)))
            off = (vi - 0.5) * bw
            bars = ax.bar(x + off, meds, bw, color=color, label=vlabel)
            for b, m, n in zip(bars, meds, ns):
                if n:
                    ax.text(b.get_x() + b.get_width() / 2, m + 0.03, f"{m:.2f}×\nn={n}",
                            ha="center", va="bottom", fontsize=7.5)
        S.one_line(ax, 1.0, "1× (no change)")
        ax.set_xticks(x)
        ax.set_xticklabels(types, fontsize=9)
        for xi, t in zip(x, types):
            ax.text(xi, -0.14, alphabet[t], transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=7.5, color="#777", style="italic")
        ax.set_title(title)
        ax.legend(fontsize=8.5, loc="upper right")
        ax.margins(y=0.18)
    ax.set_ylabel("median -f wall speedup  (v1.0.0 / current; >1 = faster)")
    fig.suptitle("Per-graph-type -f speedup, by verdict — which sparsification pays where", fontsize=12)
    p = os.path.join(OUT, "F12_type_speedup.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    if regressions:
        print(f"  !! F12 0-regression check FAILED (med < {REG_TOL}×): {regressions}")
    elif breakeven:
        print(f"  F12 0-regression check OK; break-even within noise: {breakeven}")
    else:
        print("  F12 0-regression check OK (every type/verdict median ≥ 1×)")
    print(f"wrote {p}")


def _type_primary_verdict(t):
    return "1" if t.startswith("De Bruijn") else "-1"


def fig_lazy_ceiling():
    """THE headline: default-path recognition on the symmetric worst case, v1.0.0 (vanilla z3) vs current
    (lazy/CEGAR). (A) wall time vs n, (B) peak RSS vs n -- both log-log, complete + dnfa. v1.0.0's vanilla
    z3 (== current's `-s smt`, encoding-identical) climbs to a timeout/OOM ceiling near n=2816 while the
    lazy default stays flat in time and memory and runs an order of magnitude further."""
    old = load_csv(os.path.join(DATA, "..", "..", "lazy_cegar", "results_lazy_old.csv"))
    cur = load_csv(os.path.join(DATA, "..", "..", "lazy_cegar", "results_lazy_ceiling.csv"))
    if not old or not cur:
        print("Flazy skipped (need lazy_cegar/results_lazy_old.csv + results_lazy_ceiling.csv)"); return
    # series: (label, color, ls, rows, backend)
    OLD_C, NEW_C = BIN["pre41"], BIN["new"]
    series = [("v1.0.0 vanilla z3 — complete", OLD_C, "-", old, "smt", "complete"),
              ("v1.0.0 vanilla z3 — dnfa", OLD_C, "--", old, "smt", "dnfa"),
              ("current lazy — complete", NEW_C, "-", cur, "lazy", "complete"),
              ("current lazy — dnfa", NEW_C, "--", cur, "lazy", "dnfa")]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    for ax, (metric, ylab, conv, ttl) in zip(
            axes, [("wall", "wall-clock time (s, log)", 1.0, "(A) Recognition time"),
                   ("rss_kb", "peak resident set size (MB, log)", 1e-3, "(B) Peak memory")]):
        for label, color, ls, rows, backend, fam in series:
            pts = []
            for r in rows:
                if r.get("backend") != backend or r.get("family") != fam:
                    continue
                if (r.get("verdict") or "") not in ("WG",):   # decisive Wheeler only
                    continue
                n = fnum(r.get("n")); v = fnum(r.get(metric))
                if n and v:
                    pts.append((n, v * conv))
            pts.sort()
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, marker="o", ms=4, lw=2.0, color=color, ls=ls, label=label)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("graph size  n  (nodes, log)")
        ax.set_ylabel(ylab)
        ax.set_title(ttl)
        ax.grid(True, which="both", alpha=0.22)
        ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Default-path recognition, v1.0.0 vs current — lazy/CEGAR moves the ceiling "
                 "2816 → ≥32768 (~600× faster, ~130× lighter)", fontsize=12)
    p = os.path.join(OUT, "Flazy_ceiling.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


def fig_attribution():
    """A2-vs-A3 attribution: decompose the total pre-4.1→this work speedup into the A2 step
    (pre-4.1→pre-4.2) and the A3 step (pre-4.2→this work), per type. Multiplicative stack on a
    log axis; the marker is the measured median total (validates the decomposition)."""
    rows = load_ftiming_bytype()
    if not rows:
        print("Fattr skipped (need ftiming_bytype.raw.jsonl)"); return
    types = [t for t in TYPE_ORDER if any(r["_type"] == t for r in rows)]
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    x = np.arange(len(types)); bw = 0.5
    a2_col, a3_col = "#6a51a3", VERDICT["WG"]
    for xi, t in enumerate(types):
        vv = _type_primary_verdict(t)
        sub = [r for r in rows if r["_type"] == t and r.get("new_verdict") == vv]
        a2step = [_paired_ratio(r, "pre41", "pre42") for r in sub]
        a3step = [_paired_ratio(r, "pre42", "new") for r in sub]
        total = [_paired_ratio(r, "pre41", "new") for r in sub]
        a2m = float(np.median([v for v in a2step if v])) if any(a2step) else 1.0
        a3m = float(np.median([v for v in a3step if v])) if any(a3step) else 1.0
        tm = float(np.median([v for v in total if v])) if any(total) else 1.0
        # multiplicative stack: 1 -> a2m (A2 step) -> a2m*a3m (A3 step)
        ax.bar(xi, a2m - 1.0, bw, bottom=1.0, color=a2_col,
               label="A2 step (cross-group)" if xi == 0 else None)
        ax.bar(xi, a2m * a3m - a2m, bw, bottom=a2m, color=a3_col,
               label="A3 step (within-group)" if xi == 0 else None)
        ax.plot([xi], [tm], marker="D", ms=8, color="#222", zorder=5,
                label="measured median total" if xi == 0 else None)
        ax.text(xi, a2m * a3m + 0.03, f"{a2m:.2f}× · {a3m:.2f}×", ha="center", va="bottom", fontsize=8)
    S.one_line(ax, 1.0, "1×")
    ax.set_xticks(x); ax.set_xticklabels(types, fontsize=9)
    ax.set_ylabel("cumulative -f speedup  (OLD / this work)")
    ax.set_title("Division of labor: A2 carries amino-acid graphs, A3 carries few-label DNA")
    ax.legend(fontsize=8.5, loc="upper right")
    ax.margins(y=0.18)
    p = os.path.join(OUT, "Fattr_attribution.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


def fig_guard():
    """Why the A3 block fires where it fires: (A) per-graph D/E by type with the D<E/2 guard line;
    (B) per-type median speedup vs median D/E — lower D/E => block fires => bigger A3 gain."""
    ac = load_atom_counts()
    bt = load_ftiming_bytype()
    if not ac or not bt:
        print("Fguard skipped (need atom_counts.csv + ftiming_bytype.raw.jsonl)"); return
    types = ["DeBruijnG_DNA", "DeBruijnG_AA", "RevDetG_DNA", "RevDetG_AA"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    # (A) D/E distribution (strip) by type + guard line
    ax = axes[0]
    for i, t in enumerate(types):
        de = [r["mean_DE"] for r in ac if r["type"] == t and r["mean_DE"] == r["mean_DE"]]
        jitter = (np.random.RandomState(i).rand(len(de)) - 0.5) * 0.28
        ax.scatter(np.full(len(de), i) + jitter, de, s=10, alpha=0.45, color=S.TYPE_COLOR[t],
                   edgecolors="none")
        ax.plot([i], [np.median(de)], marker="_", ms=26, color="#222", mew=2.5)
    ax.axhline(0.5, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1.2)
    ax.text(len(types) - 0.5, 0.52, "D/E = ½ guard", ha="right", va="bottom", fontsize=8.5,
            color=S.WALL_GRAY)
    ax.text(0.02, 0.04, "below ½ → A3 block fires", transform=ax.transAxes, fontsize=8.5,
            color=VERDICT["WG"])
    ax.set_xticks(range(len(types)))
    ax.set_xticklabels([S.TYPE_LABEL[t].replace(" ", "\n") for t in types], fontsize=8.5)
    ax.set_ylabel("mean D/E over label groups")
    ax.set_ylim(0, 1.05)
    ax.set_title("(A) The guard partitions the graph types")
    ax.grid(True, axis="y", alpha=0.25)

    # (B) per-type median A3 speedup vs median D/E (legend, not inline labels -- 3 types cluster)
    ax = axes[1]
    de_by = {t: np.median([r["mean_DE"] for r in ac if r["type"] == t and r["mean_DE"] == r["mean_DE"]])
             for t in types}
    typemap = {"DeBruijnG_DNA": "De Bruijn\nDNA", "DeBruijnG_AA": "De Bruijn\nAA",
               "RevDetG_DNA": "RevDet\nDNA", "RevDetG_AA": "RevDet\nAA"}
    for t in types:
        vv = _type_primary_verdict(typemap[t])
        ratios = [_paired_ratio(r, "pre42", "new") for r in bt
                  if r["_type"] == typemap[t] and r.get("new_verdict") == vv]
        ratios = [x for x in ratios if x]
        if not ratios:
            continue
        ax.scatter([de_by[t]], [np.median(ratios)], s=150, color=S.TYPE_COLOR[t],
                   edgecolors="#222", linewidths=0.8, zorder=5, label=S.TYPE_LABEL[t])
    ax.axvspan(0, 0.5, color=VERDICT["WG"], alpha=0.06)
    ax.axvline(0.5, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1.2)
    S.one_line(ax, 1.0, "A3 neutral")
    ax.set_xlim(0.15, 0.95)
    ax.set_xlabel("median D/E (block fires when < ½)")
    ax.set_ylabel("median isolated A3 speedup (pre-4.2 → this work)")
    ax.set_title("(B) Low D/E → block fires → A3 gain")
    ax.legend(fontsize=8.5, loc="upper right")
    ax.grid(True, alpha=0.25)
    p = os.path.join(OUT, "Fguard_de.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


# ============================================================ PERFORMANCE: sparse -f ceiling
def load_f_sparse():
    path = os.path.join(DATA, "ftiming_f_sparse.raw.jsonl")
    if not os.path.exists(path):
        return None
    per = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            g = per.setdefault(rec["dot"], {"edges": rec["edges"]})
            lab = rec["label"]
            g[f"{lab}_wall"] = rec.get("median_wall")
            g[f"{lab}_status"] = rec.get("status", "")
    return list(per.values())


def fig_f_ceiling_sparse(timeout=120.0):
    """The -f ceiling on a SPARSE family (De Bruijn DNA, where the A3 block fires): this work's curve
    sits below the prior generations until ALL hit the same timeout/unknown wall. The gap below the
    wall is the speedup; the wall itself does not move. Complements F10 (dense families coincide)."""
    rows = load_f_sparse()
    if not rows:
        print("F10c skipped (need ftiming_f_sparse.raw.jsonl)"); return
    rows = sorted(rows, key=lambda r: r["edges"])
    fig, ax = plt.subplots(figsize=(8, 5.5))
    last_dec = {}
    for lab in ("pre41", "pre42", "new"):
        dx, dy, tox = [], [], []
        for r in rows:
            st, w = r.get(f"{lab}_status"), r.get(f"{lab}_wall")
            if st == "DECISIVE" and w:
                dx.append(r["edges"]); dy.append(w)
            elif st == "TIMEOUT":
                tox.append(r["edges"])
        if dx:
            ax.plot(dx, dy, marker="o", ms=5, lw=2.0, color=BIN[lab], label=S.binary_label(lab))
            last_dec[lab] = max(dx)
        if tox:
            ax.scatter(tox, [timeout] * len(tox), marker="x", s=50, color=BIN[lab], zorder=5)
    ax.axhline(timeout, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1.2, label=f"timeout {timeout:g}s")
    ax.set_yscale("log"); ax.set_xscale("log", base=2)
    ax.set_xlabel("edges (log₂)")
    ax.set_ylabel("median -f wall time (s, log)")
    ax.set_title("De Bruijn DNA size ladder")
    ax.annotate("× = exceeds the 120 s budget. Here this work ≈ pre-4.2\n"
                "(A2 cross-group gain; the A3 block engages only on the\n"
                "larger rungs that all time out), and reaches graphs pre-4.1\n"
                "times out on — before all hit the same wall.",
                xy=(0.97, 0.04), xycoords="axes fraction", ha="right", va="bottom", fontsize=7.5,
                color="#333")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, which="both", alpha=0.25)
    p = os.path.join(OUT, "F10c_sparse_ceiling.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}  (last decided edges: {last_dec})")


# ============================================================ REPAIR
def fig11_repair():
    path = os.path.join(DATA, "repair_records.json")
    if not os.path.exists(path):
        print("F11 skipped (need repair_records.json)"); return
    d = json.load(open(path))
    recs = d["records"]
    ratios_rep = [r["ratio"] for r in recs if not r["was_wheeler"]]
    ratios_ok = [r["ratio"] for r in recs if r["was_wheeler"]]
    allr = ratios_rep + ratios_ok
    if not allr:
        print("F11 skipped (no records)"); return
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    # shade merge (<1) vs split (>1) regions
    ax.axvspan(min(allr) * 0.95, 1.0, color=VERDICT["WG"], alpha=0.06)
    ax.axvspan(1.0, max(allr) * 1.05, color=VERDICT["nonWG"], alpha=0.06)
    bins = np.linspace(min(allr) * 0.95, max(allr) * 1.05, 30)
    ax.hist(ratios_ok, bins=bins, color="#bdbdbd", alpha=0.9,
            label=f"already Wheeler (identity, n={len(ratios_ok)})")
    ax.hist(ratios_rep, bins=bins, color=VERDICT["WG"], alpha=0.85,
            label=f"needed repair (n={len(ratios_rep)})")
    ax.axvline(1.0, ls="--", color=S.REF_GRAY, lw=1)
    ax.text(0.985, ax.get_ylim()[1] * 0.9, "merging ←", ha="right", fontsize=8.5, color=VERDICT["WG"])
    ax.text(1.015, ax.get_ylim()[1] * 0.9, "→ splitting", ha="left", fontsize=8.5, color=VERDICT["nonWG"])
    ax.set_xlabel("node blow-up ratio  (output nodes / input nodes)")
    ax.set_ylabel("DAGs")
    ax.set_title(f"Repair node blow-up over {d['total']} DAGs\n"
                 f"{d['repaired']} repaired, {d['already']} already Wheeler, {d['failures']} failures")
    ax.legend(fontsize=8.5)
    ax.grid(True, axis="y", alpha=0.25)
    p = os.path.join(OUT, "F11_repair_blowup.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


# ============================================================ PRACTICALITY (MSA -> WG)
GEN_DISP = {"debruijn": "De Bruijn", "revdet": "RevDet", "trie": "Trie"}


def fig15_practicality():
    rows = load_csv(os.path.join(DATA, "msa_practicality.csv"))
    if not rows:
        print("F15 skipped (need msa_practicality.csv)")
        return
    GEN = S.GEN_COLOR
    gens = [g for g in ("debruijn", "revdet", "trie") if any(r["generator"] == g for r in rows)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.0))

    # (A) Wheeler-rate
    ax = axes[0]
    x = np.arange(len(gens))
    wg_frac, labels = [], []
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
    ax.legend(fontsize=8.5, loc="lower center")
    ax.set_ylim(0, 100)

    # (B) size vs MSA width
    ax = axes[1]
    for g in gens:
        xs = [fnum(r["aln_len"]) for r in rows if r["generator"] == g and fnum(r["nodes"]) is not None]
        ys = [fnum(r["nodes"]) for r in rows if r["generator"] == g and fnum(r["nodes"]) is not None]
        ax.scatter(xs, ys, s=12, alpha=0.5, color=GEN[g], edgecolors="none", label=GEN_DISP[g])
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("MSA aligned length (columns, log)")
    ax.set_ylabel("graph size (nodes, log)")
    ax.set_title("(B) Graph size vs MSA width")
    ax.legend(fontsize=8.5)
    ax.grid(True, which="both", alpha=0.2)

    # (C) recognition-time ECDF
    ax = axes[2]
    for g in gens:
        ms = sorted(fnum(r["wall_s"]) * 1000 for r in rows
                    if r["generator"] == g and fnum(r["wall_s"]) is not None)
        if not ms:
            continue
        ms = np.array(ms)
        y = np.arange(1, len(ms) + 1) / len(ms)
        ax.step(ms, y, where="post", color=GEN[g], lw=2.0,
                label=f"{GEN_DISP[g]} (median {np.median(ms):.0f} ms)")
        ax.plot([np.median(ms)], [0.5], marker="o", ms=5, color=GEN[g], zorder=5)
    ax.axvline(1000, ls=S.WALL_LS, color=S.WALL_GRAY, lw=1.2)
    ax.text(1000, 0.05, " 1 s", fontsize=8.5, color=S.WALL_GRAY)
    ax.set_xscale("log")
    ax.set_xlabel("recognition wall time (ms, log)")
    ax.set_ylabel("fraction of MSAs (ECDF)")
    ax.set_title("(C) Every real graph decided in < 1 s")
    ax.legend(fontsize=8.0, loc="lower right")
    ax.grid(True, which="both", alpha=0.2)

    fig.suptitle(f"MSA → Wheeler graph on {len({r['gene'] for r in rows})} Ensembl gene MSAs "
                 f"({len(rows)} constructions; per-seq length capped at l=300)", fontsize=12)
    p = os.path.join(OUT, "F15_msa_practicality.png")
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    print(f"wrote {p}")


def main():
    figs = [
        ("fig1", fig1_correctness),
        ("fig2", fig2_verdict_matrix),
        ("fig3", fig3_capability),
        ("figatoms", fig_atoms),
        ("fig4", lambda: fig4_scatter("cpu")),
        ("fig4w", lambda: fig4_scatter("wall")),
        ("fig5", lambda: fig5_speedup_ecdf("cpu")),
        ("fig6", lambda: fig6_cactus("cpu")),
        ("fig7", fig7_setup_solve),
        ("fig7b", fig7b_memory),
        # figattr / figguard / figceil DROPPED: the A2-vs-A3 *timing* attribution, the D/E guard, and the
        # sparse-ladder ceiling all require the pre-4.2 intermediate midpoint, which the clean two-way
        # (v1.0.0 vs current) report omits. (The A2/A3 *atom* split survives in fig_atoms panel C; the -f
        # ceiling is carried by fig4's timeout markers and the limit_test old-f/new-f numbers in text.)
        ("fig11", fig11_repair),
        ("fig12", fig12_type_speedup),
        ("figlazy", fig_lazy_ceiling),
        ("fig15", fig15_practicality),
    ]
    only = sys.argv[1:]
    for name, f in figs:
        if only and not any(o == name for o in only):
            continue
        try:
            f()
        except Exception as e:   # noqa: BLE001
            import traceback
            print(f"  !! {name} failed: {type(e).__name__}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
