#!/usr/bin/env python3
"""
run_repair_corpus.py -- comprehensive minimal Wheeler-graph repair benchmark.

For every input graph it runs up to four repair methods, each gated by trie size:
  trie   (repair/wheelerize: maximal split, always Wheeler)     -- any trie
  refine (repair/minimize.refine: fast refine-from-coarse)      -- trie <= --refine-cap
  greedy (repair/minimize.greedy: merge-from-trie)              -- trie <= --greedy-cap
  exact  (repair/minimize.exact: Z3, provably optimal)          -- trie <= --exact-cap
and VERIFIES every produced graph with the 5 invariants (repair/verify_repair). It records
per-method size/edits/wall + verification + the (type, alphabet, size) tags, one CSV row per graph.

Sources (mix for type x alphabet x size coverage):
  --source random : controlled random DAGs over a size ladder, few-label ("DNA-like") and
                    many-label ("AA-like").
  --source revdet : committed real RevDet gene graphs (data/graph/RevDetGraph/), DNA vs protein.
  --source wg     : already-Wheeler baselines (De Bruijn / Trie committed DOTs) -> must be 0-edit.

Run under python3 (z3). Long runs in detached tmux. A per-graph SIGALRM guards pathological cases.
"""

import argparse
import csv
import glob
import os
import random
import signal
import subprocess
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
    rc = subprocess.run([REC, path] + (["-i"] if int_mode else []), capture_output=True).returncode
    return {1: "WG", 255: "nonWG"}.get(rc, f"rc{rc}")


def write_input_dot(edges, path):
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (u, v, l) in edges:
            f.write(f"\t{u} -> {v} [ label = {l} ];\n")
        f.write("}\n")


def gen_random_dag(rng, n, nl, int_mode, prob):
    labs = [str(k) for k in range(nl)] if int_mode else list("abcdefghijklmnopqrst"[:nl])
    return [(f"v{i}", f"v{j}", rng.choice(labs))
            for i in range(n) for j in range(i + 1, n) if rng.random() < prob]


def classify(path, source):
    """Return (type, alphabet)."""
    p = path.lower()
    if source == "random":
        return ("random", "")
    if "revdet" in p:
        return ("RevDet", "protein" if "protein" in p or "/aa" in p or "_aa" in p else "DNA")
    if "debruijn" in p:
        return ("DeBruijn", "protein" if "aa" in p else "DNA")
    if "trie" in p:
        return ("Trie", "protein" if "aa" in p else "DNA")
    return (source, "")


def process(in_dot, int_mode, caps, tmp, ttag, atag):
    nodes, sources, out_adj, edges = dfa.build_graph(in_dot)
    if not edges or not dfa.is_acyclic(nodes, out_adj):
        return None
    rank = bo.rank_labels(edges, int_mode)
    try:
        T = dfa.determinize(sources, out_adj, max_nodes=caps["trie"])
    except RuntimeError:
        return {"skip": "trie_overflow"}

    row = {"graph": os.path.basename(in_dot), "source": ttag if ttag in ("random",) else None,
           "type": ttag, "alphabet": atag, "in_nodes": len(nodes), "in_edges": len(edges),
           "det": int(dfa.is_deterministic(out_adj)), "trie_nodes": T.n,
           "verdict_in": recognizer_verdict(in_dot, int_mode)}

    # run each method (gated by trie size), verify every output
    methods = [("trie", caps["trie"]), ("refine", caps["refine"]),
               ("greedy", caps["greedy"]), ("exact", caps["exact"])]
    for name, cap in methods:
        row[f"{name}_size"] = row[f"{name}_edits"] = row[f"t_{name}"] = row[f"verify_{name}"] = ""
        if T.n > cap:
            continue
        t0 = time.time()
        if name == "trie":
            block = list(range(T.n))
            sz = T.n
            edt = T.n - dfa.origin_classes(T)[1]
        else:
            rsz = mz.repair(T, rank, "size", name)
            red = mz.repair(T, rank, "edits", name)
            block = rsz["block_of"]
            sz = rsz["nodes"]
            edt = red["edits"]
        dt = time.time() - t0
        out = os.path.join(tmp, f"{name}.dot")
        mz.write_repair(T, block, out)
        ok, _ = vr.verify(in_dot, out, int_mode)
        # also verify the min-edits output for non-trie methods
        if name not in ("trie",):
            oute = os.path.join(tmp, f"{name}_e.dot")
            mz.write_repair(T, red["block_of"], oute)
            ok2, _ = vr.verify(in_dot, oute, int_mode)
            ok = ok and ok2
        row[f"{name}_size"] = sz
        row[f"{name}_edits"] = edt
        row[f"t_{name}"] = round(dt, 3)
        row[f"verify_{name}"] = int(ok)

    # consistency: heuristics never below exact (when exact ran)
    row["consistent"] = 1
    if row["exact_size"] != "":
        for h in ("refine", "greedy"):
            if row[f"{h}_size"] != "" and row[f"{h}_size"] < row["exact_size"]:
                row["consistent"] = 0
    return row


