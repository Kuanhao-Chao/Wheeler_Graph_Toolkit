#!/usr/bin/env python3
"""
plot_report.py -- figures for benchmark/REPORT.md (the NEW-vs-OLD WGT comparison).

Three axes, kept strictly separate:
  CORRECTNESS  F1 (false verdicts: OLD buggy/unsound vs NEW)   F2 (verdict-agreement matrix)
  CAPABILITY   F3 (graphs OLD structurally could not decide; NEW does)
  PERFORMANCE  F4 (-f scatter NEW vs OLD)   F5 (speedup ECDF)   F6 (-f cactus)
               F7 (setup/solve split)       F7b (peak RSS)
  REPAIR       F11 (node blow-up distribution)

Each figure is independent and skipped (with a note) if its data file is absent, so this can be run
repeatedly as the tmux sweeps land. Run with a working numpy/matplotlib, e.g.
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

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = HERE
TIMEOUT_DNA = 90.0   # per-graph -f timeout used in run_ftiming.sh (DNA)
TIMEOUT_AA = 120.0   # (AA)

GEN = {"new": ("#1f77b4", "NEW  (sparse A2+A3)"),
       "pre42": ("#ff7f0e", "pre-4.2  (sparse A2)"),
       "pre41": ("#d62728", "pre-4.1  (dense A2+A3)")}


# ----------------------------------------------------------------------------- parsers
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


# ----------------------------------------------------------------------------- F1
def fig1_correctness():
    buggy = parse_difftest_log(os.path.join(DATA, "corr_buggy.log"))
    new = parse_difftest_log(os.path.join(DATA, "corr_new.log"))
    exp_uns = parse_exp_log(os.path.join(DATA, "exp_unsound.log"))
    exp_hon = parse_exp_log(os.path.join(DATA, "exp_honest.log"))
    if not buggy or not new:
        print("F1 skipped (need corr_buggy.log + corr_new.log)")
        return
    order = ["smt", "perm", "perm-e", "full"]
    labels = [m for m in order if m in buggy["modes"]]
    old_fa = [buggy["modes"][m]["fa"] for m in labels]
    new_fa = [new["modes"].get(m, {"fa": 0})["fa"] for m in labels]
    disp = {"smt": "default SMT", "perm": "permutation\n(-s p)",
            "perm-e": "exhaustive\n(-s p -e)", "full": "full-range\n(-f)"}
    xlab = [disp.get(m, m) for m in labels]
    # add the exponential recognizer as a 5th group (false-accepts among in-cap non-WG)
    if exp_uns is not None:
        xlab.append("exponential\n(GT baseline)")
        old_fa.append(exp_uns.get("fa", 0))
        new_fa.append(exp_hon.get("fa", 0) if exp_hon else 0)

    x = np.arange(len(xlab))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    b1 = ax.bar(x - w / 2, old_fa, w, color="#d62728", label="OLD (buggy / unsound)")
    b2 = ax.bar(x + w / 2, new_fa, w, color="#1f77b4", label="NEW (fixed)")
    ax.bar_label(b1, padding=2, fontsize=9)
    ax.bar_label(b2, padding=2, fontsize=9)
    nonwg_b = buggy["meta"].get("nonwg", "?")
    nonwg_e = exp_uns.get("nonwg", "?") if exp_uns else "?"
    ax.set_ylabel("false-accepts  (non-WG graphs declared Wheeler)")
    ax.set_title("Correctness: false-accepts by backend, OLD vs NEW\n"
                 f"(recognizer corpus: {nonwg_b} non-WG graphs; exp corpus: {nonwg_e} in-cap non-WG)")
    ax.set_xticks(x)
    ax.set_xticklabels(xlab, fontsize=9)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.25)
    ax.margins(y=0.18)
    p = os.path.join(OUT, "F1_false_accepts.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}  (OLD fa={old_fa}, NEW fa={new_fa})")


# ----------------------------------------------------------------------------- F2
def fig2_verdict_matrix():
    sm = json.load(open(os.path.join(DATA, "static_metrics.json")))["verdict_agreement"]
    corpora = ["REAL", "SYNTH"]
    deciders = ["SMT", "PERM", "EXP"]
    agree = np.array([[sm[c][d][0] for d in deciders] for c in corpora], dtype=float)
    decided = np.array([[sm[c]["graphs"] for _ in deciders] for c in corpora], dtype=float)
    frac = agree / decided
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    im = ax.imshow(frac, cmap="Greens", vmin=0.9, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(deciders))); ax.set_xticklabels(deciders)
    ax.set_yticks(range(len(corpora)))
    ax.set_yticklabels([f"{c}\n({int(sm[c]['graphs'])} graphs)" for c in corpora])
    for i in range(len(corpora)):
        for j in range(len(deciders)):
            ax.text(j, i, f"{int(agree[i, j])}/{int(decided[i, j])}\n0 disagree",
                    ha="center", va="center", fontsize=10, color="black")
    ax.set_title("Verdict agreement vs brute-force oracle\n"
                 f"0 disagreements across {sm['total_graphs']} graphs "
                 f"({sm['total_wg']} WG, {sm['total_nonwg']} non-WG)")
    fig.colorbar(im, ax=ax, label="agree / decided", fraction=0.046, pad=0.04)
    p = os.path.join(OUT, "F2_verdict_agreement.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- F3
def fig3_capability():
    sm = json.load(open(os.path.join(DATA, "static_metrics.json")))["phase3_impact"]
    rows = sm["per_corpus"]
    names = [r["corpus"] for r in rows]
    decided = [r["old_gt_decided"] for r in rows]
    timeout = [r["old_gt_timeout"] for r in rows]
    rescued = [r["rescued_nonwg"] for r in rows]
    x = np.arange(len(names))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.3),
                                   gridspec_kw={"width_ratios": [2.3, 1]})
    ax1.bar(x, decided, color="#7fb069", label="OLD exp: decided (in cap)")
    ax1.bar(x, timeout, bottom=decided, color="#bdbdbd", label="OLD exp: timed out (no verdict)")
    # mark the rescued non-WG count atop the timeout band (red band, legended once)
    total_rescued = sum(rescued)
    for xi, d, t, rc in zip(x, decided, timeout, rescued):
        if rc:
            ax1.bar(xi, rc, bottom=d + t - rc, color="#d62728",
                    label=f"non-WG rescued by NEW ({total_rescued})")
            ax1.annotate(f"{rc} non-WG\nrescued", xy=(xi, d + t), xytext=(xi - 1.4, d + t + 18),
                         fontsize=8, color="#d62728", ha="center",
                         arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
    ax1.set_ylim(0, max(d + t for d, t in zip(decided, timeout)) * 1.30)
    ax1.set_xticks(x); ax1.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax1.set_ylabel("graphs (n<=9 decidable subset)")
    ax1.set_title("Capability: what the OLD exponential baseline could decide\n"
                  f"(timed out on {sm['total']['old_gt_timeout']}/{sm['total']['graphs']}, "
                  "incl. ALL non-WG graphs)")
    ax1.legend(fontsize=8, loc="upper right")
    ax1.grid(True, axis="y", alpha=0.25)
    # right panel: headline rescue + NEW agreement
    tot = sm["total"]
    ax2.axis("off")
    txt = (f"NEW deciders vs oracle\n\n"
           f"   recognizer (SMT):  {tot['new_wgt_agree']}/{tot['graphs']}\n"
           f"   exponential (GT):  {tot['new_gt_agree']}/{tot['graphs']}\n\n"
           f"non-WG graphs the OLD\n exp could NEVER decide,\n now decided by NEW: "
           f"{tot['rescued_nonwg']}\n\n"
           + "\n".join("  - " + os.path.basename(g) for g in sm["rescued_graphs"]))
    ax2.text(0.0, 1.0, txt, va="top", ha="left", fontsize=8.2, family="monospace",
             transform=ax2.transAxes)
    p = os.path.join(OUT, "F3_capability.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- ftiming loader
def load_ftiming():
    """Pivot ftiming_*.raw.jsonl (read incrementally; flushed continuously) into per-graph dicts.

    Each output row has name, edges, _corpus, _timeout, and per-binary {label}_wall/_cpu/_status/
    _verdict columns -- matching what the figure code expects. Reading the jsonl rather than the
    end-of-run CSV lets the figures render on partial data while the sweep is still running.
    """
    # Prefer the post-Phase-4.3 fair re-measurement (ftiming_dna2) when present; it supersedes the
    # pre-fix DNA sweep (ftiming_dna), which measured the too-loose-guard NEW under contention.
    dna_file = ("ftiming_dna2.raw.jsonl"
                if os.path.exists(os.path.join(DATA, "ftiming_dna2.raw.jsonl"))
                else "ftiming_dna.raw.jsonl")
    per_graph = {}
    for tag, fn, T in (("DNA", dna_file, TIMEOUT_DNA),
                       ("AA", "ftiming_aa.raw.jsonl", TIMEOUT_AA)):
        path = os.path.join(DATA, fn)
        if not os.path.exists(path):
            continue
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                g = per_graph.setdefault(rec["dot"], {"name": rec["name"], "edges": str(rec["edges"]),
                                                      "_corpus": tag, "_timeout": T})
                lab = rec["label"]
                g[f"{lab}_wall"] = ("" if rec.get("median_wall") is None
                                    else f"{rec['median_wall']:.6f}")
                g[f"{lab}_cpu"] = ("" if rec.get("median_cpu") is None
                                   else f"{rec['median_cpu']:.0f}")
                g[f"{lab}_status"] = rec.get("status", "")
                g[f"{lab}_verdict"] = ("" if rec.get("verdict") is None else str(rec["verdict"]))
    return list(per_graph.values())


def _metric(row, label, kind):
    """kind in {'wall','cpu'}; returns (value, status). cpu scaled to seconds (1e6 ticks/s ~ Linux)."""
    st = row.get(f"{label}_status", "")
    v = fnum(row.get(f"{label}_{kind}"))
    if kind == "cpu" and v is not None:
        v = v / 1e6   # clock() ticks ~ microseconds on Linux -> seconds
    return v, st


# ----------------------------------------------------------------------------- F4
def fig4_scatter(kind="cpu"):
    rows = load_ftiming()
    if not rows:
        print("F4 skipped (need ftiming_*.csv)"); return
    pairs = [("pre41", "new -vs- pre-4.1 (total A2+A3 gain)"),
             ("pre42", "new -vs- pre-4.2 (A3 gain)")]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    cap = max(r["_timeout"] for r in rows)
    for ax, (old, title) in zip(axes, pairs):
        wg_x, wg_y, nw_x, nw_y = [], [], [], []
        to_x, to_y = [], []
        for r in rows:
            ov, ost = _metric(r, old, kind)
            nv, nst = _metric(r, "new", kind)
            if ost == "DECISIVE" and nst == "DECISIVE" and ov and nv:
                if r.get("new_verdict") == "1":
                    wg_x.append(ov); wg_y.append(nv)
                else:
                    nw_x.append(ov); nw_y.append(nv)
            elif ost == "TIMEOUT" and nst == "DECISIVE" and nv:
                to_y.append(nv); to_x.append(cap)        # OLD timed out, NEW finished
        if wg_x:
            ax.scatter(wg_x, wg_y, s=14, alpha=0.5, color="#1f77b4", label=f"WG/SAT ({len(wg_x)})")
        if nw_x:
            ax.scatter(nw_x, nw_y, s=14, alpha=0.5, color="#d62728",
                       label=f"non-WG/UNSAT ({len(nw_x)})")
        if to_x:
            ax.scatter(to_x, to_y, s=30, marker=">", color="#9467bd",
                       label=f"OLD timed out ({len(to_x)}), NEW finished")
        lo = 1e-3
        hi = cap * 1.5
        ax.plot([lo, hi], [lo, hi], "--", color="gray", lw=1, label="y = x")
        ax.axvline(cap, ls=":", color="#d62728", lw=1, alpha=0.7)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.set_xlabel(f"OLD {old}  {kind}-time per decision (s, log)")
        ax.set_ylabel(f"NEW  {kind}-time per decision (s, log)")
        ax.set_title(title)
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, which="both", alpha=0.2)
    fig.suptitle(f"Phase-4 `-f` encoding: NEW vs OLD ({kind}-time; points below y=x = NEW faster)",
                 fontsize=12)
    p = os.path.join(OUT, f"F4_f_scatter_{kind}.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- F5
def fig5_speedup_ecdf(kind="cpu"):
    """Two panels (pre41->new = total Phase-4 gain; pre42->new = isolated A3 gain), each with the
    speedup ECDF split by verdict (SAT/Wheeler vs UNSAT/non-Wheeler). This exposes the honest
    asymmetry: the sparse encoding helps SAT instances but the aux vars can slow UNSAT refutation."""
    rows = load_ftiming()
    if not rows:
        print("F5 skipped (need ftiming_*.raw.jsonl)"); return
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True)
    vstyle = {"WG (SAT)": ("#1f77b4", 1), "non-WG (UNSAT)": ("#d62728", -1)}
    for ax, old, title in ((axes[0], "pre41", "total Phase-4 gain  (pre-4.1 -> NEW)"),
                           (axes[1], "pre42", "isolated A3 gain  (pre-4.2 -> NEW)")):
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
            ax.step(ratios, y, where="post", color=color,
                    label=f"{vlabel}  (median {med:.2f}x, n={len(ratios)})")
        ax.axvline(1.0, ls="--", color="gray", lw=1, label="1x (no change)")
        ax.set_xscale("log")
        ax.set_xlabel(f"speedup = OLD {kind}-time / NEW {kind}-time  (log; >1 = NEW faster)")
        ax.set_title(title)
        ax.legend(fontsize=8.5, loc="lower right")
        ax.grid(True, which="both", alpha=0.25)
    axes[0].set_ylabel("fraction of graphs (ECDF)")
    fig.suptitle(f"Per-graph `-f` speedup distribution by verdict ({kind}-time)", fontsize=12)
    p = os.path.join(OUT, f"F5_speedup_ecdf_{kind}.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- F6
def fig6_cactus(kind="cpu"):
    rows = load_ftiming()
    if not rows:
        print("F6 skipped (need ftiming_*.csv)"); return
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for label in ("pre41", "pre42", "new"):
        times = []
        for r in rows:
            v, st = _metric(r, label, kind)
            if st == "DECISIVE" and v:
                times.append(v)
        if not times:
            continue
        times = np.sort(np.array(times))
        ax.plot(np.arange(1, len(times) + 1), times, color=GEN[label][0],
                label=f"{GEN[label][1]}  ({len(times)} solved)", lw=1.8)
    ax.set_yscale("log")
    ax.set_xlabel("graphs solved (sorted by time)")
    ax.set_ylabel(f"{kind}-time per decision (s, log)")
    ax.set_title("`-f` cactus plot: graphs solved within a time budget\n"
                 "(further right / lower = more graphs solved faster)")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.25)
    p = os.path.join(OUT, f"F6_cactus_{kind}.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- F7
def fig7_setup_solve():
    rows = load_csv(os.path.join(DATA, "micro.setup_solve.csv"))
    if not rows:
        print("F7 skipped (need micro.setup_solve.csv)"); return
    graphs = []
    for r in rows:
        key = (r["name"], r["edges"])
        if key not in graphs:
            graphs.append(key)
    labels = ["pre41", "pre42", "new"]
    fig, ax = plt.subplots(figsize=(12, 6))
    ng = len(graphs)
    group_w = 0.8
    bw = group_w / len(labels)
    x = np.arange(ng)
    for li, lab in enumerate(labels):
        setups, solves = [], []
        for (name, edges) in graphs:
            rec = next((r for r in rows if r["name"] == name and r["binary"] == lab), None)
            s = fnum(rec["setup_med"]) if rec else None
            v = fnum(rec["solve_med"]) if rec else None
            setups.append(s or 0); solves.append(v or 0)
        off = (li - (len(labels) - 1) / 2) * bw
        c = GEN[lab][0]
        ax.bar(x + off, setups, bw, color=c, alpha=0.55,
               label=f"{lab} setup" if li == 0 else f"{lab} setup")
        ax.bar(x + off, solves, bw, bottom=setups, color=c,
               label=f"{lab} solve")
    short = [n.replace("Human_", "").replace("_orthologues", "").replace(".dot", "")
             + f"\n(e={e})" for (n, e) in graphs]
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=7.5, rotation=15)
    ax.set_ylabel("wall time (s)  -- lighter = setup, solid = solve")
    ax.set_title("`-f` setup vs solve split per generation (pre-4.1 / pre-4.2 / NEW)\n"
                 "setup = encoding build (A2/A3 sparsification target); solve = z3")
    ax.legend(fontsize=7.5, ncol=3)
    ax.grid(True, axis="y", alpha=0.25)
    p = os.path.join(OUT, "F7_setup_solve.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


def fig7b_memory():
    rows = load_csv(os.path.join(DATA, "micro.mem.csv"))
    if not rows:
        print("F7b skipped (need micro.mem.csv)"); return
    graphs = []
    for r in rows:
        if r["name"] not in graphs:
            graphs.append(r["name"])
    labels = ["pre41", "pre42", "new"]
    x = np.arange(len(graphs)); bw = 0.26
    fig, ax = plt.subplots(figsize=(11, 5.3))
    for li, lab in enumerate(labels):
        vals = []
        for g in graphs:
            rec = next((r for r in rows if r["name"] == g and r["binary"] == lab), None)
            kb = fnum(rec["peak_rss_kb"]) if rec else None
            vals.append((kb or 0) / 1e6)   # KB -> GB
        ax.bar(x + (li - 1) * bw, vals, bw, color=GEN[lab][0], label=GEN[lab][1])
    short = [g.replace("Human_", "").replace("_orthologues", "").replace(".dot", "") for g in graphs]
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=7.5, rotation=15)
    ax.set_ylabel("peak resident set size (GB)")
    ax.set_title("`-f` peak memory per generation")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)
    p = os.path.join(OUT, "F7b_memory.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- F11
def fig11_repair():
    path = os.path.join(DATA, "repair_records.json")
    if not os.path.exists(path):
        print("F11 skipped (need repair_records.json)"); return
    d = json.load(open(path))
    recs = d["records"]
    ratios_rep = [r["ratio"] for r in recs if not r["was_wheeler"]]
    ratios_ok = [r["ratio"] for r in recs if r["was_wheeler"]]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    allr = ratios_rep + ratios_ok
    if not allr:
        print("F11 skipped (no records)"); return
    bins = np.linspace(min(allr) * 0.95, max(allr) * 1.05, 30)
    ax.hist(ratios_ok, bins=bins, color="#7fb069", alpha=0.8,
            label=f"already Wheeler (identity, n={len(ratios_ok)})")
    ax.hist(ratios_rep, bins=bins, color="#1f77b4", alpha=0.8,
            label=f"needed repair (n={len(ratios_rep)})")
    ax.axvline(1.0, ls="--", color="gray", lw=1, label="1.0x (no node change)")
    ax.set_xlabel("node blow-up ratio  (output nodes / input nodes)")
    ax.set_ylabel("DAGs")
    ax.set_title(f"Repair (wheelerize) node blow-up over {d['total']} DAGs\n"
                 f"{d['repaired']} needed repair, {d['already']} already Wheeler, "
                 f"{d['failures']} failures")
    ax.legend(fontsize=8.5)
    ax.grid(True, axis="y", alpha=0.25)
    p = os.path.join(OUT, "F11_repair_blowup.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- F12 (Q1)
TYPE_FROM_DIR = {
    "DeBruijnG_DNA": "De Bruijn\nDNA", "DeBruijnG_AA": "De Bruijn\nAA",
    "RevDetG_DNA": "RevDet\nDNA", "RevDetG_AA": "RevDet\nAA",
}
TYPE_ORDER = ["De Bruijn\nDNA", "De Bruijn\nAA", "RevDet\nDNA", "RevDet\nAA"]


def load_ftiming_bytype():
    """Pivot ftiming_bytype.raw.jsonl into per-graph dicts tagged with graph type (from the dot path).

    Returns rows with _type, edges, and per-binary {label}_wall/_status plus new_verdict. Reads the
    jsonl incrementally so it renders on partial data while the per-type sweep is still running."""
    path = os.path.join(DATA, "ftiming_bytype.raw.jsonl")
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
            g = per_graph.setdefault(dotpath, {"_type": gtype, "edges": rec["edges"]})
            lab = rec["label"]
            g[f"{lab}_wall"] = rec.get("median_wall")
            g[f"{lab}_status"] = rec.get("status", "")
            if rec.get("verdict") is not None:
                g["new_verdict" if lab == "new" else f"{lab}_verdict"] = str(rec["verdict"])
    return list(per_graph.values())


def fig12_type_speedup():
    """Per-graph-type median `-f` wall speedup (pre41->new = total Phase-4 gain; pre42->new = A3 gain),
    split WG/non-WG, one panel per baseline. Includes an explicit 0-regression check."""
    rows = load_ftiming_bytype()
    if not rows:
        print("F12 skipped (need ftiming_bytype.raw.jsonl)")
        return
    vstyle = [("WG (SAT)", "1", "#1f77b4"), ("non-WG (UNSAT)", "-1", "#d62728")]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True)
    regressions = []
    for ax, old, title in ((axes[0], "pre41", "total Phase-4 gain  (pre-4.1 → NEW)"),
                           (axes[1], "pre42", "isolated A3 gain  (pre-4.2 → NEW)")):
        types = [t for t in TYPE_ORDER if any(r["_type"] == t for r in rows)]
        x = np.arange(len(types))
        bw = 0.38
        for vi, (vlabel, vval, color) in enumerate(vstyle):
            meds, ns = [], []
            for t in types:
                ratios = []
                for r in rows:
                    if r["_type"] != t or r.get("new_verdict") != vval:
                        continue
                    ov, nv = r.get(f"{old}_wall"), r.get("new_wall")
                    if (r.get(f"{old}_status") == "DECISIVE" and r.get("new_status") == "DECISIVE"
                            and ov and nv and nv > 0):
                        ratios.append(ov / nv)
                med = float(np.median(ratios)) if ratios else 0.0
                meds.append(med)
                ns.append(len(ratios))
                if ratios and med < 1.0:
                    regressions.append((old, t.replace("\n", " "), vlabel, med))
            off = (vi - 0.5) * bw
            bars = ax.bar(x + off, meds, bw, color=color, label=vlabel)
            for b, m, n in zip(bars, meds, ns):
                if n:
                    ax.text(b.get_x() + b.get_width() / 2, m + 0.03, f"{m:.2f}×\nn={n}",
                            ha="center", va="bottom", fontsize=7.5)
        ax.axhline(1.0, ls="--", color="gray", lw=1, label="1× (no change)")
        ax.set_xticks(x)
        ax.set_xticklabels(types, fontsize=9)
        ax.set_title(title)
        ax.legend(fontsize=8.5, loc="upper right")
        ax.grid(True, axis="y", alpha=0.25)
        ax.margins(y=0.18)
    axes[0].set_ylabel("median `-f` wall speedup  (OLD / NEW;  >1 = NEW faster)")
    fig.suptitle("Per-graph-type `-f` speedup, by verdict  (biological corpora)", fontsize=12)
    p = os.path.join(OUT, "F12_type_speedup.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    if regressions:
        print(f"  !! F12 0-regression check FAILED: {regressions}")
    else:
        print("  F12 0-regression check OK (no type/verdict median < 1×)")
    print(f"wrote {p}")


# ----------------------------------------------------------------------------- F15 (Q4)
GEN_COLOR = {"debruijn": "#1f77b4", "revdet": "#ff7f0e", "trie": "#2ca02c"}
GEN_DISP = {"debruijn": "De Bruijn", "revdet": "RevDet", "trie": "Trie"}


def fig15_practicality():
    """MSA → Wheeler graph practicality on real Ensembl gene MSAs (msa_practicality.csv):
    (A) Wheeler-rate by construction, (B) graph size vs MSA width, (C) recognition-time ECDF."""
    rows = load_csv(os.path.join(DATA, "msa_practicality.csv"))
    if not rows:
        print("F15 skipped (need msa_practicality.csv)")
        return
    gens = [g for g in ("debruijn", "revdet", "trie") if any(r["generator"] == g for r in rows)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.0))

    # (A) Wheeler-rate (stacked 100% bars, WG vs non-WG), with counts
    ax = axes[0]
    x = np.arange(len(gens))
    wg_frac, nw_frac, labels = [], [], []
    for g in gens:
        gr = [r for r in rows if r["generator"] == g and r["verdict"] in ("1", "-1", "0")]
        tot = len(gr) or 1
        nwg = sum(1 for r in gr if r["verdict"] == "1")
        nnw = sum(1 for r in gr if r["verdict"] in ("-1", "0"))
        wg_frac.append(100 * nwg / tot)
        nw_frac.append(100 * nnw / tot)
        labels.append((nwg, nnw))
    b1 = ax.bar(x, wg_frac, 0.6, color="#2ca02c", label="Wheeler")
    b2 = ax.bar(x, nw_frac, 0.6, bottom=wg_frac, color="#d62728", label="not Wheeler")
    for xi, (nwg, nnw), wf in zip(x, labels, wg_frac):
        ax.text(xi, 50, f"{nwg} WG\n{nnw} non", ha="center", va="center", fontsize=8.5,
                color="white", fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([GEN_DISP[g] for g in gens])
    ax.set_ylabel("share of real MSAs (%)")
    ax.set_title("(A) Wheeler-rate by construction")
    ax.legend(fontsize=8.5, loc="lower center")
    ax.set_ylim(0, 100)

    # (B) graph size vs MSA width (aligned length), colored by generator
    ax = axes[1]
    for g in gens:
        xs = [fnum(r["aln_len"]) for r in rows if r["generator"] == g and fnum(r["nodes"]) is not None]
        ys = [fnum(r["nodes"]) for r in rows if r["generator"] == g and fnum(r["nodes"]) is not None]
        ax.scatter(xs, ys, s=12, alpha=0.5, color=GEN_COLOR[g], label=GEN_DISP[g])
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("MSA aligned length (columns, log)")
    ax.set_ylabel("graph size (nodes, log)")
    ax.set_title("(B) Graph size vs MSA width\n(per-seq length capped at l=300)")
    ax.legend(fontsize=8.5)
    ax.grid(True, which="both", alpha=0.2)

    # (C) recognition-time ECDF (all sub-second)
    ax = axes[2]
    for g in gens:
        ms = sorted(fnum(r["wall_s"]) * 1000 for r in rows
                    if r["generator"] == g and fnum(r["wall_s"]) is not None)
        if not ms:
            continue
        ms = np.array(ms)
        y = np.arange(1, len(ms) + 1) / len(ms)
        ax.step(ms, y, where="post", color=GEN_COLOR[g],
                label=f"{GEN_DISP[g]} (median {np.median(ms):.0f} ms, max {ms.max():.0f} ms)")
    ax.axvline(1000, ls="--", color="gray", lw=1, label="1 s")
    ax.set_xscale("log")
    ax.set_xlabel("recognition wall time (ms, log)")
    ax.set_ylabel("fraction of MSAs (ECDF)")
    ax.set_title("(C) Recognition time on real graphs")
    ax.legend(fontsize=8.0, loc="lower right")
    ax.grid(True, which="both", alpha=0.2)

    fig.suptitle(f"MSA → Wheeler graph on {len({r['gene'] for r in rows})} Ensembl gene MSAs "
                 f"({len(rows)} construction runs)", fontsize=12)
    p = os.path.join(OUT, "F15_msa_practicality.png")
    fig.tight_layout(); fig.savefig(p, dpi=300); plt.close(fig)
    print(f"wrote {p}")


def main():
    figs = [
        ("fig1", fig1_correctness),
        ("fig2", fig2_verdict_matrix),
        ("fig3", fig3_capability),
        ("fig4", lambda: fig4_scatter("cpu")),
        ("fig4w", lambda: fig4_scatter("wall")),
        ("fig5", lambda: fig5_speedup_ecdf("cpu")),
        ("fig6", lambda: fig6_cactus("cpu")),
        ("fig7", fig7_setup_solve),
        ("fig7b", fig7b_memory),
        ("fig11", fig11_repair),
        ("fig12", fig12_type_speedup),
        ("fig15", fig15_practicality),
    ]
    only = sys.argv[1:]
    for name, f in figs:
        if only and not any(o == name for o in only):
            continue
        try:
            f()
        except Exception as e:   # noqa: BLE001
            print(f"  !! {name} failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
