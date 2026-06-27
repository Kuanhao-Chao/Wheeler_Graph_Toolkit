"""Phase C: where does RevDet -> minimal-repair break? (the path-string trie blow-up, on yeast)

For each yeast block at several (a = #sequences, l = #columns), build the RevDet graph, determinize to
the path-string trie (the dominant cost), and repair; record the trie size, repaired size, wall, and a
divergence proxy (mean pairwise % identity). The trie blows up exponentially with divergence × #seqs;
this maps the practical ceiling. Run under python3.

  python3 benchmark/compact_index/limit.py --out benchmark/compact_index/data/limit_yeast.csv
"""
import argparse
import csv
import glob
import itertools
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "repair"))
import dfa                          # noqa: E402
import minimize as mz              # noqa: E402
import brute_oracle as bo          # noqa: E402
from pipeline import revdet_to_index as r2i   # noqa: E402
from index import faithful as fa   # noqa: E402  (read_fasta)


def mean_identity(seqs, l):
    """Mean pairwise % identity over aligned columns (first l cols), ignoring all-gap columns."""
    rows = [s[:l] for s in seqs]
    if len(rows) < 2:
        return 1.0
    width = max(len(r) for r in rows)
    rows = [r.ljust(width, "-") for r in rows]
    sims = []
    for a, b in itertools.combinations(rows, 2):
        same = tot = 0
        for x, y in zip(a, b):
            if x == "-" and y == "-":
                continue
            tot += 1
            same += (x == y)
        if tot:
            sims.append(same / tot)
    return round(statistics.mean(sims), 4) if sims else 1.0


def probe(fasta, l, a, work, trie_cap, timeout_s=60):
    seqs = [s for _id, s in fa.read_fasta(fasta)][:a]
    if len(seqs) < 2:
        return None
    stem = os.path.splitext(os.path.basename(fasta))[0]
    rd = r2i.build_revdet_dot(fasta, l, a, os.path.join(work, f"{stem}.a{a}.l{l}.revdet.dot"))
    nodes, sources, out_adj, edges = dfa.build_graph(rd)
    row = {"block": os.path.basename(fasta), "a": len(seqs), "l": l,
           "cols": max(len(s[:l]) for s in seqs), "identity": mean_identity(seqs, l),
           "revdet_nodes": len(nodes), "revdet_edges": len(edges)}
    t0 = time.time()
    try:
        T = dfa.determinize(sources, out_adj, max_nodes=trie_cap)
        row["trie_nodes"] = T.n
        row["det_s"] = round(time.time() - t0, 3)
        if T.n <= 5000 and (time.time() - t0) < timeout_s:
            t1 = time.time()
            r = mz.refine(T, bo.rank_labels(edges, False), mode="size")
            row["rep_nodes"] = r["nodes"]; row["repair_s"] = round(time.time() - t1, 3)
        row["blowup"] = False
    except RuntimeError:
        row["trie_nodes"] = None; row["blowup"] = True; row["det_s"] = round(time.time() - t0, 3)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fastadir", default=os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta"))
    ap.add_argument("--blocks", type=int, default=40)
    ap.add_argument("--avals", default="2,3,4,5,7")
    ap.add_argument("--lvals", default="20,40,80,160")
    ap.add_argument("--trie-cap", type=int, default=200000)
    ap.add_argument("--work", default="/tmp/compact_limit")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data", "limit_yeast.csv"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True); os.makedirs(os.path.dirname(args.out), exist_ok=True)
    avals = [int(x) for x in args.avals.split(",")]
    lvals = [int(x) for x in args.lvals.split(",")]
    fastas = sorted(glob.glob(os.path.join(args.fastadir, "*.fa")))[:args.blocks]
    rows = []
    for fa_path in fastas:
        for a in avals:
            for l in lvals:
                try:
                    r = probe(fa_path, l, a, args.work, args.trie_cap)
                except Exception as ex:  # noqa: BLE001
                    r = {"block": os.path.basename(fa_path), "a": a, "l": l, "err": str(ex)[:80]}
                if r:
                    rows.append(r)
    cols = ["block", "a", "l", "cols", "identity", "revdet_nodes", "revdet_edges",
            "trie_nodes", "rep_nodes", "blowup", "det_s", "repair_s", "err"]
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in rows:
            w.writerow(r)
    # summary: trie size vs divergence; the repairable ceiling
    ok = [r for r in rows if r.get("trie_nodes")]
    rep = [r for r in rows if r.get("rep_nodes")]
    print(f"probes={len(rows)}  determinized={len(ok)}  repaired={len(rep)}  "
          f"blowups={sum(1 for r in rows if r.get('blowup'))}")
    if ok:
        big = max(ok, key=lambda r: r["trie_nodes"])
        print(f"  largest trie seen: {big['trie_nodes']} (a={big['a']} l={big['l']} "
              f"cols={big['cols']} identity={big['identity']} revdet={big['revdet_nodes']}n)")
        # trie growth: bin by identity
        for lo, hi in [(0.0, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.01)]:
            b = [r["trie_nodes"] for r in ok if lo <= r["identity"] < hi]
            if b:
                print(f"  identity [{lo:.2f},{hi:.2f}): median trie={int(statistics.median(b))} "
                      f"max={max(b)} (n={len(b)})")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
