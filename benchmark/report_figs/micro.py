#!/usr/bin/env python3
"""
micro.py -- setup/solve split (S4) and peak-RSS memory (S4b) for the report.

The `-f` SMT backend prints, in VERBOSE (non-`-b`) mode, two wall-clock lines:
    SMT Setup: <s> seconds      (building the QF_IDL encoding -- where Phase 4.1/4.2 sparsen it)
    SMT Solve: <s> seconds      (z3 solving the encoding)
We run pre41 / pre42 / new on a handful of headline graphs, R replicates, and record the median of
each phase. The A2 (4.1) and A3 (4.2) sparsifications attack SETUP (fewer constraints) and indirectly
SOLVE (smaller formula). Missing "SMT Solve:" after a timeout is recorded as solve=TIMEOUT.

Memory: /usr/bin/time -v <bin> <graph> -f  ->  "Maximum resident set size (kbytes)".

Output: <out>.setup_solve.csv  and  <out>.mem.csv
Usage:  python3 benchmark/report_figs/micro.py --out benchmark/report_figs/data/micro
"""
import argparse
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

BINS = {
    "pre41": "recognizer/bin/recognizer_pre41",
    "pre42": "recognizer/bin/recognizer_linux_old",
    "new":   "recognizer/bin/recognizer_linux",
}
# headline graphs: k_5 DNA (where within-group A3 structure exists) + a k_4 mid baseline.
TARGETS = [
    "data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_DOCK4_orthologues_DNA_k_5_l_2000_a_7.dot",
    "data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_TRPC1_orthologues_DNA_k_5_l_2000_a_8.dot",
    "data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_ZRANB3_orthologues_DNA_k_5_l_2000_a_8.dot",
    "data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_DOCK4_orthologues_DNA_k_4_l_2000_a_7.dot",
    "data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_ZRANB3_orthologues_DNA_k_4_l_2000_a_6.dot",
]
SETUP_RE = re.compile(r"SMT Setup:\s*([0-9.eE+-]+)\s*seconds")
SOLVE_RE = re.compile(r"SMT Solve:\s*([0-9.eE+-]+)\s*seconds")


def median(xs):
    xs = sorted(xs)
    k = len(xs)
    return None if k == 0 else (xs[k // 2] if k % 2 else 0.5 * (xs[k // 2 - 1] + xs[k // 2]))


def run_verbose(binpath, dot, timeout):
    """Return (setup, solve) in seconds, or (None, 'TIMEOUT')/(None, None)."""
    try:
        r = subprocess.run([binpath, dot, "-f"], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        sm = SETUP_RE.search(out)
        return (float(sm.group(1)) if sm else None), "TIMEOUT"
    sm = SETUP_RE.search(r.stdout)
    vm = SOLVE_RE.search(r.stdout)
    return (float(sm.group(1)) if sm else None), (float(vm.group(1)) if vm else None)


def peak_rss_kb(binpath, dot, timeout):
    """Peak RSS in KB via /usr/bin/time -v, or None / 'TIMEOUT'."""
    try:
        r = subprocess.run(["/usr/bin/time", "-v", binpath, dot, "-f"],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", r.stderr)
    return int(m.group(1)) if m else None


def edges(dot):
    n = 0
    with open(os.path.join(ROOT, dot)) as fh:
        for line in fh:
            if "->" in line:
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--replicates", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=240.0)
    args = ap.parse_args()

    ss_path = args.out + ".setup_solve.csv"
    with open(ss_path, "w") as out:
        out.write("name,edges,binary,setup_med,solve_med,setup_status,solve_status\n")
        for dot in TARGETS:
            name = os.path.basename(dot)
            ne = edges(dot)
            for label, rel in BINS.items():
                binpath = os.path.join(ROOT, rel)
                setups, solves, sstat, vstat = [], [], "OK", "OK"
                for _ in range(args.replicates):
                    s, v = run_verbose(binpath, os.path.join(ROOT, dot), args.timeout)
                    if s is not None:
                        setups.append(s)
                    else:
                        sstat = "MISSING"
                    if isinstance(v, (int, float)):
                        solves.append(v)
                    else:
                        vstat = v or "MISSING"
                        break   # timeout/missing: don't repeat
                sm = median(setups)
                vm = median(solves)
                out.write(f"{name},{ne},{label},"
                          f"{'' if sm is None else f'{sm:.6f}'},"
                          f"{'' if vm is None else f'{vm:.6f}'},{sstat},{vstat}\n")
                out.flush()
                print(f"{name[:46]:46s} e={ne:5d} {label:5s} setup={sm} solve={vm} [{vstat}]",
                      flush=True)

    mem_path = args.out + ".mem.csv"
    with open(mem_path, "w") as out:
        out.write("name,edges,binary,peak_rss_kb\n")
        for dot in TARGETS:
            name = os.path.basename(dot)
            ne = edges(dot)
            for label, rel in BINS.items():
                rss = peak_rss_kb(os.path.join(ROOT, rel), os.path.join(ROOT, dot), args.timeout)
                out.write(f"{name},{ne},{label},{rss}\n")
                out.flush()
                print(f"MEM {name[:42]:42s} {label:5s} -> {rss} KB", flush=True)
    print(f"\nwrote {ss_path}\nwrote {mem_path}")


if __name__ == "__main__":
    main()
