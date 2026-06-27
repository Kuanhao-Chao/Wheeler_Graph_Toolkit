"""Brute-force ground truth for LOCATE: where does a string occur, in which species, at which
genomic coordinate?

Independent of index/locate.py on purpose: it inlines its OWN ungap/cap and its OWN MAF coordinate
transform, so a shared bug cannot hide in both the index and its oracle. The only shared code is
plain FASTA reading (plumbing, not locate logic).

`locate_brute(fasta, coords, P, a, l)` scans every position of every (first-`a`, ungapped, capped)
record for P and returns the exact set of genomic occurrences as tuples
  (species, src, gstart, gend, strand)
with 0-based half-open coordinates on the + strand of each source.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from index.faithful import read_fasta  # noqa: E402  (plumbing only)


def _ungap_cap(seq, l):
    """Inlined ungap + upper + cap (own copy; do NOT reuse the index's). l in (None,-1) -> no cap."""
    u = seq.replace("-", "").upper()
    if l is None or l < 0 or l >= len(u):
        return u
    return u[:l]


def transform(coord, pos, m):
    """Inlined coordinate transform (own copy). Ungapped offset `pos`, length `m` -> (gstart, gend,
    strand), 0-based half-open on the + strand of the source. For a - strand record the + strand
    holds revcomp(P) over [gstart, gend)."""
    start, size, strand, srcSize = coord["start"], coord["size"], coord["strand"], coord["srcSize"]
    if strand == "-":
        return (srcSize - (start + pos + m), srcSize - (start + pos), "-")
    return (start + pos, start + pos + m, "+")


def locate_brute(fasta, coords, P, a=None, l=None):
    """Exact set of (species, src, gstart, gend, strand) where P occurs in the indexed content."""
    P = P.upper()
    recs = read_fasta(fasta)
    if a is not None:
        recs = recs[:a]
    out = set()
    m = len(P)
    if m == 0:
        return out
    for i, (_rid, seq) in enumerate(recs):
        u = _ungap_cap(seq, l)
        c = coords[i]
        for pos in range(len(u) - m + 1):
            if u[pos:pos + m] == P:
                gs, ge, st = transform(c, pos, m)
                out.add((c["fasta_id"], c["src"], gs, ge, st))
    return out
