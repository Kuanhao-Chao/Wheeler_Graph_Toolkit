"""Phase G3 demo -- build the whole-chrI Wheeler index the FEASIBLE (sharded) way and query it.

A single whole-chromosome De Bruijn graph at a faithful k exceeds the recognizer ceiling
(benchmark/genome_index/scaling.py), so chrI is indexed as one small-k De Bruijn Wheeler graph PER
MAF block (a shard), with the C++ FM-index per shard and a query router (index/genome_index.py).

This script:
  * builds the sharded chrI index over all chrI blocks (k small -> each shard Wheeler & tiny);
  * reports build time, shard count, total nodes/edges, on-disk index size;
  * queries real chrI k-mers (present) + fabricated k-mers (absent) through the C++ router, and
    CROSS-CHECKS a sample against the Python router + the brute oracle (the correctness gate);
  * extrapolates the per-shard cost to the whole genome (~16 chr, ~50-60k blocks).

Run under python3 (the De Bruijn generator is shelled to myenv). Harness-tracked background (it is a
few thousand recognizer calls).  -> data/genome_chrI_demo.json
"""
import argparse
import glob
import json
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import oracle               # noqa: E402
from index import genome_index as gi   # noqa: E402

PY_BIO = os.environ.get("WGT_PY_BIO", os.path.expanduser("~/miniconda3/envs/myenv/bin/python"))
FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")


def dir_bytes(d):
    return sum(os.path.getsize(os.path.join(d, f))
               for f in ("I.txt", "O.txt", "L.txt") if os.path.exists(os.path.join(d, f)))


def read_seqs(fa):
    seqs, cur = [], []
    name = None
    for line in open(fa):
        if line.startswith(">"):
            if cur:
                seqs.append("".join(cur)); cur = []
        else:
            cur.append(line.strip())
    if cur:
        seqs.append("".join(cur))
    return seqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", type=int, default=4, help="De Bruijn order (small -> each shard Wheeler)")
    ap.add_argument("-l", type=int, default=10_000_000)
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--blocks", type=int, default=0, help="0 = all chrI blocks")
    ap.add_argument("--work", default="/dev/shm/chrI_demo")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "genome_chrI_demo.json"))
    args = ap.parse_args()

    if not os.path.exists(gi.CPP_BIN):
        import subprocess
        subprocess.run(["make", "-s"], cwd=os.path.dirname(gi.CPP_BIN))
    os.makedirs(args.work, exist_ok=True)
    fastas = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))
    if args.blocks:
        fastas = fastas[:args.blocks]

    # --- build the sharded index ---
    t0 = time.time()
    man = gi.build_shards(fastas, k=args.k, l=args.l, a=args.a, work=args.work, py_bio=PY_BIO)
    build_s = time.time() - t0
    shards = man["shards"]
    tot_nodes = tot_edges = tot_bytes = 0
    for d in shards:
        nodes, edges = oracle.parse_dot(open(os.path.join(d, "graph.dot")).read())
        tot_nodes += len(nodes); tot_edges += len(edges); tot_bytes += dir_bytes(d)

    res = {"chrom": "chrI", "k": args.k, "a": args.a, "blocks_total": len(fastas),
           "shards_wheeler": len(shards), "non_wheeler": len(man["non_wheeler"]),
           "failed": len(man["failed"]), "build_s": round(build_s, 2),
           "total_nodes": tot_nodes, "total_edges": tot_edges, "index_bytes": tot_bytes,
           "build_s_per_shard": round(build_s / max(1, len(shards)), 4)}

    # --- query: present (real k-mers) + absent (fabricated), verify a sample ---
    rng = random.Random(7)
    present, absent = [], []
    for fa in fastas[:60]:
        for s in read_seqs(fa):
            u = s.replace("-", "")
            if len(u) >= 12:
                i = rng.randint(0, len(u) - 6)
                present.append(u[i:i + 6])           # a real 6-mer (forward; De Bruijn spells reverse)
            if len(present) >= 40:
                break
        if len(present) >= 40:
            break
    # De Bruijn paths spell reverse(seq); query reverse(kmer) to ask "does this 6-mer occur"
    present_q = [p[::-1] for p in present]
    absent = ["".join(rng.choice("ACGT") for _ in range(8)) for _ in range(40)] + ["ZZZ", "QQQQ"]

    cpp = gi.ShardedGenomeIndex(shards, engine="cpp")
    t1 = time.time(); cpp_present = cpp.query_batch(present_q); t2 = time.time()
    cpp_absent = cpp.query_batch(absent); t3 = time.time()
    res["present_found"] = sum(1 for p in present_q if cpp_present[p]["present"])
    res["present_total"] = len(present_q)
    res["absent_found"] = sum(1 for p in absent if cpp_absent[p]["present"])
    res["absent_total"] = len(absent)
    res["query_s_present_batch"] = round(t2 - t1, 3)
    res["query_s_absent_batch"] = round(t3 - t2, 3)
    res["query_ms_per_pattern"] = round(1000 * (t3 - t1) / max(1, len(present_q) + len(absent)), 3)

    # cross-check a sample vs Python router + oracle
    parsed = []
    for d in shards:
        nodes, edges = oracle.parse_dot(open(os.path.join(d, "graph.dot")).read())
        parsed.append((nodes, edges))
    py = gi.ShardedGenomeIndex(shards, engine="py")
    sample = (present_q[:15] + absent[:15])
    py_res = py.query_batch(sample)
    mism = 0
    for p in sample:
        o_hits = o_tot = 0
        for nodes, edges in parsed:
            r = oracle.reachable(nodes, edges, p)
            if r:
                o_hits += 1; o_tot += len(r)
        c = cpp.query(p); y = py_res[p]
        ok = (c["present"] == (o_hits > 0) == y["present"] and
              c["n_shards_hit"] == o_hits == y["n_shards_hit"] and
              c["total_matches"] == o_tot == y["total_matches"])
        if not ok:
            mism += 1
    res["verify_sample"] = len(sample)
    res["verify_mismatches"] = mism

    # --- whole-genome extrapolation (sacCer3: ~12.2 Mb, ~16 chr) ---
    # chrI ~= 0.23 Mb -> genome ~= 53x chrI by length; blocks scale similarly
    genome_factor = 12_200_000 / 230_000
    res["extrapolation"] = {
        "genome_factor_vs_chrI": round(genome_factor, 1),
        "est_shards": int(len(fastas) * genome_factor),
        "est_build_s": round(build_s * genome_factor, 1),
        "est_index_bytes": int(tot_bytes * genome_factor),
        "note": "small-k De Bruijn shard size is bounded (<=4^k nodes), so per-shard cost is O(1) in "
                "genome length; whole-genome build scales ~linearly in #blocks."}

    with open(args.out, "w") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
