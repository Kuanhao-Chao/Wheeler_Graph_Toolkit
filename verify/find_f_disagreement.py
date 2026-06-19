#!/usr/bin/env python3
"""
find_f_disagreement.py -- search for a SMALL graph where -f (full_range_search) false-rejects.

We established (witness-order validation on an n=800 graph) that -f false-rejects some Wheeler
graphs. To root-cause it we want a minimal reproducer. Strategy: in the n<=9 oracle-decidable
regime, sweep (nodes, labels, density), generate random graphs, and report any graph where the
brute oracle says WHEELER but recognizer -f says NOT WHEELER. The oracle is ground truth, so such a
graph is a definitive -f false-reject -- small enough to dump and diff its SMT encoding.

Uses two graph sources:
  * gen_complete_WG.py (guaranteed-Wheeler by construction; -f rejecting one is a bug), and
  * fully random graphs (mixed), filtered to oracle==WHEELER.

Run: python3 verify/find_f_disagreement.py --tries 4000 --seed 1
"""

import argparse
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import brute_oracle as bo  # noqa: E402
from difftest import write_random_dot  # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
GEN = os.path.join(ROOT, "generator", "Random_generator", "gen_complete_WG.py")


def f_verdict(path):
    """recognizer -f -i: return 1 (WG), 0 (not WG), or None (timeout/err)."""
    try:
        r = subprocess.run([REC, path, "-i", "-f"], capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode == 1:
        return 1
    if r.returncode in (255, -1):
        return 0
    return None


def oracle_verdict(path):
    nodes, edges = bo.parse_dot(path)
    if len(nodes) > 9:
        return None
    rank = bo.rank_labels(edges, int_mode=True)
    return 1 if bo.is_wheeler(nodes, edges, rank) else 0


def gen_complete(path, n, e, l, rng):
    seed_args = [sys.executable, GEN, "-n", str(n), "-e", str(e), "-l", str(l), "-r", "1", "-s",
                 "-o", path]
    r = subprocess.run(seed_args, capture_output=True)
    return r.returncode == 0 and os.path.exists(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--keep", type=int, default=5, help="how many reproducers to keep")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    tmp = os.path.join(HERE, "_ftmp")
    os.makedirs(tmp, exist_ok=True)
    out = os.path.join(HERE, "repro_f")
    os.makedirs(out, exist_ok=True)

    found = []
    checked = 0
    for i in range(args.tries):
        n = rng.randint(6, 9)
        # many labels + high density (the regime where -f diverged)
        l = rng.randint(2, max(2, n))
        path = os.path.join(tmp, f"g{i}.dot")
        use_gen = (i % 2 == 0)
        if use_gen:
            maxe = n * l + n - l - 1
            mine = n - 1
            if maxe < mine:
                continue
            e = rng.randint(max(mine, 1), maxe)
            if not gen_complete(path, n, e, l, rng):
                continue
        else:
            max_simple = n * (n - 1) * l
            e = rng.randint(n, max(n, min(max_simple, n * 4)))
            write_random_dot(path, n, l, e, rng, allow_self=True, allow_dup=True)

        truth = oracle_verdict(path)
        if truth != 1:           # only care about graphs that ARE Wheeler
            continue
        checked += 1
        fv = f_verdict(path)
        if fv == 0:              # oracle says WG, -f says NOT WG => -f false-reject
            nodes, edges = bo.parse_dot(path)
            dst = os.path.join(out, f"frej_{len(found):03d}_n{len(nodes)}_e{len(edges)}_l{len({x[2] for x in edges})}.dot")
            with open(path) as s, open(dst, "w") as d:
                d.write(s.read())
            found.append((len(nodes), len(edges), dst))
            print(f"FALSE-REJECT: oracle=WG -f=notWG  n={len(nodes)} e={len(edges)} -> {dst}")
            if len(found) >= args.keep:
                break

    print(f"\nchecked {checked} Wheeler graphs; found {len(found)} -f false-rejects")
    if found:
        found.sort()
        print(f"smallest reproducer: n={found[0][0]} e={found[0][1]} -> {found[0][2]}")
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    sys.exit(0 if found else 3)


if __name__ == "__main__":
    main()
