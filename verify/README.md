# `verify/` — correctness verification for the Wheeler-graph recognizer

This directory holds an **independent** correctness-verification suite for the WGT recognizer
(`recognizer/`). It exists because the repo previously had *no* verdict-correctness testing — the
benchmarks measured only runtime, and the exponential "baseline" cannot serve as ground truth
(its decision logic is broken; see the roadmap).

## Components

| File | What it is |
|------|------------|
| `brute_oracle.py` | A trivially-correct, brute-force Wheeler-graph decision **oracle**: for n ≤ ~9 it enumerates all `n!` node orderings and checks the three Wheeler axioms directly. Shares no logic with the recognizer, so it is genuine ground truth. |
| `difftest.py` | **Differential tester**: generates random labeled digraphs (+ guaranteed-positive WGs) and asserts the recognizer's verdict matches the oracle in every backend (default SMT, `-s p`, `-f`; optionally `-s p -e`). Saves any disagreement to `repro/`. |
| `edgecases.py` | A curated set of **structural edge cases** (self-loops, parallel edges, disconnected components, multiple roots, pure cycles, empty graph) checked against the oracle in all backends; several carry a hand-derived expected verdict that also cross-checks the oracle. |

## Running

The recognizer must be built first. On this Linux host the documented `make z3` path is unnecessary
(Z3 is already in conda); build directly:

```bash
cd recognizer
g++ -std=c++17 -pthread -O3 -w -I /home/kh.chao/miniconda3/include/ \
    $(find src -name '*.cpp') src/libz3.a -lstdc++fs -o bin/recognizer_linux
cd ..

python3 verify/brute_oracle.py data/example/example.dot        # oracle on one graph
python3 verify/edgecases.py                                    # curated edge cases
python3 verify/difftest.py --random 3000 --positives 500 --max-n 7   # differential sweep
python3 verify/difftest.py --random 1500 --max-n 6 --allow-self --allow-dup  # incl. self-loops/dups
```

`difftest.py` exits non-zero if any recognizer/oracle disagreement is found; reproducers land in
`verify/repro/`.

## Label ordering

Both tools rank edge labels the same way the recognizer does (`recognizer/src/wg.cpp:141-159`):
lexicographic over label strings by default, or numeric with `-i` (oracle: `--int`). The random
corpora use integer labels with `-i`/`--int` so the order is unambiguous.

## Bugs found (all fixed in the working tree; see git diff of `recognizer/src/`)

1. **`-s p` false-accepted non-Wheeler graphs** — `permutation_start()` had no reject-on-exhaustion;
   `main` returned the default `valid_wg=true`. Minimal repro: `S1→S2; S2→S1` (label 0).
2. **`-s p -e` (exhaustive) accepted everything** — the accept path was a no-op under `-e` and
   `main` declared WG unconditionally. (This was the paper's GT benchmark mode.)
3. **Propagation fast-path accepted with no final `WG_checker()`** — now guarded.
4. **`int` overflow** in the SMT-vs-permutation dispatch heuristic — now saturating.
5. **`-f` SIGABRT on degenerate input** — `z3::distinct([])` on an empty range group — now guarded.

Also fixed a bug in the oracle itself (it shortcut `n≤1 → Wheeler` without checking axioms; a single
node with two different-label self-loops violates axiom 2).

After fixes: **8,900+ random graphs (incl. self-loops/parallel edges) + 16 curated edge cases,
zero recognizer/oracle disagreements** across all four backends. No correctness bug was found in the
SMT backend.
