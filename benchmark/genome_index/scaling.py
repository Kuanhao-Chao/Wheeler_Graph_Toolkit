"""Phase G2 -- genome-scale ceiling study for the Wheeler-graph index pipeline.

Answers "how big a single Wheeler-graph index can each component build?" by constructing real-yeast
De Bruijn graphs of increasing size and measuring, at each size, the wall time + peak RSS of every
pipeline stage SEPARATELY:

  (a) Python De Bruijn generator   (generator/DeBruijnGraph_generator, via myenv Biopython)
  (b) C++ recognizer               (recognizer/bin/recognizer_linux -b -w; records the verdict)
  (c) Python FM-index build        (index/wg_index.py WGIndex.from_iol)
  (d) C++ FM-index build + query   (index/cpp/wg_index --info / --bench)

Two size knobs, both on REAL sequence:
  * De Bruijn order k  -- node count saturates near 4^k, so larger k => more nodes (the node axis);
  * concatenated chrI length (number of MAF blocks) -- edges grow ~linearly with sequence length
    even after the node count saturates (the edge / L-array axis).

Each stage runs under `timeout <S> /usr/bin/time -v ...` so an over-budget stage is recorded, not
hung, and its peak RSS is captured. -> data/genome_scaling.csv + a printed summary of each
component's ceiling and which one binds first.

Run under python3 (the driver shells the generator to myenv).  Harness-tracked background for the
full sweep; --probe prints just the resulting graph sizes for a grid (fast, no measurement).
"""
import argparse
import csv
import glob
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from pipeline import msa_to_index as m2i  # noqa: E402

PY_BIO = os.environ.get("WGT_PY_BIO", os.path.expanduser("~/miniconda3/envs/myenv/bin/python"))
PY_IDX = os.environ.get("WGT_PY", sys.executable)           # for the pure-stdlib Python index
CPP_BIN = os.path.join(ROOT, "index", "cpp", "wg_index")
FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
# reference first, then by descending coverage across chrI blocks (see headers)
SPECIES = ["sacCer3", "sacPar", "sacMik", "sacBay", "sacKud", "sacCas", "sacKlu"]
_RSS = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")


# --------------------------------------------------------------------------- MSA concatenation
def read_fasta(path):
    name, seq, out = None, [], {}
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith(">"):
            if name is not None:
                out[name] = "".join(seq)
            name = line[1:].strip(); seq = []
        else:
            seq.append(line)
    if name is not None:
        out[name] = "".join(seq)
    return out


def build_concat_msa(n_blocks, a, out_fa):
    """Concatenate the first n_blocks chrI blocks into one aligned FASTA over `a` species
    (reference + the next a-1 by coverage); a species absent in a block is gap-filled for that
    block's width, keeping every row the same length (a faithful gapped concatenation)."""
    blocks = sorted(glob.glob(os.path.join(FADIR, "*.fa")))[:n_blocks]
    chosen = SPECIES[:a]
    rows = {sp: [] for sp in chosen}
    for bf in blocks:
        recs = read_fasta(bf)
        width = max(len(s) for s in recs.values())
        for sp in chosen:
            rows[sp].append(recs.get(sp, "-" * width))
    with open(out_fa, "w") as fh:
        for sp in chosen:
            fh.write(f">{sp}\n{''.join(rows[sp])}\n")
    # report ungapped reference length (the effective sequence length driving edges)
    ref = "".join(rows[chosen[0]]).replace("-", "")
    return out_fa, len(ref), len(blocks)


# --------------------------------------------------------------------------- timed subprocess
def timed_run(cmd, timeout_s, cwd=None):
    """Run `timeout S /usr/bin/time -v cmd`. Returns dict(rc, stdout, wall_s, rss_kb, timed_out)."""
    full = ["timeout", str(timeout_s), "/usr/bin/time", "-v"] + cmd
    t0 = time.time()
    p = subprocess.run(full, capture_output=True, text=True, cwd=cwd)
    wall = time.time() - t0
    timed_out = (p.returncode == 124)
    m = _RSS.search(p.stderr)
    rss = int(m.group(1)) if m else None
    return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
            "wall_s": round(wall, 3), "rss_kb": rss, "timed_out": timed_out}


