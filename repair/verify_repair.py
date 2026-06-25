#!/usr/bin/env python3
"""
verify_repair.py -- the 5 correctness invariants every repaired graph must satisfy (any n).

Given the INPUT graph and a REPAIRED graph (both DOT), confirm the repair is correct:

  (i)   the C++ recognizer accepts the repaired graph as a Wheeler graph (exit 1);
  (ii)  the brute oracle accepts it too, when small enough (<= 9 nodes);
  (iii) the order the recognizer emits (nodes.txt via -w) independently validates against the
        three axioms (check_order) -- an n-UNBOUNDED soundness witness;
  (iv)  the repaired graph spells the EXACT same path-string set as the input (lossless);
  (v)   the repaired graph uses the EXACT same label set as the input (so label ranks, hence the
        A2 ordering, mean the same thing -- a silent-failure guard).

Used by the test harness and the experiment scripts. Importable: verify(inp, out, int_mode).
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "verify"))
sys.path.insert(0, HERE)
import brute_oracle as bo  # noqa: E402
import check_order as co  # noqa: E402
import dfa  # noqa: E402

REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")


def _strings_and_labels(path):
    nodes, sources, out_adj, edges = dfa.build_graph(path)
    return dfa.path_strings(sources, out_adj), dfa.label_set(edges), nodes, edges


def verify(input_dot, output_dot, int_mode=False, oracle_cap=9):
    """Return (ok, results) where results maps each invariant to True/False/None(n/a)."""
    r = {"recognizer": None, "oracle": None, "order_valid": None,
         "strings_preserved": None, "labels_preserved": None, "detail": ""}

    in_strings, in_labels, _, _ = _strings_and_labels(input_dot)
    out_strings, out_labels, out_nodes, out_edges = _strings_and_labels(output_dot)

    # (iv) lossless path-string set
    r["strings_preserved"] = (in_strings == out_strings)
    # (v) identical label set (allow the degenerate empty-language case)
    r["labels_preserved"] = (in_labels == out_labels) or (len(in_strings) <= 1 and not out_edges)

    # (i) recognizer accepts
    args = [REC, output_dot] + (["-i"] if int_mode else [])
    rc = subprocess.run(args, capture_output=True).returncode
    r["recognizer"] = (rc == 1)

    # (ii) brute oracle (small only)
    if len(out_nodes) <= oracle_cap:
        rank = bo.rank_labels(out_edges, int_mode)
        r["oracle"] = bo.is_wheeler(out_nodes, out_edges, rank)

    # (iii) independent order validation on the recognizer's emitted order
    if r["recognizer"]:
        workdir = tempfile.mkdtemp()
        try:
            wargs = [REC, output_dot, "-w", "-o", workdir + "/"] + (["-i"] if int_mode else [])
            subprocess.run(wargs, capture_output=True)
            stem = os.path.splitext(os.path.basename(output_dot))[0]
            order_file = os.path.join(workdir, f"out__{stem}", "nodes.txt")
            if os.path.exists(order_file):
                rank = bo.rank_labels(out_edges, int_mode)
                pos = co.parse_order(order_file)
                ok_ord, reason = co.check(out_nodes, out_edges, rank, pos)
                r["order_valid"] = ok_ord
                if not ok_ord:
                    r["detail"] += f"order: {reason}; "
            else:
                r["order_valid"] = None  # n/a (e.g. edge-free graph emits nothing)
        finally:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)

    checks = [r["recognizer"], r["oracle"], r["order_valid"],
              r["strings_preserved"], r["labels_preserved"]]
    ok = all(c for c in checks if c is not None) and r["recognizer"] is True \
        and r["strings_preserved"] is True and r["labels_preserved"] is True
    return ok, r


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Verify a repaired Wheeler graph (5 invariants).")
    ap.add_argument("input_dot")
    ap.add_argument("output_dot")
    ap.add_argument("--int", action="store_true")
    args = ap.parse_args()
    ok, r = verify(args.input_dot, args.output_dot, args.int)
    label = {True: "PASS", False: "FAIL", None: "n/a "}
    print(f"  (i)   recognizer accepts : {label[r['recognizer']]}")
    print(f"  (ii)  brute oracle       : {label[r['oracle']]}")
    print(f"  (iii) order validates    : {label[r['order_valid']]}")
    print(f"  (iv)  strings preserved  : {label[r['strings_preserved']]}")
    print(f"  (v)   labels preserved   : {label[r['labels_preserved']]}")
    if r["detail"]:
        print(f"  detail: {r['detail']}")
    print("RESULT:", "OK ✓" if ok else "FAILED ✗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
