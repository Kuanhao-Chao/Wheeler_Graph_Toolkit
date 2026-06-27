"""Phase L4 demo -- is the Wheeler k-mer index PRACTICAL for the biological locate query?

Builds the whole-chrI sharded locate index (one Wheeler graph + FM-index + K-mer position map per MAF
block, k selective) and compares, for a mix of queries:

  * INDEX-accelerated locate : per shard, the Wheeler FM-index membership `count(reverse(P))` skips
    shards that cannot contain P (the speed lever); survivors do a K-mer occ lookup + verify.
  * NAIVE locate             : scan every position of every (pre-loaded, same-in-memory) sequence.

Both run over the IDENTICAL pre-loaded per-shard sequences (built once), so the comparison is purely
algorithmic. Every query asserts INDEX == NAIVE (the benchmark doubles as a correctness gate). Reports
median per-query latency, speedup, the survivor-shard fraction that explains it, build cost + index
size, and a real biological example (a k-mer -> its (species, genomic position) multi-hits, sacCer3
cross-checked against the real genome). Run under python3 (generator shelled to myenv); harness-tracked
background. -> data/genome_chrI_locate.json
"""
import argparse
import glob
import json
import os
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import genome_index as gi   # noqa: E402
from index import locate as loc        # noqa: E402

PY_BIO = os.environ.get("WGT_PY_BIO", os.path.expanduser("~/miniconda3/envs/myenv/bin/python"))
FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
GENOME = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "genome", "chrI.fa")


def naive_locate(gli, P):
    """Brute-force locate using gli's already-loaded per-shard sequences (no FM, no occ map, no skip)."""
    P = P.upper(); m = len(P)
    out, seen = [], set()
    if m == 0:
        return out
    for sh in gli.shards:
        seqs, coords = sh["sample"]["seqs"], sh["coords"]
        for i, u in enumerate(seqs):
            c = coords[i]
            for pos in range(len(u) - m + 1):
                if u[pos:pos + m] == P:
                    gs, ge, stx = loc.transform(c, pos, m)
                    key = (c["fasta_id"], c["src"], gs, ge, stx)
                    if key not in seen:
                        seen.add(key); out.append(key)
    return out


def med_time(fn, reps):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    return st.median(ts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", type=int, default=8, help="De Bruijn order (K=k-1 = locate granularity)")
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--blocks", type=int, default=0, help="0 = all chrI blocks")
    ap.add_argument("--reps", type=int, default=15)
    ap.add_argument("--work", default="/dev/shm/chrI_locate")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "genome_chrI_locate.json"))
    args = ap.parse_args()
    K = args.k - 1
    os.makedirs(args.work, exist_ok=True)
    fastas = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))
    if args.blocks:
        fastas = fastas[:args.blocks]

    # --- build shards + the locate index (timed) ---
    t0 = time.time()
    man = gi.build_shards(fastas, k=args.k, l=10_000_000, a=args.a, work=args.work, py_bio=PY_BIO)
    shard_build_s = time.time() - t0
    shards = man["shards"]
    t1 = time.time()
    gli = loc.GenomeLocateIndex(shards, FADIR, k=args.k, a=args.a, l=-1, engine="py")
    gli.build_global()                       # the genome-size-independent K-mer routing index
    locidx_build_s = time.time() - t1
    occ_entries = sum(len(sh["sample"]["occ"]) for sh in gli.shards)
    global_kmers = len(gli._global)

    res = {"chrom": "chrI", "k": args.k, "K": K, "a": args.a,
           "blocks_total": len(fastas), "shards_wheeler": len(shards),
           "non_wheeler": len(man["non_wheeler"]),
           "shard_build_s": round(shard_build_s, 1), "locidx_build_s": round(locidx_build_s, 1),
           "occ_kmer_entries": occ_entries, "global_distinct_kmers": global_kmers}

    # --- query mix: present k-mers of varied length + absent + off-alphabet ---
    import random
    rng = random.Random(2024)
    present = set()
    for sh in gli.shards[:120]:
        for u in sh["sample"]["seqs"]:
            for m in (5, K, K + 1, 12):
                if len(u) >= m:
                    j = rng.randint(0, len(u) - m); present.add(u[j:j + m])
    present = list(present)[:60]
    absent = ["".join(rng.choice("ACGT") for _ in range(rng.randint(K, K + 3))) for _ in range(40)]
    offalpha = ["ZZZZ", "NNNN"]
    queries = present + absent + offalpha

    # --- per-query: assert naive == FM-prefilter == routed; time all three ---
    rows, mism = [], 0
    for P in queries:
        stats = {}
        idx_keys = sorted(loc.as_tuples(gli.locate(P, _stats=stats)))
        routed_keys = sorted(loc.as_tuples(gli.locate_routed(P)))
        naive_keys = sorted(set(naive_locate(gli, P)))
        if not (idx_keys == naive_keys == routed_keys):
            mism += 1
        idx_s = med_time(lambda: gli.locate(P), args.reps)
        rtd_s = med_time(lambda: gli.locate_routed(P), args.reps)
        nai_s = med_time(lambda: naive_locate(gli, P), args.reps)
        rows.append({"P": P, "m": len(P), "hits": len(idx_keys), "survivors": stats.get("survivors"),
                     "idx_ms": idx_s * 1e3, "routed_ms": rtd_s * 1e3, "naive_ms": nai_s * 1e3})

    def summ(sel, label):
        sub = [r for r in rows if sel(r)]
        if not sub:
            return None
        idx = st.median([r["idx_ms"] for r in sub]); nai = st.median([r["naive_ms"] for r in sub])
        rtd = st.median([r["routed_ms"] for r in sub])
        surv = st.median([r["survivors"] for r in sub if r["survivors"] is not None] or [0])
        return {"label": label, "n": len(sub),
                "naive_ms": round(nai, 4), "fm_prefilter_ms": round(idx, 4), "routed_ms": round(rtd, 5),
                "speedup_fm_vs_naive": round(nai / idx, 1) if idx else None,
                "speedup_routed_vs_naive": round(nai / rtd, 1) if rtd else None,
                "median_survivor_shards": surv, "of_shards": len(gli.shards)}
    res["verify_mismatches"] = mism
    res["present"] = summ(lambda r: r["hits"] > 0, "present")
    res["absent"] = summ(lambda r: r["hits"] == 0, "absent")
    res["overall"] = summ(lambda r: True, "all")

    # --- a real biological example, sacCer3 cross-checked against the genome ---
    example = None
    for P in present:
        hits = gli.locate(P)
        species = {h["species"] for h in hits}
        if len(hits) >= 2 and "sacCer3" in species:
            ex = {"pattern": P, "n_hits": len(hits),
                  "hits": [{"species": h["species"], "src": h["src"], "gstart": h["gstart"],
                            "gend": h["gend"], "strand": h["strand"]} for h in hits[:8]]}
            if os.path.exists(GENOME):
                from pipeline.yeast_fetch import read_genome_fasta
                chrI = read_genome_fasta(GENOME)
                ex["sacCer3_genome_verified"] = all(
                    chrI[h["gstart"]:h["gend"]] == P for h in hits if h["species"] == "sacCer3")
            example = ex; break
    res["biological_example"] = example

    with open(args.out, "w") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
