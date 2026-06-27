"""Phase F: three-way compactness on yeast -- De Bruijn vs deterministic min-repair vs Wheeler-NFA repair.

Per yeast block: De Bruijn(k=4) nodes/edges; deterministic RevDet repair (refine min-size, with a
fail-fast trie cap); and the trie-free incremental Wheeler-NFA repair (repair/wnfa.py). Reports the size
comparison, WNFA convergence (vs determinization fallback), nondeterminism, and whether WNFA succeeds on
blocks where the deterministic repair's trie blows up. Run under python3.

  python3 benchmark/compact_index/measure_wnfa.py --limit 40 -a 2 -l 40 --out .../data/compact_wnfa_a2.csv
"""
import argparse
import csv
import glob
import os
import re
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "repair"))
import dfa                       # noqa: E402
import minimize as mz           # noqa: E402
import brute_oracle as bo       # noqa: E402
import wnfa                      # noqa: E402
from pipeline import msa_to_index as m2i      # noqa: E402
from pipeline import revdet_to_index as r2i   # noqa: E402

PY_BIO = r2i.PY_BIO
_ER = re.compile(r"(\w+)\s*->\s*(\w+)\s*\[")


def count_dot(path):
    nodes, e = set(), 0
    for line in open(path):
        m = _ER.search(line.replace(" ", "")) or _ER.search(line)
        if m:
            nodes.update((m.group(1), m.group(2))); e += 1
    return len(nodes), e


def measure(fa, l, a, work, trie_cap=8000, wnfa_rounds=600):
    row = {"block": os.path.basename(fa), "l": l, "a": a}
    # De Bruijn k=4
    try:
        dbdot = os.path.join(work, "db.dot")
        m2i.build_dot(fa, 4, l, a, dbdot, py=PY_BIO)
        row["db4_nodes"], row["db4_edges"] = count_dot(dbdot)
    except Exception as ex:  # noqa: BLE001
        row["db4_nodes"] = None; row["db_err"] = str(ex)[:60]
    # RevDet
    rd = r2i.build_revdet_dot(fa, l, a, os.path.join(work, "rd.dot"))
    nodes, sources, out_adj, edges = dfa.build_graph(rd)
    row["revdet_nodes"], row["revdet_edges"] = len(nodes), len(edges)
    lr = bo.rank_labels(edges, False)
    # deterministic repair (fail-fast trie cap)
    t0 = time.time()
    try:
        T = dfa.determinize(sources, out_adj, max_nodes=trie_cap)
        row["trie_nodes"] = T.n
        row["det_nodes"] = mz.refine(T, lr, mode="size")["nodes"]
        row["det_blowup"] = False
    except RuntimeError:
        row["trie_nodes"] = None; row["det_nodes"] = None; row["det_blowup"] = True
    row["det_s"] = round(time.time() - t0, 2)
    # Wheeler-NFA repair (trie-free)
    t1 = time.time()
    try:
        rec = wnfa.repair(rd, work, max_rounds=wnfa_rounds)
        row["wnfa_nodes"] = len(rec["nodes"]); row["wnfa_edges"] = len(rec["edges"])
        row["wnfa_splits"] = rec["splits"]; row["wnfa_nondet"] = rec["nondet"]
        row["wnfa_fallback"] = rec["fallback"]; row["wnfa_ok"] = rec["ok"]
    except Exception as ex:  # noqa: BLE001
        row["wnfa_ok"] = False; row["wnfa_err"] = str(ex)[:60]
    row["wnfa_s"] = round(time.time() - t1, 2)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fastadir", default=os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta"))
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("-l", type=int, default=40)
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--trie-cap", type=int, default=8000)
    ap.add_argument("--wnfa-rounds", type=int, default=600)
    ap.add_argument("--work", default="/tmp/compact_wnfa")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data", "compact_wnfa.csv"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True); os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fastas = sorted(glob.glob(os.path.join(args.fastadir, "*.fa")))[:args.limit]
    rows = []
    for fa in fastas:
        try:
            rows.append(measure(fa, args.l, args.a, args.work,
                                trie_cap=args.trie_cap, wnfa_rounds=args.wnfa_rounds))
        except Exception as ex:  # noqa: BLE001
            rows.append({"block": os.path.basename(fa), "a": args.a, "l": args.l, "err": str(ex)[:80]})
    cols = ["block", "l", "a", "db4_nodes", "db4_edges", "revdet_nodes", "revdet_edges",
            "trie_nodes", "det_nodes", "det_blowup", "wnfa_nodes", "wnfa_edges", "wnfa_splits",
            "wnfa_nondet", "wnfa_fallback", "wnfa_ok", "det_s", "wnfa_s"]
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in rows:
            w.writerow(r)
    # summary
    okw = [r for r in rows if r.get("wnfa_ok")]
    conv = [r for r in okw if not r.get("wnfa_fallback")]
    nondet = [r for r in conv if r.get("wnfa_nondet")]
    both = [r for r in okw if r.get("det_nodes") and r.get("wnfa_nodes")]
    wnfa_smaller_than_det = [r for r in both if r["wnfa_nodes"] < r["det_nodes"]]
    vs_db = [r for r in okw if r.get("db4_nodes") and r.get("wnfa_nodes")]
    wnfa_smaller_than_db = [r for r in vs_db if r["wnfa_nodes"] < r["db4_nodes"]]
    det_blew = [r for r in rows if r.get("det_blowup")]
    wnfa_won_where_det_blew = [r for r in det_blew if r.get("wnfa_ok")]
    print(f"a={args.a} blocks={len(rows)}  WNFA ok={len(okw)} converged(no fallback)={len(conv)} "
          f"nondet={len(nondet)}")
    if both:
        print(f"  WNFA nodes < deterministic in {len(wnfa_smaller_than_det)}/{len(both)} "
              f"(median WNFA {st.median([r['wnfa_nodes'] for r in both])} vs det "
              f"{st.median([r['det_nodes'] for r in both])})")
    if vs_db:
        print(f"  WNFA nodes < De Bruijn-k4 in {len(wnfa_smaller_than_db)}/{len(vs_db)} "
              f"(median WNFA {st.median([r['wnfa_nodes'] for r in vs_db])} vs DB "
              f"{st.median([r['db4_nodes'] for r in vs_db])})")
    print(f"  deterministic trie-blowups: {len(det_blew)}; of those WNFA succeeded on "
          f"{len(wnfa_won_where_det_blew)} (trie-free scales past the wall)")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
