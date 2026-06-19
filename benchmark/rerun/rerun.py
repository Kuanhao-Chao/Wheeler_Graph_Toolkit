#!/usr/bin/env python3
"""
rerun.py -- re-run the GT_vs_WGT benchmark corpora with the FIXED Linux binaries.

Phase 3 of the verification effort. The committed run_*.sh scripts hardcode the macOS arm64
`recognizer` binary (won't run on Linux) and the OLD broken `recognizer_e`, and they append blindly
into committed 2022/2023 result files. This harness instead:

  * uses the LINUX builds: recognizer/bin/recognizer_linux  and the fixed
    benchmark/exponential_recognizer/bin/recognizer_e;
  * writes to a SEPARATE results tree (benchmark/rerun/results/...), never touching committed data,
    so OLD vs NEW can be diffed;
  * emits CANONICAL 4-column rows  "<verdict>\t<n>\t<cpu_time>\t<repo_relative_path>"  (we parse the
    binary's stdout for verdict+time and write our own node count + path -- no quoting ambiguity);
  * is idempotent/resumable via a sidecar .done file (skip inputs already completed);
  * supports an n-cap (--max-n) so the in-session run stays on the oracle-decidable / recognizer_e
    -decidable subset, and --limit for quick smoke runs.

Sides:
  GT  -> recognizer_e <dot>                      (col0: 1=WG / 0=not-WG / -1=over-cap)
  WGT -> recognizer_linux <dot> -b -s p [-i] -e  (exit/col0: 1=WG, -1=not-WG)   [-i only for RandomG]

Run:
  python3 benchmark/rerun/rerun.py --types all --sides both --max-n 9
  python3 benchmark/rerun/rerun.py --types RandomG --sides GT --limit 50 --fresh
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # repo root
sys.path.insert(0, os.path.join(ROOT, "verify"))
import brute_oracle as bo                                # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
EXP = os.path.join(ROOT, "benchmark", "exponential_recognizer", "bin", "recognizer_e")
CORPUS_ROOT = os.path.join(ROOT, "data", "graph", "GT_vs_WGT")
OUT_ROOT = os.path.join(HERE, "results", "GT_vs_WGT")

GT_TYPES = ["DeBruijnG_AA", "DeBruijnG_DNA", "DeBruijnGNC_AA", "DeBruijnGNC_DNA",
            "RandomG", "RevDetG_AA", "RevDetG_DNA", "Trie_AA", "Trie_DNA"]
INT_TYPES = {"RandomG"}        # only RandomG uses integer labels (-i); the rest are string-mode
TIMEOUT_S = 30
SENTINEL = "-1\t0\t60000000"   # GT_vs_WGT timeout/over-cap row prefix (matches committed scripts)


def list_dots(gtype):
    d = os.path.join(CORPUS_ROOT, gtype)
    out = []
    for root, _, files in os.walk(d):
        for fn in files:
            if fn.endswith(".dot"):
                out.append(os.path.join(root, fn))
    return sorted(out)


def canonical(path):
    """Repo-relative path string, used as the stable col3 and the idempotency key."""
    return os.path.relpath(path, ROOT)


def parse_line(stdout):
    """Return (col0:int|None, col2:str|None) from the last 4-field benchmark line of stdout."""
    last = None
    for line in stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            last = parts
    if last is None:
        return None, None
    try:
        return int(last[0]), last[2]
    except (ValueError, IndexError):
        return None, None


def run_one(side, path, n, int_mode, timeout):
    """Run one graph; return a canonical 4-col row string (no trailing newline)."""
    canon = canonical(path)
    if side == "GT":
        cmd = [EXP, path]
    else:  # WGT
        cmd = [REC, path, "-b", "-s", "p"] + (["-i"] if int_mode else []) + ["-e"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"{SENTINEL}\t{canon}"
    col0, col2 = parse_line(r.stdout)
    if side == "WGT" and col0 is None:
        # recognizer signals via exit code too: 1=WG, 255(=-1)=not-WG.
        col0 = 1 if r.returncode == 1 else (-1 if r.returncode in (255, -1) else None)
    if col0 is None or col2 is None:
        return f"{SENTINEL}\t{canon}"          # treat unpar. as over-cap/undecided
    return f"{col0}\t{n}\t{col2}\t{canon}"


def run_side(gtype, side, max_n, limit, fresh, timeout):
    outdir = os.path.join(OUT_ROOT, gtype)
    os.makedirs(outdir, exist_ok=True)
    outfile = os.path.join(outdir, f"{side}_out.txt")
    donefile = os.path.join(outdir, f"{side}_out.done")
    if fresh:
        for p in (outfile, donefile):
            if os.path.exists(p):
                os.remove(p)
    done = set()
    if os.path.exists(donefile):
        with open(donefile) as fh:
            done = {ln.strip() for ln in fh if ln.strip()}

    int_mode = gtype in INT_TYPES
    dots = list_dots(gtype)
    ran = skipped = capped = 0
    with open(outfile, "a") as out, open(donefile, "a") as dlog:
        for path in dots:
            canon = canonical(path)
            if canon in done:
                skipped += 1
                continue
            n = len(bo.parse_dot(path)[0])
            if max_n is not None and n > max_n:
                capped += 1
                continue
            row = run_one(side, path, n, int_mode, timeout)
            out.write(row + "\n")
            out.flush()
            dlog.write(canon + "\n")
            dlog.flush()
            ran += 1
            if limit and ran >= limit:
                break
    return ran, skipped, capped, outfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default="all", help="comma-list of graph types, or 'all'")
    ap.add_argument("--sides", default="both", choices=["GT", "WGT", "both"])
    ap.add_argument("--max-n", type=int, default=None, help="skip graphs with more than this many nodes")
    ap.add_argument("--limit", type=int, default=None, help="cap graphs per (type,side) -- smoke runs")
    ap.add_argument("--timeout", type=int, default=TIMEOUT_S)
    ap.add_argument("--fresh", action="store_true", help="truncate existing output/done first")
    args = ap.parse_args()

    types = GT_TYPES if args.types == "all" else [t.strip() for t in args.types.split(",")]
    sides = ["GT", "WGT"] if args.sides == "both" else [args.sides]

    print(f"binaries: REC={REC}\n          EXP={EXP}")
    print(f"max_n={args.max_n} limit={args.limit} timeout={args.timeout}s fresh={args.fresh}\n")
    grand = 0
    for gtype in types:
        for side in sides:
            ran, skipped, capped, outfile = run_side(
                gtype, side, args.max_n, args.limit, args.fresh, args.timeout)
            grand += ran
            print(f"  {gtype:<16} {side:<3}: ran={ran:<5} skipped(done)={skipped:<5} "
                  f"capped(>n)={capped:<6} -> {os.path.relpath(outfile, ROOT)}")
    print(f"\nTotal graphs run: {grand}")


if __name__ == "__main__":
    main()
