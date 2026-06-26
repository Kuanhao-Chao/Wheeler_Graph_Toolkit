#!/usr/bin/env python3
"""bench_dl.py -- Round-1 native difference-logic solver vs the Z3 (QF_IDL) backend.

Climbs a size ladder on the Wheeler-by-construction synthetic families (complete, dnfa; the families
the recognition ceiling is measured on) and records, for each (family, n, backend), the verdict and
wall time within a per-run timeout. Backends:
  smt = the production Z3 backend (-s smt)
  dl  = the native propagation+restart solver (-s dl); verdict 0 from the recognizer = UNDECIDED
        (dl punted -- in production it would fall back to z3).

Reproducible: same (family, n, seed) => same graph (the generators are seeded). Writes a CSV that the
NATIVE_DL_SOLVER.md write-up cites. This quantifies the negative result: dl decides small instances
(sometimes faster than z3) but its DFS blows up ~n=512, an order of magnitude below z3's ceiling,
because z3's theory propagation makes the search trivial where hand-rolled bounds propagation does not.

Usage:  python3 bench_dl.py --timeout 30 --out results_dl.csv
"""
import argparse, os, subprocess, time, csv, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
GEN = {"complete": os.path.join(ROOT, "generator", "Random_generator", "gen_complete_WG.py"),
       "dnfa":     os.path.join(ROOT, "generator", "Random_generator", "gen_d-nfa_WG.py")}
PY = sys.executable


def feasible_edges(n, labels, density, root=1):
    lo = n - root
    hi = n * labels + n - labels - root
    return max(lo, min(int(round(density * n)), hi))


def gen(family, n, labels, density, seed, path):
    e0 = feasible_edges(n, labels, density)
    lo, hi = n - 1, n * labels + n - labels - 1
    for delta in (0, 1, -1, 2, -2, 3, -3, 4, 5, 6):
        e = e0 + delta
        if e < lo or e > hi:
            continue
        cmd = [PY, GEN[family], "-n", str(n), "-e", str(e), "-l", str(labels), "-s", "--seed", str(seed), "-o", path]
        if family == "dnfa":
            cmd += ["-d", "2"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(path):
            return e
    return None


def run(backend, path, timeout):
    """Return (verdict, wall). verdict in {WG, nonWG, UNDECIDED, TIMEOUT}."""
    cmd = [REC, path, "-b", "-i", "-s", backend]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", float(timeout)
    wall = time.time() - t0
    rc = r.returncode
    if rc == 1:
        return "WG", wall
    if rc in (255, -1):
        return "nonWG", wall
    if rc == 0:
        return "UNDECIDED", wall
    return f"ERR{rc}", wall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--labels", type=int, default=3)
    ap.add_argument("--density", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ns", default="64,128,192,256,320,384,448,512,640,768,1024,1536,2048,2816")
    ap.add_argument("--families", default="complete,dnfa")
    ap.add_argument("--backends", default="smt,dl")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "results_dl.csv"))
    args = ap.parse_args()

    ns = [int(x) for x in args.ns.split(",")]
    families = args.families.split(",")
    backends = args.backends.split(",")
    tmp = os.path.join(os.path.dirname(__file__), "_tmp")
    os.makedirs(tmp, exist_ok=True)

    rows = []
    print(f"{'family':<10}{'n':>6}{'edges':>7}  " + "".join(f"{b:>22}" for b in backends))
    for family in families:
        # once a backend times out at some n, it will only get worse -> stop attempting it for this family
        dead = set()
        for n in ns:
            path = os.path.join(tmp, f"{family}_{n}.dot")
            e = gen(family, n, args.labels, args.density, args.seed, path)
            if e is None:
                continue
            cells = []
            for b in backends:
                if b in dead:
                    rows.append({"family": family, "n": n, "edges": e, "backend": b, "verdict": "SKIP", "wall": ""})
                    cells.append(f"{'skip':>22}")
                    continue
                verdict, wall = run(b, path, args.timeout)
                rows.append({"family": family, "n": n, "edges": e, "backend": b, "verdict": verdict, "wall": f"{wall:.3f}"})
                cells.append(f"{verdict+' '+format(wall,'.2f')+'s':>22}")
                if verdict in ("TIMEOUT",):
                    dead.add(b)
            print(f"{family:<10}{n:>6}{e:>7}  " + "".join(cells))
            sys.stdout.flush()

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["family", "n", "edges", "backend", "verdict", "wall"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
