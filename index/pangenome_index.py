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


def _block_wmers(idx, w):
    """The set of length-w DNA substrings of a block, decoded from idx.T (the INDEXED content, so the
    set is sound: every w-mer of every indexed occurrence is present). Separators (codes < a) split
    documents; DNA codes (>= a) decode to ACGT."""
    out, cur = set(), []
    for code in idx.T:
        if code < idx.a:                            # separator -> document boundary
            for i in range(len(cur) - w + 1):
                out.add("".join(cur[i:i + w]))
            cur = []
        else:
            cur.append("ACGT"[code - idx.a])
    for i in range(len(cur) - w + 1):               # final document (T ends with a separator, so usually empty)
        out.add("".join(cur[i:i + w]))
    return out


class PangenomeIndex:
    def __init__(self, fastas, a=4, l=-1, s=4, sample="rate", w=8):
        self.w = w
        self.blocks = []
        for fa in fastas:
            cpath = fa.replace(".fa", ".coords.json")
            coords = json.load(open(cpath)) if os.path.exists(cpath) else None
            idx = SuffixIndex.from_fasta(fa, a=a, l=l, coords=coords, s=s, sample=sample)
            self.blocks.append({"stem": os.path.basename(fa), "idx": idx,
                                "syms": set(idx.T),                 # cheap symbol pre-check
                                "wmers": _block_wmers(idx, w)})     # SOUND selective prefilter
        self._gmap = None

    def _survives(self, b, P, codes):
        """SOUND per-block prefilter: skip a block only if it cannot contain P (a symbol or, for
        |P|>=w, a w-mer of P is absent). If P occurs in B then all its w-mers occur in B, so a survivor
        is never a false negative; exact per-block locate then removes false survivors."""
        if codes is None or any(c not in b["syms"] for c in set(codes)):
            return False
        if len(P) >= self.w:
            wm = b["wmers"]
            return all(P[i:i + self.w] in wm for i in range(len(P) - self.w + 1))
        return True                                # |P| < w -> cannot filter on w-mers; query the block

    def locate(self, P, _stats=None):
        P = P.upper()
        results, touched, survivors = [], 0, 0
        for b in self.blocks:
            if not self._survives(b, P, b["idx"]._encode(P)):
                continue
            survivors += 1
            hits = b["idx"].locate(P)
            if hits:
                touched += 1
            for h in hits:
                h = dict(h); h["block"] = b["stem"]; results.append(h)
        if _stats is not None:
            _stats.update({"touched": touched, "survivors": survivors, "blocks": len(self.blocks)})
        return _dedup_sort(results, genomic=True)

    # --------------------------------------------------------------- global w-mer router (genome-scale)
    def build_global(self):
        """Global w-mer -> sorted block-id list. A genome query intersects the lists of P's w-mers, so
        only the (few) candidate blocks are touched -- the genome-size-independent routing of the
        De Bruijn locate (index/locate.GenomeLocateIndex), reused here over the suffix shards."""
        g = {}
        for bi, b in enumerate(self.blocks):
            for wm in b["wmers"]:
                g.setdefault(wm, []).append(bi)
        self._gmap = g
        return self

    def locate_routed(self, P, _stats=None):
        P = P.upper()
        if self._gmap is None:
            self.build_global()
        if len(P) < self.w:
            return self.locate(P, _stats)          # too short to route -> fall back (still sound)
        wmers = [P[i:i + self.w] for i in range(len(P) - self.w + 1)]
        lists = [self._gmap.get(wm) for wm in set(wmers)]
        if any(lst is None for lst in lists):      # a w-mer of P is in no block -> P is genome-absent
            cands = []
        else:
            cands = set(min(lists, key=len))       # intersect, starting from the rarest w-mer
            for lst in lists:
                cands &= set(lst)
        results, touched = [], 0
        for bi in cands:
            b = self.blocks[bi]
            hits = b["idx"].locate(P)
            if hits:
                touched += 1
            for h in hits:
                h = dict(h); h["block"] = b["stem"]; results.append(h)
        if _stats is not None:
            _stats.update({"touched": touched, "candidates": len(cands), "blocks": len(self.blocks)})
        return _dedup_sort(results, genomic=True)

    def species_of(self, P):
        return {h["species"] for h in self.locate(P)}

    @classmethod
    def chrI(cls, n=0, a=4, l=-1, s=4, sample="rate"):
        fastas = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))
        if n:
            fastas = fastas[:n]
        return cls(fastas, a=a, l=l, s=s, sample=sample)
