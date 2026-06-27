"""Authority for the Wheeler-graph INDEX technical report: recompute EVERY number the report cites from
committed data and print a claimed-vs-computed PASS/FAIL table. The report must cite ONLY rows that PASS.

Mirrors benchmark/report_figs/verify_report_numbers.py (chk/approx, binary memory units). Loads the
committed index data under data/ + the audit constants in index/AUDIT.md. Run under any python3
(stdlib only): `python3 benchmark/report_figs/verify_index_report_numbers.py`.
"""
import csv
import json
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")

_rows = []
PASS, FAIL = "PASS", "FAIL"


def chk(metric, computed, claimed, ok, note=""):
    _rows.append((PASS if ok else FAIL, metric, str(computed), str(claimed), note))


def approx(a, b, tol=0.02):
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return a == b


def _load(name):
    return json.load(open(os.path.join(DATA, name)))


# ---------------------------------------------------------------- 1. full yeast genome
g = _load("suffix_genome_scaling.json")
agg = g["aggregate"]
chk("genome.chromosomes", agg["chromosomes"], 17, agg["chromosomes"] == 17)
chk("genome.total_blocks", agg["total_blocks"], 44063, agg["total_blocks"] == 44063)
chk("genome.total_suffix_nodes", agg["total_suffix_nodes"], 43366827, agg["total_suffix_nodes"] == 43366827)
chk("genome.build_s", agg["total_build_s"], 318.4, approx(agg["total_build_s"], 318.4))
chk("genome.peak_rss_mb (chrIV)", agg["max_chrom_rss_mb"], 1270.5, approx(agg["max_chrom_rss_mb"], 1270.5))
chk("genome.inmem_all_mb", agg["total_inmem_mb"], 11012.0, approx(agg["total_inmem_mb"], 11012.0))
chk("genome.ondisk_mb", agg["total_ondisk_mb"], 334.4, approx(agg["total_ondisk_mb"], 334.4))
ratio = agg["total_inmem_mb"] / agg["total_ondisk_mb"]
chk("genome.ondisk_vs_inmem_ratio", round(ratio, 1), "~33x", approx(ratio, 32.9, 0.05))
chk("genome.routed_ms", agg["median_routed_ms"], 2.6, approx(agg["median_routed_ms"], 2.6367))
chk("genome.verify_mismatches", agg["total_verify_mismatches"], 0, agg["total_verify_mismatches"] == 0)
chk("genome.sacCer3_genome_checks", agg["total_sacCer3_genome_checks"], 8687, agg["total_sacCer3_genome_checks"] == 8687)
hp = agg["human_projection"]
chk("human.factor", hp["factor_vs_yeast"], 262.3, approx(hp["factor_vs_yeast"], 262.3))
chk("human.est_blocks", hp["est_blocks"], "~11.6M", approx(hp["est_blocks"], 11557508, 0.001))
chk("human.build_h", hp["est_build_h_single_core"], 23.2, approx(hp["est_build_h_single_core"], 23.2))
chk("human.ondisk_gb", hp["est_ondisk_gb"], 85.7, approx(hp["est_ondisk_gb"], 85.7))
chk("human.inmem_all_gb", hp["est_inmem_all_gb"], 2820.7, approx(hp["est_inmem_all_gb"], 2820.7))
pc = {r["chrom"]: r for r in g["per_chrom"] if "n_blocks" in r}
chk("genome.chrIV blocks", pc["chrIV"]["n_blocks"], 5884, pc["chrIV"]["n_blocks"] == 5884)
chk("genome.chrIV build_s", pc["chrIV"]["build_s"], 41.3, approx(pc["chrIV"]["build_s"], 41.3))
chk("genome.chrM blocks", pc["chrM"]["n_blocks"], 318, pc["chrM"]["n_blocks"] == 318)
# the largest-RSS chromosome is chrIV
maxc = max(pc.values(), key=lambda r: r["build_rss_mb"] or 0)
chk("genome.max_rss is chrIV", maxc["chrom"], "chrIV", maxc["chrom"] == "chrIV")

# ---------------------------------------------------------------- 2. chrI a x s sweep
rows = [r for r in csv.DictReader(open(os.path.join(DATA, "suffix_chrI_scaling.csv")))]
def cell(sample, a, s):
    for r in rows:
        if r["sample"] == sample and r["a"] == str(a) and r["s"] == str(s):
            return r
    return None
