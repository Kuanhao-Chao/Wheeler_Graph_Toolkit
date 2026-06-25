#!/usr/bin/env python3
"""
run_repair_corpus.py -- minimal Wheeler-graph repair experiment over a corpus.

For each non-Wheeler DAG it records the repaired size under three methods and verifies every
output with the 5 invariants (repair/verify_repair.py):
  * trie       (existing repair/wheelerize.py: maximal split, always Wheeler)
  * greedy     (repair/minimize.greedy: within-gate merge from the trie)  -- min-size & min-edits
  * exact (Z3) (repair/minimize.exact) when the trie is small enough      -- provable optimum

Sources:
  --source random : random labeled DAGs (n in [--nmin,--nmax], 1..3 labels)
  --source revdet : committed non-WG RevDet gene graphs under data/graph/RevDetGraph/

Writes one CSV row per processed graph. Graphs whose trie exceeds --trie-cap are skipped (greedy
cost grows with trie size); a per-graph SIGALRM timeout guards pathological cases.

Run under python3 (z3). Intended for detached tmux for the full corpus.
"""

import argparse
import csv
import glob
import os
import random
import signal
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, os.path.join(ROOT, "repair"))
import brute_oracle as bo  # noqa: E402
import dfa  # noqa: E402
import minimize as mz  # noqa: E402
import verify_repair as vr  # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def recognizer_verdict(path, int_mode):
    import subprocess
    rc = subprocess.run([REC, path] + (["-i"] if int_mode else []), capture_output=True).returncode
    return {1: "WG", 255: "nonWG"}.get(rc, f"rc{rc}")


def write_input_dot(edges, path):
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (u, v, l) in edges:
            f.write(f"\t{u} -> {v} [ label = {l} ];\n")
        f.write("}\n")


def gen_random_dag(rng, n, nl, int_mode, prob=0.45):
    labs = [str(k) for k in range(nl)] if int_mode else list("abcdefghij"[:nl])
    return [(f"v{i}", f"v{j}", rng.choice(labs))
            for i in range(n) for j in range(i + 1, n) if rng.random() < prob]


