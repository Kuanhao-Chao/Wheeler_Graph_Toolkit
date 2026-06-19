# Wheelie: the recognition algorithm

A living, source-grounded description of how the WGT recognizer (`recognizer/src/`) decides whether
an edge-labeled digraph is a **Wheeler graph**. File:line anchors are current as of the `devel`
branch (after the Phase 1 correctness fixes).

## What it decides

A directed, edge-labeled graph `G=(V,E)` is a **Wheeler graph** iff there is a total order `π` on
the nodes (a bijection `V → {0,…,n−1}`) satisfying, for edges `e1=(u1,v1,a1)`, `e2=(u2,v2,a2)`:

- **(A1)** every in-degree-0 node precedes every in-degree-positive node;
- **(A2)** `a1 < a2  ⇒  π(v1) < π(v2)` (smaller label ⇒ earlier head);
- **(A3)** `a1 = a2 ∧ π(u1) < π(u2)  ⇒  π(v1) ≤ π(v2)` (same label, tail order ⇒ head order).

Recognition is NP-complete, so the search for `π` is the hard part. The independent statement of
these axioms used as ground truth lives in `verify/brute_oracle.py:9-14`.

## Input contract (`wg.cpp` parser)

Input is a `strict digraph` DOT file. After whitespace removal, edge lines must match
`(\w+)->(\w+)\[label=(\w+)\];`. **Nodes are inferred only from edges** — standalone node
declarations are ignored. Labels are ranked by the distinct label strings: lexicographically by
default, numerically with `-i`. Parsing + label ranking: `wg.cpp` (the parse loop around
`wg.cpp:130-164`).

## The three-phase pipeline (`wg.cpp:164-206`)

```
parse DOT ─► add_edges() ─► [Step 1] relabel_initialization()
                            [Step 2] innodelist_sort_relabel()   (renaming heuristic → _node_ranges)
                            [Step 3] solve_smt()  OR  permutation_start()
```

Everything hangs off the `digraph` class (`graph.hpp`); its methods are split across `graph.cpp`
(algorithm), `smt.cpp` (Z3 backend), `get_func.cpp`/`print_func.cpp` (accessors/printers).

### Step 1 — `relabel_initialization()` (`graph.cpp`)
Establishes the initial constraints implied by the axioms (in-degree-0 prefix, per-label head
grouping) and assigns initial labels/groups. If these constraints are already violated, the graph
is not a Wheeler graph and the run rejects immediately.

### Step 2 — `innodelist_sort_relabel()` — the renaming heuristic (`graph.cpp`)
The key to making recognition fast in practice. It sorts/relabels nodes by their incoming-edge
structure and **narrows each node to an order range `[lb, ub]`** (`_node_ranges`, declared in
`graph.hpp`). This shrinks the search space *before* the solver runs. With `-f` / `full_range_search`
this step still runs but its range-narrowing branches are disabled, handing the full space to SMT.

### Step 3 — solve within the ranges (dispatch at `wg.cpp:186-206`)
- `full_range_search` (`-f`) → `solve_smt()` (forces SMT regardless of `-s`).
- solver `"default"`/`"smt"` → `solve_smt()`.
- solver `"p"`, or `permutation_counter < PERMUTATION_CUTOFF`, or `-e` → `permutation_start()`.
- With `-e` (exhaustive), the decision is made **by count**: accept iff `get_valid_WG_num() > 0`
  (`wg.cpp:193-204`). *(This guard is a Phase-1 fix; the exhaustive path previously accepted
  unconditionally — a false ACCEPT for every non-WG that reached it.)*

The dispatch heuristic compares an estimated permutation cost (`permutation_counter`, a saturating
product of per-group range sizes — Phase-1 fix for an `int` overflow) against `PERMUTATION_CUTOFF`.

## Backend 1 — SMT (`smt.cpp:solve_smt`)

Encodes the node order as a Z3 `QF_IDL` problem: one integer order variable per node, constrained to
its `_node_ranges` window, all-distinct (guarded against the degenerate empty case — Phase-1 fix for
a `z3::distinct([])` abort), plus the A2/A3 ordering constraints between edges (per-label head/tail
monotonicity; cross-label head ordering under `-f`). `s.check()` is handled three ways: **`sat`** ⇒
Wheeler (the model is re-checked by `SMT_WG_final_check()` before accepting); **`unsat`** ⇒ not
Wheeler; **`unknown`** ⇒ *undecided* — z3 can give up on very large `-f` encodings, and conflating
`unknown` with `unsat` falsely rejects a solvable Wheeler graph (Phase-4 soundness fix; use the
default backend for such graphs). The cross-group A2 encoding under `-f` is the sparse per-label
head-boundary form (Phase 4.1, `#lo_/#hi_`); within-group A3 is still all-pairs `O(E_l²)`
(Phase-4.2 target).

## Backend 2 — Permutation (`graph.cpp:permutation_start`)

Enumerates valid orderings per edge-label group within the `_node_ranges` windows, pruning with
`WG_checker*`. Roots are permuted, then each edge-label group; a leaf order is accepted via
`valid_wheeler_graph()` only after `WG_checker()` passes (`graph.cpp`). When the enumeration is
exhausted with no valid order, the graph is rejected (`graph.cpp:647-649` — Phase-1 fix; previously
exhaustion fell through to a false ACCEPT). `-e` keeps enumerating to count *all* valid orders
instead of stopping at the first.

`WG_checker()` / `WG_checker_in_edge_group()` verify A1/A2/A3 directly on a (partial) order; in
`-x/--explain` mode they record the violating edge pairs into `_violations` (`get_violations()`),
the bridge to the repair tooling (`repair/`).

## Verdict & output contract

- **Exit code / benchmark column:** `exit_program(v)` prints the benchmark row
  `<v>\t<n>\t<cpu_us>\t<path>` (under `-b`) and exits with `v`: **`1` = Wheeler, `-1` (→255) = not
  Wheeler, `0` = undecided** (SMT returned `unknown` — see the SMT backend above)
  (`graph.cpp`, around the `exit_program` definition).
- **Default run** writes no files — it prints `(v) It is a wheeler graph!!` (preceded by `solved by
  SMT` / `solved by permutation` / `Decided after propagation`).
- **`-w`** gates all on-disk output (`out__<stem>/` with `I.txt`/`O.txt`/`L.txt`/`nodes.txt`/
  `graph.dot`). **`-r`** writes `range.txt` during Step 2. **`-x/--explain`** prints the recorded
  axiom violations and forces the SMT backend.

## Correctness scaffolding (how this is trusted)

- `verify/brute_oracle.py` — independent n! ground truth (shares no code with the recognizer).
- `verify/difftest.py`, `verify/edgecases.py` — differential tests, all backends, ~10k graphs + 16
  curated edge cases; `verify/EDGECASES_SPEC.md` documents the latter.
- `verify/difftest_exp.py` — same for the rebuilt exponential baseline (`recognizer_e`).
- `benchmark/rerun/verdict_agreement.py` — verdict-agreement metric over real + synthetic corpora.

The five Phase-1 bug fixes (permutation reject-on-exhaustion, `-e` decide-by-count, fast-path guard,
dispatch overflow, `distinct([])` guard) were each found by oracle disagreement and are regression-
covered by the harnesses above.
