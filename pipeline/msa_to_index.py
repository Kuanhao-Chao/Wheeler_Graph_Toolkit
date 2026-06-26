"""Phase 2 driver: MSA block -> De Bruijn graph -> recognizer (-w) -> succinct WG output.

For one aligned FASTA block it builds the De Bruijn graph with the existing generator, runs the
recognizer with `-w` (emitting the Gagie I/O/L structure + the relabeled Wheeler-order `graph.dot`),
and returns the verdict and the output directory the Phase-3 index consumes. Batch mode reports the
Wheeler rate over many real yeast blocks.

  ~/miniconda3/envs/myenv/bin/python pipeline/msa_to_index.py block.fa -k 4 -l 40 -a 2 --work /tmp/wg
  ~/miniconda3/envs/myenv/bin/python pipeline/msa_to_index.py --batch data/.../yeast/fasta -k 4 -l 40 -a 2
"""
import argparse
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_DIR = os.path.join(ROOT, "generator", "DeBruijnGraph_generator")
GEN_PY = os.path.join(GEN_DIR, "DeBruijnGraph_generator.py")
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")


def build_dot(fasta, k, l, a, out_dot, py=None):
    py = py or sys.executable
    r = subprocess.run([py, GEN_PY, "-o", out_dot, "-k", str(k), "-l", str(l), "-a", str(a),
                        os.path.abspath(fasta)],
                       cwd=GEN_DIR, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(out_dot):
        raise RuntimeError(f"generator failed on {fasta}: {r.stderr.strip()[:300]}")
    return out_dot


def recognize(dot, work, write=True, timeout=120):
    """Run the recognizer (benchmark mode, optionally -w). Returns
    {verdict:1/-1/0, nodes:int, outdir:str|None}."""
    os.makedirs(work, exist_ok=True)
    cmd = [REC, os.path.abspath(dot), "-b", "-o", work + os.sep] + (["-w"] if write else [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    verdict, nodes = 0, None
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[0].lstrip("-").isdigit():
            verdict, nodes = int(parts[0]), int(parts[1])
    stem = os.path.splitext(os.path.basename(dot))[0]
    outdir = os.path.join(work, "out__" + stem)
    return {"verdict": verdict, "nodes": nodes,
            "outdir": outdir if (write and os.path.isdir(outdir)) else None}


def process_block(fasta, k, l, a, work, py=None, write=True):
    stem = os.path.splitext(os.path.basename(fasta))[0]
    dot = os.path.join(work, stem + ".dot")
    os.makedirs(work, exist_ok=True)
    build_dot(fasta, k, l, a, dot, py=py)
    res = recognize(dot, work, write=write)
    res.update({"fasta": os.path.basename(fasta), "dot": dot, "k": k, "l": l, "a": a})
    return res


def batch(fastas, k, l, a, work, py=None, write=False):
    rows, wg = [], 0
    for fa in fastas:
        try:
            r = process_block(fa, k, l, a, work, py=py, write=write)
        except Exception as e:  # noqa: BLE001
            r = {"fasta": os.path.basename(fa), "verdict": None, "error": str(e)[:120]}
        rows.append(r)
        if r.get("verdict") == 1:
            wg += 1
    decided = [r for r in rows if r.get("verdict") in (1, -1)]
    return {"n": len(rows), "wheeler": wg, "decided": len(decided),
            "wheeler_rate": (wg / len(decided) if decided else 0.0), "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fasta", nargs="?")
    ap.add_argument("--batch", help="directory of *.fa blocks to sweep")
    ap.add_argument("-k", type=int, default=4)
    ap.add_argument("-l", type=int, default=40)
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--work", default=os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "wg"))
    args = ap.parse_args()
    if args.batch:
        fastas = sorted(glob.glob(os.path.join(args.batch, "*.fa")))
        if args.limit:
            fastas = fastas[:args.limit]
        summ = batch(fastas, args.k, args.l, args.a, args.work)
        print(f"De Bruijn (k={args.k}, l={args.l}, a={args.a}) over {summ['n']} yeast blocks: "
              f"Wheeler {summ['wheeler']}/{summ['decided']} decided "
              f"({100*summ['wheeler_rate']:.1f}%)")
    elif args.fasta:
        r = process_block(args.fasta, args.k, args.l, args.a, args.work)
        print(f"{r['fasta']}: verdict={r['verdict']} nodes={r['nodes']} outdir={r['outdir']}")
    else:
        ap.error("give a FASTA or --batch <dir>")


if __name__ == "__main__":
    main()
