# Round 2: lazy / CEGAR A3 generation — does it move the ceiling? (Yes, a lot.)

Round 2 of the recognition-performance program. **Round 1** (the native difference-logic solver
`-s dl`, `native_dl/NATIVE_DL_SOLVER.md`) was a *negative* result: a hand-rolled propagator landed 3–9×
*below* z3 because it attacked the **search**, and z3's QF_IDL theory propagation already makes the
search trivial. But Round 1's profiling diagnosis was right and pointed elsewhere: on the synthetic
worst case z3 solves with near-zero search yet **explodes in memory/allocations over the O(E²)
materialized A3 encoding** (allocations ~12,000× over n=400→1000; on `-f`, death by 5.6 GB / 902 k
assertions at n≈850). The binding constraint is the *encoding*, not the search.

Round 2 attacks the encoding **while keeping z3's winning search**. The result is decisive: on the
default (production) path the recognition ceiling moves from z3's **2816 / 2176** nodes (`complete` /
`dnfa`, 600 s) to **≥ 32768** — solved in **under a minute and in tens of MB**, where vanilla z3 needs
**hundreds of seconds and many GB** and then dies.

## The idea: A3 is a *chain* constraint, so generate it lazily

After the renaming heuristic, the `_node_ranges` brackets discharge A1 + A2; the residual is a
permutation (all-different) plus **A3**: "within each label group, heads are monotone non-decreasing in
tail order." The production encoding (`smt.cpp`) writes A3 as **O(E²) pairwise implications** — for every
pair of same-label edges, `tail_i < tail_j ⇒ head_i ≤ head_j`. That quadratic blow-up is the wall.

But A3 is O(E²) *only statically*, because the tail order is unknown a priori. **Given a concrete
candidate order the tail order is known, so a violation is forbidden by O(E) consecutive-pair lemmas.**
So we run counterexample-guided lazy SMT (CEGAR), `recognizer/src/lazy_solve.cpp`, backend `-s lazy`:

1. Assert the **base** only — A1 brackets + all-different (+ sparse A2 under `-f`). **No A3.**
2. `s.check()`. `unsat` ⇒ not a Wheeler graph (a *subset* of the full encoding is already UNSAT).
3. `sat` ⇒ read the model and re-check A3 in O(E log E) (`a3_collect_violations`, the side-effect-free
   twin of `WG_checker_in_edge_group`). If **no** violation, the model is a Wheeler order — gate it with
   `WG_checker()` and **accept**. Otherwise add **only the consecutive-pair A3 lemmas the model
   violates** (monotone `s.add`, so z3 keeps its learned clauses), and go to 2.

z3 never materializes the full O(E²) formula; it only ever sees the handful of A3 pairs that actually
bind. Budget/abort exhaustion returns *undecided* and the caller falls back to vanilla `solve_smt()`, so
no verdict can regress.

### Soundness — verified
Invariant: at every `check()` the constraint set is a **subset** of `solve_smt()`'s full encoding (same
base + a subset of the identical pairwise A3 lemmas), so `Models(lazy) ⊇ Models(full)`. Hence UNSAT ⇒
genuinely non-WG (no false reject), every accept is double-gated by `WG_checker` (no false accept), and
budget exhaustion only falls back (never rejects). It **terminates** (each round adds ≥ 1 new pair from
the finite universe `U = Σ_l C(E_l,2)`; in the limit it equals the full encoding). Empirically confirmed
— **0 disagreements with the brute-force oracle**:

| gate | graphs | false-accept | false-reject |
|---|---|---|---|
| `difftest.py --modes smt,lazy,full-lazy` (random 5000 + positives 1000) | 5,726 | 0 / mode | 0 / mode |
| `difftest.py --dense --allow-dup` (big A3 groups — the lazy stress case) | 4,344 | 0 / mode | 0 / mode |
| `difftest.py --allow-self` | 3,368 | 0 / mode | 0 / mode |
| `edgecases.py` (self-loops, parallel edges, cycles, disjoint unions, …) | 16 | 0 / mode | 0 / mode |
| `check_order.py` re-validates emitted orders, n = 80 (default) and n = 120 (`-f`) | — | valid | valid |

