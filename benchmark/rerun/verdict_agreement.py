#!/usr/bin/env python3
"""
verdict_agreement.py -- the correctness metric the benchmark pipeline never had.

Every committed plot is timing-only (no plot reads the verdict column). This script cross-tabulates
the VERDICTS of four independent deciders, using the brute oracle as ground truth:

    ORACLE   verify/brute_oracle.py            (n! enumeration; ground truth)
    SMT      recognizer_linux        (default) (Z3 backend)
    PERM     recognizer_linux  -s p            (permutation backend)
    EXP      recognizer_e                      (rebuilt exponential baseline; skip over-cap)

Two corpora:
  * REAL   -- the n<=9 oracle-decidable subset of the GT_vs_WGT benchmark graphs (per-corpus label
              mode: RandomG integer, biological string). These are almost all *constructed Wheeler*
              graphs, so they mainly test the ACCEPT path.
  * SYNTH  -- random graphs (self-loops + parallel edges, a real WG/non-WG mix) + the 16 curated
              edge cases. These exercise the REJECT path and the `-s p -e` always-accept bug (#2).

A disagreement with the oracle is a recognizer bug, reported (not averaged away). Output:
benchmark/VERDICT_AGREEMENT.md.

Run: python3 benchmark/rerun/verdict_agreement.py --synth 1500 --seed 7
"""

import argparse
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "verify"))
import brute_oracle as bo                                          # noqa: E402
from difftest import write_random_dot, recognizer_verdict         # noqa: E402
from difftest_exp import exp_verdict                              # noqa: E402
from edgecases import CASES, dot                                  # noqa: E402

TYPES = ["DeBruijnG_AA", "DeBruijnG_DNA", "DeBruijnGNC_AA", "DeBruijnGNC_DNA",
         "RandomG", "RevDetG_AA", "RevDetG_DNA", "Trie_AA", "Trie_DNA"]
INT_TYPES = {"RandomG"}
CORPUS = os.path.join(ROOT, "data", "graph", "GT_vs_WGT")
MAX_N = 9


def four_verdicts(path, int_mode):
    """Return dict of {oracle, smt, perm, exp} each in {1,0,None}. None = undecided/over-cap."""
    nodes, edges = bo.parse_dot(path)
    rank = bo.rank_labels(edges, int_mode=int_mode)
    oracle = 1 if bo.is_wheeler(nodes, edges, rank) else 0
    base = ["-i"] if int_mode else []

    def rec(extra):
        v = recognizer_verdict(path, base + extra)
        return v if v in (0, 1) else None       # TIMEOUT / ERR -> undecided

    smt = rec([])               # default backend = SMT
    perm = rec(["-s", "p"])     # permutation backend
    ev = exp_verdict(path)
    exp = ev if ev in (0, 1) else None          # None (over-cap) / TIMEOUT / ERR -> undecided
    return {"oracle": oracle, "smt": smt, "perm": perm, "exp": exp}


def tally(graphs, label):
    """graphs: list of (path, int_mode). Returns (stats, disagreements)."""
    stats = {k: {"agree": 0, "disagree": 0, "undecided": 0} for k in ("smt", "perm", "exp")}
    n_wg = n_nwg = 0
    disagreements = []
    for path, int_mode in graphs:
        v = four_verdicts(path, int_mode)
        truth = v["oracle"]
        n_wg += (truth == 1)
        n_nwg += (truth == 0)
        for k in ("smt", "perm", "exp"):
            if v[k] is None:
                stats[k]["undecided"] += 1
            elif v[k] == truth:
                stats[k]["agree"] += 1
            else:
                stats[k]["disagree"] += 1
                disagreements.append((label, os.path.relpath(path, ROOT), k, v[k], truth))
    return stats, n_wg, n_nwg, disagreements


def discover_real():
    graphs = []
    for t in TYPES:
        d = os.path.join(CORPUS, t)
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for fn in sorted(files):
                if not fn.endswith(".dot"):
                    continue
                p = os.path.join(root, fn)
                if len(bo.parse_dot(p)[0]) <= MAX_N:
                    graphs.append((p, t in INT_TYPES))
    return graphs


