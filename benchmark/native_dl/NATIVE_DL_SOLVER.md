# Round 1: a native difference-logic solver — does it beat Z3? (No.)

Round 1 of the recognition-performance program (plan: push the synthetic worst-case ceiling past Z3's
`complete` 2816 / `dnfa` 2176 @ 600 s). Stage-0 profiling found that on the synthetic worst case **Z3
solves with near-zero search** (tens–hundreds of SAT conflicts even at n=1000) **but explodes in memory
/ allocations** over the O(E²) materialized A3 encoding (9.4e12 allocations / 1.6 GB at n=1000; on `-f`,
death by `reason_unknown="Overflow ... vector"` at 5.6 GB / n=850). That diagnosis motivated a
**non-materializing native solver**: decide the post-heuristic residual by propagation in O(V+E) memory,
never building the O(E²) formula.

This documents what was built, that it is **provably sound**, and the **negative performance result**:
the native solver does **not** move the ceiling — it lands 3–9× *below* Z3 — because Z3's QF_IDL theory
propagation is already near-optimal for the binding constraint, which is **search**, not memory.

## What was built (`recognizer/src/dl_solve.cpp`, backend `-s dl`)

After the renaming heuristic, the `_node_ranges` brackets already discharge A1 + A2, so the residual is:
a permutation respecting the brackets, plus **A3** ("within each label group, heads are monotone
non-decreasing in tails"). `digraph::solve_dl()` decides it with a trailed constraint-propagation search:

- **Interval domains** `D(v) = [lo,hi]` per node (O(V) ints), seeded from the brackets.
- **Propagation to a fixpoint** (incremental dirty-group worklist — a domain change re-examines only the
  constraints that touch it):
  - **R1 (A3), both directions** — for two same-label edges: `tail_a` entailed-strictly before `tail_b`
    (`hi[tail_a] < lo[tail_b]`) ⇒ `head_a ≤ head_b`; *and the contrapositive* `head_a` entailed-strictly
    after `head_b` ⇒ `tail_a ≥ tail_b`. (The head←tail flow alone gives the search no feedback from head
    assignments — adding the contrapositive was necessary but not sufficient.)
  - **R3 (all-different)** — bound-consistent singleton elimination within each (small) bracket.
- **Trailed DFS** with **geometric randomized restarts**: a deterministic leftmost-first pass, then
  randomized variable+value descents with doubling node budgets. A restart that exhausts its whole tree
  with **no** cutoff yields a sound verdict; randomized restarts find SAT witnesses on the symmetric
  satisfiable families where any *fixed* order backtracks exponentially.
- **Outcome**: empty domain ⇒ non-WG; full (all-singleton) candidate ⇒ written and **re-validated by
  `WG_checker()`** before ACCEPT; global decision budget exhausted ⇒ **0 = undecided** (production falls
  back to `solve_smt()`; the `-s dl` backend reports it as a non-verdict).

### Soundness — verified
The domain invariant ("`[lo,hi]` contains every bracket-respecting Wheeler position") means propagation
removes only positions no Wheeler order uses, and `WG_checker()` gates every accept. So a propagation or
search bug can only cause an unnecessary fallback / false-reject (both caught by the oracle), **never a
false-accept**, and budget-exhaustion never rejects. Empirically confirmed — **0 disagreements with the
brute-force oracle**:

| gate | graphs | false-accept | false-reject |
|---|---|---|---|
| `difftest.py --modes smt,perm,full,dl` (5000 random + 600 positive) | 5,456 | 0 / mode | 0 / mode |
| `difftest.py --modes dl` (6000 random + 800 positive, seed 7) | 6,574 | 0 | 0 |
| `edgecases.py` (self-loops, parallel edges, A2 traps, disjoint unions, …) | 16 | 0 | 0 |

(The smt/perm/full modes also stayed at 0 — the new file is a no-regression addition.)

## Performance — the negative result (`results_dl.csv`, `bench_dl.py`)

Wheeler-by-construction ladders, labels=3, e≈1.5n, seed 1, 30 s per run (so Z3's true 600 s ceilings —
`complete` 2816 / `dnfa` 2176, see `benchmark/limit_test/`) are themselves capped here; the point is the
**relative** behaviour):

| family | Z3 `-s smt` | native `-s dl` |
|---|---|---|
| complete | WG up to **n=1024 in 16.0 s** (30 s-cap reached ~1536) | WG only to **n≈256**, **TIMEOUT at n=320** |
| dnfa | WG up to **n=768 in 16.1 s** | WG only to **n≈320**, **TIMEOUT at n=384** |

`dl` is competitive *only* on small instances and **erratically** — it is faster than Z3 at n≤192
(complete n=128: 0.03 s vs 0.18 s) yet much slower nearby (complete n=256: 3.19 s vs 0.75 s; dnfa n=192:
**9.5 s** vs 0.99 s, then n=320: 0.64 s). Then it falls off a cliff. Its ceiling is **3–9× below Z3's**.

### Why (root cause)
Z3's **QF_IDL theory propagation** maintains the difference-constraint graph and propagates bounds
globally (shortest-path / negative-cycle reasoning), so on these instances its **search is trivial**
(Stage-0: 55→510 conflicts as n goes 400→1000). Hand-rolled **bounds propagation** (entailed-strict
pairwise A3 + bound-consistent all-different) is strictly weaker: it rarely fires on overlapping domains,
so the native **search explodes**. The cliff is a knife-edge — each instance *is* backtrack-free under
*some* variable order (leftmost solves one n, smallest-domain another), but no fixed order wins
universally and the propagation is too weak to choose; randomized restarts only postpone the cliff a
little. **The binding constraint on the default path is the search, governed by propagation strength —
and Z3 already does that near-optimally.** (Memory is the wall only under `-f`; but `-f` gives full
`[1,n]` domains with no brackets, so the native propagation is *even weaker* there — it cannot help the
`-f` wall either.)

### Corollary — the obvious encoding levers are already taken
Shrinking Z3's encoding was the other candidate. But the smaller **block A3 form** (O(D²+E)) was already
measured to **regress on exactly the `complete` family** (`smt.cpp:121`: "n=512 complete: 36.5 s →
timeout"), which is why it is gated to `-f` / De-Bruijn graphs; and the default path is already
optimized by the heuristic's `fixed[]` (≈60 % of nodes fixed ⇒ A3 pairs collapse to cheap
non-disjunctive constraints). Both obvious levers — native search and encoding compression — are
exhausted on the synthetic ceiling.

## Verdict
This **confirms `RECOGNITION_LIMITS.md`**: for the general / symmetric worst case we are at the practical
limit. A hand-rolled difference-logic propagator does not beat Z3's theory solver; reproducing Z3's
strength would mean reimplementing its incremental IDL propagation, which Z3 already does in optimized
C++. The native solver is retained as a **sound, opt-in experimental backend** (`-s dl`) — it decides
small / structured residuals with O(V+E) memory — but is **not wired into the production dispatch**
(a pre-solve pass would only add overhead before Z3 on the hard instances that define the ceiling).

**Reproduce:** `python3 benchmark/native_dl/bench_dl.py --timeout 30` → `results_dl.csv`;
`python3 verify/difftest.py --modes dl --random 6000 --positives 800`; `python3 verify/edgecases.py`.
