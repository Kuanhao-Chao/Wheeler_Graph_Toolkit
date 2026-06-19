#!/usr/bin/env python3
"""
difftest_exp.py -- differential testing of the (fixed) EXPONENTIAL recognizer vs the brute oracle.

The exponential baseline `benchmark/exponential_recognizer/bin/recognizer_e` was rebuilt into an
honest decision procedure (it now enumerates node orderings and checks the 3 Wheeler axioms on the
actual graph). This harness confirms it agrees with the independent ground-truth oracle
(verify/brute_oracle.py) on the same corpora the main recognizer was validated against.

Verdict encoding of recognizer_e (column 1 of its single benchmark line):
    1  = Wheeler graph
    0  = NOT a Wheeler graph
   -1  = over-cap / not enumerated (too big)   -> skipped in the comparison

Label ranking: recognizer_e sorts label strings lexicographically, so we rank the oracle in STRING
mode here (not --int). All corpora use single-digit labels, so string and numeric order coincide.

Usage:
  python3 verify/difftest_exp.py --random 4000 --max-n 7 --seed 1
"""

import argparse
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import brute_oracle as bo                                   # noqa: E402
from difftest import write_random_dot, gen_positive         # noqa: E402
from edgecases import CASES, dot                            # noqa: E402

EXP = os.path.join(ROOT, "benchmark", "exponential_recognizer", "bin", "recognizer_e")
REPRO = os.path.join(HERE, "repro_exp")


def exp_verdict(path, timeout=60):
    """Return 1 (WG), 0 (not WG), None (over-cap/undecided), 'TIMEOUT', or ('ERR', detail)."""
    try:
        r = subprocess.run([EXP, path], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    # recognizer_e prints exactly one benchmark line: "<col0>\t<n>\t<time>\t<path>".
    last = None
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            last = parts
    if last is None:
        return ("ERR", f"no benchmark line (rc={r.returncode}, out={r.stdout!r})")
    try:
        col0 = int(last[0])
    except ValueError:
        return ("ERR", f"bad col0: {last[0]!r}")
    if col0 == 1:
        return 1
    if col0 == 0:
        return 0
    if col0 == -1:
        return None        # over-cap / undecided
    return ("ERR", f"unexpected col0={col0}")


def oracle_verdict(path, max_n):
    """Ground truth in STRING-rank mode (matches recognizer_e's lexicographic label sort)."""
    nodes, edges = bo.parse_dot(path)
    if len(nodes) > max_n:
        return None
    rank = bo.rank_labels(edges, int_mode=False)
    return 1 if bo.is_wheeler(nodes, edges, rank) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--random", type=int, default=4000)
    ap.add_argument("--positives", type=int, default=500)
    ap.add_argument("--max-n", type=int, default=7, help="oracle cap; also keeps exp enumeration cheap")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--keep-tmp", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    os.makedirs(REPRO, exist_ok=True)
    tmp = os.path.join(HERE, "_exptmp")
    os.makedirs(tmp, exist_ok=True)

    checked = pos = bad = anom = skipped = 0
    examples = []

    def handle(path, tag):
        nonlocal checked, pos, bad, anom, skipped
        truth = oracle_verdict(path, args.max_n)
        if truth is None:
            skipped += 1
            return
        v = exp_verdict(path)
        if v is None:                 # exp over-cap: cannot compare
            skipped += 1
            return
        if isinstance(v, tuple) or v == "TIMEOUT":
            anom += 1
            if len(examples) < 40:
                examples.append(f"ANOMALY [{tag}] {v} {path}")
            return
        checked += 1
        if truth == 1:
            pos += 1
        if v != truth:
            bad += 1
            dst = os.path.join(REPRO, f"mismatch_{bad:04d}_{tag}.dot")
            with open(path) as src, open(dst, "w") as out:
                out.write(src.read())
            msg = f"MISMATCH [{tag}] oracle={truth} exp={v} -> {dst}"
            examples.append(msg)
            print(msg)

    # --- curated structural edge cases ---
    for name, (edges, _expect, _note) in CASES.items():
        path = os.path.join(tmp, "ec_" + name + ".dot")
        with open(path, "w") as f:
            f.write(dot(edges))
        handle(path, "edgecase")

    # --- random graphs (include self-loops AND parallel edges: exp must handle them too) ---
    for i in range(args.random):
        n = rng.randint(2, args.max_n)
        n_labels = rng.randint(1, 4)           # single-digit labels
        n_edges = rng.randint(1, max(1, n * 3))
        path = os.path.join(tmp, f"rand_{i}.dot")
        write_random_dot(path, n, n_labels, n_edges, rng, allow_self=True, allow_dup=True)
        handle(path, "rand")

    # --- guaranteed-positive Wheeler graphs ---
    for i in range(args.positives):
        kind = "complete" if (i % 2 == 0) else "dnfa"
        path = os.path.join(tmp, f"pos_{i}.dot")
        if gen_positive(path, rng, kind):
            handle(path, f"pos_{kind}")

    print("\n================ EXP vs ORACLE SUMMARY ================")
    print(f"checked         : {checked}")
    print(f"  truth Wheeler : {pos}")
    print(f"  truth non-WG  : {checked - pos}")
    print(f"skipped         : {skipped}  (oracle/exp over their caps)")
    print(f"MISMATCHES      : {bad}")
    print(f"anomalies       : {anom}  (timeouts / unexpected output)")
    if bad == 0 and anom == 0:
        print("RESULT: fixed exponential recognizer agrees with the oracle on every decided graph. ✓")
    else:
        print("RESULT: discrepancies found -- see verify/repro_exp/ and messages above.")
        for e in examples[:40]:
            print("  " + e)

    if not args.keep_tmp:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)

    sys.exit(1 if (bad or anom) else 0)


if __name__ == "__main__":
    main()
