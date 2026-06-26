# Wheeler-graph recognition: where is the performance limit?

Stage 1 of the recognition-performance research program — a literature + lower-bound assessment,
cross-referenced with our own Stage-0 profiling (`--profile` in `recognizer/src/`). All hardness
numbers below were verified against primary sources (citations at the end).

## 1. Hardness — the worst case is genuinely exponential
- **Recognition is NP-complete for alphabet σ ≥ 2, even when the graph is a DAG** (Gibney & Thankachan,
  ESA 2019 / *Algorithmica* 2022; reduction from Betweenness, Opatrný 1979). For **σ = 1 it is linear**
  (reduces to "DAG has queue number one"). σ=2 is the exact tractability threshold; acyclicity does not help.
- **Bounded-nondeterminism dichotomy (d = max out-edges with the same label per node):** polynomial for
  **d ≤ 2**, NP-complete for **d ≥ 5**; **d ∈ {3,4} is open**.
- **Optimization variant (WGV = min edges to delete to become Wheeler):** APX-hard (constant-factor,
  via Feedback Arc Set); under UGC, **inapproximable to *every* constant** — so even approximate
  "repair-by-edge-deletion" has no worst-case guarantee. (Note: our Phase-5 repair is *lossless
  node-splitting*, a different, always-feasible operation — not the hard WGV deletion problem.)
- Published exact algorithm: `2^{e·log σ + O(n+e)}`.
- Distinct problem (do not conflate): recognizing whether an automaton's *language* is Wheeler is
  **PSPACE-complete for NFA input, polynomial (O(mn)) for DFA input**.

