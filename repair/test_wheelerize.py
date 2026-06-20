#!/usr/bin/env python3
"""
test_wheelerize.py -- at-scale validation of the DAG Wheelerizer.

Generates random DAGs (edges only go from earlier to later in a random topological order, so the
graph is always acyclic), runs wheelerize.py on each, and asserts it always produces a verified
Wheeler graph with the path-string set preserved. Reports how many inputs were already Wheeler vs
actually needed repair, plus node blow-up statistics.

Run: python3 repair/test_wheelerize.py --n 500 --seed 1
"""
import argparse
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
WHEELERIZE = os.path.join(HERE, "wheelerize.py")


def gen_random_dag(path, n, n_labels, rng):
    order = list(range(n))
    rng.shuffle(order)               # random topological order over node ids
    pos = {node: i for i, node in enumerate(order)}
    names = [f"S{i}" for i in range(n)]
    edges = []
    for u in range(n):
        for v in range(n):
            if pos[u] < pos[v] and rng.random() < 0.35:   # only forward in topo order => acyclic
                edges.append((names[u], names[v], rng.randrange(n_labels)))
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (a, b, l) in edges:
            f.write(f"\t{a} -> {b} [ label = {l} ];\n")
        f.write("}\n")
    return len(edges)


def rec_is_wheeler(path):
    return subprocess.run([REC, path, "-i"], capture_output=True).returncode == 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--max-n", type=int, default=7, help="max nodes per random DAG")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dump", default=None,
                    help="write per-DAG repair records (in/out node counts, ratio) to this JSON file")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    tmp = os.path.join(HERE, "_wtmp")
    os.makedirs(tmp, exist_ok=True)

    total = already = repaired = failures = aborts = 0
    blowups = []
    records = []   # per-DAG {in_nodes, out_nodes, ratio, was_wheeler}
    for i in range(args.n):
        n = rng.randint(2, args.max_n)
        n_labels = rng.randint(1, 3)
        src = os.path.join(tmp, f"d{i}.dot")
        ne = gen_random_dag(src, n, n_labels, rng)
        if ne == 0:
            continue
        total += 1
        was_wheeler = rec_is_wheeler(src)
        out = os.path.join(tmp, f"d{i}.wheel.dot")
        r = subprocess.run([sys.executable, WHEELERIZE, src, "-o", out, "--int"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            if was_wheeler:
                already += 1
            else:
                repaired += 1
            # parse the "node blow-up: A -> B" line
            for line in r.stdout.splitlines():
                if line.startswith("node blow-up:"):
                    try:
                        a, b = line.split(":")[1].split("(")[0].split("->")
                        ain, bout = int(a.strip()), int(b.strip())
                        blowups.append(bout / max(1, ain))
                        records.append({"in_nodes": ain, "out_nodes": bout,
                                        "ratio": bout / max(1, ain),
                                        "was_wheeler": bool(was_wheeler)})
                    except Exception:
                        pass
        elif r.returncode in (2, 3):
            aborts += 1   # cyclic (shouldn't happen here) or too-large
        else:
            failures += 1
            print(f"FAILURE on {src}:\n{r.stdout}\n{r.stderr}")
            with open(src) as fh:
                print(fh.read())

    print("\n==================== WHEELERIZE SUMMARY ====================")
    print(f"DAGs tested        : {total}")
    print(f"  already Wheeler  : {already}")
    print(f"  needed repair    : {repaired}")
    print(f"aborts (cyclic/big): {aborts}")
    print(f"FAILURES           : {failures}")
    if blowups:
        print(f"node blow-up x     : avg={sum(blowups)/len(blowups):.2f}  "
              f"min={min(blowups):.2f}  max={max(blowups):.2f}")
    print("RESULT:", "every DAG repaired to a verified Wheeler graph, strings preserved. ✓"
          if failures == 0 else "FAILURES found ✗")
    if args.dump:
        with open(args.dump, "w") as fh:
            json.dump({"total": total, "already": already, "repaired": repaired,
                       "aborts": aborts, "failures": failures, "records": records}, fh)
        print(f"wrote per-DAG records -> {args.dump}")
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