def process(in_dot, int_mode, trie_cap, exact_cap, tmp):
    """Return a result dict, or None to skip."""
    nodes, sources, out_adj, edges = dfa.build_graph(in_dot)
    if not edges or not dfa.is_acyclic(nodes, out_adj):
        return None
    label_rank = bo.rank_labels(edges, int_mode)
    try:
        T = dfa.determinize(sources, out_adj, max_nodes=trie_cap * 4)
    except RuntimeError:
        return {"skip": "trie_overflow"}
    if T.n > trie_cap:
        return {"skip": f"trie>{trie_cap}"}

    row = {"graph": os.path.basename(in_dot), "in_nodes": len(nodes), "in_edges": len(edges),
           "det": int(dfa.is_deterministic(out_adj)), "trie_nodes": T.n,
           "verdict_in": recognizer_verdict(in_dot, int_mode)}

    t0 = time.time()
    gs = mz.greedy(T, label_rank, "size", int_mode)
    ge = mz.greedy(T, label_rank, "edits", int_mode)
    row["t_greedy"] = round(time.time() - t0, 2)
    row["greedy_size"] = gs["nodes"]
    row["greedy_edits_nodes"] = ge["nodes"]
    row["greedy_edits"] = ge["edits"]

    row["exact_size"] = ""
    row["exact_edits"] = ""
    row["t_exact"] = ""
    if T.n <= exact_cap:
        t0 = time.time()
        rs = mz.exact(T, label_rank, "size", timeout_ms=8000)
        re = mz.exact(T, label_rank, "edits", timeout_ms=8000)
        row["t_exact"] = round(time.time() - t0, 2)
        row["exact_size"] = rs["nodes"]
        row["exact_edits"] = re["nodes"]

    # verify trie + both greedy outputs with the 5 invariants
    trie_dot = os.path.join(tmp, "trie.dot")
    gs_dot = os.path.join(tmp, "gs.dot")
    ge_dot = os.path.join(tmp, "ge.dot")
    mz.write_repair(T, list(range(T.n)), trie_dot)
    mz.write_repair(T, gs["block_of"], gs_dot)
    mz.write_repair(T, ge["block_of"], ge_dot)
    ok_t, _ = vr.verify(in_dot, trie_dot, int_mode)
    ok_s, _ = vr.verify(in_dot, gs_dot, int_mode)
    ok_e, _ = vr.verify(in_dot, ge_dot, int_mode)
    row["verify_trie"] = int(ok_t)
    row["verify_gsize"] = int(ok_s)
    row["verify_gedits"] = int(ok_e)
    row["verify_ok"] = int(ok_t and ok_s and ok_e)
    # consistency vs exact (greedy must never beat the optimum)
    row["consistent"] = 1
    if row["exact_size"] != "" and (gs["nodes"] < row["exact_size"] or ge["nodes"] < row["exact_edits"]):
        row["consistent"] = 0
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["random", "revdet"], required=True)
    ap.add_argument("--n", type=int, default=200, help="graphs to process")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--nmin", type=int, default=3)
    ap.add_argument("--nmax", type=int, default=9)
    ap.add_argument("--int", action="store_true")
    ap.add_argument("--trie-cap", type=int, default=80)
    ap.add_argument("--exact-cap", type=int, default=20)
    ap.add_argument("--per-graph-timeout", type=int, default=90)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    int_mode = args.int  # RevDet gene graphs use string labels (A/C/G/T, amino acids)
    # UNIQUE per-run scratch dir: concurrent runs must NOT share trie/gs/ge.dot (clobbering them
    # between write and verify produces spurious verification failures).
    import tempfile
    tmp = tempfile.mkdtemp(prefix="repair_", dir=HERE)
    signal.signal(signal.SIGALRM, _alarm)

    # build the work list of input DOT paths
    work = []
    if args.source == "random":
        rng = random.Random(args.seed)
        for i in range(args.n * 3):   # over-generate; many will be trivial/WG
            n = rng.randint(args.nmin, args.nmax)
            nl = rng.randint(1, 3)
            edges = gen_random_dag(rng, n, nl, int_mode)
            if not edges:
                continue
            p = os.path.join(tmp, f"rand_{i}.dot")
            write_input_dot(edges, p)
            work.append(p)
            if len(work) >= args.n:
                break
    else:
        files = sorted(glob.glob(os.path.join(ROOT, "data/graph/RevDetGraph/**/*.dot"),
                                 recursive=True))
        rng = random.Random(args.seed)
        rng.shuffle(files)
        work = files  # filtered (non-WG, DAG, trie<=cap) inside process()

    rows = []
    nfail = 0
    ncons = 0
    processed = 0
    t_start = time.time()
    for p in work:
        if processed >= args.n:
            break
        try:
            signal.alarm(args.per_graph_timeout)
            r = process(p, int_mode, args.trie_cap, args.exact_cap, tmp)
            signal.alarm(0)
        except _Timeout:
            print(f"  TIMEOUT {os.path.basename(p)}", flush=True)
            continue
        except Exception as e:
            print(f"  ERROR {os.path.basename(p)}: {e}", flush=True)
            continue
        if r is None or "skip" in r:
            continue
        if args.source == "revdet" and r["verdict_in"] != "nonWG":
            continue  # only repair genuinely non-WG inputs
        rows.append(r)
        processed += 1
        if not r["verify_ok"]:
            nfail += 1
            print(f"  *** VERIFY FAIL: {r['graph']}", flush=True)
        if not r["consistent"]:
            ncons += 1
            print(f"  *** INCONSISTENT (greedy<exact): {r['graph']}", flush=True)
        if processed % 10 == 0:
            print(f"  [{processed}] {r['graph']}: in={r['in_nodes']} trie={r['trie_nodes']} "
                  f"gsize={r['greedy_size']} gedits={r['greedy_edits']} "
                  f"t={r['t_greedy']}s  (elapsed {time.time()-t_start:.0f}s)", flush=True)

    cols = ["graph", "in_nodes", "in_edges", "det", "verdict_in", "trie_nodes",
            "greedy_size", "greedy_edits_nodes", "greedy_edits",
            "exact_size", "exact_edits", "t_greedy", "t_exact",
            "verify_trie", "verify_gsize", "verify_gedits", "verify_ok", "consistent"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

    print(f"\nDONE: processed {processed} non-WG graphs -> {args.out}")
    print(f"  verification failures: {nfail}")
    print(f"  consistency failures (greedy<exact): {ncons}")
    if rows:
        red = [r["trie_nodes"] / r["greedy_size"] for r in rows if r["greedy_size"]]
        red.sort()
        print(f"  trie/greedy-size reduction: median {red[len(red)//2]:.2f}x  "
              f"max {red[-1]:.2f}x")
        eds = sorted(r["greedy_edits"] for r in rows)
        print(f"  greedy min-edits (node duplications): median {eds[len(eds)//2]}  max {eds[-1]}")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
