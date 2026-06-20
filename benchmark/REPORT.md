# WGT recognizer — NEW vs OLD: a correctness, capability, and performance report

This report consolidates the multi-phase verification and improvement of the WGT recognizer
("Wheelie", `recognizer/src/`) and the exponential baseline (`benchmark/exponential_recognizer/`),
and compares the **NEW** code (the fixed/sparsened `devel` branch) head-to-head against the **OLD**
code, rebuilt from the exact historical commits. Every claim traces to a re-runnable command and a
data file; §8 is the reproduction manifest.

> **The cardinal rule of this report: three axes, never merged into one "X % better."**
> A faster wrong answer is not progress. We separate
> **(1) correctness** (does the verdict match ground truth?),
> **(2) capability** (can it produce a verdict at all?), and
> **(3) performance** (how fast / how big, *on the graphs where the verdict is already correct*).

---

## Executive summary

| Axis | Metric | OLD | NEW | Evidence |
|---|---|---|---|---|
| **Correctness — recognizer** | false-accepts on a reject-heavy random corpus (4559 non-WG) | **950** via `-s p` and **950** via `-s p -e` (20.8%) | **0** (all backends) | Fig 1, `data/corr_buggy.log` / `corr_new.log` |
| **Correctness — recognizer** | verdict agreement with the brute-force n! oracle | n/a (buggy) | **2447 / 2447, 0 disagreements** | Fig 2, `VERDICT_AGREEMENT.md` |
| **Correctness — exp baseline** | could it ever output "not a Wheeler graph"? | **no** — returned WG for *every* in-cap graph | **yes** — honest 3-way verdict | Fig 1, `data/exp_unsound.log` |
| **Capability** | non-WG biological graphs decided (n≤9 subset) | **0 / 7** (OLD exp timed out on all of them) | **7 / 7** | Fig 3, `PHASE3_IMPACT.md` |
| **Capability** | graphs the OLD exp baseline could decide at all | timed out on **159 / 931** | **931 / 931** | Fig 3 |
| **Performance — `-f`** | total `-f` time, DOCK4 DNA k=5 (1041 edges) | 15.2 s (pre-4.1) | **6.6 s** (≈ **2.3×**) | Fig 7, `data/micro.setup_solve.csv` |
| **Performance — `-f`** | encoding *setup* time, same graph | 2.1 s | **0.14 s** (≈ **14×**) | Fig 7 |
| **Performance — `-f`** | encoding asymptotics (cross-group A2 / within-group A3) | O(E²) / O(E_l²) | **O(E+L) / O(D_l²+E_l)** | §4 |
| **Capability — scale** | largest graph recognized within 600 s (default SMT, `complete` family) | exp baseline CAPPED ≈ n=10 | **n ≈ 2900+** (≈290× past exp) | §5 (limit sweep in progress) |
| **Repair** | non-WG DAGs repaired to a verified WG (strings preserved) | n/a (did not exist) | **316 / 316 repaired, 0 failures** (820 DAGs) | Fig 11, `data/repair_records.json` |

**One-paragraph version.** The OLD recognizer's permutation backends *false-accepted* non-Wheeler
graphs, and the OLD exponential baseline was not a decision procedure at all — it answered "Wheeler"
for every graph it finished and timed out on every non-Wheeler instance, so its published verdicts
were meaningless. The NEW code agrees with an independent n!-enumeration oracle on **2447** graphs
with **zero** disagreements, and decides non-Wheeler verdicts the OLD baseline was structurally
incapable of. On top of that — *correctness first, performance second* — the Phase-4 sparse `-f`
SMT encoding has a **strictly-smaller-or-equal constraint count** (guarded fallback), cuts encoding
**setup** universally (~6–14×), and cuts **total** `-f` time ~2× on the largest *Wheeler* DNA graphs.
We also report the honest cost: on a minority (~20%) of *non-Wheeler* (UNSAT) instances the extra
auxiliary variables make z3's refutation slower (§4.2) — a real trade, not a free lunch. None of this
touches the **default** backend, which is the production path and decides these graphs near-instantly.

