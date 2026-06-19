#!/usr/bin/env python3
"""
edgecases.py -- curated structural edge-case tests for the WGT recognizer.

The random sweep in difftest.py uses simple graphs (no self-loops, no duplicate edges). This
file targets the structural corner cases that are easy to get wrong: self-loops, parallel edges
(same and different label), disconnected components, multiple roots, pure cycles, and the empty
graph. For each case we compare the brute-force oracle (ground truth) against the recognizer in
all three backends (default SMT, -s p, -f).

Some cases carry an `expect` (my hand-derived truth) -- we assert the ORACLE matches it too, which
is an extra independent check on the oracle itself. `expect=None` means "trust the oracle."

Run: python3 verify/edgecases.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute_oracle as bo          # noqa: E402
from difftest import recognizer_verdict, MODES  # noqa: E402

# Edge cases also exercise -e exhaustive mode (permutation backend), which difftest's big sweep
# omits for speed. -e applies only to the permutation backend.
EC_MODES = dict(MODES)
EC_MODES["perm_e"] = ["-i", "-s", "p", "-e"]

TMP = os.path.join(HERE, "_edgetmp")


def dot(edges):
    """edges: list of (tail, head, label). Returns a DOT string."""
    body = "".join(f"\t{u} -> {v} [ label = {l} ];\n" for (u, v, l) in edges)
    return "strict digraph {\n" + body + "}\n"


# name -> (edges, expect, note). expect: 1 WG, 0 not WG, None trust-oracle.
CASES = {
    "empty_no_edges":            ([],                                     1, "0 nodes -> trivially Wheeler"),
    "single_edge":               ([("A", "B", 0)],                       1, "one edge, A is root"),
    "self_loop_single":          ([("X", "X", 0)],                       1, "lone self-loop is Wheeler"),
    "self_loop_dupe_same_label": ([("X", "X", 0), ("X", "X", 0)],        1, "duplicate identical self-loop"),
    "self_loop_two_labels":      ([("X", "X", 0), ("X", "X", 1)],        0, "a<b needs head_a<head_b but both are X"),
    "parallel_same_label":       ([("A", "B", 0), ("A", "B", 0)],        1, "duplicate identical edge"),
    "parallel_diff_label":       ([("A", "B", 0), ("A", "B", 1)],        0, "a<b needs B<B -> impossible"),
    "two_cycle_same_label":      ([("S1", "S2", 0), ("S2", "S1", 0)],    0, "rootless 2-cycle, the minimal repro"),
    "three_cycle_same_label":    ([("A", "B", 0), ("B", "C", 0), ("C", "A", 0)], None, "rootless 3-cycle"),
    "disjoint_two_WG":           ([("A", "B", 0), ("C", "D", 0)],        1, "two disjoint single-edge WGs"),
    "disjoint_WG_plus_nonWG":    ([("A", "B", 0), ("S1", "S2", 0), ("S2", "S1", 0)], 0, "non-WG component poisons union"),
    "two_roots_shared_succ":     ([("R1", "X", 0), ("R2", "X", 0)],      1, "two roots into one node, same label"),
    "two_roots_cross_labels":    ([("R1", "X", 0), ("R2", "Y", 1), ("R1", "Y", 0), ("R2", "X", 1)], None, "root order interacts w/ labels"),
    "self_loop_plus_edge":       ([("A", "A", 0), ("A", "B", 0)],        None, "self-loop on a source-ish node"),
    "sink_chain":                ([("A", "B", 0), ("B", "C", 0)],        1, "simple path a/a"),
    "diamond_same_label":        ([("A", "B", 0), ("A", "C", 0), ("B", "D", 0), ("C", "D", 0)], None, "merge node D"),
}


def main():
    os.makedirs(TMP, exist_ok=True)
    n_fail = 0
    n_oracle_surprise = 0
    cols = list(EC_MODES)
    hdr = f"{'case':<28} {'oracle':>7}" + "".join(f"{m:>7}" for m in cols) + "  result"
    print(hdr)
    print("-" * len(hdr))
    for name, (edges, expect, note) in CASES.items():
        path = os.path.join(TMP, name + ".dot")
        with open(path, "w") as f:
            f.write(dot(edges))

        nodes, parsed = bo.parse_dot(path)
        rank = bo.rank_labels(parsed, int_mode=True)
        truth = 1 if bo.is_wheeler(nodes, parsed, rank) else 0

        rec = {m: recognizer_verdict(path, args) for m, args in EC_MODES.items()}

        # agreement of every backend with the oracle
        backends_ok = all(rec[m] == truth for m in EC_MODES)
        oracle_ok = (expect is None) or (truth == expect)

        status = "ok"
        if not oracle_ok:
            status = f"ORACLE!=expect({expect})"
            n_oracle_surprise += 1
        if not backends_ok:
            status = "RECOGNIZER MISMATCH"
            n_fail += 1

        row = f"{name:<28} {truth:>7}" + "".join(f"{str(rec[m]):>7}" for m in cols)
        print(f"{row}  {status}   [{note}]")

    print("-" * 72)
    print(f"recognizer mismatches : {n_fail}")
    print(f"oracle surprises      : {n_oracle_surprise}")
    if n_fail == 0 and n_oracle_surprise == 0:
        print("RESULT: all edge cases agree (oracle == hand-truth, recognizer == oracle). ✓")
    sys.exit(1 if (n_fail or n_oracle_surprise) else 0)


if __name__ == "__main__":
    main()