# --------------------------------------------------------------------------- one (n_blocks, k) point
def measure(n_blocks, k, a, l_cap, work, budget):
    row = {"n_blocks": n_blocks, "k": k, "a": a}
    fa = os.path.join(work, f"concat_b{n_blocks}_a{a}.fa")
    _, reflen, nb = build_concat_msa(n_blocks, a, fa)
    row["ref_len"] = reflen

    dot = os.path.join(work, f"g_b{n_blocks}_k{k}_a{a}.dot")
    # (a) generator
    g = timed_run([PY_BIO, m2i.GEN_PY, "-o", dot, "-k", str(k), "-l", str(l_cap), "-a", str(a),
                   os.path.abspath(fa)], budget["gen"], cwd=m2i.GEN_DIR)
    row["gen_s"] = g["wall_s"]; row["gen_rss_kb"] = g["rss_kb"]; row["gen_to"] = g["timed_out"]
    if g["rc"] != 0 or not os.path.exists(dot):
        row["stage_failed"] = "generator"; return row
    # count nodes/edges directly from the DOT
    nodes, edges = count_dot(dot)
    row["dot_nodes"] = nodes; row["dot_edges"] = edges

    # (b) recognizer (-b -w)
    rwork = os.path.join(work, f"rec_b{n_blocks}_k{k}")
    os.makedirs(rwork, exist_ok=True)
    rec = timed_run([m2i.REC, os.path.abspath(dot), "-b", "-w", "-o", rwork + os.sep], budget["rec"])
    row["rec_s"] = rec["wall_s"]; row["rec_rss_kb"] = rec["rss_kb"]; row["rec_to"] = rec["timed_out"]
    verdict = None
    for line in rec["stdout"].splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[0].lstrip("-").isdigit():
            verdict = int(parts[0])
    row["verdict"] = verdict
    stem = os.path.splitext(os.path.basename(dot))[0]
    outdir = os.path.join(rwork, "out__" + stem)
    if rec["timed_out"] or verdict != 1 or not os.path.isdir(outdir):
        row["stage_failed"] = "recognizer"; return row

    # (c) Python index build (subprocess: from_iol + report wall; RSS via /usr/bin/time)
    snippet = (f"import time,sys; sys.path.insert(0,{ROOT!r}); "
               f"from index.wg_index import WGIndex; "
               f"t=time.time(); idx=WGIndex.from_iol({outdir!r}); "
               f"print('PYIDX_S', time.time()-t, 'n', idx.n, 'E', idx.E)")
    pi = timed_run([PY_IDX, "-c", snippet], budget["pyidx"])
    row["pyidx_to"] = pi["timed_out"]; row["pyidx_rss_kb"] = pi["rss_kb"]
    mptr = re.search(r"PYIDX_S ([\d.]+)", pi["stdout"])
    row["pyidx_s"] = round(float(mptr.group(1)), 3) if mptr else None
    if pi["timed_out"] or mptr is None:
        row["pyidx_failed"] = True       # record the ceiling but keep going for the C++ index

    # (d) C++ index build + query
    ci = timed_run([CPP_BIN, outdir, "--info"], budget["cppidx"])
    mb = re.search(r"build_ms=([\d.]+)", ci["stdout"])
    row["cppidx_build_ms"] = round(float(mb.group(1)), 3) if mb else None
    row["cppidx_rss_kb"] = ci["rss_kb"]; row["cppidx_to"] = ci["timed_out"]
    cb = timed_run([CPP_BIN, outdir, "--bench", "200000"], budget["cppidx"])
    mq = re.search(r"us_per_query=([\d.]+)", cb["stdout"])
    row["cppidx_us_per_query"] = float(mq.group(1)) if mq else None
    return row


_ER = re.compile(r"(\w+)\s*->\s*(\w+)\s*\[")


def count_dot(path):
    nodes, e = set(), 0
    for line in open(path):
        m = _ER.search(line.replace(" ", "")) or _ER.search(line)
        if m:
            nodes.update((m.group(1), m.group(2))); e += 1
    return len(nodes), e


