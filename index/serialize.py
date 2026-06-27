"""Serialize the suffix pangenome index to disk: build once, load fast, measure footprint.

Two formats (both zlib-compressed):
  * "rebuild" -- store just the decoded DNA rows + params; load = full rebuild (incl. the O(n log^2 n)
    suffix sort). Smallest on disk (only the sequence text).
  * "arrays"  -- store the SA-derived arrays (BWT, DOC, the SA samples + phi structure, doc_start, T);
    load reconstructs the index WITHOUT re-sorting suffixes (rebuilds only the cheap C[]/block-rank/doc).
    Larger on disk, fast load. Recommended for the genome index.

A loaded index answers `locate`/`count` identically to a freshly built one (its `SA` is None either way --
SA is a build intermediate no query path uses). Pure stdlib.
"""
import os
import pickle
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from index.suffix_index import SuffixIndex, build_text, dna_code  # noqa: E402


def decode_seqs(T, a):
    """Inverse of build_text: recover the ungapped DNA rows from the encoded text (separators < a)."""
    seqs, cur = [], []
    for code in T:
        if code < a:
            seqs.append("".join(cur)); cur = []
        else:
            cur.append("ACGT"[code - a])
    return seqs


# ----------------------------------------------------------------- single SuffixIndex
def _arrays_blob(idx):
    return {
        "fmt": "arrays", "a": idx.a, "n": idx.n, "s": idx.s, "sample": idx.sample_mode,
        "sigma": idx.sigma, "r": idx.r, "n_samples": idx.n_samples,
        "T": idx.T, "BWT": idx.BWT, "DOC": idx.DOC, "doc_start": idx.doc_start,
        "sa_val": idx.sa_val, "sampled": idx.sampled,
        "phi_keys": idx._phi_keys, "phi_vals": idx._phi_vals,
        "tail_rows": idx._tail_rows, "tail_sa": idx._tail_sa, "sa_bottom": idx._sa_bottom,
        "coords": idx.coords,
    }


def _from_arrays(b):
    idx = SuffixIndex.__new__(SuffixIndex)
    idx.a = b["a"]; idx.n = b["n"]; idx.s = b["s"]; idx.sample_mode = b["sample"]
    idx.sigma = b["sigma"]; idx.r = b["r"]; idx.n_samples = b["n_samples"]
    idx.T = b["T"]; idx.BWT = b["BWT"]; idx.DOC = b["DOC"]; idx.doc_start = b["doc_start"]
    idx.sa_val = b["sa_val"]; idx.sampled = b["sampled"]
    idx._phi_keys = b["phi_keys"]; idx._phi_vals = b["phi_vals"]
    idx._tail_rows = b["tail_rows"]; idx._tail_sa = b["tail_sa"]; idx._sa_bottom = b["sa_bottom"]
    idx.coords = b["coords"]
    idx.SA = None                                  # build intermediate; no query path uses it
    idx.code = dna_code(idx.a)
    # rebuild the cheap derived structures (NOT the expensive suffix sort)
    idx.doc = []
    for d in range(idx.a):
        end = idx.doc_start[d + 1] if d + 1 < idx.a else idx.n
        idx.doc += [d] * (end - idx.doc_start[d])
    cnt = [0] * idx.sigma
    for x in idx.T:
        cnt[x] += 1
    idx.C = [0] * idx.sigma
    run = 0
    for c in range(idx.sigma):
        idx.C[c] = run; run += cnt[c]
    idx._build_rank()
    return idx


def dumps(idx, fmt="arrays"):
    if fmt == "rebuild":
        blob = {"fmt": "rebuild", "seqs": decode_seqs(idx.T, idx.a),
                "s": idx.s, "sample": idx.sample_mode, "coords": idx.coords}
    else:
        blob = _arrays_blob(idx)
    return zlib.compress(pickle.dumps(blob, protocol=pickle.HIGHEST_PROTOCOL), 6)


def loads(data):
    b = pickle.loads(zlib.decompress(data))
    if b["fmt"] == "rebuild":
        return SuffixIndex(b["seqs"], coords=b["coords"], s=b["s"], sample=b["sample"])
    return _from_arrays(b)


def save(idx, path, fmt="arrays"):
    with open(path, "wb") as f:
        f.write(dumps(idx, fmt))
    return os.path.getsize(path)


def load(path):
    with open(path, "rb") as f:
        return loads(f.read())


# ----------------------------------------------------------------- whole PangenomeIndex
def save_pangenome(pg, path, fmt="arrays"):
    """Persist every block index + the build params. The router (_gmap/wmers) is rebuilt on load."""
    blocks = [{"stem": b["stem"], "idx": dumps(b["idx"], fmt)} for b in pg.blocks]
    blob = {"w": pg.w, "blocks": blocks}
    with open(path, "wb") as f:
        f.write(zlib.compress(pickle.dumps(blob, protocol=pickle.HIGHEST_PROTOCOL), 6))
    return os.path.getsize(path)


def load_pangenome(path):
    from index.pangenome_index import PangenomeIndex, _block_wmers
    with open(path, "rb") as f:
        blob = pickle.loads(zlib.decompress(f.read()))
    pg = PangenomeIndex.__new__(PangenomeIndex)
    pg.w = blob["w"]; pg._gmap = None; pg.blocks = []
    for bl in blob["blocks"]:
        idx = loads(bl["idx"])
        pg.blocks.append({"stem": bl["stem"], "idx": idx,
                          "syms": set(idx.T), "wmers": _block_wmers(idx, pg.w)})
    return pg
