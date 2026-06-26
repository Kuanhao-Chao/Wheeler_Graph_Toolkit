#!/usr/bin/env python
"""Phase 1 of the MSA-indexing pipeline: acquire real yeast DNA multiple-sequence alignments.

Downloads the UCSC *sacCer3 multiz7way* whole-genome alignment (MAF) and turns each alignment block
into an aligned DNA FASTA the existing generators can consume. MAF parsing reuses Biopython
(`Bio.AlignIO`, format "maf") rather than a hand-rolled parser.

The parsing is factored so it can be unit-tested on an in-memory MAF string with no network
(`iter_blocks`, `block_records`, `write_blocks`). The actual download is a thin `curl` wrapper kept
out of the tested path.

Run with a Biopython-capable python, e.g.:
  ~/miniconda3/envs/myenv/bin/python pipeline/yeast_fetch.py --smoke --chrom chrI
  ~/miniconda3/envs/myenv/bin/python pipeline/yeast_fetch.py --parse data/.../chrI.maf --out data/.../fasta
"""
import argparse
import io
import os
import re
import subprocess
import sys

from Bio import AlignIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEAST = os.path.join(ROOT, "data", "multiseq_alignment", "yeast")
UCSC_BASE = "https://hgdownload.soe.ucsc.edu/goldenPath/sacCer3/multiz7way/maf"

# DNA alphabet we keep (uppercased); blocks with other symbols (besides gaps) are dropped.
_DNA = set("ACGT")


def iter_blocks(handle):
    """Yield Biopython MultipleSeqAlignment objects from a MAF file handle (or StringIO)."""
    # AlignIO.parse handles the `a`/`s` block structure of MAF for us.
    yield from AlignIO.parse(handle, "maf")


def _src_to_id(src, used):
    """Turn a MAF source name (e.g. 'sacCer3.chrI') into a short, unique, \\w-safe FASTA id."""
    species = src.split(".")[0]
    base = re.sub(r"[^0-9A-Za-z_]", "_", species) or "seq"
    name, i = base, 1
    while name in used:               # guarantee uniqueness within a block
        i += 1
        name = f"{base}_{i}"
    used.add(name)
    return name


def block_records(aln):
    """[(id, gapped_seq_uppercased), ...] for one alignment block, ids unique within the block."""
    used = set()
    out = []
    for rec in aln:
        out.append((_src_to_id(rec.id, used), str(rec.seq).upper()))
    return out


def _ungapped(seq):
    return seq.replace("-", "")


def block_ok(recs, min_species, min_cols, max_cols):
    """Keep a block only if it has enough species, a sane width, and is pure DNA (A/C/G/T + gaps)."""
    if len(recs) < min_species:
        return False
    cols = len(recs[0][1])
    if cols < min_cols or cols > max_cols:
        return False
    for _id, seq in recs:
        if set(_ungapped(seq)) - _DNA:        # non-DNA residue (N, lowercase soft-mask already upper)
            return False
        if not _ungapped(seq):                # all-gap row
            return False
    return True


def write_fasta(recs, path):
    with open(path, "w") as fh:
        for rid, seq in recs:
            fh.write(f">{rid}\n{seq}\n")


def write_blocks(handle, out_dir, chrom="chr", min_species=2, min_cols=8, max_cols=2000, limit=None):
    """Parse a MAF handle, filter blocks, write each kept block as an aligned FASTA. Returns a manifest
    list of dicts: {path, n_species, cols, start}."""
    os.makedirs(out_dir, exist_ok=True)
    manifest, kept = [], 0
    for bi, aln in enumerate(iter_blocks(handle)):
        recs = block_records(aln)
        if not block_ok(recs, min_species, min_cols, max_cols):
            continue
        # genomic start of the reference row (first record), if MAF annotation present
        start = getattr(aln[0], "annotations", {}).get("start", bi)
        stem = f"{chrom}_blk{kept:05d}_s{start}"
        path = os.path.join(out_dir, stem + ".fa")
        write_fasta(recs, path)
        manifest.append({"path": path, "stem": stem, "n_species": len(recs),
                         "cols": len(recs[0][1]), "start": start})
        kept += 1
        if limit and kept >= limit:
            break
    return manifest


# --------------------------------------------------------------------------- download (untested path)
def download_maf(chrom, dest_dir=None):
    """Download <chrom>.maf from UCSC sacCer3 multiz7way (the file is gzip-compressed despite the
    .maf name), decompress, and cache. Returns the path to the plain-text MAF."""
    import gzip
    import shutil
    dest_dir = dest_dir or os.path.join(YEAST, "maf")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{chrom}.maf")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"[cached] {dest} ({os.path.getsize(dest)} bytes)")
        return dest
    raw = dest + ".raw"
    url = f"{UCSC_BASE}/{chrom}.maf"
    print(f"[download] {url} -> {raw}")
    r = subprocess.run(["curl", "-fSL", "--retry", "3", "-o", raw, url],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        sys.exit(f"download failed ({r.returncode}): {r.stderr.strip()[:400]}")
    with open(raw, "rb") as fh:
        is_gz = fh.read(2) == b"\x1f\x8b"
    if is_gz:
        with gzip.open(raw, "rb") as fi, open(dest, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        os.remove(raw)
    else:
        os.replace(raw, dest)
    print(f"[ready] {dest} ({os.path.getsize(dest)} bytes)")
    return dest


def main():
    ap = argparse.ArgumentParser(description="UCSC sacCer3 multiz MAF -> per-block DNA FASTA")
    ap.add_argument("--chrom", default="chrI")
    ap.add_argument("--parse", help="parse an existing MAF file instead of downloading")
    ap.add_argument("--out", default=os.path.join(YEAST, "fasta"))
    ap.add_argument("--smoke", action="store_true", help="download chrom + parse + report")
    ap.add_argument("--min-species", type=int, default=2)
    ap.add_argument("--min-cols", type=int, default=8)
    ap.add_argument("--max-cols", type=int, default=2000)
    ap.add_argument("--limit", type=int, default=None, help="cap number of blocks written")
    args = ap.parse_args()

    maf = args.parse or (download_maf(args.chrom) if args.smoke else None)
    if not maf:
        ap.error("give --parse <maf> or --smoke")
    with open(maf) as fh:
        man = write_blocks(fh, args.out, chrom=args.chrom, min_species=args.min_species,
                           min_cols=args.min_cols, max_cols=args.max_cols, limit=args.limit)
    print(f"wrote {len(man)} block FASTA(s) to {args.out}")
    for m in man[:5]:
        print(f"  {m['stem']}  species={m['n_species']} cols={m['cols']}")
    if len(man) > 5:
        print(f"  ... (+{len(man) - 5} more)")


if __name__ == "__main__":
    main()
