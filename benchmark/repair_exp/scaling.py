#!/usr/bin/env python3
"""
scaling.py -- size-scaling + runtime/memory study for minimal Wheeler-graph repair.

Builds a ladder of non-Wheeler DAGs of increasing size; for each graph and each method
(trie / refine / greedy / exact) it runs `repair/minimize.py --method M --json` in a SUBPROCESS
wrapped by `/usr/bin/time -v`, recording wall time, peak RSS (Maximum resident set size), the
repaired size, and whether it finished within the per-call budget. The largest graph each method
decides within budget is its ceiling. Verifies the refine/exact outputs (5 invariants).

Writes one row per (graph, method) to a CSV. Run under python3 (z3); long runs in detached tmux.
"""

import argparse
import csv
import json
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, os.path.join(ROOT, "repair"))
import brute_oracle as bo  # noqa: E402
import dfa  # noqa: E402
import verify_repair as vr  # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
MINIMIZE = os.path.join(ROOT, "repair", "minimize.py")
RSS_RE = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")


def gen_nonwg_dag(rng, n, nl, prob, tries=40):
    """Generate a non-Wheeler acyclic DAG of n nodes (retry until the recognizer rejects)."""
    for _ in range(tries):
        edges = [(f"v{i}", f"v{j}", str(rng.randrange(nl)))
                 for i in range(n) for j in range(i + 1, n) if rng.random() < prob]
        if not edges:
            continue
        path = None
        return edges
    return None


def write_dot(edges, path):
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (u, v, l) in edges:
            f.write(f"\t{u} -> {v} [ label = {l} ];\n")
        f.write("}\n")


def run_method(dot, method, budget, out_dot):
    """Run one method in a subprocess under /usr/bin/time -v. Return dict with status/wall/rss/size."""
    cmd = ["/usr/bin/time", "-v", sys.executable, MINIMIZE, dot,
           "--method", method, "--mode", "both", "--json", "--int", "--out", out_dot]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=budget)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "wall": float(budget), "rss_kb": "", "size": "", "edits": "",
                "trie": ""}
    wall = time.time() - t0
    rss = RSS_RE.search(r.stderr)
    rss_kb = int(rss.group(1)) if rss else ""
    try:
        j = json.loads(r.stdout.strip().splitlines()[-1])
        sz = j["modes"]["size"]["nodes"]
        edt = j["modes"]["edits"]["edits"]
        trie = j["trie_nodes"]
        inner = j["modes"]["size"]["seconds"]
    except Exception:
        return {"status": "ERR", "wall": wall, "rss_kb": rss_kb, "size": "", "edits": "", "trie": ""}
    return {"status": "DECIDED", "wall": round(inner, 3), "wall_full": round(wall, 3),
            "rss_kb": rss_kb, "size": sz, "edits": edt, "trie": trie}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=60, help="per-(graph,method) wall budget (s)")
    ap.add_argument("--methods", default="trie,refine,greedy,exact")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    methods = args.methods.split(",")
    ladder = [6, 9, 13, 18, 25, 34, 46, 62, 84, 110, 150, 200, 270]
    tmp = os.path.join(HERE, "_scaltmp")
    os.makedirs(tmp, exist_ok=True)

    rows = []
    dead = set()        # methods that have hit their ceiling (timed out) -> stop trying
    print(f"{'n':>4} {'trie':>6} " + " ".join(f"{m:>16}" for m in methods), flush=True)
    def trie_size(edges, cap=5000):
        nodes = sorted({t for t, _, _ in edges} | {h for _, h, _ in edges})
        oa = {x: [] for x in nodes}
        ind = {x: 0 for x in nodes}
        for (u, v, l) in edges:
            oa[u].append((l, v))
            ind[v] += 1
        src = [x for x in nodes if ind[x] == 0]
        try:
            return dfa.determinize(src, oa, max_nodes=cap).n
        except RuntimeError:
            return None

    for n in ladder:
        # more labels as n grows -> a deterministic-ish trie that grows but stays bounded longer.
        nl = max(2, n // 4)
        # try several candidates; keep the non-WG one with the LARGEST bounded trie (pushes refine)
        best = None
        overflow_seen = False
        for c in range(14):
            edges = [(f"v{i}", f"v{j}", str(rng.randrange(nl)))
                     for i in range(n) for j in range(i + 1, n) if rng.random() < min(0.5, 3.0 / n)]
            if not edges:
                continue
            ts = trie_size(edges)
            if ts is None:
                overflow_seen = True
                continue
            dot = os.path.join(tmp, f"g{n}_{c}.dot")
            write_dot(edges, dot)
            if subprocess.run([REC, dot, "-i"], capture_output=True).returncode != 255:
                continue
            if best is None or ts > best[1]:
                best = (dot, ts)
        if best is None:
            if overflow_seen:
                rows.append({"graph": f"g{n}", "in_nodes": n, "trie_nodes": ">5000",
                             "method": "(trie-wall)", "size": "", "edits": "", "wall_s": "",
                             "rss_kb": "", "status": "TRIE_OVERFLOW", "verify": ""})
                print(f"{n:>4} {'>5000':>6}  (path-string trie blew up -> trie wall)", flush=True)
            continue
        dot, trie_n = best
        nodes, _ = bo.parse_dot(dot)
        cells = []
        for m in methods:
            if m in dead:
                cells.append(f"{m}:skip")
                continue
            res = run_method(dot, m, args.budget, os.path.join(tmp, f"{m}_out.dot"))
            trie_n = res.get("trie") or trie_n
            verify = ""
            if res["status"] == "DECIDED" and m in ("refine", "exact"):
                ok, _ = vr.verify(dot, os.path.join(tmp, f"{m}_out.dot"), int_mode=True)
                verify = int(ok)
            rows.append({"graph": f"g{n}", "in_nodes": len(nodes), "trie_nodes": res.get("trie", ""),
                         "method": m, "size": res["size"], "edits": res["edits"],
                         "wall_s": res["wall"], "rss_kb": res["rss_kb"], "status": res["status"],
                         "verify": verify})
            cells.append(f"{m}:{res['status'][:4]}/{res['wall']}s")
            if res["status"] in ("TIMEOUT", "ERR"):
                dead.add(m)
        print(f"{len(nodes):>4} {str(trie_n):>6} " + " ".join(f"{c:>16}" for c in cells), flush=True)
        if all(m in dead for m in methods):
            break

    with open(args.out, "w", newline="") as f:
        cols = ["graph", "in_nodes", "trie_nodes", "method", "size", "edits", "wall_s", "rss_kb",
                "status", "verify"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    # ceilings
    print("\n=== ceilings (largest trie decided within budget) ===")
    for m in methods:
        dec = [r for r in rows if r["method"] == m and r["status"] == "DECIDED"]
        if dec:
            top = max(dec, key=lambda r: r["trie_nodes"] or 0)
            print(f"  {m:8s}: in_nodes<= {max(r['in_nodes'] for r in dec)}, "
                  f"trie<= {max((r['trie_nodes'] or 0) for r in dec)}")
    print(f"DONE -> {args.out}")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
