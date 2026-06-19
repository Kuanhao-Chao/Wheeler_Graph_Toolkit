# Structural edge-case specification

The intended Wheeler-recognition behavior on structural corner cases — the inputs that are easy to
get wrong and that the random differential sweep (`difftest.py`, simple graphs only) does not cover.
Each case is encoded and machine-checked in `verify/edgecases.py` (the `CASES` table); this file is
its human-readable spec. Every rule traces back to the three axioms (`brute_oracle.py:9-14`):

- **(A1)** in-degree-0 nodes form a prefix of the order;
- **(A2)** `a < b ⇒ head(e_a)` ordered before `head(e_b)`;
- **(A3)** same label, `tail(u) < tail(u') ⇒ head(v) ≤ head(v')`.

Verdict column: **1** = Wheeler, **0** = not Wheeler. All 16 cases are cross-checked three ways:
the hand-derived verdict below = the brute oracle = the recognizer (all backends, including
`-s p -e`, via `edgecases.py:EC_MODES`).

## Parallel / multiple edges

| case | edges | verdict | why |
|---|---|:--:|---|
| `parallel_same_label` | `A→B`, `A→B` (both label 0) | **1** | A duplicate identical edge adds no new constraint. |
| `parallel_diff_label` | `A→B` (0), `A→B` (1) | **0** | A2 needs `head(0) < head(1)`, but both heads are `B`: `π(B) < π(B)` is impossible. |

Note the parser keeps one edge per matching line (`_edgeLabel_2_edge` retains duplicates) even
though `strict digraph` adjacency would collapse them — so parallel edges with *different* labels
are real, distinct constraints.

## Self-loops

| case | edges | verdict | why |
|---|---|:--:|---|
| `self_loop_single` | `X→X` (0) | **1** | A lone self-loop is trivially orderable. |
| `self_loop_dupe_same_label` | `X→X` (0), `X→X` (0) | **1** | Duplicate identical self-loop — no new constraint. |
| `self_loop_two_labels` | `X→X` (0), `X→X` (1) | **0** | A2 needs `π(X) < π(X)` — impossible. The minimal self-loop counterexample. |
| `self_loop_plus_edge` | `X→X` (0), `X→Y` (0) | *oracle* | A self-loop on a non-source node interacts with A1/A3; trust the oracle. |

`self_loop_two_labels` is also the case that exposed an early **oracle** bug: a naive `n≤1 ⇒
Wheeler` shortcut wrongly accepts it. A single node can carry self-loops, so n==1 must still be
axiom-checked (`brute_oracle.py:90-94`).

## Disconnected components

| case | edges | verdict | why |
|---|---|:--:|---|
| `disjoint_two_WG` | `A→B` (0), `C→D` (0) | **1** | Two independent single-edge Wheeler graphs; a combined order exists. |
| `disjoint_WG_plus_nonWG` | `A→B` (0) + a 2-cycle `S1⇄S2` (0) | **0** | Wheeler-ness is global: one non-Wheeler component makes the whole graph non-Wheeler. |

## Single / empty

| case | edges | verdict | why |
|---|---|:--:|---|
| `empty_no_edges` | (none) | **1** | 0 nodes (nodes come only from edges) — vacuously Wheeler. |
| `single_edge` | `A→B` (0) | **1** | One edge; `A` is the in-degree-0 root. |

## Multiple roots / shared successors

| case | edges | verdict | why |
|---|---|:--:|---|
| `two_roots_shared_succ` | `R1→X` (0), `R2→X` (0) | **1** | Two in-degree-0 roots into one node, same label — A1 lets both roots take the prefix. |
| `two_roots_cross_labels` | `R1→X`(0),`R2→Y`(1),`R1→Y`(0),`R2→X`(1) | *oracle* | Root order interacts with the label constraints; trust the oracle. |

## Pure cycles (no in-degree-0 node)

| case | edges | verdict | why |
|---|---|:--:|---|
| `two_cycle_same_label` | `S1→S2` (0), `S2→S1` (0) | **0** | A3: with one label, `π(S1)<π(S2) ⇒ π(S2)≤π(S1)` — contradiction. The minimal rootless counterexample. |
| `three_cycle_same_label` | `A→B→C→A` (0) | *oracle* | Rootless 3-cycle; trust the oracle. |

## Merge structures

| case | edges | verdict | why |
|---|---|:--:|---|
| `sink_chain` | `A→B→C` (0) | **1** | A simple path is always Wheeler. |
| `diamond_same_label` | `A→B`,`A→C`,`B→D`,`C→D` (all 0) | *oracle* | A merge node `D` with two same-label in-edges; trust the oracle. |

## Why these matter

The recognizer has three accept paths (SMT model, permutation leaf, propagation fast-path) and a
heuristic dispatch; corner cases are where they diverge. Cases like `self_loop_two_labels`,
`parallel_diff_label`, and `two_cycle_same_label` are the *minimal* witnesses for each axiom and are
the fastest regression signal that a change broke soundness. `disjoint_WG_plus_nonWG` guards the
global (not per-component) nature of the property. The `-s p -e` column specifically guards bug #2
(exhaustive always-accept), which `difftest.py`'s sweep omits for speed.
