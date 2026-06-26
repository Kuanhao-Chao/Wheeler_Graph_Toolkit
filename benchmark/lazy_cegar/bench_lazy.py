#!/usr/bin/env python3
"""bench_lazy.py -- Round-2 lazy/CEGAR A3 backend vs the vanilla Z3 (QF_IDL) backend.

Climbs a size ladder on the Wheeler-by-construction families (complete, dnfa) and records, per
(family, n, backend): verdict, wall time, peak RSS, and the recognizer's own --profile fields. The
Round-2 question is whether the lazy/CEGAR backend -- which never materializes the full O(E^2) A3
encoding -- moves the recognition ceiling and/or shrinks memory vs vanilla z3:

  smt        -s smt        default-path control (heuristic brackets + full A3)
  lazy       -s lazy       default-path lazy/CEGAR (brackets + A3 on demand)
  full       -f            full-range control  (-f, the z3 memory wall ~n=832)
  full-lazy  -f -s lazy    full-range lazy/CEGAR -- the PRIMARY target

Headline metrics:
  - ceiling: largest n each backend decides within --timeout (TIMEOUT once it gives up).
  - encoding size: PROFILE `assertions` (smt) and `materialized_a3`/`pair_universe` (lazy) -- the
    lazy backend's whole thesis is materialized_a3 << pair_universe.
  - memory: peak RSS via /usr/bin/time -v (did we avoid the 5.6 GB -f overflow?), and z3 `zmem_mb`.

Reproducible: same (family, n, seed) => same graph. Writes a CSV the Round-2 write-up cites.

Usage:  python3 bench_lazy.py --timeout 60 --out results_lazy.csv
"""
import argparse, os, subprocess, time, csv, sys, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REC = os.environ.get("WGT_REC") or os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
GEN = {"complete": os.path.join(ROOT, "generator", "Random_generator", "gen_complete_WG.py"),
       "dnfa":     os.path.join(ROOT, "generator", "Random_generator", "gen_d-nfa_WG.py")}
PY = sys.executable

# backend -> recognizer args (always -b benchmark + -i int-labels + --profile for the stderr metrics).
BACKENDS = {
    "smt":       ["-s", "smt"],
    "lazy":      ["-s", "lazy"],
    "full":      ["-f"],
    "full-lazy": ["-f", "-s", "lazy"],
}

GNU_TIME = "/usr/bin/time"


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
        cmd = [PY, GEN[family], "-n", str(n), "-e", str(e), "-l", str(labels), "-s",
               "--seed", str(seed), "-o", path]
        if family == "dnfa":
            cmd += ["-d", "2"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(path):
            return e
    return None


_PROFILE_KEYS = ("rounds", "materialized_a3", "pair_universe", "assertions", "zmem_mb", "allocs",
                 "conflicts", "decisions", "solve_s")


def parse_profile(stderr):
    """Pull the PROFILE smt/lazy fields and the peak RSS (from /usr/bin/time -v) out of stderr."""
    out = {}
    for line in stderr.splitlines():
        if line.startswith("PROFILE smt") or line.startswith("PROFILE lazy"):
            for k in _PROFILE_KEYS:
                m = re.search(r"\b" + k + r"=([-\d.eE+]+)", line)
                if m:
                    out[k] = m.group(1)
        m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", line)
        if m:
            out["rss_kb"] = m.group(1)
    return out


def run(backend, path, timeout):
    """Return (verdict, wall, profile_dict)."""
    cmd = [GNU_TIME, "-v", REC, path, "-b", "-i", "--profile"] + BACKENDS[backend]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", float(timeout), {}
    wall = time.time() - t0
    rc = r.returncode
    prof = parse_profile(r.stderr)
    if rc == 1:
        v = "WG"
    elif rc in (255, -1):
        v = "nonWG"
    elif rc == 0:
        v = "UNDECIDED"
    else:
        v = f"ERR{rc}"
    return v, wall, prof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--labels", type=int, default=3)
    ap.add_argument("--density", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ns", default="64,128,256,384,512,640,768,832,1024,1280,1536,2048,2816")
    ap.add_argument("--families", default="complete,dnfa")
    ap.add_argument("--backends", default="smt,lazy,full,full-lazy")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "results_lazy.csv"))
    args = ap.parse_args()

    ns = [int(x) for x in args.ns.split(",")]
    families = args.families.split(",")
    backends = args.backends.split(",")
    tmp = os.path.join(os.path.dirname(__file__), "_tmp")
    os.makedirs(tmp, exist_ok=True)

    fields = ["family", "n", "edges", "backend", "verdict", "wall", "rss_kb",
              "rounds", "materialized_a3", "pair_universe", "assertions", "zmem_mb",
              "allocs", "conflicts", "decisions", "solve_s"]
    rows = []
    print(f"{'family':<9}{'n':>6}{'e':>7}  " + "".join(f"{b:>26}" for b in backends), flush=True)
    for family in families:
        dead = set()
        for n in ns:
            path = os.path.join(tmp, f"{family}_{n}.dot")
            e = gen(family, n, args.labels, args.density, args.seed, path)
            if e is None:
                continue
            cells = []
            for b in backends:
                if b in dead:
                    rows.append({"family": family, "n": n, "edges": e, "backend": b, "verdict": "SKIP"})
                    cells.append(f"{'skip':>26}")
                    continue
                v, wall, prof = run(b, path, args.timeout)
                row = {"family": family, "n": n, "edges": e, "backend": b, "verdict": v,
                       "wall": f"{wall:.3f}"}
                row.update(prof)
                rows.append(row)
                extra = ""
                if "materialized_a3" in prof:
                    extra = f" a3={prof['materialized_a3']}/{prof.get('pair_universe','?')}"
                rssm = f" {int(prof['rss_kb'])//1024}M" if "rss_kb" in prof else ""
                cells.append(f"{v+' '+format(wall,'.1f')+'s'+rssm+extra:>26}")
                if v == "TIMEOUT":
                    dead.add(b)
            print(f"{family:<9}{n:>6}{e:>7}  " + "".join(cells), flush=True)

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
