"""Memory measurement for the suffix pangenome index: peak RSS (process) + in-memory footprint
(structure-by-structure), reused by the chrI/genome scale benchmarks.

  peak_rss_build(fastas, a, s, sample, w)  -> peak RSS (kB) of building a PangenomeIndex (subprocess +
                                              /usr/bin/time -v), reusing scaling.timed_run.
  inmem_footprint(idx)                     -> {field: bytes} for one SuffixIndex (deep sizeof).
  pangenome_footprint(pg)                  -> per-block sum + the router (_gmap, wmers) breakdown.
"""
import os
import sys
from sys import getsizeof

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from benchmark.genome_index.scaling import timed_run  # noqa: E402

PY = sys.executable


def deep_size(o, _seen=None):
    """Recursive sizeof over lists/tuples/dicts/sets of ints/strs (no double-count)."""
    if _seen is None:
        _seen = set()
    oid = id(o)
    if oid in _seen:
        return 0
    _seen.add(oid)
    sz = getsizeof(o)
    if isinstance(o, (list, tuple, set)):
        sz += sum(deep_size(x, _seen) for x in o)
    elif isinstance(o, dict):
        sz += sum(deep_size(k, _seen) + deep_size(v, _seen) for k, v in o.items())
    return sz


def inmem_footprint(idx):
    f = {
        "T": deep_size(idx.T), "BWT": deep_size(idx.BWT), "DOC": deep_size(idx.DOC),
        "doc": deep_size(idx.doc), "doc_start": deep_size(idx.doc_start),
        "block_rank": deep_size(idx._brank),
        "sa_val": deep_size(idx.sa_val), "sampled": deep_size(idx.sampled),
        "phi": deep_size(idx._phi_keys) + deep_size(idx._phi_vals)
               + deep_size(idx._tail_rows) + deep_size(idx._tail_sa),
        "SA": deep_size(idx.SA) if idx.SA is not None else 0,
        "coords": deep_size(idx.coords),
    }
    f["total"] = sum(f.values())
    return f


def pangenome_footprint(pg):
    per_block = {}
    for b in pg.blocks:
        for k, v in inmem_footprint(b["idx"]).items():
            per_block[k] = per_block.get(k, 0) + v
        per_block["wmers"] = per_block.get("wmers", 0) + deep_size(b["wmers"])
    router = deep_size(pg._gmap) if getattr(pg, "_gmap", None) else 0
    blocks_total = sum(v for k, v in per_block.items() if k != "total")
    return {"blocks": len(pg.blocks), "per_structure": per_block,
            "blocks_total_bytes": blocks_total, "router_gmap_bytes": router,
            "total_bytes": blocks_total + router}


def peak_rss_build(fastas, a=4, s=4, sample="rate", w=8, timeout_s=1200):
    """Peak RSS (kB) of building a PangenomeIndex over `fastas` in a fresh subprocess. The fasta list is
    passed via a temp JSON file (NOT embedded in the command line -- a chromosome's list exceeds ARG_MAX)."""
    import json
    import tempfile
    lf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(list(fastas), lf); lf.close()
    snippet = (
        f"import sys, json; sys.path.insert(0,{ROOT!r}); "
        f"from index.pangenome_index import PangenomeIndex; "
        f"fas=json.load(open({lf.name!r})); "
        f"pg=PangenomeIndex(fas, a={a}, l=-1, s={s}, sample={sample!r}, w={w}); pg.build_global(); "
        f"print('BLOCKS', len(pg.blocks))"
    )
    r = timed_run([PY, "-c", snippet], timeout_s)
    os.remove(lf.name)
    return {"rss_kb": r["rss_kb"], "wall_s": r["wall_s"], "timed_out": r["timed_out"],
            "blocks": int(r["stdout"].split("BLOCKS")[1].split()[0]) if "BLOCKS" in r["stdout"] else None}


if __name__ == "__main__":
    import glob
    import json
    from index.pangenome_index import PangenomeIndex
    fas = sorted(glob.glob(os.path.join(ROOT, "data/multiseq_alignment/yeast/fasta/chrI_*.fa")))[:60]
    pg = PangenomeIndex(fas, a=4, l=-1, s=4, sample="rate", w=8); pg.build_global()
    print(json.dumps(pangenome_footprint(pg), indent=2)[:1200])
    print(json.dumps(peak_rss_build(fas, a=4, s=4), indent=2))