def make_synth(n_random, seed, tmp):
    rng = random.Random(seed)
    os.makedirs(tmp, exist_ok=True)
    graphs = []
    # edge cases (integer labels)
    for name, (edges, _e, _n) in CASES.items():
        p = os.path.join(tmp, f"ec_{name}.dot")
        with open(p, "w") as f:
            f.write(dot(edges))
        graphs.append((p, True))
    # random graphs: self-loops + parallel edges, real WG/non-WG mix
    for i in range(n_random):
        n = rng.randint(2, MAX_N)
        n_labels = rng.randint(1, 4)
        n_edges = rng.randint(1, max(1, n * 3))
        p = os.path.join(tmp, f"r_{i}.dot")
        write_random_dot(p, n, n_labels, n_edges, rng, allow_self=True, allow_dup=True)
        graphs.append((p, True))
    return graphs


def fmt(stats, n):
    parts = []
    for k in ("smt", "perm", "exp"):
        s = stats[k]
        dec = s["agree"] + s["disagree"]
        parts.append(f"| {k.upper()} | {s['agree']}/{dec} | {s['disagree']} | {s['undecided']} |")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", type=int, default=1500, help="number of random synthetic graphs")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--real-limit", type=int, default=None, help="cap REAL graphs (smoke runs)")
    args = ap.parse_args()

    real = discover_real()
    if args.real_limit:
        real = real[:args.real_limit]
    tmp = os.path.join(HERE, "_synthtmp")
    synth = make_synth(args.synth, args.seed, tmp)

    print(f"REAL n<=9 graphs: {len(real)};  SYNTH graphs: {len(synth)}")
    rs, r_wg, r_nwg, r_dis = tally(real, "REAL")
    ss, s_wg, s_nwg, s_dis = tally(synth, "SYNTH")

    L = []
    def emit(x=""): L.append(x)
    emit("# Phase 3 — Verdict-agreement metric (NEW)")
    emit()
    emit("The benchmark plots are all timing-only — no figure reads the verdict column. This is the "
         "missing **correctness** metric: every decider's verdict vs the brute-force oracle "
         "(`verify/brute_oracle.py`, ground truth). A disagreement is a recognizer bug.")
    emit()
    emit("Deciders: **SMT** = `recognizer_linux` (default), **PERM** = `recognizer_linux -s p`, "
         "**EXP** = rebuilt `recognizer_e` (over-cap graphs counted as undecided).")
    emit()
    emit(f"## REAL — n≤9 GT_vs_WGT benchmark graphs ({len(real)}: {r_wg} WG, {r_nwg} non-WG)")
    emit("Mostly *constructed Wheeler* graphs → exercises the ACCEPT path on real biological inputs.")
    emit()
    emit("| decider | agree/decided | disagree | undecided |")
    emit("|---|--:|--:|--:|")
    emit(fmt(rs, len(real)))
    emit()
    emit(f"## SYNTH — random + edge cases ({len(synth)}: {s_wg} WG, {s_nwg} non-WG)")
    emit("Self-loops, parallel edges, a real WG/non-WG mix, and the 16 curated edge cases → "
         "exercises the REJECT path and the `-s p -e` always-accept bug (#2).")
    emit()
    emit("| decider | agree/decided | disagree | undecided |")
    emit("|---|--:|--:|--:|")
    emit(fmt(ss, len(synth)))
    emit()
    total_dis = r_dis + s_dis
    emit("## Result")
    emit()
    if not total_dis:
        emit(f"**Zero disagreements** across {len(real) + len(synth)} graphs "
             f"({r_wg + s_wg} Wheeler, {r_nwg + s_nwg} non-Wheeler). Every decider matches the "
             f"oracle on every graph it decided — across both the accept-heavy real corpora and the "
             f"reject-heavy synthetic corpus. ✓")
    else:
        emit(f"**{len(total_dis)} DISAGREEMENT(S)** — recognizer bug(s):")
        for (lbl, p, k, got, truth) in total_dis[:60]:
            emit(f"- [{lbl}] {k.upper()} said {got}, oracle {truth}: `{p}`")
    out_md = os.path.join(ROOT, "benchmark", "VERDICT_AGREEMENT.md")
    with open(out_md, "w") as fh:
        fh.write("\n".join(L) + "\n")

    # cleanup synth tmp
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)

    print("REAL :", rs)
    print("SYNTH:", ss)
    print(f"disagreements: {len(total_dis)}")
    print(f"wrote {os.path.relpath(out_md, ROOT)}")
    sys.exit(1 if total_dis else 0)


if __name__ == "__main__":
    main()