chk("chrI.all verify_mismatches==0", set(r["verify_mismatches"] for r in rows), {"0"},
    all(r["verify_mismatches"] == "0" for r in rows))
chk("chrI.all n_blocks==992", set(r["n_blocks"] for r in rows), {"992"},
    all(r["n_blocks"] == "992" for r in rows))
for a, b in [(2, 3.15), (4, 6.04), (7, 8.75)]:
    chk(f"chrI.build_s a={a} (rate,s=1)", cell("rate", a, 1)["build_s"], b, approx(cell("rate", a, 1)["build_s"], b))
mb = lambda kb: round(int(kb) / 1024, 1)   # binary MiB
for s, disk, rtd in [(1, 7.6, 0.860), (4, 5.6, 0.976), (16, 5.0, 1.369)]:
    c = cell("rate", 4, s)
    chk(f"chrI.ondisk_mb a=4 s={s}", mb(c["ondisk_arrays_kb"]), disk, approx(mb(c["ondisk_arrays_kb"]), disk, 0.04))
    chk(f"chrI.routed_ms a=4 s={s}", c["routed_ms"], rtd, approx(c["routed_ms"], rtd, 0.05))

# ---------------------------------------------------------------- 3. resolution (suffix vs DeBruijn vs RevDet)
rs = _load("genome_resolution.json")["summary"]
chk("res.blocks", rs["blocks"], 71, rs["blocks"] == 71)
chk("res.multi_species_queries", rs["multi_species_queries"], 653, rs["multi_species_queries"] == 653)
chk("res.suffix_species_rate", rs["suffix_correct_species_rate"], 1.0, rs["suffix_correct_species_rate"] == 1.0)
chk("res.debruijn_species_rate", rs["debruijn_native_species_rate"], 0.0, rs["debruijn_native_species_rate"] == 0.0)
chk("res.debruijn_superset_fp", rs["debruijn_superset_fp"], rs["recombinants_total"],
    rs["debruijn_superset_fp"] == rs["recombinants_total"] == 592)
chk("res.suffix_fp", rs["suffix_fp"], 0, rs["suffix_fp"] == 0)
chk("res.revdet_superset_blocks", rs["revdet_superset_blocks"], 71, rs["revdet_superset_blocks"] == 71)
chk("res.median_nodes", rs["median_nodes"], {"suffix": 257, "debruijn": 211, "revdet": 117},
    rs["median_nodes"] == {"suffix": 257, "debruijn": 211, "revdet": 117})
chk("res.median_locate_us suffix", rs["median_locate_us"]["suffix"], 8.37, approx(rs["median_locate_us"]["suffix"], 8.37))
chk("res.median_locate_us occ_map", rs["median_locate_us"]["occ_map"], 17.03, approx(rs["median_locate_us"]["occ_map"], 17.03))

# ---------------------------------------------------------------- 4. pangenome demo + router decomposition
pg = _load("genome_pangenome.json")
chk("pangenome.blocks", pg["blocks"], 992, pg["blocks"] == 992)
chk("pangenome.build_s", pg["build_s"], 5.4, approx(pg["build_s"], 5.4))
chk("pangenome.query_ms", pg["query_ms_per_pattern"], 7.7, approx(pg["query_ms_per_pattern"], 7.7))
chk("pangenome.verify_mismatches", pg["verify_mismatches"], 0, pg["verify_mismatches"] == 0)
ex = pg["biological_example"]
chk("pangenome.example CATTACCC", (ex["pattern"], ex["n_hits"], sorted(ex["species"])),
    ("CATTACCC", 9, ["sacCer3", "sacKud", "sacMik", "sacPar"]),
    ex["pattern"] == "CATTACCC" and ex["n_hits"] == 9 and sorted(ex["species"]) == ["sacCer3", "sacKud", "sacMik", "sacPar"])
rt = _load("suffix_router.json")
chk("router.touch_all_ms", rt["touch_all_ms"], 25.5, approx(rt["touch_all_ms"], 25.5, 0.15))
chk("router.wmer_prefilter_ms", rt["wmer_prefilter_ms"], 2.78, approx(rt["wmer_prefilter_ms"], 2.78, 0.15))
chk("router.routed_ms", rt["routed_ms"], 0.157, approx(rt["routed_ms"], 0.157, 0.2))
chk("router.speedup_routed_vs_touchall", rt["speedup_routed_vs_touchall"], "~162x", rt["speedup_routed_vs_touchall"] >= 100)
chk("router.median_survivors", rt["median_survivors"], 2, rt["median_survivors"] <= 4)
chk("router.gmap_wmers", rt["gmap_distinct_wmers"], 64354, rt["gmap_distinct_wmers"] == 64354)

