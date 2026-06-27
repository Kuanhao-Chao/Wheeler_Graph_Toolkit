"""Phase 3 -- scale/speed/MEMORY benchmark of the suffix pangenome index on yeast.

Per (chrom, a, s) cell: build TIME, peak RSS, in-memory footprint (structure breakdown), on-disk size
(both serialize formats), count + locate warm-median latency (genome-routed, median of N reps), router
survivor fraction, resolution (>=2-species fraction), and a built-in correctness gate
(locate == locate_routed == union(oracle), 0 mismatches). Resumable CSV keyed by (chrom,a,s).

  python3 benchmark/genome_index/suffix_scaling.py --chrom chrI --a 2,4,7 --s 1,4,16 --sample runs
  python3 benchmark/genome_index/suffix_scaling.py --genome   # all chromosomes, per-chrom rows
"""
import argparse
import csv
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


def med_time(fn, reps):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    return st.median(ts)


def measure(chrom, a, s, sample, reps, blocks, work):
    fastas = sorted(glob.glob(os.path.join(FADIR, f"{chrom}_*.fa")))
    if blocks:
        fastas = fastas[:blocks]
    row = {"chrom": chrom, "a": a, "s": s, "sample": sample, "n_blocks": len(fastas)}

    # build (in-process for footprint) + peak RSS (subprocess)
    t0 = time.time(); pg = PangenomeIndex(fastas, a=a, l=-1, s=s, sample=sample, w=8); pg.build_global()
    row["build_s"] = round(time.time() - t0, 2)
    rss = mp.peak_rss_build(fastas, a=a, s=s, sample=sample, w=8)
    row["build_rss_kb"] = rss["rss_kb"]
    fp = mp.pangenome_footprint(pg)
    row["inmem_kb"] = round(fp["total_bytes"] / 1024)
    row["inmem_router_kb"] = round(fp["router_gmap_bytes"] / 1024)
    row["inmem_blocks_kb"] = round(fp["blocks_total_bytes"] / 1024)
    row["total_suffix_nodes"] = sum(b["idx"].n for b in pg.blocks)
    row["total_sa_samples"] = sum(b["idx"].n_samples for b in pg.blocks)

    # on-disk size (both formats)
    for fmt in ("arrays", "rebuild"):
        p = os.path.join(work, f"{chrom}_a{a}_s{s}_{sample}_{fmt}.bin")
        row[f"ondisk_{fmt}_kb"] = round(ser.save_pangenome(pg, p, fmt) / 1024)
        os.remove(p)

    # query set: real present (multi-species) + absent
    import random
    rng = random.Random(2024)
    present = []
    for fa in fastas[:120]:
        for _id, seq in read_fasta(fa)[:a]:
            u = _ungap_cap(seq, -1)
            if len(u) >= 12:
                j = rng.randint(0, len(u) - 8); present.append(u[j:j + 8])
        if len(present) >= 60:
            break
    present = list(dict.fromkeys(present))[:40]
    absent = ["".join(rng.choice("ACGT") for _ in range(rng.randint(9, 12))) for _ in range(20)]

    # warm-median latency: count, locate (per-block prefilter), locate_routed
    sample_q = present[:20] or ["ACGTACGT"]
    row["count_us"] = round(1e6 * med_time(lambda: [pg.blocks[0]["idx"].count(P) for P in sample_q], reps) / len(sample_q), 2)
    row["locate_ms"] = round(1e3 * med_time(lambda: [pg.locate(P) for P in sample_q], reps) / len(sample_q), 3)
    row["routed_ms"] = round(1e3 * med_time(lambda: [pg.locate_routed(P) for P in sample_q], reps) / len(sample_q), 4)
    surv = []
    multi = 0
    for P in present:
        stt = {}; hits = pg.locate(P, _stats=stt); surv.append(stt.get("survivors", 0))
        if len({h["species"] for h in hits}) >= 2:
            multi += 1
    row["median_survivors"] = st.median(surv) if surv else 0
    row["of_blocks"] = len(pg.blocks)
    row["multi_species_frac"] = round(multi / max(1, len(present)), 3)

    # correctness gate: locate == locate_routed == union(oracle) on a sample
    coords = {fa: json.load(open(fa.replace(".fa", ".coords.json"))) for fa in fastas}
    mism = 0
    for P in (present[:15] + absent[:10]):
        got = sx.as_tuples(pg.locate(P)); rtd = sx.as_tuples(pg.locate_routed(P))
        truth = set()
        for fa in fastas:
            truth |= lor.locate_brute(fa, coords[fa], P, a=a, l=-1)
        if not (got == rtd == truth):
            mism += 1
    row["verify_mismatches"] = mism
    return row


COLS = ["chrom", "a", "s", "sample", "n_blocks", "total_suffix_nodes", "total_sa_samples",
        "build_s", "build_rss_kb", "inmem_kb", "inmem_blocks_kb", "inmem_router_kb",
        "ondisk_arrays_kb", "ondisk_rebuild_kb", "count_us", "locate_ms", "routed_ms",
        "median_survivors", "of_blocks", "multi_species_frac", "verify_mismatches"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrom", default="chrI")
    ap.add_argument("--a", default="2,4,7")
    ap.add_argument("--s", default="1,4,16")
    ap.add_argument("--sample", default="runs")
    ap.add_argument("--reps", type=int, default=11)
    ap.add_argument("--blocks", type=int, default=0)
    ap.add_argument("--work", default="/dev/shm/suffix_scaling")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "suffix_chrI_scaling.csv"))
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True); os.makedirs(os.path.dirname(args.out), exist_ok=True)
    avals = [int(x) for x in args.a.split(",")]
    svals = [int(x) for x in args.s.split(",")]

    done = {}
    if os.path.exists(args.out):
        for r in csv.DictReader(open(args.out)):
            done[(r["chrom"], r["a"], r["s"], r["sample"])] = r
    rows = list(done.values())
    for a in avals:
        for s in svals:
            key = (args.chrom, str(a), str(s), args.sample)
            if key in done:
                print(f"[skip] {key}", flush=True); continue
            print(f"[measure] chrom={args.chrom} a={a} s={s} sample={args.sample} ...", flush=True)
            try:
                r = measure(args.chrom, a, s, args.sample, args.reps, args.blocks, args.work)
            except Exception as ex:  # noqa: BLE001
                r = {"chrom": args.chrom, "a": a, "s": s, "sample": args.sample, "error": str(ex)[:120]}
            rows.append(r)
            print(f"   -> build {r.get('build_s')}s rss {r.get('build_rss_kb')}kB inmem {r.get('inmem_kb')}kB "
                  f"ondisk_arrays {r.get('ondisk_arrays_kb')}kB locate {r.get('locate_ms')}ms "
                  f"routed {r.get('routed_ms')}ms mism {r.get('verify_mismatches')}", flush=True)
            with open(args.out, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore"); w.writeheader()
                for rr in rows:
                    w.writerow(rr)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
