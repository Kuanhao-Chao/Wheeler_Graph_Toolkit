#!/usr/bin/env python3
"""
Regression test for the Phase-4.2 sparse within-group A3 block encoding (smt.cpp, `-f` path).

Under `-f` (full_range_search) the within-group axiom-A3 constraints are emitted in an
O(E_l + D_l^2) "endpoint-block" form (key on the side with fewer distinct nodes, bracket the other
side into a [#mn,#mx] window) instead of the O(E_l^2) all-pairs form, whenever that is strictly
cheaper. Both fixtures below have a label group with shared HEADS (H_l < E_l), so the head-keyed
block path fires under `-f`:

  block_a3_wg.dot     -- a Wheeler graph (star into node 5); label 0 has E=4, T=4, H=1.
  block_a3_nonwg.dot  -- NOT a Wheeler graph;               label 0 has E=5, T=4, H=3.

The block encoding is equisatisfiable with the all-pairs form, so every backend (default SMT,
permutation, and `-f`) must agree with the independent brute-force oracle on BOTH fixtures. The
non-WG fixture in particular exercises the UNSAT path *through* the block code (z3 must prove no
ordering exists). Truth is computed here from verify/brute_oracle.py, so the test is self-validating.

Run on demand:  python3 verify/regression/test_block_a3.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
sys.path.insert(0, os.path.join(ROOT, "verify"))
import brute_oracle as bo  # noqa: E402

FIXTURES = ["block_a3_wg.dot", "block_a3_nonwg.dot"]

# backend label -> recognizer args (always integer labels)
BACKENDS = [
    ("default-SMT", ["-i"]),
    ("perm",        ["-i", "-s", "p"]),
    ("full (-f)",   ["-i", "-f"]),
]


def oracle_truth(dot):
    nodes, edges = bo.parse_dot(dot)
    lr = bo.rank_labels(edges, int_mode=True)
    return 1 if bo.is_wheeler(nodes, edges, lr) else 0


def rec_verdict(dot, args):
    # exit: 1 = Wheeler, 255 = not-WG, 0 = undecided
    rc = subprocess.run([REC, dot] + args, capture_output=True, timeout=120).returncode
    return {1: 1, 255: 0, 0: "UNDECIDED"}.get(rc, f"exit{rc}")


def main():
    failures = 0
    for fx in FIXTURES:
        dot = os.path.join(HERE, fx)
        truth = oracle_truth(dot)
        tword = "WHEELER" if truth == 1 else "not-WG"
        print(f"fixture: {fx}  (oracle: {tword})")
        for name, args in BACKENDS:
            v = rec_verdict(dot, args)
            vword = {1: "WHEELER", 0: "not-WG"}.get(v, str(v))
            ok = (v == truth)
            print(f"  {name:<12} -> {vword:<10} expect {tword}: {'OK' if ok else 'FAIL'}")
            if not ok:
                failures += 1
    print("RESULT:", "PASS ✓" if failures == 0 else f"FAIL ({failures})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
