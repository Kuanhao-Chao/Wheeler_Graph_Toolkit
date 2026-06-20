#!/usr/bin/env python3
"""
ftiming.py -- 3-point `-f` (full-range SMT) timing sweep across recognizer generations.

Runs each binary with `-b -f` on every .dot in the given corpora, R replicates, under a per-graph
wall-clock timeout, and records the median wall time + the `-b` CPU-tick column + the verdict. This
is the controlled OLD-vs-NEW performance measurement for Phase 4.1 (sparse cross-group A2,
O(E^2)->O(E+L)) and Phase 4.2 (sparse within-group A3, O(E_l^2)->O(D_l^2+E_l)):

    pre41  (c396d2b56)        dense A2 + dense A3   -> baseline
    pre42  (recognizer_linux_old = 3f9045d2d)  sparse A2 + dense A3 -> isolates the A2 gain
    new    (recognizer_linux)  sparse A2 + sparse A3 -> isolates the A3 gain

Methodology / honesty:
  * Biological graphs carry STRING edge labels, so we DO NOT pass -i (label order is lexicographic).
  * A timeout is recorded as TIMEOUT and is never read as a verdict; on the first TIMEOUT/ERR for a
    (graph,binary) the remaining replicates are skipped (a timeout repeated 3x is still a timeout).
  * The `-b` row is: "<verdict>\t<nodes>\t<cpu_ticks>\t<path>"  (verdict 1=WG, -1=non-WG, 0=undecided).
    cpu_ticks is raw clock() (CPU, not wall); wall is measured here with perf_counter.
  * Verdict disagreements between binaries are recorded (pre41 predates the z3-unknown soundness fix)
    so the report can flag them rather than silently averaging over them.
  * Resumable: every (graph,binary) result is appended to raw.jsonl and skipped on restart.

Usage:
  python3 benchmark/report_figs/ftiming.py \
      --binaries new=recognizer/bin/recognizer_linux,pre42=recognizer/bin/recognizer_linux_old,pre41=recognizer/bin/recognizer_pre41 \
      --corpus data/graph/SMT_vs_RHSMT/DeBruijnG_DNA,data/graph/SMT_vs_RHSMT/RevDetG_DNA \
      --timeout 60 --replicates 3 --out benchmark/report_figs/ftiming_dna
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def edge_count(path):
    n = 0
    try:
        with open(path) as fh:
            for line in fh:
                if "->" in line:
                    n += 1
    except OSError:
        pass
    return n


def parse_b_row(stdout):
    """Return (verdict:int, nodes:int, cpu:float) from the last tab-separated benchmark line."""
    last = None
    for line in stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            last = parts
    if last is None:
        return None
    try:
        return int(last[0]), int(last[1]), float(last[2])
    except ValueError:
        return None


def run_once(binpath, dot, timeout):
    """One `-b -f` run. Return dict(status, verdict, nodes, cpu, wall)."""
    t0 = time.perf_counter()
    try:
        r = subprocess.run([binpath, dot, "-b", "-f"], capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "wall": timeout}
    wall = time.perf_counter() - t0
    parsed = parse_b_row(r.stdout)
    if parsed is None:
        return {"status": "ERR", "wall": wall, "rc": r.returncode,
                "out": r.stdout[-200:], "err": r.stderr[-200:]}
    verdict, nodes, cpu = parsed
    return {"status": "DECISIVE", "verdict": verdict, "nodes": nodes, "cpu": cpu, "wall": wall}


def median(xs):
    xs = sorted(xs)
    k = len(xs)
    if k == 0:
        return None
    return xs[k // 2] if k % 2 else 0.5 * (xs[k // 2 - 1] + xs[k // 2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binaries", required=True,
                    help="comma list label=path (path relative to repo root or absolute)")
    ap.add_argument("--corpus", required=True, help="comma list of directories of .dot files")
    ap.add_argument("--timeout", type=float, default=60.0, help="per-graph wall timeout (s)")
    ap.add_argument("--replicates", type=int, default=3)
    ap.add_argument("--out", required=True, help="output prefix (writes <out>.raw.jsonl, <out>.csv)")
    args = ap.parse_args()

    bins = {}
    for tok in args.binaries.split(","):
        label, path = tok.split("=", 1)
        bins[label] = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if not os.path.exists(bins[label]):
            sys.exit(f"missing binary {label}: {bins[label]}")

    dots = []
    for d in args.corpus.split(","):
        dd = d if os.path.isabs(d) else os.path.join(ROOT, d)
        for f in sorted(os.listdir(dd)):
            if f.endswith(".dot"):
                p = os.path.join(dd, f)
                dots.append((p, edge_count(p)))
    dots.sort(key=lambda t: t[1])   # small -> large, so partial results are useful
    print(f"binaries : {list(bins)}")
    print(f"graphs   : {len(dots)}  (edge range {dots[0][1]}..{dots[-1][1]})")
    print(f"timeout  : {args.timeout}s   replicates {args.replicates}\n", flush=True)

    raw_path = args.out + ".raw.jsonl"
    done = set()   # (label, dot) already recorded
    if os.path.exists(raw_path):
        with open(raw_path) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    done.add((rec["label"], rec["dot"]))
                except ValueError:
                    pass
        print(f"resuming: {len(done)} (binary,graph) results already cached\n", flush=True)

    raw = open(raw_path, "a")
    for i, (dot, ne) in enumerate(dots):
        name = os.path.basename(dot)
        for label, binpath in bins.items():
            if (label, dot) in done:
                continue
            walls, cpus, verdicts, status = [], [], [], "DECISIVE"
            for rep in range(args.replicates):
                res = run_once(binpath, dot, args.timeout)
                if res["status"] != "DECISIVE":
                    status = res["status"]
                    walls = [res["wall"]]
                    break
                walls.append(res["wall"])
                cpus.append(res["cpu"])
                verdicts.append(res["verdict"])
            rec = {"label": label, "dot": dot, "name": name, "edges": ne,
                   "status": status,
                   "median_wall": median(walls),
                   "median_cpu": median(cpus) if cpus else None,
                   "nodes": (None if status != "DECISIVE" else res.get("nodes")),
                   "verdict": (verdicts[0] if verdicts else None),
                   "replicates": len(walls)}
            raw.write(json.dumps(rec) + "\n")
            raw.flush()
            tag = (f"{rec['median_wall']:.3f}s v={rec['verdict']}" if status == "DECISIVE"
                   else status)
            print(f"[{i+1}/{len(dots)}] {name[:48]:48s} e={ne:5d} {label:5s} -> {tag}", flush=True)
    raw.close()

    # --- summary CSV: one row per graph with a column per binary ---
    recs = []
    with open(raw_path) as fh:
        for line in fh:
            try:
                recs.append(json.loads(line))
            except ValueError:
                pass
    by_graph = {}
    for r in recs:
        by_graph.setdefault(r["dot"], {})[r["label"]] = r
    labels = list(bins)
    csv_path = args.out + ".csv"
    with open(csv_path, "w") as out:
        cols = ["name", "edges"] + [f"{l}_wall" for l in labels] + \
               [f"{l}_cpu" for l in labels] + [f"{l}_status" for l in labels] + \
               [f"{l}_verdict" for l in labels]
        out.write(",".join(cols) + "\n")
        for dot, byl in sorted(by_graph.items(), key=lambda kv: next(iter(kv[1].values()))["edges"]):
            any_rec = next(iter(byl.values()))
            row = [any_rec["name"], str(any_rec["edges"])]
            for l in labels:
                row.append("" if l not in byl or byl[l]["median_wall"] is None
                           else f"{byl[l]['median_wall']:.4f}")
            for l in labels:
                row.append("" if l not in byl or byl[l]["median_cpu"] is None
                           else f"{byl[l]['median_cpu']:.0f}")
            for l in labels:
                row.append("" if l not in byl else byl[l]["status"])
            for l in labels:
                row.append("" if l not in byl or byl[l]["verdict"] is None
                           else str(byl[l]["verdict"]))
            out.write(",".join(row) + "\n")
    print(f"\nwrote {raw_path}\nwrote {csv_path}")


if __name__ == "__main__":
    main()
