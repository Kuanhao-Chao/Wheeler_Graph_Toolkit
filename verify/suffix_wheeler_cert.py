"""Certify that the tagged suffix index's order IS a Wheeler order (closing the theory<->implementation
loop with the recognizer).

The FM-index is the canonical Wheeler graph (Gagie-Manzini-Siren): nodes = suffixes in sorted order,
the Wheeler order = the suffix-array rank, edges = the LF map. We exhibit that graph explicitly --
node `i` (the i-th smallest suffix) --LF--> node `LF(i)` labeled `BWT[i]` -- and check three ways:
  1. the SA-rank order is a valid Wheeler order        (verify/check_order on pos = identity);
  2. brute force agrees it is Wheeler                  (verify/brute_oracle, n<=9);
  3. the real recognizer independently accepts it      (recognizer_linux -i -w),
     and its emitted Wheeler order is order-isomorphic to the SA rank.

Run under python3. Integer labels (the symbol codes) + recognizer `-i` so its numeric label rank
matches our separators<DNA ordering.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import brute_oracle as bo            # noqa: E402
import check_order as co            # noqa: E402
from index import suffix_index as sx  # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")


def suffix_graph(idx):
    """The BWT/LF Wheeler graph of a SuffixIndex: nodes 0..n-1 (= SA rank), edge i -> LF(i) label BWT[i]."""
    nodes = list(range(idx.n))
    edges = [(i, idx.lf(i), str(idx.BWT[i])) for i in range(idx.n)]
    return nodes, edges


def write_dot(nodes, edges, path):
    with open(path, "w") as f:
        f.write("strict digraph  {\n")
        for (u, v, l) in edges:
            f.write(f"\t{u} -> {v} [label={l}];\n")
        f.write("}\n")


def _run_recognizer(dot, work):
    os.makedirs(work, exist_ok=True)
    cmd = [REC, os.path.abspath(dot), "-i", "-b", "-w", "-o", work + os.sep]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    verdict = None
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[0].lstrip("-").isdigit():
            verdict = int(parts[0])
    stem = os.path.splitext(os.path.basename(dot))[0]
    outdir = os.path.join(work, "out__" + stem)
    return verdict, (outdir if os.path.isdir(outdir) else None)


def certify(idx, work, run_recognizer=True):
    """Return a dict of the three certifications. `idx` is a built SuffixIndex."""
    nodes, edges = suffix_graph(idx)
    lr = bo.rank_labels(edges, int_mode=True)
    res = {"n": idx.n}

    # 1. the SA-rank (identity) order is a valid Wheeler order
    pos_identity = {i: i for i in range(idx.n)}
    ok1, reason1 = co.check(nodes, edges, lr, pos_identity)
    res["sa_order_is_wheeler"] = ok1
    res["sa_order_reason"] = reason1

    # 2. brute force (only small n)
    if idx.n <= 9:
        res["brute_wheeler"] = bool(bo.is_wheeler(nodes, edges, lr))
    else:
        res["brute_wheeler"] = None

    # 3. the recognizer accepts, and its order is order-isomorphic to the SA rank
    if run_recognizer and os.path.exists(REC):
        dot = os.path.join(work, f"suffixcert_n{idx.n}.dot")
        write_dot(nodes, edges, dot)
        verdict, outdir = _run_recognizer(dot, work)
        res["recognizer_verdict"] = verdict
        res["recognizer_iso_to_sa_rank"] = None
        if verdict == 1 and outdir:
            # nodes.txt: <old_node>\t<wheeler_pos> ; old node == our SA rank id
            wpos = {}
            for line in open(os.path.join(outdir, "nodes.txt")):
                old, wp = line.split()
                wpos[int(old)] = int(wp)
            ok3, _ = co.check(nodes, edges, lr, wpos)        # emitted order is valid (it must be)
            res["recognizer_order_valid"] = ok3
            # order-isomorphic to SA rank == identity: node i has wheeler pos i+1 (1-based)
            res["recognizer_iso_to_sa_rank"] = all(wpos.get(i) == i + 1 for i in range(idx.n))
    return res


if __name__ == "__main__":
    import json
    import tempfile
    seqs = sys.argv[1:] or ["ACGACG", "ACGTAC"]
    idx = sx.SuffixIndex(seqs, coords=None, s=1)
    print(json.dumps(certify(idx, tempfile.mkdtemp(prefix="sufcert_")), indent=2))