# --------------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", default="4,6,8,10,12,16,20", help="comma De Bruijn orders")
    ap.add_argument("--blocks", default="20,80,300", help="comma chrI block counts (length axis)")
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--l-cap", type=int, default=10_000_000, help="generator seqLen cap (large=no cap)")
    ap.add_argument("--work", default="/dev/shm/wg_scaling")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "genome_scaling.csv"))
    ap.add_argument("--gen-budget", type=int, default=600)
    ap.add_argument("--rec-budget", type=int, default=600)
    ap.add_argument("--pyidx-budget", type=int, default=300)
    ap.add_argument("--cppidx-budget", type=int, default=120)
    ap.add_argument("--probe", action="store_true", help="just print resulting graph sizes, no timing")
    args = ap.parse_args()

    if not os.path.exists(CPP_BIN):
        subprocess.run(["make", "-s"], cwd=os.path.dirname(CPP_BIN))
    os.makedirs(args.work, exist_ok=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    ks = [int(x) for x in args.ks.split(",")]
    blocks = [int(x) for x in args.blocks.split(",")]
    budget = {"gen": args.gen_budget, "rec": args.rec_budget,
              "pyidx": args.pyidx_budget, "cppidx": args.cppidx_budget}

    if args.probe:
        for nb in blocks:
            fa = os.path.join(args.work, f"concat_b{nb}_a{args.a}.fa")
            _, reflen, _ = build_concat_msa(nb, args.a, fa)
            for k in ks:
                dot = os.path.join(args.work, f"probe_b{nb}_k{k}.dot")
                r = subprocess.run([PY_BIO, m2i.GEN_PY, "-o", dot, "-k", str(k),
                                    "-l", str(args.l_cap), "-a", str(args.a), os.path.abspath(fa)],
                                   cwd=m2i.GEN_DIR, capture_output=True, text=True)
                if r.returncode == 0 and os.path.exists(dot):
                    n, e = count_dot(dot)
                    print(f"blocks={nb:4d} ref_len={reflen:7d} k={k:3d} -> nodes={n:7d} edges={e:8d}")
                else:
                    print(f"blocks={nb:4d} k={k:3d} -> GEN FAIL {r.stderr.strip()[:80]}")
        return

    # resume: keep rows already measured (keyed by n_blocks,k,a) so a focused re-run extends the CSV
    done = {}
    if os.path.exists(args.out):
        import csv as _csv
        for r in _csv.DictReader(open(args.out)):
            try:
                key = (int(r["n_blocks"]), int(r["k"]), int(r["a"]))
            except (KeyError, ValueError):
                continue
            for kk, vv in list(r.items()):           # coerce numeric-looking fields back
                if vv == "":
                    r[kk] = None
            done[key] = r
    rows = list(done.values())
    for nb in blocks:
        for k in ks:
            if (nb, k, args.a) in done:
                print(f"[skip] blocks={nb} k={k} a={args.a} (already in CSV)", flush=True)
                continue
            print(f"[measure] blocks={nb} k={k} a={args.a} ...", flush=True)
            try:
                r = measure(nb, k, args.a, args.l_cap, args.work, budget)
            except Exception as ex:  # noqa: BLE001
                r = {"n_blocks": nb, "k": k, "a": args.a, "error": str(ex)[:120]}
            rows.append(r)
            print(f"   -> nodes={r.get('dot_nodes')} edges={r.get('dot_edges')} "
                  f"verdict={r.get('verdict')} rec_s={r.get('rec_s')} "
                  f"pyidx_s={r.get('pyidx_s')} pyidx_to={r.get('pyidx_to')} "
                  f"cppidx_build_ms={r.get('cppidx_build_ms')}", flush=True)
            write_csv(rows, args.out)
    write_csv(rows, args.out)
    summarize(rows)
    print(f"wrote {args.out}")


COLS = ["n_blocks", "k", "a", "ref_len", "dot_nodes", "dot_edges", "verdict",
        "gen_s", "gen_rss_kb", "gen_to", "rec_s", "rec_rss_kb", "rec_to",
        "pyidx_s", "pyidx_rss_kb", "pyidx_to", "pyidx_failed",
        "cppidx_build_ms", "cppidx_rss_kb", "cppidx_us_per_query", "cppidx_to",
        "stage_failed", "error"]


def write_csv(rows, out):
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore"); w.writeheader()
        for r in rows:
            w.writerow(r)


def summarize(rows):
    ok = [r for r in rows if r.get("dot_nodes")]
    print("\n=== ceilings ===")
    rec_ok = [r for r in ok if r.get("verdict") == 1 and not r.get("rec_to")]
    if rec_ok:
        big = max(rec_ok, key=lambda r: r["dot_nodes"])
        print(f"recognizer: largest accepted graph nodes={big['dot_nodes']} edges={big['dot_edges']} "
              f"(rec_s={big['rec_s']}, rss={big.get('rec_rss_kb')}KB)")
    pyf = [r for r in ok if r.get("pyidx_to") or r.get("pyidx_failed")]
    pyok = [r for r in ok if r.get("pyidx_s") is not None]
    if pyok:
        bigpy = max(pyok, key=lambda r: r["dot_edges"])
        print(f"Python index: largest built edges={bigpy['dot_edges']} (pyidx_s={bigpy['pyidx_s']}, "
              f"rss={bigpy.get('pyidx_rss_kb')}KB)")
    if pyf:
        small_fail = min(pyf, key=lambda r: r["dot_edges"])
        print(f"Python index: first failure at edges={small_fail['dot_edges']} "
              f"(to={small_fail.get('pyidx_to')})")
    cppok = [r for r in ok if r.get("cppidx_build_ms") is not None]
    if cppok:
        bigc = max(cppok, key=lambda r: r["dot_edges"])
        print(f"C++ index: largest built edges={bigc['dot_edges']} (build_ms={bigc['cppidx_build_ms']}, "
              f"rss={bigc.get('cppidx_rss_kb')}KB, {bigc.get('cppidx_us_per_query')}us/query)")


if __name__ == "__main__":
    main()