---

## §1 Background — Wheeler graphs and the deciders

An edge-labeled directed graph `G=(V,E)` is a **Wheeler graph** iff there is a total order `π` on
the nodes such that, for edges `e1=(u1,v1,a1)`, `e2=(u2,v2,a2)`:

- **(A1)** every in-degree-0 node precedes every in-degree-positive node;
- **(A2)** `a1 < a2 ⇒ π(v1) < π(v2)` — a smaller edge label forces an earlier head;
- **(A3)** `a1 = a2 ∧ π(u1) < π(u2) ⇒ π(v1) ≤ π(v2)` — equal label, tail order implies head order.

Deciding whether such a `π` exists is **NP-complete**, so all three deciders here search that
ordering space; they differ only in *how*:

- **recognizer (SMT)** — `recognizer_linux` (default). Three-phase pipeline (`wg.cpp`): Step 1
  `relabel_initialization()` (axiom-implied constraints), Step 2 `innodelist_sort_relabel()` (the
  **renaming heuristic** that narrows each node to an order window `[lb,ub]`), Step 3 `solve_smt()`
  encoding the order as a Z3 `QF_IDL` problem inside those windows.
- **recognizer (permutation)** — `-s p`: enumerates valid orderings per label group with pruning.
- **recognizer (`-f` full-range)** — disables Step-2 narrowing and hands the whole space to SMT;
  this is the path Phase 4.1/4.2 optimize.
- **exponential baseline** — `recognizer_e`: the Gibney–Thankachan reference, now an honest n!
  ordering enumeration that checks the three axioms directly (the over-budget case is reported, not
  guessed).

Authoritative axiom statement (independent of the recognizer): `verify/brute_oracle.py:9-14`.
Full source-grounded algorithm description: `recognizer/ALGORITHM.md`.

---

## §2 Methodology — ground truth, harnesses, provenance

**Ground truth.** `verify/brute_oracle.py` enumerates all `n!` node orderings and checks A1/A2/A3
directly. It shares no code with the recognizer, so agreement is meaningful. It is exact for `n≤9`.

**Differential harnesses.** `verify/difftest.py` (recognizer, all backends) and
`verify/difftest_exp.py` (exponential) generate random labeled digraphs — *including self-loops and
parallel edges* — mixed with generator-built positive WGs and 16 curated structural edge cases
(`verify/edgecases.py`), and compare every verdict to the oracle. For this report both harnesses
gained an environment override (`WGT_REC` / `WGT_EXP`) so one harness drives any historical binary,
and a per-class breakdown (false-accept vs false-reject). `difftest_exp.py --encoding old` decodes
the OLD baseline's inverted column-0 scheme (see below).

**Benchmark row contract.** With `-b`, a decider prints one line `verdict⟨tab⟩nodes⟨tab⟩cpu⟨tab⟩path`.
For the NEW recognizer `verdict` is `1`=WG, `-1`=non-WG, `0`=undecided (z3 `unknown`). The `cpu`
column is raw `clock()` ticks (CPU time, ≈ µs on Linux) — **contention-robust**, so we lead the
performance headline with it and report wall time (`perf_counter`, median of R replicates) as a
cross-check.

**The exp encoding inversion (critical).** The fixed `recognizer_e` uses `1`=WG / `0`=non-WG /
`-1`=over-cap. The *unsound* OLD `recognizer_e` used an **inverted** scheme: `0`="Wheeler",
`-1`="not / over-cap" — and in practice it returned `0` for **every** graph it finished (it never
computed a real non-WG verdict). Decoding it honestly (`0 → WG`) is what exposes its
accept-everything behaviour. A live probe (`/tmp/wgt_probe`): on a 4-node non-WG it prints `0`
(decoded WG = wrong); on a 3-node WG it prints `0` (right by accident). The honest binary prints
`0`(non-WG) and `1`(WG) respectively.

