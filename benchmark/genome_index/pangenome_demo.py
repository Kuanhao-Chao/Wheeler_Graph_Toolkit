"""Phase P5 demo -- the whole-chrI tagged suffix pangenome index: query a string -> (species, genomic
position), multi-hit, exact, with NATIVE species resolution.

Builds the sharded suffix Wheeler index over all chrI MAF blocks, then queries real strings and reports
every (species, genomic coordinate, strand) occurrence. A sample is cross-checked against the brute
oracle and (for sacCer3) against the real chrI genome. Contrasts the native species resolution with the
De Bruijn index (which cannot name species from the graph). Run under python3.
-> data/genome_pangenome.json
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
from index.pangenome_index import PangenomeIndex      # noqa: E402
from index import suffix_index as sx                  # noqa: E402
from index import locate_oracle as lor                # noqa: E402
from index.faithful import read_fasta, _ungap_cap     # noqa: E402

FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
GENOME = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "genome", "chrI.fa")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-a", type=int, default=4)
    ap.add_argument("-s", type=int, default=4)
    ap.add_argument("--blocks", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "genome_pangenome.json"))
    args = ap.parse_args()
    fastas = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))
    if args.blocks:
        fastas = fastas[:args.blocks]

    t0 = time.time()
    pg = PangenomeIndex(fastas, a=args.a, l=-1, s=args.s)
    build_s = time.time() - t0
    nblocks = len(pg.blocks)
    tot_nodes = sum(b["idx"].n for b in pg.blocks)
    tot_samples = sum(b["idx"].n_samples for b in pg.blocks)

    res = {"chrom": "chrI", "a": args.a, "s": args.s, "blocks": nblocks,
           "build_s": round(build_s, 1), "total_suffix_nodes": tot_nodes,
           "total_sa_samples": tot_samples, "build_ms_per_block": round(1000 * build_s / max(1, nblocks), 2)}

    # query mix: real multi-species k-mers (present) + absent + off-alphabet
    rng = random.Random(2024)
    present = []
    for fa in fastas[:200]:
        for _id, s in read_fasta(fa)[:args.a]:
            u = _ungap_cap(s, -1)
            if len(u) >= 10:
                j = rng.randint(0, len(u) - 8); present.append(u[j:j + 8])
        if len(present) >= 60:
            break
    present = list(dict.fromkeys(present))[:50]
    absent = ["".join(rng.choice("ACGT") for _ in range(rng.randint(8, 12))) for _ in range(30)] + ["ZZZ"]

    # latency + species-resolution
    tq = time.time()
    multi_species = 0
    for P in present:
        sp = pg.species_of(P)
        if len(sp) >= 2:
            multi_species += 1
    res["query_ms_per_pattern"] = round(1000 * (time.time() - tq) / max(1, len(present)), 2)
    res["present_multi_species"] = multi_species
    res["present_total"] = len(present)
    res["absent_found"] = sum(1 for P in absent if pg.locate(P))

    # verify a sample vs the brute oracle (union over the touched blocks) + the real genome
    coords_cache = {fa: json.load(open(fa.replace(".fa", ".coords.json"))) for fa in fastas}
    chrI = None
    if os.path.exists(GENOME):
        from pipeline.yeast_fetch import read_genome_fasta
        chrI = read_genome_fasta(GENOME)
    mism = genome_checked = 0
    for P in (present[:20] + absent[:10]):
        got = sx.as_tuples(pg.locate(P))
        truth = set()
        for fa in fastas:
            truth |= lor.locate_brute(fa, coords_cache[fa], P, a=args.a, l=-1)
        if got != truth:
            mism += 1
        if chrI is not None:
            for h in pg.locate(P):
                if h["species"] == "sacCer3" and not (chrI[h["gstart"]:h["gend"]] == P):
                    mism += 1
                elif h["species"] == "sacCer3":
                    genome_checked += 1
    res["verify_sample"] = len(present[:20] + absent[:10])
    res["verify_mismatches"] = mism
    res["sacCer3_genome_checks"] = genome_checked

    # a concrete biological example: a multi-species k-mer -> its (species, genomic) hits
    example = None
    for P in present:
        hits = pg.locate(P)
        sp = {h["species"] for h in hits}
        if len(sp) >= 3:
            example = {"pattern": P, "n_hits": len(hits), "species": sorted(sp),
                       "hits": [{"species": h["species"], "src": h["src"], "gstart": h["gstart"],
                                 "gend": h["gend"], "strand": h["strand"]} for h in hits[:10]]}
            break
    res["biological_example"] = example
    res["resolution_note"] = ("the suffix pangenome index reports the species SET + positions natively; "
                              "the De Bruijn index returns a collapsed node range that names no species")

    with open(args.out, "w") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
