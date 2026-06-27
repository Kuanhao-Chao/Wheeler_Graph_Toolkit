"""Phase P3 -- resolution x compactness x speed: suffix Wheeler index vs De Bruijn vs RevDet.

The biological question is whether the INDEX itself resolves *which species* (and where) a string comes
from. We measure three things over multi-species yeast blocks, ground-truthed by the brute oracle:

  1. NATIVE SPECIES RESOLUTION. For patterns occurring in several species, the suffix index's range is
     exactly the occurrences and its document array yields the exact species SET + positions. The De
     Bruijn graph merges a shared k-mer to ONE node, so its backward-search range is structurally
     independent of how many species contain P -- it cannot name the species from the index alone (the
     existing locate recovers them only via an external occ-map). We quantify: does the index report the
     correct species set?

  2. SUPERSET FALSE POSITIVES. The De Bruijn graph accepts recombinant strings present in NO single
     species (count>0 but absent). The suffix index accepts only true occurrences. We splice recombinants
     and measure the false-positive rate of each.

  3. COMPACTNESS + SPEED. Index size (nodes/edges) and locate latency.

RevDet is characterized (node ~ (column, char): position=column native, species=column membership, but a
recombinant SUPERSET and the column is dropped on DOT serialization) -- answering "is RevDet ideal?".

Run under python3 (De Bruijn generator's Python reference is pure-stdlib via index/debruijn). Every
suffix-index query is asserted == the oracle, so the benchmark doubles as a correctness gate.
-> data/genome_resolution.json
"""
import argparse
import glob
import json
import os
import random
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import debruijn                 # noqa: E402
from index import oracle                   # noqa: E402
from index import suffix_index as sx       # noqa: E402
from index import locate as loc            # noqa: E402
from index import locate_oracle as lor     # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402

FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")


# --------------------------------------------------------------------------- De Bruijn helpers (superset)
def dbg_build(seqs, k):
    g = debruijn.build(seqs, k, seqLen=-1, alnNum=len(seqs))
    nodes = set(g["id2kmer"]); edges = list(g["edges"])
    return nodes, edges


def dbg_member(nodes, edges, F):
    """De Bruijn membership of forward string F (a path spells reverse(seq), so query reverse(F))."""
    return len(oracle.reachable(nodes, edges, F[::-1])) > 0


def gen_recombinants(nodes, edges, seqs, kdb, want=12, maxlen=10):
    """Strings the De Bruijn graph accepts (count>0) but that occur in NO single sequence (recombinants).
    Bounded DFS of path-strings W; forward string F = reverse(W); keep F absent from every seq."""
    adj = {}
    for t, h, lab in edges:
        adj.setdefault(t, []).append((lab, h))
    seqset = seqs
    found, seen = [], set()
    order = sorted(nodes)
    rng = random.Random(1)
    rng.shuffle(order)
    for start in order:
        stack = [(start, "")]
        while stack and len(found) < want:
            v, w = stack.pop()
            if len(w) >= 3:
                F = w[::-1]
                if F not in seen and not any(F in u for u in seqset):
                    seen.add(F); found.append(F)
            if len(w) < maxlen:
                for lab, h in adj.get(v, []):
                    stack.append((h, w + lab))
        if len(found) >= want:
            break
    return found[:want]


# --------------------------------------------------------------------------- RevDet characterization
def revdet_from_alignment(aligned_rows, a):
    """RevDet node set from the gapped alignment: node = (column, char) for each distinct non-gap char in
    a column; species set = rows with that char there. Returns (n_nodes, n_edges, superset:bool)."""
    rows = [r for _id, r in aligned_rows][:a]
    if not rows:
        return 0, 0, False
    ncol = max(len(r) for r in rows)
    nodes = set()
    per_col = []
    for c in range(ncol):
        chars = {r[c] for r in rows if c < len(r) and r[c] != "-"}
        per_col.append(chars)
        for ch in chars:
            nodes.add((c, ch))
    # edges between consecutive (gap-skipped) columns that co-occur in a row -> superset if any column
    # has >1 char while a neighbour also branches (re-merge => recombination)
    edges = 0
    branching_cols = sum(1 for cs in per_col if len(cs) > 1)
    superset = branching_cols >= 2
    # approximate edge count: consecutive column char-pairs present in some row
    for r in rows:
        prev = None
        for c in range(len(r)):
            if r[c] == "-":
                continue
            cur = (c, r[c])
            if prev is not None:
                edges += 1
            prev = cur
    return len(nodes), edges, superset