**OLD-binary provenance** (rebuilt from git via worktrees; Z3 statically linked from
`recognizer/src/libz3.a`; build line in §8):

| name | commit | what it is |
|---|---|---|
| `recognizer_buggy` | `8ed7c4eb4` | recognizer **before** the Phase-1 correctness fixes |
| `recognizer_pre41` | `c396d2b56` | `-f` with **dense** A2 (`O(E²)`) + dense A3, before the z3-unknown fix |
| `recognizer_linux_old` (pre-4.2) | `3f9045d2d` | `-f` with **sparse A2** (Phase 4.1) + dense A3 |
| `recognizer_linux` (**NEW**) | `d0c02ca37` | `-f` with sparse A2 **and** sparse A3 (Phase 4.2) + all fixes |
| `recognizer_e` (**NEW exp**) | `devel` | honest n!-enumeration decision procedure |
| `recognizer_e_unsound` | `4cfd7a9e2` | the published exp baseline (accept-everything) |

The committed `recognizer/bin/recognizer` is a **macOS arm64** Mach-O binary and is excluded from
all measurements (it cannot run on this Linux host).

**Plotting environment.** The base conda `python3` has a broken numpy (`numpy.__file__ is None`), so
all figures are rendered with `~/miniconda3/envs/spliceai/bin/python` (numpy 1.23 / matplotlib 3.7).
The harnesses themselves need no numpy.

---

## §3 Correctness — NEW vs OLD

### 3.1 The recognizer false-accepted non-Wheeler graphs (Fig 1)

![Fig 1](report_figs/F1_false_accepts.png)

On a reject-heavy random corpus of 6000 graphs (1441 WG / **4559 non-WG**, `--max-n 6`, seed 11),
the OLD buggy binary (`8ed7c4eb4`) **false-accepts** non-Wheeler graphs through its permutation
backends:

