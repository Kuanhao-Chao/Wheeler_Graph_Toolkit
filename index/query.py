#!/usr/bin/env python
"""End-to-end: index a real DNA MSA block and query it for a pattern.

Builds the De Bruijn Wheeler graph from an aligned FASTA block (generator), recognizes it, and builds
the FM-index from the recognizer's I/O/L; then backward-searches for a DNA pattern. Because a path in
this construction spells the *reverse* of a sequence, a pattern P is queried as reverse(P) by default
(so a "hit" means P occurs in the alignment's sequences).

  ~/miniconda3/envs/myenv/bin/python index/query.py <block.fa> --pattern ACGTAC [-k 5 -l 60 -a 2]
  ~/miniconda3/envs/myenv/bin/python index/query.py --iol <out__dir> --pattern ACGTAC [--no-reverse]
"""
import argparse
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from index.wg_index import WGIndex          # noqa: E402
from pipeline import msa_to_index as m2i    # noqa: E402
from index import locate as loc             # noqa: E402


def build_index_from_fasta(fasta, k, l, a, work):
    r = m2i.process_block(fasta, k=k, l=l, a=a, work=work)
    if r["verdict"] != 1:
        raise SystemExit(f"block is not a Wheeler graph (verdict={r['verdict']}); cannot index as-is "
                         f"(repair is future work)")
    return WGIndex.from_iol(r["outdir"]), r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fasta", nargs="?")
    ap.add_argument("--iol", help="query an existing recognizer out__ dir instead of building")
    ap.add_argument("--pattern", required=True, help="DNA pattern to search for")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("-l", type=int, default=60)
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--no-reverse", action="store_true",
                    help="query the pattern as given (paths spell reverse, so default reverses it)")
    ap.add_argument("--locate", action="store_true",
                    help="report (species, source, genomic coords, strand) of every occurrence "
                         "(needs <fasta>.coords.json; build-from-FASTA mode only)")
    args = ap.parse_args()

    if args.iol:
        idx = WGIndex.from_iol(args.iol)
        src = args.iol
    elif args.fasta:
        with tempfile.TemporaryDirectory() as work:
            idx, r = build_index_from_fasta(args.fasta, args.k, args.l, args.a, work)
            src = f"{os.path.basename(args.fasta)} (k={args.k},l={args.l},a={args.a}; " \
                  f"{idx.n} nodes, {idx.E} edges, Wheeler)"
            if args.locate:
                return _report_locate(args, idx, src)
            return _report(idx, args, src)
    else:
        ap.error("give a FASTA block or --iol <dir>")
    _report(idx, args, src)


def _report_locate(args, idx, src):
    coords_path = os.path.splitext(args.fasta)[0] + ".coords.json"
    if not os.path.exists(coords_path):
        raise SystemExit(f"--locate needs a coords sidecar: {coords_path} (run yeast_fetch to emit it)")
    coords = json.load(open(coords_path))
    sample = loc.build_locate_sample(args.fasta, args.k, a=args.a, l=args.l if args.l > 0 else -1)
    P = args.pattern.upper()
    hits = loc.locate_shard(P, sample, coords, count_fn=idx.count)
    print(f"index: {src}")
    print(f"locate: {P!r} -> {len(hits)} occurrence(s)")
    for h in sorted(hits, key=lambda h: (h["species"], h["src"], h["gstart"])):
        print(f"  {h['species']:>10}  {h['src']}  {h['gstart']}-{h['gend']} ({h['strand']})  "
              f"[block offset {h['ungapped_pos']}]")


def _report(idx, args, src):
    q = args.pattern.upper()
    qq = q if args.no_reverse else q[::-1]
    lo, hi, n = idx.count(qq)
    print(f"index: {src}")
    print(f"query: {q!r}" + ("" if args.no_reverse else f"  (searched as reverse {qq!r})"))
    if n > 0:
        print(f"  FOUND: {n} Wheeler-order node(s) in range [{lo},{hi}) "
              f"-> pattern occurs in the alignment")
    else:
        print("  not found (0 occurrences)")


if __name__ == "__main__":
    main()