COLS = ["graph", "type", "alphabet", "in_nodes", "in_edges", "det", "verdict_in", "trie_nodes",
        "trie_size", "refine_size", "greedy_size", "exact_size",
        "refine_edits", "greedy_edits", "exact_edits",
        "t_trie", "t_refine", "t_greedy", "t_exact",
        "verify_trie", "verify_refine", "verify_greedy", "verify_exact", "consistent"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["random", "revdet", "wg"], required=True)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--int", action="store_true")
    ap.add_argument("--trie-cap", type=int, default=6000)
    ap.add_argument("--refine-cap", type=int, default=6000)
    ap.add_argument("--greedy-cap", type=int, default=70)   # greedy is the slow method (cross-check only)
    ap.add_argument("--exact-cap", type=int, default=22)
    ap.add_argument("--per-graph-timeout", type=int, default=180)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    int_mode = args.int
    caps = {"trie": args.trie_cap, "refine": args.refine_cap,
            "greedy": args.greedy_cap, "exact": args.exact_cap}
    import tempfile
    tmp = tempfile.mkdtemp(prefix="repaircorpus_", dir=HERE)
    signal.signal(signal.SIGALRM, _alarm)

    work = []   # list of (path, type_tag, alphabet_tag, only_nonwg)
    if args.source == "random":
        rng = random.Random(args.seed)
        sizes = [5, 7, 9, 12, 16, 22, 30, 42, 60, 85, 120]
        i = 0
        while len(work) < args.n:
            n = rng.choice(sizes)
            many = rng.random() < 0.5
            nl = rng.randint(8, 16) if many else rng.randint(1, 3)
            prob = 0.5 if not many else 0.30
            edges = gen_random_dag(rng, n, nl, int_mode, prob)
            i += 1
            if not edges:
                continue
            p = os.path.join(tmp, f"rand_{i}.dot")
            write_input_dot(edges, p)
            work.append((p, "random", "many-label" if many else "few-label", False))
            if i > args.n * 6:
                break
    elif args.source == "revdet":
        files = glob.glob(os.path.join(ROOT, "data/graph/RevDetGraph/**/*.dot"), recursive=True)
        random.Random(args.seed).shuffle(files)
        for f in files:
            t, a = classify(f, "revdet")
            work.append((f, t, a, True))
    else:  # wg baselines (already-Wheeler -> 0-edit no-op)
        pats = ["data/graph/**/DeBruijn*/**/*.dot", "data/graph/**/[Tt]rie*/**/*.dot"]
        files = []
        for pat in pats:
            files += glob.glob(os.path.join(ROOT, pat), recursive=True)
        random.Random(args.seed).shuffle(files)
        for f in files:
            t, a = classify(f, "wg")
            work.append((f, t, a, False))

    rows, nfail, ncons, processed = [], 0, 0, 0
    t_start = time.time()
    for (p, t, a, only_nonwg) in work:
        if processed >= args.n:
            break
        try:
            signal.alarm(args.per_graph_timeout)
            r = process(p, int_mode, caps, tmp, t, a)
            signal.alarm(0)
        except _Timeout:
            print(f"  TIMEOUT {os.path.basename(p)}", flush=True)
            continue
        except Exception as e:
            print(f"  ERROR {os.path.basename(p)}: {e}", flush=True)
            continue
        if r is None or "skip" in r:
            continue
        if only_nonwg and r["verdict_in"] != "nonWG":
            continue
        rows.append(r)
        processed += 1
        # a verify failure on ANY method that ran is a hard failure
        vfails = [m for m in ("trie", "refine", "greedy", "exact")
                  if r[f"verify_{m}"] == 0]
        if vfails:
            nfail += 1
            print(f"  *** VERIFY FAIL {r['graph']}: {vfails}", flush=True)
        if not r["consistent"]:
            ncons += 1
            print(f"  *** INCONSISTENT (heuristic<exact): {r['graph']}", flush=True)
        if processed % 25 == 0:
            print(f"  [{processed}] {r['graph']} type={r['type']} in={r['in_nodes']} "
                  f"trie={r['trie_nodes']} refine_size={r['refine_size']} "
                  f"(elapsed {time.time()-t_start:.0f}s)", flush=True)

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})

    print(f"\nDONE: {processed} graphs -> {args.out}")
    print(f"  verification failures: {nfail}   consistency failures: {ncons}")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