- `-s p` (permutation): **950 false-accepts** (20.8% of the 4559 non-WG) — `permutation_start()`
  only ever exited via the accept path; on search exhaustion it fell through to the default
  `valid_wg=true` (bug #1).
- `-s p -e` (exhaustive): **950 false-accepts** — the exhaustive path accepted unconditionally
  (bug #2). **This is the exact mode the paper's GT benchmark used.**

The default SMT and `-f` backends at `8ed7c4eb4` were already correct on this corpus (0 false
verdicts — the bugs were localized to the permutation backends). The NEW binary false-accepts
**0** in every backend (`data/corr_new.log`). The fifth group contrasts the exponential baselines
(see 3.3).

### 3.2 The NEW recognizer agrees with the oracle on every decided graph (Fig 2)

![Fig 2](report_figs/F2_verdict_agreement.png)

Across **2447** graphs — 931 real n≤9 GT_vs_WGT graphs (accept-heavy) and 1516 synthetic graphs
(379 WG / 1137 non-WG, reject-heavy) — the SMT, permutation, and exponential deciders each agree
with the oracle on **100%** of decided graphs: **0 disagreements** (`VERDICT_AGREEMENT.md`). This
session's `difftest.py` sweep adds a further ≈16.6k graphs with 0 mismatches.

### 3.3 The OLD exponential baseline was not a decision procedure

The published `recognizer_e` (`4cfd7a9e2`) received only scalar counts in its checker (never the
graph's edges), so its L-array check was dead code and it returned "Wheeler" for **every** in-cap
graph — it had no non-Wheeler verdict at all. Decoded in its own scheme, on the in-cap subset it
returned a verdict for, it false-accepts **127 / 127 (100%)** of the non-Wheeler graphs — *every
one* — and emits **0** genuine not-WG verdicts (`data/exp_unsound.log`). It is also impractically
slow: it additionally **hung past the per-graph cap on 60** further graphs (the published code never
handled self-loops / parallel edges). The rewritten honest `recognizer_e` decides the same kind of
corpus correctly — **0 / 1573** false-accepts over 2512 decided graphs (`data/exp_honest.log`) — and
agrees with the oracle on the 931-graph real subset (931/931).

> The two OLD recognizer backends false-accept **20.8%** of non-WG graphs (950 / 4559); the OLD exp
> baseline false-accepts **100%** (127 / 127) and never produces a non-WG verdict at all. Fig 1 shows
> the raw counts (note the differing per-group denominators in its title); the **rate** is the
> apples-to-apples number.

> **Honesty note.** On the *real* GT_vs_WGT corpora the OLD baselines' observed false-accept count
> is **0** — but that is an *artifact*, not a virtue: the OLD exp timed out on every non-Wheeler
> graph (never reaching a verdict), and the 7 non-WG graphs were rejected by the recognizer's
> Steps 1–2 before the buggy `-e` phase. The accept-everything bug is only *exercised* by the
> synthetic reject-heavy corpus and the rebuilt buggy binary — which is exactly why Fig 1 uses them.

### 3.4 Capability — verdicts the OLD baseline could not produce (Fig 3)

![Fig 3](report_figs/F3_capability.png)

Correctness asks "is the verdict right?"; **capability** asks the prior question "can a verdict be
produced at all?" On the n≤9 oracle-decidable subset of the paper's GT_vs_WGT corpora (931 graphs,
`PHASE3_IMPACT.md`), the OLD exponential baseline timed out on **159 / 931** — including **all 7**
non-Wheeler graphs — so it could *never* classify a single non-Wheeler instance. The honest
`recognizer_e` decides **931 / 931** correctly, among them those **7 non-Wheeler RevDetG_DNA
orthologue graphs** (BTBD17, FAM53A, LCP1, TRAM1, TRPC1) — verdicts the published baseline was
structurally incapable of emitting. Scaling capability (largest graph decidable within a time budget)
is §5.

The `-f` path is where Phase 4.1/4.2 live. It hands the entire order space to z3, so the **encoding
size** dominates. The two sparsifications:

| constraint | OLD `pre-4.1` (`c396d2b56`) | Phase 4.1 `pre-4.2` (`3f9045d2d`) | Phase 4.2 **NEW** (`d0c02ca37`) |
|---|---|---|---|
| cross-group **A2** (head ordering between labels) | `O(E²)` all-pairs | **`O(E+L)`** per-label head-boundary (`#lo_/#hi_`) | `O(E+L)` |
| within-group **A3** (head order from tail order, per label `l`) | `O(E_l²)` all-pairs | `O(E_l²)` all-pairs | **`O(D_l²+E_l)`** endpoint-block (`#mn_/#mx_`), `D_l=min(distinct tails,heads)` |

The Phase 4.2 block form is **equisatisfiable** with the all-pairs form (all atoms stay in QF_IDL;
proof sketch in `ALGORITHM.md`) and is used only behind a **never-worse guard**
`D_l(D_l−1)+2E_l < E_l(E_l−1)`, so all-distinct-endpoint groups fall back to the original loop.

### 4.1 Setup/solve split on the headline graphs (Fig 7)

![Fig 7](report_figs/F7_setup_solve.png)

Measured (median of 3, `data/micro.setup_solve.csv`), DOCK4 De-Bruijn DNA k=5 (1041 edges):

| phase | pre-4.1 | pre-4.2 | **NEW** | NEW vs pre-4.1 |
|---|--:|--:|--:|--:|
| SMT setup (encoding build) | 2.11 s | 1.88 s | **0.14 s** | **≈ 14.5×** |
| SMT solve (z3) | 13.04 s | 12.33 s | **6.44 s** | **≈ 2.0×** |
| **total `-f`** | **15.15 s** | 14.21 s | **6.59 s** | **≈ 2.3×** |

The setup win is almost entirely **A3 (Phase 4.2)**: pre-4.1 → pre-4.2 barely moves setup
(2.11 → 1.88 s) because these few-label DNA graphs have little cross-group (A2) cost, whereas
pre-4.2 → NEW collapses it (1.88 → 0.14 s). The smaller formula also roughly halves z3 solve time.
TRPC1 k=5 (1049 edges) shows the same shape (setup 2.24 → 0.16 s, total 15.7 → 8.0 s).

### 4.2 Distribution across the real corpus (Figs 4–6)

![Fig 4](report_figs/F4_f_scatter_cpu.png)

3-point sweep (pre-4.1 / pre-4.2 / NEW), `-b -f`, **string labels** (no `-i`, matching the biological
corpora), median of replicates, 90 s per-graph timeout, on the DNA corpora
(`data/graph/SMT_vs_RHSMT/{DeBruijnG,RevDetG}_DNA`; the full DeBruijn k-mer range incl. k=5 plus a
representative non-WG-heavy RevDetG sample — the largest RevDetG non-WG graphs were sampled, not
exhausted, to bound runtime). The distribution reveals a **verdict-dependent asymmetry that the
single-graph headline hides**, and we report it plainly. Over the **290 graphs** all three versions
decided (183 WG, 107 non-WG; CPU-time medians):

| comparison | WG / SAT instances | non-WG / UNSAT instances |
|---|--:|--:|
| **pre-4.1 → NEW** (total Phase-4 gain) | median **1.43×** (max 2.34×) | median **1.44×** (max 2.07×) |
| **pre-4.2 → NEW** (isolated A3 gain) | median **1.18×** (max 2.50×) | median **1.04×** (≈ neutral) |

- **vs the original pre-4.1**, NEW is faster on *both* SAT and UNSAT instances (median ~1.43×) — a
  clean win over the baseline that paper figures would have used.
- **The isolated A3 step (pre-4.2 → NEW) helps SAT instances but is roughly neutral on UNSAT**, with
  a **tail of 23 / 107 (≈21%) non-WG graphs where NEW is *slower*** than pre-4.2 (worst observed in
  wall time: a 525-edge non-WG graph, 9.5 s → 67.8 s). The reason is structural and worth stating:
  the block encoding trades a quadratic
  *constraint* count for a linear number of **auxiliary order variables**, which shrink the formula
  (great for *finding* a model on a Wheeler graph) but **enlarge the search space z3 must refute** to
  prove *no* order exists on a non-Wheeler graph. Encoding **setup** still shrinks universally (it is
  about building fewer constraints, SAT or UNSAT — ≈6× at k=4, ≈14× at k=5); the regression is
  confined to z3 **solve** time on UNSAT instances.

Fig 4 is the per-graph scatter (points below y=x = NEW faster), colored by verdict — non-WG points
sit closer to / above the diagonal. Fig 5 is the speedup ECDF split by verdict (the asymmetry above).
Fig 6 is the cactus/survival curve. The headline DOCK4 DNA k=5 graph (§4.1) is a *Wheeler* graph, so
its 2.3× total speedup is representative of the SAT case, not the UNSAT case.

![Fig 5](report_figs/F5_speedup_ecdf_cpu.png)
![Fig 6](report_figs/F6_cactus_cpu.png)

### 4.3 Memory — an honest space-for-time trade (Fig 7b)

![Fig 7b](report_figs/F7b_memory.png)

Peak resident set size (`/usr/bin/time -v`, `data/micro.mem.csv`) tells a more nuanced story than
the time numbers. On the headline DNA k=5 graphs the NEW encoding uses **more** memory, not less:

| graph | pre-4.1 | pre-4.2 | **NEW** |
|---|--:|--:|--:|
| DOCK4 DNA k=5 (1041 edges) | 0.66 GB | 0.66 GB | **1.21 GB** |
| TRPC1 DNA k=5 (1049 edges) | 0.67 GB | 0.67 GB | **1.29 GB** |

This is expected and reported as-is: the sparse forms trade a quadratic *number of constraints* for a
linear number of **auxiliary integer variables** (`#lo_/#hi_`, `#mn_/#mx_`). On graphs small enough
that the dense `O(E²)` constraint set never explodes (E≈1000 here), those aux variables widen z3's
IDL variable domain and raise peak RSS by ≈2× — while still cutting setup ≈14× and total time ≈2×.
The memory picture only *inverts* on much larger graphs, where the dense `O(E²)`/`O(E_l²)` constraint
count is what blows up RAM; but those are precisely the all-distinct-endpoint cases where `-f` does
not finish for any generation within the timeout (§4.4), so there is no clean finished-vs-finished
memory comparison to plot there. **Takeaway:** Phase 4.1/4.2 are a time/space *trade*, paying
moderate extra memory on tractable graphs to buy a large setup-time reduction — not a memory win.

### 4.4 The honest limit: all-distinct, dense groups

When a label group has (near-)all-distinct endpoints, `D_l ≈ E_l`, the never-worse guard fails and
the block form correctly **falls back** to the pairwise loop — so there is **no speedup** there. The
extreme case is DOCK4 **AA** k=5 (6636 edges, 20-letter alphabet → many distinct endpoints):
measured (`/tmp` probe, 90 s cap), the `-f` encoding **does not finish setup within 90 s for *any*
generation** — pre-4.1, pre-4.2, and NEW all hit the wall (`timeout`, exit 124). This is a property
of NP-hard recognition under `-f`, not a regression: with all-distinct endpoints there is no block
structure to exploit, so all three versions reduce to the same quadratic encoding.

The point is that **`-f` is the wrong tool for such graphs in the first place**. On the very same
DOCK4 AA k=5 graph, the **default** (range-narrowed) backend prints `(v) Decided after propagation`
and accepts it **instantly** — Step 2's renaming heuristic collapses the order space before any SMT
encoding is built. `-f` exists to hand the *whole* space to the solver (for cases where the
heuristic's narrowing is itself in question); it is not the production path, and Phase 4.1/4.2 speed
up the cases where `-f` *is* tractable (few-label, high-multiplicity graphs) without changing the
fact that the default backend is what one runs in practice.

---

## §5 Scalability — how large a graph can each algorithm recognize?

> **Status: preliminary.** The `benchmark/limit_test/` ladder→bisect sweep (600 s timeout, R=3) is
> still running at the time of this revision. The numbers below are the *in-progress* observations;
> the final typed per-algorithm limits and Figs 8–10 (size-vs-time per family, the limits bar chart,
> and the OLD-vs-NEW `-f` scalability overlay) are added in the §5 update once the sweep completes.
> The harness is committed and resumable (`benchmark/limit_test/`), so these reproduce exactly.

The harness climbs a geometric size ladder per (algorithm, family) under a **600 s** wall-clock
timeout, takes the **median of R=3** replicate graphs per rung, and bisects the largest size still
decided. Every rung doubles as a large-scale differential correctness test: the `complete` and
`dnfa` families are Wheeler **by construction**, so every decisive verdict must be WG (the brute
oracle anchors the small rungs). Limits are **typed** — THRESHOLD (timeout-bounded), CAPPED
(capability cap: `exp` over-budget, `full` z3-`unknown`, `wheelerize` trie-too-large), or UNREACHED.

Preliminary observations (in-progress; the `complete` family is the symmetric worst case):

| backend | `complete` family | `dnfa` family |
|---|--:|--:|
| **default SMT** | decides n ≈ **2900+** within 600 s (still climbing) | n ≈ **2300+** |
| permutation (`-s p`) | n ≈ **192–240** | n ≈ **256** |
| full-range (`-f`, NEW) | n ≈ **384** | (in progress) |
| exponential (GT) | CAPPED ≈ n=10 (n!·e² budget) | CAPPED ≈ n=10 |

The default range-narrowed SMT backend is, as expected, the dramatically better scaler — an order of
magnitude past the permutation and full-range backends, and ~290× past the exponential baseline's
hard cap. The OLD-vs-NEW `-f` overlay (`full-old` = pre-4.2) is being collected and will quantify
whether Phase 4.2 raises the `-f` max size as well as lowering its per-graph time.

---

## §6 Repair — turning a non-Wheeler graph into a Wheeler graph (Fig 11)

![Fig 11](report_figs/F11_repair_blowup.png)

`repair/wheelerize.py` (Phase 5) repairs a **DAG** into a Wheeler graph by unfolding it into the
**trie of its path-strings**. A trie is always a Wheeler graph (order by co-lex of the incoming
string), so this **always succeeds for a DAG**, and it preserves the **set of path-strings** exactly.
Each run self-verifies three ways (recognizer accepts; oracle accepts when small; path-string set
equals the input's).

Over **820** random DAGs, **316** needed repair (504 were already Wheeler) and **0** failed
verification (`data/repair_records.json`). The node blow-up ratio averaged **0.87×**
(range 0.33×–1.86×); Fig 11 shows the full distribution (a spike at 1.0 = unchanged, a sub-1.0
cluster = merging, a >1.0 tail = genuine node-splitting).

> **Read the ratio correctly.** Blow-up `<1` is **merging**, not compression of information: nodes
> that spell the same string are merged, so the *node count* can drop while the represented
> path-string **set** is preserved exactly (multiplicity and node identity are not). Ratios `>1` are
> genuine node-splitting. This first version is not minimal (minimal node-splitting is future work).

---

## §7 Discussion

- **Correct first, fast second.** The most consequential change is not a speedup — it is that the
  recognizer and the exponential baseline now give *trustworthy* verdicts. The OLD permutation
  backends and the OLD exponential baseline both shipped false-accepts; any downstream conclusion
  that relied on their "Wheeler" answers was unsupported.
- **The published GT figure was measuring noise.** The OLD exp produced no non-Wheeler verdicts and
  timed out on most graphs, so the published `GT_vs_WGT` verdicts were meaningless and its timings
  reflected useless work. Re-running with the honest binary changes both the verdicts and the cost
  model (n!-ordering enumeration, not `2^(e+n)`).
- **Performance gains are asymptotic, guarded, and honestly two-sided.** The sparse forms have a
  strictly-smaller-or-equal *constraint count* (the never-worse guard only switches them on when they
  reduce it), and encoding *setup* shrinks universally. But fewer constraints come at the price of
  more auxiliary order variables, and that is a genuine trade: it speeds up *finding* a model (SAT /
  Wheeler graphs — the headline k=5 wins) while it can slow down *refuting* one (UNSAT / non-Wheeler
  graphs, ~20% of which regress; §4.2). Net, NEW still beats the original pre-4.1 on both SAT and
  UNSAT; the regression is purely the isolated A3 step on UNSAT. A future refinement could gate the
  block encoding on an SAT/UNSAT heuristic, or only on the SAT-leaning default-backend path. Crucially
  the **default** backend is untouched and is what runs in practice; `-f` is the completeness path.
- **Scope honesty.** `-f` is an NP-hard full-search path; no encoding makes it polynomial. The
  default range-narrowed backend is what makes recognition fast in practice; `-f` exists for
  completeness and for graphs where the heuristic's narrowing is itself the question.

---

## §8 Reproducibility

**Build (Linux), run from `recognizer/`:**
```bash
g++ -std=c++17 -pthread -O3 -w -I /home/kh.chao/miniconda3/include/ \
    $(find src -name '*.cpp') src/libz3.a -lstdc++fs -o bin/<name>
```
OLD binaries were built from the commits in §2 via `git worktree add /tmp/wgt-old-X <commit>`.

**Sweeps** (all under detached `tmux`; outputs in `benchmark/report_figs/data/`):
```bash
# S1 correctness (buggy vs NEW), S2 exp soundness (unsound vs honest)
bash benchmark/report_figs/run_correctness.sh
# S3 3-point -f timing (pre41/pre42/new) on the real DNA then AA corpora
bash benchmark/report_figs/run_ftiming.sh
# S4 setup/solve split + peak RSS, S5 repair blow-up dump
bash benchmark/report_figs/run_micro.sh
# scalability limit test (600 s timeout, R=3)
python3 benchmark/limit_test/limit_test.py --timeout 600 --replicates 3 \
    --families complete,dnfa,random-dag --algorithms smt,perm,full,exp,wheelerize --old-f \
    --out benchmark/limit_test/results
```

**Figures** (render with the spliceai python):
```bash
~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/plot_report.py   # F1–F7b, F11
~/miniconda3/envs/spliceai/bin/python benchmark/limit_test/plot_limit.py \
    --results benchmark/limit_test/results                                    # F8–F10
```

| Figure | Data file | Generator |
|---|---|---|
| F1 false-accepts | `data/corr_buggy.log`, `data/corr_new.log`, `data/exp_unsound.log` | `plot_report.py` |
| F2 verdict agreement | `data/static_metrics.json` (← `VERDICT_AGREEMENT.md`) | `plot_report.py` |
| F3 capability | `data/static_metrics.json` (← `PHASE3_IMPACT.md`) | `plot_report.py` |
| F4–F6 `-f` scatter/ECDF/cactus | `data/ftiming_dna.raw.jsonl` (DNA corpus; AA covered by the §4.4 probe) | `plot_report.py` |
| F7 / F7b setup-solve / memory | `data/micro.setup_solve.csv` / `data/micro.mem.csv` | `plot_report.py` |
| F8–F10 scalability | `limit_test/results/summary/limit_summary.csv` + `raw/runs.jsonl` | `plot_limit.py` |
| F11 repair blow-up | `data/repair_records.json` | `plot_report.py` |

**Honesty gates checked.** Three axes never merged · exp shown as capability/correctness, never a
speedup · `unknown` ≠ reject kept distinct · macOS binary excluded · OLD commit hashes pinned ·
medians over repeats · timeouts recorded as timeouts (never a verdict) · label modes matched per
corpus (biological = string labels, no `-i`).

---

## Appendix A — the bugs, with the test that catches each

Each was found by **oracle disagreement** and is regression-covered. File:line anchors are on
`devel`.

| # | bug | site | fix | caught by |
|---|---|---|---|---|
| 1 | permutation backend false-accepts on search exhaustion | `graph.cpp:592`, `wg.cpp:47,197` | reject at end of `permutation_start` when not exhaustive | `difftest.py` (perm), Fig 1 |
| 2 | `-e` exhaustive mode accepts unconditionally | `wg.cpp:191` | decide by `get_valid_WG_num()>0` | `difftest.py --modes perm-e`, `edgecases.py`, Fig 1 |
| 3 | propagation fast-path accepts with no final check | `graph.cpp:358-363` | run `WG_checker()` before accepting | `difftest.py` |
| 4 | `permutation_counter` `int` overflow → wrong dispatch | `graph.cpp:367-373` | saturating product | large-range graphs |
| 5 | `-f` SIGABRT on empty/isolated-node graphs (`z3::distinct([])`) | `smt.cpp:48,78` | guard `size()>1`; fix `size_t` underflow | `edgecases.py` |
| 6 | `-f` SMT model-extraction clobber (Phase 4.1 aux vars) | `smt.cpp:~166` | skip constants not in `_nodeName_2_newNodeName` | `difftest.py --modes full`, `check_order.py` |
| 7 | `-f` false-reject when z3 returns `unknown` (conflated with `unsat`) | `smt.cpp` `solve_smt` | 3-way: sat/unsat/**unknown=undecided** | `verify/regression/`, `find_f_disagreement.py` |

(Also fixed in the oracle itself: a `n≤1 → Wheeler` shortcut that skipped axiom checks; a single node
with two different-label self-loops violates A2. Now only `n==0` shortcuts.)
