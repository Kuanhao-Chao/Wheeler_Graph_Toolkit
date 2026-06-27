"""Phase 4 -- build + measure the FULL yeast-genome suffix pangenome index, per chromosome.

One PangenomeIndex per chromosome (bounds RAM, gives the per-chromosome breakdown), sample='runs' (the
r-index/genome mode). Measures: blocks, suffix nodes, build time, peak RSS, in-memory footprint, on-disk
serialized size; a routed-locate warm-median latency on the largest-built chromosome (genome-size-
independent); a correctness sample (locate == oracle + sacCer3 hits vs the real genome). Aggregates to
genome totals and projects to human MSA. Harness-tracked background; resumable per-chromosome.
-> data/suffix_genome_scaling.json
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
from index.pangenome_index import PangenomeIndex   # noqa: E402
from index import suffix_index as sx               # noqa: E402
from index import serialize as ser                 # noqa: E402
from index import locate_oracle as lor             # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402
from benchmark.genome_index import memprobe as mp  # noqa: E402

FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
GENOMEDIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "genome")
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI"]
CHROMS = ["chr" + r for r in ROMAN] + ["chrM"]


def med_time(fn, reps):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    return st.median(ts)


def build_chrom(chrom, a, s, work, reps):
    fastas = sorted(glob.glob(os.path.join(FADIR, f"{chrom}_*.fa")))
    if not fastas:
        return None
    row = {"chrom": chrom, "n_blocks": len(fastas)}
    t0 = time.time()
    pg = PangenomeIndex(fastas, a=a, l=-1, s=s, sample="runs", w=8); pg.build_global()
    row["build_s"] = round(time.time() - t0, 1)
    row["suffix_nodes"] = sum(b["idx"].n for b in pg.blocks)
    rss = mp.peak_rss_build(fastas, a=a, s=s, sample="runs", w=8, timeout_s=1800)
    row["build_rss_mb"] = round(rss["rss_kb"] / 1024, 1) if rss["rss_kb"] else None
    fp = mp.pangenome_footprint(pg)
    row["inmem_mb"] = round(fp["total_bytes"] / 1024 / 1024, 1)
    row["inmem_router_mb"] = round(fp["router_gmap_bytes"] / 1024 / 1024, 1)
    # serialize to disk (the practical persistent footprint)
    p = os.path.join(work, f"{chrom}.idx")
    row["ondisk_mb"] = round(ser.save_pangenome(pg, p, fmt="arrays") / 1024 / 1024, 1)

    # routed-locate warm-median latency (genome-size-independent) on this chromosome
    rng = __import__("random").Random(7)
    present = []
    for fa in fastas[:200]:
        for _id, seq in read_fasta(fa)[:a]:
            u = _ungap_cap(seq, -1)
            if len(u) >= 12:
                present.append(u[rng.randint(0, len(u) - 8):][:8])
        if len(present) >= 40:
            break
    present = list(dict.fromkeys(present))[:30] or ["ACGTACGT"]
    row["routed_ms"] = round(1e3 * med_time(lambda: [pg.locate_routed(P) for P in present], reps) / len(present), 4)

    # correctness sample (a): a SUB-index over the first K blocks vs the oracle over the SAME K blocks
    # (consistent block set -> a clean equality check, decoupled from the full-chromosome index).
    K = min(60, len(fastas))
    sub_fastas = fastas[:K]
    sub_coords = {fa: json.load(open(fa.replace(".fa", ".coords.json"))) for fa in sub_fastas}
    pg_sub = PangenomeIndex(sub_fastas, a=a, l=-1, s=s, sample="runs", w=8)
    rng2 = __import__("random").Random(5)
    sub_pats = set()
    for fa in sub_fastas[:20]:
        for _id, seq in read_fasta(fa)[:a]:
            u = _ungap_cap(seq, -1)
            if len(u) >= 8:
                sub_pats.add(u[rng2.randint(0, len(u) - 6):][:6])
    sub_pats |= {"".join(rng2.choice("ACGT") for _ in range(6)) for _ in range(10)}
    mism = 0
    for P in sub_pats:
        got = sx.as_tuples(pg_sub.locate(P))
        truth = set()
        for fa in sub_fastas:
            truth |= lor.locate_brute(fa, sub_coords[fa], P, a=a, l=-1)
        if got != truth:
            mism += 1
    # correctness sample (b): every located sacCer3 '+' hit on the FULL index matches the real genome
    gpath = os.path.join(GENOMEDIR, f"{chrom}.fa")
    genome = None
    if os.path.exists(gpath):
        from pipeline.yeast_fetch import read_genome_fasta
        genome = read_genome_fasta(gpath)
    gchk = 0
    if genome is not None:
        for P in present[:20]:
            for h in pg.locate(P):
                if h["species"] == "sacCer3" and h["strand"] == "+":
                    if genome[h["gstart"]:h["gend"]] != P:
                        mism += 1
                    else:
                        gchk += 1
    row["verify_mismatches"] = mism
    row["sacCer3_genome_checks"] = gchk
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=4)
    ap.add_argument("--s", type=int, default=4)
    ap.add_argument("--reps", type=int, default=9)
    ap.add_argument("--work", default="/dev/shm/genome_idx")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "suffix_genome_scaling.json"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)

    rows = []
    if os.path.exists(args.out):
        rows = [r for r in json.load(open(args.out)).get("per_chrom", []) if "n_blocks" in r]
    done = {r["chrom"] for r in rows}
    for chrom in CHROMS:
        if chrom in done:
            print(f"[skip] {chrom}", flush=True); continue
        print(f"[build] {chrom} ...", flush=True)
        try:
            r = build_chrom(chrom, args.a, args.s, args.work, args.reps)
        except Exception as ex:  # noqa: BLE001
            import traceback; traceback.print_exc()
            r = {"chrom": chrom, "error": str(ex)[:160]}
        if r:
            rows.append(r)
            print(f"   -> {r['n_blocks']} blocks, build {r['build_s']}s rss {r['build_rss_mb']}MB "
                  f"inmem {r['inmem_mb']}MB ondisk {r['ondisk_mb']}MB routed {r['routed_ms']}ms "
                  f"mism {r['verify_mismatches']}", flush=True)
            _write(rows, args)
    _write(rows, args)
    print("GENOME_BUILD_DONE")


def _write(rows, args):
    ok = [r for r in rows if "n_blocks" in r]
    agg = {
        "chromosomes": len(ok), "total_blocks": sum(r["n_blocks"] for r in ok),
        "total_suffix_nodes": sum(r["suffix_nodes"] for r in ok),
        "total_build_s": round(sum(r["build_s"] for r in ok), 1),
        "total_inmem_mb": round(sum(r["inmem_mb"] for r in ok), 1),
        "total_ondisk_mb": round(sum(r["ondisk_mb"] for r in ok), 1),
        "max_chrom_rss_mb": max((r["build_rss_mb"] or 0) for r in ok) if ok else 0,
        "median_routed_ms": round(st.median([r["routed_ms"] for r in ok]), 4) if ok else None,
        "total_verify_mismatches": sum(r["verify_mismatches"] for r in ok),
        "total_sacCer3_genome_checks": sum(r["sacCer3_genome_checks"] for r in ok),
    }
    # human MSA projection (~3.2 Gb / 12.2 Mb ~= 262x by length)
    if agg["chromosomes"]:
        f = 3.2e9 / 12.2e6
        agg["human_projection"] = {
            "factor_vs_yeast": round(f, 1),
            "est_blocks": int(agg["total_blocks"] * f),
            "est_build_h_single_core": round(agg["total_build_s"] * f / 3600, 1),
            "est_ondisk_gb": round(agg["total_ondisk_mb"] * f / 1024, 1),
            "est_inmem_all_gb": round(agg["total_inmem_mb"] * f / 1024, 1),
            "note": "routed query is genome-size-independent (~flat); build + on-disk + held-in-mem are "
                    "linear in #blocks; the in-mem router (w-mer sets + global map) is the binding "
                    "structure -> load-on-demand from the on-disk arrays index is the practical path.",
        }
    with open(args.out, "w") as fh:
        json.dump({"a": args.a, "s": args.s, "aggregate": agg, "per_chrom": rows}, fh, indent=2)


if __name__ == "__main__":
    main()
