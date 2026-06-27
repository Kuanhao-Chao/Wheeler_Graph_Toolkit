"""Locate over the sharded Wheeler-graph k-mer index: given a DNA string P, report every occurrence
as (species, source/contig, genomic coordinate, strand) — multiple hits included.

The biology the membership index couldn't answer. Design (correctness-first; see index/LOCATE.md):

  * Per shard (one MAF block), a forward inverted index `occ`: K-mer -> [(record_idx, ungapped_pos)]
    (K = k-1), built by one scan of the same ungapped/capped first-`a` records the De Bruijn graph was
    built from. Plus the per-record genomic coords (the `<stem>.coords.json` sidecar).
  * `locate_shard(P)`:
      1. FM PREFILTER — `count(reverse(P))` on the shard's Wheeler FM-index (the recognized index under
         test). It is SOUND (every real substring => count>0), so count==0 lets us skip the shard.
      2. CANDIDATES — if |P|>=K, the occurrences of P's first K-mer; else a direct scan (short shards).
      3. VERIFY — char-compare the ungapped sequence at each candidate (kills the De Bruijn recombinant
         superset's false positives). Only verified hits are emitted -> EXACT.
  * Positions are computed forward (the reverse convention touches only the prefilter), then mapped to
    genomic coordinates per strand (UCSC 0-based half-open).

`GenomeLocateIndex` composes this across all shards (the per-shard count==0 skip is the speed lever)
and aggregates/dedups/sorts. Verified exactly against index/locate_oracle.py and, for the reference
species, against the real sacCer3 genome.

Pure stdlib; the FM prefilter uses index/wg_index.WGIndex (in-process) or the C++ binary.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from index.faithful import _ungap_cap, read_fasta  # noqa: E402
from index.wg_index import WGIndex                  # noqa: E402

CPP_BIN = os.path.join(ROOT, "index", "cpp", "wg_index")


# --------------------------------------------------------------------------- coordinate transform
def transform(coord, pos, m):
    """Ungapped offset `pos`, length `m` -> (gstart, gend, strand): 0-based half-open on the + strand
    of the source. For a - strand record the + strand holds revcomp(P) over [gstart, gend)."""
    start, size, strand, srcSize = coord["start"], coord["size"], coord["strand"], coord["srcSize"]
    if strand == "-":
        return (srcSize - (start + pos + m), srcSize - (start + pos), "-")
    return (start + pos, start + pos + m, "+")


# --------------------------------------------------------------------------- per-shard locate sample
def build_locate_sample(fasta, k, a=None, l=-1):
    """{seqs, recs, K, occ}: the ungapped/capped first-`a` records + a K-mer (K=k-1) inverted index."""
    recs = read_fasta(fasta)
    if a is not None:
        recs = recs[:a]
    seqs = [_ungap_cap(seq, l) for _id, seq in recs]
    K = k - 1
    occ = {}
    for i, u in enumerate(seqs):
        for pos in range(len(u) - K + 1):
            occ.setdefault(u[pos:pos + K], []).append((i, pos))
    return {"seqs": seqs, "recs": [rid for rid, _ in recs], "K": K, "occ": occ}


def locate_shard(P, sample, coords, count_fn=None):
    """Exact occurrences of P in this shard's content -> list of hit dicts. `count_fn(W)->(lo,hi,n)`
    is the optional FM prefilter (skip when count(reverse(P))==0)."""
    P = P.upper()
    m = len(P)
    if m == 0:
        return []
    if count_fn is not None:
        _lo, _hi, n = count_fn(P[::-1])      # reverse convention -- prefilter ONLY
        if n == 0:
            return []
    seqs, K, occ = sample["seqs"], sample["K"], sample["occ"]
    if m >= K and K > 0:
        cands = occ.get(P[:K], [])
    else:                                    # |P| < K (or K==0): direct scan of the short shard seqs
        cands = [(i, pos) for i, u in enumerate(seqs) for pos in range(len(u) - m + 1)]
    hits = []
    for (i, pos) in cands:
        if seqs[i][pos:pos + m] == P:        # VERIFY against the actual sequence
            c = coords[i]
            gs, ge, st = transform(c, pos, m)
            hits.append({"species": c["fasta_id"], "src": c["src"], "gstart": gs, "gend": ge,
                         "strand": st, "record_idx": i, "ungapped_pos": pos})
    return hits


def as_tuples(hits):
    """Project hit dicts to the comparable genomic-occurrence set (species, src, gstart, gend, strand)."""
    return {(h["species"], h["src"], h["gstart"], h["gend"], h["strand"]) for h in hits}


# --------------------------------------------------------------------------- the genome-wide router
def _cpp_count_fn(outdir, binary=CPP_BIN):
    def count(W):
        r = subprocess.run([binary, outdir, "--query", W], capture_output=True, text=True)
        lo, hi, n = r.stdout.split()
        return int(lo), int(hi), int(n)
    return count


class GenomeLocateIndex:
    """Locate across all shards. Lazily builds per-shard locate samples + coords + FM prefilter.

    shard_dirs : recognizer out__<stem>/ dirs (Wheeler shards).
    fadir      : where <stem>.fa and <stem>.coords.json live.
    engine     : 'py' (in-process WGIndex.count) | 'cpp' (per-shard binary) | 'none' (no prefilter).
    """
    def __init__(self, shard_dirs, fadir, k, a=None, l=-1, engine="py"):
        self.k, self.a, self.l, self.engine = k, a, l, engine
        self.shards = []
        for d in shard_dirs:
            stem = os.path.basename(os.path.normpath(d))
            if stem.startswith("out__"):
                stem = stem[len("out__"):]
            fasta = os.path.join(fadir, stem + ".fa")
            coords = json.load(open(os.path.join(fadir, stem + ".coords.json")))
            sample = build_locate_sample(fasta, k, a, l)
            if engine == "py":
                count_fn = WGIndex.from_iol(d).count
            elif engine == "cpp":
                count_fn = _cpp_count_fn(d)
            else:
                count_fn = None
            self.shards.append({"stem": stem, "dir": d, "sample": sample,
                                "coords": coords, "count_fn": count_fn})

    def locate(self, P, _stats=None):
        results, survivors = [], 0
        for sh in self.shards:
            hits = locate_shard(P, sh["sample"], sh["coords"], sh["count_fn"])
            if hits:
                survivors += 1
            for h in hits:
                h = dict(h); h["shard"] = sh["stem"]; results.append(h)
        if _stats is not None:
            _stats["survivors"] = survivors
            _stats["shards"] = len(self.shards)
        # dedup exact genomic tuple; keep richest record per tuple; sort
        seen, out = set(), []
        for h in sorted(results, key=lambda h: (h["species"], h["src"], h["gstart"], h["gend"])):
            key = (h["species"], h["src"], h["gstart"], h["gend"], h["strand"])
            if key not in seen:
                seen.add(key); out.append(h)
        return out


# --------------------------------------------------------------------------- naive baseline (for the demo)
def locate_naive(fastas_coords, P, a=None, l=-1):
    """Brute-force genome-wide locate with NO index: scan every record of every block. Returns the
    same dedup'd hit list shape as GenomeLocateIndex.locate. `fastas_coords` = [(fasta, coords), ...]."""
    P = P.upper()
    m = len(P)
    out, seen = [], set()
    if m == 0:
        return out
    for fasta, coords in fastas_coords:
        recs = read_fasta(fasta)
        if a is not None:
            recs = recs[:a]
        for i, (_rid, seq) in enumerate(recs):
            u = _ungap_cap(seq, l)
            c = coords[i]
            for pos in range(len(u) - m + 1):
                if u[pos:pos + m] == P:
                    gs, ge, st = transform(c, pos, m)
                    key = (c["fasta_id"], c["src"], gs, ge, st)
                    if key not in seen:
                        seen.add(key)
                        out.append({"species": c["fasta_id"], "src": c["src"], "gstart": gs,
                                    "gend": ge, "strand": st})
    out.sort(key=lambda h: (h["species"], h["src"], h["gstart"], h["gend"]))
    return out