## 2. Polynomial special cases — the actionable fast-paths (H8)
- **Tries / labeled forests: ALWAYS Wheeler**, constructively (order by the lexicographic rank of each
  node's node-to-root path = the XBWT). Linear, no search.
- **σ = 1 (single label): linear.**
- **DFA / input-deterministic / reverse-deterministic (d ≤ 1): polynomial recognition** —
  O(|δ|·log|Q|) by partition refinement (Becker et al., ESA 2023); acyclic-DFA prefix sort O(m·log n)
  (Kim et al., CPM 2023). **This is the reverse-deterministic fast-path, and the RevDet corpus is
  exactly this family.**
- Collapsed (k-mer-keyed) de Bruijn graphs are Wheeler by construction.
- **DAGs in general: no special tractability** (NP-complete even restricted to DAGs).

## 3. Parameterized / FPT — the key NEGATIVE result
- **No FPT in alphabet σ** (NP-complete already at the fixed value σ=2 forecloses it).
- **No known FPT (or even XP) in co-lexicographic width p for *deciding* Wheelerness of a general
  graph / NFA.** Co-lex width = 1 ⇔ Wheeler, but the width-1 *decision* on general inputs inherits the
  NP-completeness. Co-lex width is powerful for *indexing* (poly given a width-p order) and for *DFAs*
  (min-width order of a DFA is poly; of an NFA is NP-hard), and *language* width via the minimum DFA is
  XP (O(m^p)) with a matching SETH lower bound — but none of these give a general FPT recognizer.
- **Conclusion: there is no parameter known to tame the general recognition problem.**

## 4. Solver/encoding evidence (maps onto our Stage-0 profiling)
- WGT/Wheelie is the **only published SMT recognizer** (Z3 **QF_IDL**, per-node integer positions +
  all-different + range, axioms as difference constraints, with the renaming heuristic pruning first).
- **A Boolean relative-order SAT encoding is theoretically *worse* for the size wall:** it needs
  O(n²–n³) transitivity clauses, whereas IDL's theory check is polynomial per Boolean assignment
  (negative-cycle detection). So a SAT order-encoding will **not** fix our measured `-f` z3
  memory-overflow wall (Stage-0: 902k assertions / 5.6 GB / `reason_unknown="Overflow ... vector"` at
  n=850) — it would be larger. The `-f` wall moves only by **shrinking the encoding** (the Phase 4.1–4.3
  direction, pushed further) or a **non-materializing / native search** that never builds the whole formula.
- The one concrete "better backend" lead: a **specialized ordering-theory DPLL(T)** solver (Ge et al.,
  LCPC 2015 — "ordering constraints, a special case of difference logic"). The IDL-vs-SAT comparison on
  Wheeler instances is *unpublished* — a genuine open contribution.

## 5. Verdict — are we near the limit?
**For the general worst case: yes.** NP-completeness is robust (σ=2, DAGs, d≥5), the optimization variant
is constant-factor inapproximable, and no FPT parameter is known. A general recognizer cannot beat
worst-case exponential on evidence available. **The realistic headroom is therefore NOT asymptotic; it is:**
1. **(a) Fast-path the polynomial subclasses** (trie/forest, σ=1, DFA/reverse-deterministic) — theory-
   backed, high-ROI, and directly serves the RevDet-heavy biological corpus. **← Round-1 priority (H8).**
2. **(c) Encoding/solver engineering** — symmetry-breaking on the default-backend residual blow-up (H2),
   encoding compression / a non-materializing search for the `-f` memory wall, and possibly an
   ordering-theory backend. Constant/polynomial-factor wins, not class improvements.
3. **(b) An FPT parameter — ruled out** for the general case; do not claim it.

This matches our Stage-0 profiling exactly: the heuristic already solves structured/real graphs with no
solver (max_range=1), the fundamental wall is the symmetric `complete`/`dnfa` residual (exponential), and
the `-f` wall is an encoding-size artifact. The WGT design is well-aligned with the theory; the gains to
chase are fast-path coverage + encoding/solver tuning.

**Round-1 empirical confirmation (native-solver attempt — see `native_dl/NATIVE_DL_SOLVER.md`).** We
prototyped the most direct attack on (2c): a sound native difference-logic / bound-consistency propagator
with a trailed randomized-restart search (backend `-s dl`), to decide the residual without materializing
Z3's O(E²) encoding. It is **verified sound** (0 oracle disagreements over ~12k graphs + all edge cases)
but does **not** move the ceiling — it decides only to n≈300–400 on `complete`/`dnfa` (3–9× *below* Z3)
before its search explodes, because Z3's QF_IDL **theory propagation** already makes the search trivial
where hand-rolled bounds propagation does not. The other (2c) lever, encoding compression, was likewise
already shown to regress on the `complete` family (the block A3 form, `smt.cpp:121`). So the binding
constraint is search-guided-by-propagation, which Z3 does near-optimally: **strong empirical evidence
that, for the symmetric worst case, we are at the practical limit.**

**Round-2 revision (lazy/CEGAR A3 — see `lazy_cegar/LAZY_CEGAR.md`).** Round 1's "practical limit"
conclusion was **too strong for the default path**: it held two levers fixed (a non-materializing native
*search*, and *static* encoding compression / block-A3) but missed a third — **lazy / dynamic encoding
generation**. A3 is a *chain* constraint, hence O(E²) only *statically* (the tail order is unknown a
priori); given a concrete order a violation is forbidden by O(E) consecutive-pair lemmas. Generating A3
lazily by CEGAR — keeping Z3's near-optimal search but feeding it only the A3 pairs that actually bind
(backend `-s lazy`) — moves the default ceiling from Z3's **2816/2176 to ≥ 32768** (`complete`/`dnfa`),
**~600× faster / ~130× lighter** at n=2816, **verified sound** (0 oracle disagreements over 13,438
graphs + edge cases). It works because the Step-2 heuristic's brackets make the O(E²) A3 encoding
~99.99 % redundant (at n=32768 only ~4k of ~400M pairs bind). A separate env-gated Z3 `arith.solver`
sweep (`lazy_cegar/h1_arith_sweep.txt`) confirms no Z3 engine flag — including the difference-logic
engine — beats the default, so the lever was the *encoding*, not the solver. **Caveats that keep the
broader limit intact:** the worst-case asymptotics are unchanged (still NP-complete); the `-f` regime
(heuristic bypassed) and truly residual-dense instances stay hard — lazy times out there ~n≈256. So the
sharpened verdict: the *default/production* path was **not** at the practical limit (lazy is strictly
better and a candidate default backend), while the general worst case remains genuinely exponential.

## Primary sources
Gagie–Manzini–Sirén (TCS 2017); Gibney–Thankachan (ESA 2019 / Algorithmica 2022, arXiv:1902.01960);
Opatrný (SICOMP 1979); Alanko–D'Agostino–Policriti–Prezza (SODA 2020, arXiv:1902.01088; Wheeler
Languages, arXiv:2002.10303); Cotumaccio–Prezza (SODA 2021); Cotumaccio–D'Agostino–Policriti–Prezza
(JACM 2023, arXiv:2208.04931 / 2102.06798); Becker et al. (ESA 2023, arXiv:2305.05129; SPIRE 2023,
arXiv:2306.04737; width complexity 2024, arXiv:2410.04771); Kim et al. (CPM 2023, arXiv:2304.10962);
D'Agostino–Martincigh–Policriti (TCS 2023, arXiv:2203.12534); Equi–Grossi–Mäkinen–Tomescu (ICALP 2019 /
TALG 2023); Chao et al. WGT (iScience 2023); Bryant–Velev (2000, cs/0008001); Cotton–Maler (SAT 2006);
Ge–Ma–Huang–Zhang (LCPC 2015).
