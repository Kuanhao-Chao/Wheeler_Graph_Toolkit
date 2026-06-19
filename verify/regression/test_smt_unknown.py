#!/usr/bin/env python3
"""
Regression test: the recognizer must never report "not a Wheeler graph" just because the SMT solver
returned UNKNOWN.

`hard_wg_smt_unknown.dot` is a genuine Wheeler graph (n=800, e=6000, l=100; default-SMT and the
permutation backend both decide it WHEELER, and its order is independently axiom-valid -- see
verify/check_order.py). Under `-f` (full_range_search) the SMT encoding is so large that z3 returns
`unknown`. The original code did `if (res==sat) valid_wg=true; else valid_wg=false;`, so `unknown`
was treated as `unsat` and the graph was FALSELY reported "not a Wheeler graph" (exit 255).

After the fix, `-f` must return UNDECIDED (exit 0), never not-WG (exit 255). The default and
permutation backends must still return WHEELER (exit 1).

NOTE: slow (~100s) -- the `-f` run waits out z3's unknown. Run on demand:
  python3 verify/regression/test_smt_unknown.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")
DOT = os.path.join(HERE, "hard_wg_smt_unknown.dot")

# exit codes: 1 = Wheeler, 255 = not Wheeler, 0 = undecided (SMT unknown)
CASES = [
    ("default-SMT", ["-i"],          {1},      "WHEELER"),
    ("perm",        ["-i", "-s", "p"], {1},    "WHEELER"),
    ("full (-f)",   ["-i", "-f"],     {0, 1},  "UNDECIDED or WHEELER (NEVER not-WG)"),
]


def run(args):
    r = subprocess.run([REC, DOT] + args, capture_output=True, timeout=600)
    return r.returncode


def main():
    print(f"fixture: {os.path.relpath(DOT, ROOT)}")
    failures = 0
    for name, args, ok_codes, desc in CASES:
        rc = run(args)
        # subprocess maps the C exit(-1) to 255
        ok = rc in ok_codes
        verdict = {1: "WHEELER", 255: "not-WG", 0: "UNDECIDED"}.get(rc, f"exit {rc}")
        print(f"  {name:<12} -> {verdict:<10} (exit {rc})  expect {desc}: {'OK' if ok else 'FAIL'}")
        if not ok:
            failures += 1
            if rc == 255:
                print(f"      !! REGRESSION: {name} falsely reports this Wheeler graph as NOT Wheeler")
    print("RESULT:", "PASS ✓" if failures == 0 else f"FAIL ({failures})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
