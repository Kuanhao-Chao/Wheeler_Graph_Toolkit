"""A sharded Wheeler-graph index over a whole-genome MSA.

A single whole-genome De Bruijn graph at a faithful (large) k grows ~linearly with genome length and
pushes the recognizer past its practical ceiling (see benchmark/genome_index/scaling.py). The
practical architecture is therefore SHARDED: one Wheeler graph + FM-index per MAF block (or per
chromosome window), plus a query router.

  build_shards(fastas, k, l, a, work, py_bio)
      For each block FASTA: De Bruijn DOT -> recognizer -w -> a shard dir with I.txt/O.txt/L.txt +
      graph.dot.  Returns a manifest: the Wheeler shards (indexable) and the non-Wheeler/failed ones.

  ShardedGenomeIndex(shard_dirs, engine='cpp'|'py', cpp_bin=...)
      query(P) -> {present, n_shards_hit, total_matches, hits:[(shard_idx, lo, hi, n)]}.
      A pattern occurs in the genome (under this construction) iff it occurs in >=1 shard; the router
      reports WHICH shards and the total node-match count.  Correctness-first: every shard is queried.
      At genome scale a k-mer sketch per shard prefilters which shards to touch (noted; not needed for
      correctness).

The C++ engine ('cpp') runs index/cpp/wg_index per shard; the Python engine ('py') loads WGIndex
objects.  Both must agree with the brute oracle (index/tests/test_genome_index.py).
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from index.wg_index import WGIndex      # noqa: E402
from pipeline import msa_to_index as m2i  # noqa: E402

CPP_BIN = os.path.join(ROOT, "index", "cpp", "wg_index")


# --------------------------------------------------------------------------- build
def build_shards(fastas, k, l, a, work, py_bio=None, write=True):
    """Build one shard per block. Returns {shards:[dir,...], non_wheeler:[fa,...], failed:[(fa,err)]}."""
    os.makedirs(work, exist_ok=True)
    shards, non_wheeler, failed = [], [], []
    for fa in fastas:
        try:
            r = m2i.process_block(fa, k=k, l=l, a=a, work=work, py=py_bio, write=write)
        except Exception as ex:  # noqa: BLE001
            failed.append((os.path.basename(fa), str(ex)[:100])); continue
        if r["verdict"] == 1 and r["outdir"]:
            shards.append(r["outdir"])
        else:
            non_wheeler.append(os.path.basename(fa))
    return {"shards": shards, "non_wheeler": non_wheeler, "failed": failed}


# --------------------------------------------------------------------------- router
class ShardedGenomeIndex:
    def __init__(self, shard_dirs, engine="cpp", cpp_bin=CPP_BIN):
        self.shard_dirs = list(shard_dirs)
        self.engine = engine
        self.cpp_bin = cpp_bin
        self._py = None
        if engine == "py":
            self._py = [WGIndex.from_iol(d) for d in self.shard_dirs]
        elif engine != "cpp":
            raise ValueError("engine must be 'cpp' or 'py'")

    # -- single pattern
    def query(self, pattern):
        hits = []
        if self.engine == "py":
            for i, idx in enumerate(self._py):
                lo, hi, n = idx.count(pattern)
                if n > 0:
                    hits.append((i, lo, hi, n))
        else:
            for i, d in enumerate(self.shard_dirs):
                lo, hi, n = self._cpp_one(d, pattern)
                if n > 0:
                    hits.append((i, lo, hi, n))
        return {"present": bool(hits), "n_shards_hit": len(hits),
                "total_matches": sum(h[3] for h in hits), "hits": hits}

    # -- batch (efficient for many patterns: one subprocess per shard via --queries)
    def query_batch(self, patterns):
        patterns = [p for p in patterns if p]
        if self.engine == "py":
            return {p: self.query(p) for p in patterns}
        # cpp: per shard, run all patterns at once
        per = {p: [] for p in patterns}
        for i, d in enumerate(self.shard_dirs):
            res = self._cpp_batch(d, patterns)
            for p, (lo, hi, n) in res.items():
                if n > 0:
                    per[p].append((i, lo, hi, n))
        return {p: {"present": bool(per[p]), "n_shards_hit": len(per[p]),
                    "total_matches": sum(h[3] for h in per[p]), "hits": per[p]} for p in patterns}

    def _cpp_one(self, outdir, pattern):
        if not pattern:
            # empty pattern -> whole node range; mirror count("")
            r = subprocess.run([self.cpp_bin, outdir, "--query", ""], capture_output=True, text=True)
        else:
            r = subprocess.run([self.cpp_bin, outdir, "--query", pattern], capture_output=True, text=True)
        lo, hi, n = r.stdout.split()
        return int(lo), int(hi), int(n)

    def _cpp_batch(self, outdir, patterns):
        qf = os.path.join(outdir, "_router_q.txt")
        with open(qf, "w") as fh:
            for p in patterns:
                fh.write(p + "\n")
        r = subprocess.run([self.cpp_bin, outdir, "--queries", qf], capture_output=True, text=True)
        out = {}
        for line in r.stdout.splitlines():
            t = line.split()
            if len(t) >= 4:
                out[t[0]] = (int(t[-3]), int(t[-2]), int(t[-1]))
        # patterns absent from output (shouldn't happen) default to empty
        for p in patterns:
            out.setdefault(p, (1, 1, 0))
        return out


def chrI_shards(work, k=4, l=40, a=2, n=80, py_bio=None):
    """Convenience: build the first n chrI block shards (the G3 demo corpus)."""
    fadir = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
    fastas = sorted(glob.glob(os.path.join(fadir, "chrI_*.fa")))[:n]
    return build_shards(fastas, k, l, a, work, py_bio=py_bio)
