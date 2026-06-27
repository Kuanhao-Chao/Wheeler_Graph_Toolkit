"""Persist the two report micro-benchmarks the audit found missing from committed data:
  (a) the suffix-index ROUTER decomposition on chrI (touch-all vs per-block w-mer prefilter vs global
      routed) -> data/suffix_router.json
  (b) C++ wg_suffix locate vs Python SuffixIndex.locate on a real block -> data/cpp_vs_py_suffix.json
Both with warm-cache median latency. Run under python3 (the C++ binary is shelled).
"""
import glob
import json
import os
import random
import statistics as st
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index.pangenome_index import PangenomeIndex   # noqa: E402
from index.suffix_index import SuffixIndex          # noqa: E402
from index.faithful import read_fasta, _ungap_cap   # noqa: E402

FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
CPP = os.path.join(ROOT, "index", "cpp", "wg_suffix")


def med(fn, reps):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    return st.median(ts)


def router_decomposition(a=4, s=4, w=8, reps=15):
    fastas = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))
    pg = PangenomeIndex(fastas, a=a, l=-1, s=s, sample="rate", w=w); pg.build_global()

    def touch_all(P):                              # baseline: locate over every block, no prefilter
        P = P.upper(); out = []
        for b in pg.blocks:
            if b["idx"]._encode(P) is not None:
                out += b["idx"].locate(P)
        return out

    rng = random.Random(1)
    pats = []
    for fa in fastas[:300]:
        for _id, sseq in read_fasta(fa)[:a]:
            u = _ungap_cap(sseq, -1)
            if len(u) >= 12:
                pats.append(u[rng.randint(0, len(u) - 10):][:10])
        if len(pats) >= 60:
            break
    pats = list(dict.fromkeys(pats))[:50]
    ta = 1e3 * med(lambda: [touch_all(P) for P in pats], reps) / len(pats)
    pf = 1e3 * med(lambda: [pg.locate(P) for P in pats], reps) / len(pats)
    rt = 1e3 * med(lambda: [pg.locate_routed(P) for P in pats], reps) / len(pats)
    surv = []
    for P in pats:
        stt = {}; pg.locate(P, _stats=stt); surv.append(stt.get("survivors", 0))
    return {"chrom": "chrI", "blocks": len(pg.blocks), "a": a, "s": s, "w": w,
            "gmap_distinct_wmers": len(pg._gmap), "queries": len(pats),
            "touch_all_ms": round(ta, 4), "wmer_prefilter_ms": round(pf, 4), "routed_ms": round(rt, 5),
            "speedup_prefilter_vs_touchall": round(ta / pf, 1), "speedup_routed_vs_touchall": round(ta / rt, 1),
            "median_survivors": st.median(surv), "of_blocks": len(pg.blocks)}


def cpp_vs_py(reps=200000):
    fa = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))[1]
    idx = SuffixIndex.from_fasta(fa, a=2, l=-1, s=4, sample="rate")
    u = _ungap_cap(read_fasta(fa)[0][1], -1)
    rng = random.Random(1)
    pats = [u[rng.randint(0, len(u) - 6):][:6] for _ in range(1000)]
    t0 = time.perf_counter()
    for i in range(reps):
        idx.locate(pats[i % len(pats)])
    py_us = 1e6 * (time.perf_counter() - t0) / reps
    r = subprocess.run([CPP, fa, "--a", "2", "--l", "-1", "--s", "4", "--bench", str(reps)],
                       capture_output=True, text=True)
    cpp_us = float([t for t in r.stdout.split() if t.startswith("us_per_locate=")][0].split("=")[1])
    return {"block": os.path.basename(fa), "a": 2, "s": 4, "reps": reps,
            "python_us_per_locate": round(py_us, 3), "cpp_us_per_locate": round(cpp_us, 4),
            "speedup_cpp_vs_python": round(py_us / cpp_us, 1)}


if __name__ == "__main__":
    out_router = os.path.join(ROOT, "data", "suffix_router.json")
    out_cpp = os.path.join(ROOT, "data", "cpp_vs_py_suffix.json")
    r1 = router_decomposition()
    json.dump(r1, open(out_router, "w"), indent=2)
    print(json.dumps(r1, indent=2)); print(f"wrote {out_router}")
    r2 = cpp_vs_py()
    json.dump(r2, open(out_cpp, "w"), indent=2)
    print(json.dumps(r2, indent=2)); print(f"wrote {out_cpp}")