## Performance — the positive result (`results_lazy_ceiling.csv`, `bench_lazy.py`)

Wheeler-by-construction ladders, labels = 3, e = 1.5 n, 600 s/run, peak RSS via `/usr/bin/time -v`;
`a3 = materialized_a3 / pair_universe` from the recognizer's `--profile` line.

**`complete` family (default path):**

| n | vanilla `-s smt` | lazy `-s lazy` | A3 pairs materialized |
|---|--:|--:|--:|
| 2048 | WG 198.2 s / 6465 MB | **WG 0.5 s / 43 MB** | 290 / 1,573,603 |
| 2816 | WG 538.6 s / 7488 MB | **WG 0.9 s / 56 MB** | 346 / 2,973,756 |
| 4096 | **TIMEOUT (600 s)** | **WG 1.5 s / 64 MB** | 491 / 6,289,665 |
| 8192 | — | **WG 4.6 s / 103 MB** | 963 / 25,174,753 |
| 16384 | — | **WG 16.1 s / 185 MB** | 1,910 / 100,701,172 |
| 32768 | — | **WG 60.5 s / 350 MB** | 3,835 / 402,722,292 (0.001 %) |

`dnfa` is the same story (vanilla ceiling 2176; lazy reaches the ladder top with the same flat
memory/time growth). At n = 2816, lazy is **~600× faster and ~130× lighter** than vanilla z3, and its
ceiling is **≥ 32768** — the ladder limit, not the solver's: lazy never stalls.

### Why it works (and why Round 1 didn't)
The heuristic's brackets nearly determine the order, so the O(E²) A3 encoding is **~99.99 % redundant** —
at n = 32768 only **3,835 of 402,722,292** pairs ever bind. Vanilla z3 still builds and propagates all
402 M; lazy adds the 3,835 that matter and keeps z3's CDCL search for the rest. Round 1 lost because it
*replaced* z3's search with a weaker hand-rolled one; Round 2 wins because it **keeps z3's search and
only defers the encoding**. Same diagnosis, opposite fix.

### The `-f` regime — an honest non-result
Lazy does **not** rescue the `-f` (full-range) path. There the renaming heuristic is bypassed, so the
domains are full `[1,n]` with no brackets; the first models are far from sorted and lazy needs many
rounds (`results_lazy_probe.csv`: n = 128 takes **583 rounds / 22.2 s**). It *does* keep memory low
(n = 128: 75 MB vs vanilla `-f`'s 94 MB; and where vanilla `-f` balloons to 374 MB at n = 256, lazy stays
flat) — but it trades the memory wall for round-overhead **time**, timing out around n ≈ 256, *below*
vanilla `-f`'s memory-bound ~832. An
eager variant (add the whole group's chain per round) cut rounds 583 → 10 at n = 128 but made each
`check()` expensive (1.7 s), so wall time was unchanged and it still timed out at n = 256. **Conclusion:
the heuristic's tight brackets are the load-bearing ingredient; without them (`-f`) the symmetric
residual is hard regardless of A3-encoding strategy.** This is exactly why the default path — heuristic +
lazy — is the win, and it sharpens the Round-1 finding rather than contradicting it.

## Verdict
The §5.3 "at the practical limit" conclusion was premature for the **default path**: it held the
*static* encoding-compression lever (block-A3, which added aux vars and regressed) and the
native-*search* lever fixed, but **lazy/dynamic encoding generation** is a third lever, and it moves the
default ceiling by **> 10×** with a ~600×/~130× time/memory win at fixed n — all verified sound. The
worst-case asymptotics are unchanged (recognition is still NP-complete; `RECOGNITION_LIMITS.md`), and the
`-f` regime and truly residual-dense instances remain hard. But for the production path on the synthetic
worst case, the ceiling was **not** at the practical limit — lazy A3 generation is strictly better and is
a candidate to become the default backend.

**Reproduce:** `python3 benchmark/lazy_cegar/bench_lazy.py --timeout 600 --backends smt,lazy` →
`results_lazy_ceiling.csv`; correctness: `python3 verify/difftest.py --modes smt,lazy,full-lazy
--random 5000 --positives 1000` (+ `--dense --allow-dup`, `--allow-self`) and `python3
verify/edgecases.py`.
