"""Phase B: is RevDet + minimal-repair a more COMPACT index than the De Bruijn graph? (yeast)

Per yeast chrI block, build the De Bruijn graph (k=4,5) and the RevDet -> minimal-repair graph, record
nodes/edges (and trie size, repair blow-up), and report the node/edge compactness ratio. Run under
python3 (z3 for repair); the generators are shelled to a Biopython python.

  python3 benchmark/compact_index/measure.py --limit 60 -a 2 --out benchmark/compact_index/data/compact_yeast.csv
"""
import argparse
import csv
import glob
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from pipeline import msa_to_index as m2i        # noqa: E402  (De Bruijn build+recognize)
from pipeline import revdet_to_index as r2i     # noqa: E402  (RevDet -> repair -> index)

PY_BIO = r2i.PY_BIO


def count_dot(path):
    nodes, edges = set(), 0
    import re
    er = re.compile(r"(\w+)\s*->\s*(\w+)\s*\[")
    for line in open(path):
        m = er.search(line.replace(" ", "")) or er.search(line)
        if m:
            nodes.update((m.group(1), m.group(2))); edges += 1
    return len(nodes), edges


def debruijn_counts(fasta, k, l, a, work):
    stem = os.path.splitext(os.path.basename(fasta))[0]
    dot = os.path.join(work, f"{stem}.db{k}.dot")
    m2i.build_dot(fasta, k, l, a, dot, py=PY_BIO)
    return count_dot(dot)


def measure_block(fasta, l, a, work):
    row = {"block": os.path.basename(fasta), "l": l, "a": a}
    for k in (4, 5):
        try:
            n, e = debruijn_counts(fasta, k, l, a, work)
            row[f"db{k}_nodes"], row[f"db{k}_edges"] = n, e
        except Exception as ex:  # noqa: BLE001
            row[f"db{k}_nodes"] = row[f"db{k}_edges"] = None
            row["db_err"] = str(ex)[:80]
    t0 = time.time()
    try:
        rec, idx = r2i.process_block(fasta, l=l, a=a, work=work)
        row["revdet_nodes"] = rec.get("revdet_nodes")
        row["revdet_wheeler"] = rec.get("revdet_wheeler")
        row["trie_nodes"] = rec.get("trie_nodes")
        row["blowup"] = (rec.get("reason") == "trie_blowup")
        row["ok"] = rec.get("ok", False)
        if rec.get("ok"):
            row["rep_nodes"] = idx.n
            row["rep_edges"] = idx.E
    except Exception as ex:  # noqa: BLE001
        row["ok"] = False; row["err"] = str(ex)[:100]
    row["revdet_repair_s"] = round(time.time() - t0, 3)
    # compactness ratios (De Bruijn k=4 / RevDet+repair); >1 means RevDet+repair is SMALLER
    if row.get("ok") and row.get("db4_nodes"):
        row["node_ratio_db4_over_rep"] = round(row["db4_nodes"] / row["rep_nodes"], 3)
        row["edge_ratio_db4_over_rep"] = round(row["db4_edges"] / row["rep_edges"], 3)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fastadir", default=os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta"))
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("-l", type=int, default=40)
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--work", default="/tmp/compact_measure")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data", "compact_yeast.csv"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fastas = sorted(glob.glob(os.path.join(args.fastadir, "*.fa")))[:args.limit]
    rows = [measure_block(fa, args.l, args.a, args.work) for fa in fastas]
    cols = ["block", "l", "a", "db4_nodes", "db4_edges", "db5_nodes", "db5_edges",
            "revdet_nodes", "revdet_wheeler", "trie_nodes", "rep_nodes", "rep_edges",
            "blowup", "ok", "revdet_repair_s", "node_ratio_db4_over_rep", "edge_ratio_db4_over_rep"]
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    ok = [r for r in rows if r.get("ok")]
    blow = [r for r in rows if r.get("blowup")]
    ratios = [r["node_ratio_db4_over_rep"] for r in ok if r.get("node_ratio_db4_over_rep")]
    smaller = [x for x in ratios if x > 1.0]
    print(f"blocks={len(rows)}  repaired_ok={len(ok)}  trie_blowup={len(blow)}")
    if ratios:
        print(f"node ratio De Bruijn(k4)/RevDet+repair: median={statistics.median(ratios):.2f} "
              f"(>1 = RevDet smaller); RevDet smaller in {len(smaller)}/{len(ratios)} blocks")
        print(f"  median rep_nodes={statistics.median([r['rep_nodes'] for r in ok])} "
              f"vs db4_nodes={statistics.median([r['db4_nodes'] for r in ok if r.get('db4_nodes')])}; "
              f"median trie={statistics.median([r['trie_nodes'] for r in ok if r.get('trie_nodes')])}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