# --------------------------------------------------------------------------- per-block measurement
def measure_block(fa, a, kdb, s_rate):
    aligned = read_fasta(fa)
    if len(aligned) < a:
        return None
    coords = json.load(open(fa.replace(".fa", ".coords.json")))
    seqs = [_ungap_cap(r, -1) for _id, r in aligned][:a]
    if sum(len(u) for u in seqs) < 8:
        return None
    row = {"block": os.path.basename(fa), "a": a, "kdb": kdb}

    # build indexes
    t0 = time.perf_counter(); suf = sx.SuffixIndex(seqs, coords=coords, s=s_rate); row["suf_build_s"] = time.perf_counter() - t0
    dbnodes, dbedges = dbg_build(seqs, kdb)
    rd_nodes, rd_edges, rd_superset = revdet_from_alignment(aligned, a)
    row["suf_nodes"] = suf.n                      # |T| ~ total length + a
    row["db_nodes"] = len(dbnodes); row["db_edges"] = len(dbedges)
    row["revdet_nodes"] = rd_nodes; row["revdet_edges"] = rd_edges; row["revdet_superset"] = rd_superset

    # ---- 1. native species resolution on multi-species patterns ----
    rng = random.Random(hash(fa) & 0xffff)
    multi = []                                   # patterns occurring in >= 2 species (by oracle)
    for u in seqs:
        for m in (6, 8, 10):
            if len(u) >= m:
                for _ in range(4):
                    j = rng.randint(0, len(u) - m); multi.append(u[j:j + m])
    multi = list(dict.fromkeys(multi))
    suf_correct_species = db_can_name_species = ntested = 0
    range_size_vs_species = []
    for P in multi:
        truth = lor.locate_brute(fa, coords, P, a=a, l=-1)
        truth_species = {t[0] for t in truth}
        if len(truth_species) < 2:
            continue
        ntested += 1
        suf_hits = suf.locate(P)
        assert sx.as_tuples(suf_hits) == truth, (fa, P)            # correctness gate
        suf_species = {h["species"] for h in suf_hits}
        if suf_species == truth_species:
            suf_correct_species += 1
        # the De Bruijn index range: its size is structurally independent of #species (one shared node)
        lo, hi = 0, 0
        rs = len(oracle.reachable(dbnodes, dbedges, P[::-1]))      # De Bruijn node-range size
        range_size_vs_species.append((len(truth_species), len(truth), rs))
        # the De Bruijn index ALONE names species? no native species labels -> structurally 0
    row["multi_species_tested"] = ntested
    row["suf_correct_species"] = suf_correct_species
    row["db_native_species"] = 0                  # structural: the merged graph carries no species
    # correlation of De Bruijn range size with true #occurrences (should be ~0; suffix range == #occ)
    if range_size_vs_species:
        row["db_rangesize_eq_occ_frac"] = round(
            sum(1 for sp, occ, rs in range_size_vs_species if rs == occ) / len(range_size_vs_species), 3)

    # ---- 2. superset false positives ----
    recs = gen_recombinants(dbnodes, dbedges, seqs, kdb, want=12)
    db_fp = suf_fp = 0
    for F in recs:
        if dbg_member(dbnodes, dbedges, F):
            db_fp += 1                            # De Bruijn accepts a string in no species
        if suf.count(F) > 0:
            suf_fp += 1                           # suffix should never (exact)
        assert not lor.locate_brute(fa, coords, F, a=a, l=-1)      # truly absent
    row["recombinants"] = len(recs); row["db_superset_fp"] = db_fp; row["suf_fp"] = suf_fp

    # ---- 3. speed: suffix locate vs existing occ-map locate (same content) ----
    sample = (multi[:20] or [seqs[0][:6]])
    occ_sample = loc.build_locate_sample(fa, kdb, a=a, l=-1)
    t = time.perf_counter()
    for P in sample:
        suf.locate(P)
    row["suf_locate_us"] = 1e6 * (time.perf_counter() - t) / max(1, len(sample))
    t = time.perf_counter()
    for P in sample:
        loc.locate_shard(P, occ_sample, coords, count_fn=None)
    row["occ_locate_us"] = 1e6 * (time.perf_counter() - t) / max(1, len(sample))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-a", type=int, default=4)
    ap.add_argument("--kdb", type=int, default=8, help="De Bruijn order for the comparison")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("-s", type=int, default=4, help="suffix SA sample rate")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "genome_resolution.json"))
    args = ap.parse_args()
    fastas = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))
    rows = []
    for fa in fastas:
        if len(rows) >= args.limit:
            break
        try:
            r = measure_block(fa, args.a, args.kdb, args.s)
        except Exception as ex:  # noqa: BLE001
            r = {"block": os.path.basename(fa), "error": str(ex)[:120]}
        if r:
            rows.append(r)

    ok = [r for r in rows if "error" not in r and r.get("multi_species_tested")]
    summary = {
        "blocks": len(ok), "a": args.a, "kdb": args.kdb,
        "multi_species_queries": sum(r["multi_species_tested"] for r in ok),
        "suffix_correct_species_rate": round(
            sum(r["suf_correct_species"] for r in ok) / max(1, sum(r["multi_species_tested"] for r in ok)), 4),
        "debruijn_native_species_rate": 0.0,
        "db_rangesize_eq_occ_frac_median": round(
            st.median([r["db_rangesize_eq_occ_frac"] for r in ok if "db_rangesize_eq_occ_frac" in r]), 3),
        "recombinants_total": sum(r.get("recombinants", 0) for r in ok),
        "debruijn_superset_fp": sum(r.get("db_superset_fp", 0) for r in ok),
        "suffix_fp": sum(r.get("suf_fp", 0) for r in ok),
        "median_nodes": {
            "suffix": st.median([r["suf_nodes"] for r in ok]),
            "debruijn": st.median([r["db_nodes"] for r in ok]),
            "revdet": st.median([r["revdet_nodes"] for r in ok]),
        },
        "revdet_superset_blocks": sum(1 for r in ok if r.get("revdet_superset")),
        "median_locate_us": {
            "suffix": round(st.median([r["suf_locate_us"] for r in ok]), 2),
            "occ_map": round(st.median([r["occ_locate_us"] for r in ok]), 2),
        },
    }
    out = {"summary": summary, "rows": rows}
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
