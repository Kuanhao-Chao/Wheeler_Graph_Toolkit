#!/usr/bin/env python3
"""
difftest.py -- differential testing of the WGT recognizer against the brute-force oracle.

For each small graph we compute the GROUND-TRUTH verdict with brute_oracle.py and compare it
to the recognizer's verdict in every backend (default SMT, `-s p` permutation, `-f` full-range).
Any disagreement is a bug in the recognizer (or, in principle, the oracle) and is saved as a
minimal-ish reproducer under verify/repro/.

Corpora:
  - random simple labeled digraphs (no self-loops, no duplicate (u,v,label) triples) -- a mix of
    Wheeler and non-Wheeler, which is where negatives/edge interactions live;
  - guaranteed-positive Wheeler graphs from gen_complete_WG.py / gen_d-nfa_WG.py.

All runs use integer labels: recognizer `-i`, oracle `--int`, so label order is unambiguous.

Usage:
  python3 verify/difftest.py --random 3000 --max-n 7 --seed 1
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

# Recognizer binary. Override with WGT_REC (a bare name resolved under recognizer/bin/, or a full
# path) to point the same harness at a historical binary, e.g. WGT_REC=recognizer_buggy.
_rec_env = os.environ.get("WGT_REC")
if _rec_env and os.path.sep in _rec_env:
    REC = _rec_env
else:
    REC = os.path.join(ROOT, "recognizer", "bin", _rec_env or "recognizer_linux")
GEN_COMPLETE = os.path.join(ROOT, "generator", "Random_generator", "gen_complete_WG.py")
GEN_DNFA = os.path.join(ROOT, "generator", "Random_generator", "gen_d-nfa_WG.py")
REPRO = os.path.join(HERE, "repro")

# recognizer backends to test. Each is a list of extra args (always with -i).
MODES = {
    "smt":    ["-i"],                   # default backend = SMT
    "perm":   ["-i", "-s", "p"],        # permutation backend
    "full":   ["-i", "-f"],            # full-range search (always SMT)
    "perm-e": ["-i", "-s", "p", "-e"],  # exhaustive permutation (the -e accept-on-exhaustion path)
    "dl":     ["-i", "-s", "dl"],       # native difference-logic propagator (in isolation, no z3 fallback)
    "lazy":      ["-i", "-s", "lazy"],        # lazy/CEGAR A3 backend, default path (falls back to z3 if undecided)
    "full-lazy": ["-i", "-f", "-s", "lazy"],  # lazy/CEGAR A3 backend, full-range (-f) path
}
# Modes actually run this invocation (default keeps the historical 3; perm-e opt-in via --modes).
DEFAULT_MODES = ["smt", "perm", "full"]


def recognizer_verdict(path, mode_args, timeout=25):
    """Return 1 (WG), 0 (not WG), 'TIMEOUT', or ('ERR', returncode)."""
    try:
        r = subprocess.run([REC, path] + mode_args,
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    rc = r.returncode
    if rc == 1:
        return 1
    if rc in (255, -1):
        return 0
    if rc == 0:
        # The dl pre-solver exits 0 when it cannot decide by propagation alone (a legitimate
        # non-verdict; production falls back to z3). Other backends never return 0.
        return "UNDECIDED"
    return ("ERR", rc)


def oracle_verdict(path, max_n):
    nodes, edges = bo.parse_dot(path)
    if len(nodes) > max_n:
        return None  # undecidable at this cap
    label_rank = bo.rank_labels(edges, int_mode=True)
    return 1 if bo.is_wheeler(nodes, edges, label_rank) else 0


def write_random_dot(path, n, n_labels, n_edges, rng, allow_self=False, allow_dup=False):
    nodes = [f"S{i}" for i in range(1, n + 1)]
    chosen = []          # list, to allow duplicate triples when allow_dup
    seen = set()
    guard = 0
    while len(chosen) < n_edges and guard < n_edges * 40 + 50:
        guard += 1
        u = rng.choice(nodes)
        v = rng.choice(nodes)
        if not allow_self and u == v:
            continue
        lab = rng.randrange(n_labels)
        t = (u, v, lab)
        if not allow_dup and t in seen:
            continue
        seen.add(t)
        chosen.append(t)
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (u, v, lab) in chosen:
            f.write(f"\t{u} -> {v} [ label = {lab} ];\n")
        f.write("}\n")
    return len(chosen)


def gen_positive(path, rng, kind="complete"):
    """Generate a guaranteed-positive WG via the project generators. Returns True on success."""
    n = rng.randint(3, 7)
    L = rng.randint(1, 3)
    root = 1
    maxe = n * L + n - L - root
    mine = n - root
    if maxe < mine:
        return False
    e = rng.randint(mine, maxe)
    gen = GEN_COMPLETE if kind == "complete" else GEN_DNFA
    args = [sys.executable, gen, "-n", str(n), "-e", str(e), "-l", str(L),
            "-r", str(root), "-s", "-o", path]
    if kind == "dnfa":
        args += ["-d", str(rng.randint(1, 3))]
    r = subprocess.run(args, capture_output=True)
    return r.returncode == 0 and os.path.exists(path)


def check_graph(path, max_n, modes):
    """Return (truth, {mode: verdict}, mismatches:list, anomalies:list)."""
    truth = oracle_verdict(path, max_n)
    results = {}
    mismatches = []
    anomalies = []
    if truth is None:
        return None, results, mismatches, anomalies
    for mode in modes:
        v = recognizer_verdict(path, MODES[mode])
        results[mode] = v
        if v in (0, 1):
            if v != truth:
                mismatches.append(mode)
        elif v == "TIMEOUT":
            anomalies.append(f"{mode}:TIMEOUT")
        elif v == "UNDECIDED":
            pass  # legitimate non-verdict (dl pre-solver); not a mismatch, not an anomaly
        else:
            anomalies.append(f"{mode}:{v}")
    return truth, results, mismatches, anomalies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--random", type=int, default=2000, help="number of random graphs")
    ap.add_argument("--positives", type=int, default=500, help="number of guaranteed-positive graphs")
    ap.add_argument("--max-n", type=int, default=7)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--keep-tmp", action="store_true")
    ap.add_argument("--allow-self", action="store_true", help="include self-loops in random graphs")
    ap.add_argument("--allow-dup", action="store_true", help="include duplicate parallel edges")
    ap.add_argument("--dense", action="store_true",
                    help="dense few-label (1-2) near-complete regime: exercises the -f within-group "
                         "A3 block encoding (E_l >> distinct heads/tails). Combine with --allow-dup.")
    ap.add_argument("--modes", default=",".join(DEFAULT_MODES),
                    help="comma list of backends to test (smt,perm,full,perm-e); default smt,perm,full")
    args = ap.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for m in modes:
        if m not in MODES:
            sys.exit(f"unknown mode {m!r}; choose from {list(MODES)}")
    print(f"recognizer  : {REC}")
    print(f"modes       : {modes}\n")

    rng = random.Random(args.seed)
    os.makedirs(REPRO, exist_ok=True)
    tmpdir = os.path.join(HERE, "_difftmp")
    os.makedirs(tmpdir, exist_ok=True)

    n_checked = 0
    n_pos_truth = 0
    n_undecided = 0
    bad = 0   # mismatches
    anom = 0  # timeouts / errors
    # per-mode {false_accept: truth=0 but verdict=1, false_reject: truth=1 but verdict=0}
    fa = {m: 0 for m in modes}
    fr = {m: 0 for m in modes}
    examples = []

    def handle(path, tag):
        nonlocal n_checked, n_pos_truth, n_undecided, bad, anom
        truth, results, mismatches, anomalies = check_graph(path, args.max_n, modes)
        for m in mismatches:
            if truth == 0 and results[m] == 1:
                fa[m] += 1
            elif truth == 1 and results[m] == 0:
                fr[m] += 1
        if truth is None:
            n_undecided += 1
            return
        n_checked += 1
        if truth == 1:
            n_pos_truth += 1
        if mismatches:
            bad += 1
            # save reproducer
            dst = os.path.join(REPRO, f"mismatch_{bad:04d}_{tag}.dot")
            with open(path) as src, open(dst, "w") as out:
                out.write(src.read())
            msg = (f"MISMATCH [{tag}] truth={truth} "
                   f"results={results} modes={mismatches} -> {dst}")
            examples.append(msg)
            print(msg)
        if anomalies:
            anom += 1
            if len(examples) < 60:
                examples.append(f"ANOMALY [{tag}] {anomalies} {path}")

    # --- random simple graphs ---
    for i in range(args.random):
        n = rng.randint(2, args.max_n)
        if args.dense:
            # Few labels + near-complete edge count => large E_l with few distinct heads/tails,
            # so the -f within-group A3 block path fires (and its never-worse guard is satisfied).
            n_labels = rng.randint(1, 2)
            max_simple = n * (n - 1) * n_labels
            hi = max_simple + (n * n_labels if args.allow_dup else 0)
            n_edges = rng.randint(max(1, max_simple // 2), max(1, hi))
        else:
            n_labels = rng.randint(1, 4)
            # edge count from sparse to fairly dense
            max_simple = n * (n - 1) * n_labels
            n_edges = rng.randint(1, max(1, min(max_simple, n * 3)))
        path = os.path.join(tmpdir, f"rand_{i}.dot")
        write_random_dot(path, n, n_labels, n_edges, rng,
                         allow_self=args.allow_self, allow_dup=args.allow_dup)
        handle(path, "rand")

    # --- guaranteed positives ---
    for i in range(args.positives):
        kind = "complete" if (i % 2 == 0) else "dnfa"
        path = os.path.join(tmpdir, f"pos_{i}.dot")
        if gen_positive(path, rng, kind):
            handle(path, f"pos_{kind}")

    print("\n==================== SUMMARY ====================")
    print(f"checked         : {n_checked}")
    print(f"  truth Wheeler : {n_pos_truth}")
    print(f"  truth non-WG  : {n_checked - n_pos_truth}")
    print(f"undecided(>maxn): {n_undecided}")
    print(f"MISMATCHES      : {bad}")
    print(f"anomalies       : {anom} (timeouts / unexpected exit codes)")
    print("per-mode false verdicts (truth vs binary):")
    for m in modes:
        print(f"  {m:7s} : false-accept(nonWG->WG)={fa[m]:4d}   false-reject(WG->nonWG)={fr[m]:4d}")
    if bad == 0 and anom == 0:
        print("RESULT: recognizer agrees with the oracle on every decided graph. ✓")
    else:
        print("RESULT: discrepancies found — see verify/repro/ and messages above.")

    if not args.keep_tmp:
        for f in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, f))
        os.rmdir(tmpdir)

    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
