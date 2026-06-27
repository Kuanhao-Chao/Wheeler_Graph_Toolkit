"""A genome-wide pangenome index with native species + position resolution.

Mirrors the sharded architecture of index/genome_index.py, but each shard is a tagged suffix Wheeler
index (index/suffix_index.SuffixIndex) instead of a De Bruijn FM-index -- so a query returns, natively
and exactly, every (species, genomic coordinate, strand) occurrence across the genome, multi-hit. No
recognizer is needed at build time (the suffix order is Wheeler by theorem; certified on small
instances in verify/suffix_wheeler_cert.py).

Build is per MAF block (block |T| is small); a genome query unions the per-block locates. A lightweight
per-block character prefilter skips blocks that cannot contain P (the speed lever; a k-mer sketch is the
natural next step).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from index.suffix_index import SuffixIndex, as_tuples, _dedup_sort  # noqa: E402

FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")


class PangenomeIndex:
    def __init__(self, fastas, a=4, l=-1, s=4, sample="rate"):
        self.blocks = []
        for fa in fastas:
            cpath = fa.replace(".fa", ".coords.json")
            coords = json.load(open(cpath)) if os.path.exists(cpath) else None
            idx = SuffixIndex.from_fasta(fa, a=a, l=l, coords=coords, s=s, sample=sample)
            present = set(idx.T)                    # symbols present in this block (prefilter)
            self.blocks.append({"stem": os.path.basename(fa), "idx": idx, "syms": present})

    def locate(self, P, _stats=None):
        P = P.upper()
        results, touched = [], 0
        for b in self.blocks:
            idx = b["idx"]
            codes = idx._encode(P)
            if codes is None or any(c not in b["syms"] for c in set(codes)):
                continue                            # prefilter: a symbol of P is absent from this block
            hits = idx.locate(P)
            if hits:
                touched += 1
            for h in hits:
                h = dict(h); h["block"] = b["stem"]; results.append(h)
        if _stats is not None:
            _stats["touched"] = touched; _stats["blocks"] = len(self.blocks)
        return _dedup_sort(results, genomic=True)

    def species_of(self, P):
        return {h["species"] for h in self.locate(P)}

    @classmethod
    def chrI(cls, n=0, a=4, l=-1, s=4, sample="rate"):
        fastas = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))
        if n:
            fastas = fastas[:n]
        return cls(fastas, a=a, l=l, s=s, sample=sample)