# ---------------------------------------------------------------- 5. C++ vs Python suffix locate
cp = _load("cpp_vs_py_suffix.json")
chk("cpp.python_us", cp["python_us_per_locate"], 35.3, approx(cp["python_us_per_locate"], 35.3, 0.2))
chk("cpp.cpp_us", cp["cpp_us_per_locate"], 0.39, approx(cp["cpp_us_per_locate"], 0.391, 0.2))
chk("cpp.speedup", cp["speedup_cpp_vs_python"], "~90x", cp["speedup_cpp_vs_python"] >= 50)

# ---------------------------------------------------------------- 6. De Bruijn locate decomposition (baseline)
loc = _load("genome_chrI_locate.json")["overall"]
chk("locate.naive_ms", loc["naive_ms"], 43.8, approx(loc["naive_ms"], 43.8034))
chk("locate.fm_ms", loc["fm_prefilter_ms"], 7.2, approx(loc["fm_prefilter_ms"], 7.222))
chk("locate.routed_ms", loc["routed_ms"], 0.021, approx(loc["routed_ms"], 0.02139, 0.1))
chk("locate.speedup_fm", loc["speedup_fm_vs_naive"], 6.1, approx(loc["speedup_fm_vs_naive"], 6.1))
chk("locate.speedup_routed", loc["speedup_routed_vs_naive"], 2047.8, approx(loc["speedup_routed_vs_naive"], 2047.8))
chk("locate.median_survivors", loc["median_survivor_shards"], 7.5, approx(loc["median_survivor_shards"], 7.5))
le = _load("genome_chrI_locate.json")["biological_example"]
chk("locate.example GCAACCG", (le["pattern"], le["n_hits"], le.get("sacCer3_genome_verified")),
    ("GCAACCG", 16, True), le["pattern"] == "GCAACCG" and le["n_hits"] == 16 and le.get("sacCer3_genome_verified"))

# ---------------------------------------------------------------- 7. De Bruijn single-graph ceiling
sc = [r for r in csv.DictReader(open(os.path.join(DATA, "genome_scaling.csv")))]
ok = [r for r in sc if r.get("verdict") == "1" and r.get("rec_to") == "False"]
big = max(ok, key=lambda r: int(r["dot_nodes"]))
chk("ceiling.largest_nodes", big["dot_nodes"], 68376, big["dot_nodes"] == "68376")
chk("ceiling.largest_rec_s", big["rec_s"], 168.2, approx(big["rec_s"], 168.205))
to = [r["dot_nodes"] for r in sc if r.get("rec_to") == "True"]
chk("ceiling.timeout_nodes", to, ["118306"], "118306" in to)
cppus = [float(r["cppidx_us_per_query"]) for r in sc if r.get("cppidx_us_per_query")]
chk("ceiling.cppidx_us_median", round(st.median(cppus), 3), 0.094, approx(st.median(cppus), 0.094, 0.1))

# ---------------------------------------------------------------- 8. audit constants (present in AUDIT.md)
audit = open(os.path.join(ROOT, "index", "AUDIT.md")).read().lower()
for needle in ["1 bug", "all other algorithms robust", "2,067,185", "8,000", "dawg.count",
               "27,280", "11,088", "2,770", "160k", "1.6m"]:
    chk(f"audit.text '{needle}'", needle in audit, True, needle in audit)
chk("audit.>4M cases", (">4 million" in audit) or ("4 million" in audit) or ("4,000,000" in audit),
    True, (">4 million" in audit) or ("4 million" in audit) or ("4,000,000" in audit))


# ---------------------------------------------------------------- print
def main():
    npass = sum(1 for r in _rows if r[0] == PASS)
    nfail = len(_rows) - npass
    w = max(len(r[1]) for r in _rows)
    print("=" * 100)
    print(f"{'':4} {'metric':<{w}}  {'computed':<22} | report-claim")
    print("-" * 100)
    for status, metric, comp, claim, note in _rows:
        mark = "[PASS]" if status == PASS else "[FAIL]"
        line = f"{mark} {metric:<{w}}  {comp:<22} | {claim}"
        if note:
            line += f"   ({note})"
        print(line)
    print("-" * 100)
    print(f"PASS {npass}/{len(_rows)}   FAIL {nfail}")
    return nfail == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
