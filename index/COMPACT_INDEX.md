# Toward a more compact Wheeler index: RevDet + repair vs De Bruijn (yeast) — findings & ideas

Goal: a *more succinct* indexable Wheeler graph for a DNA MSA than the order-k De Bruijn graph, by
starting from the compact **RevDet** column automaton and **repairing** it to be Wheeler with as few
nodes/edges as possible. This documents what we measured on yeast (`sacCer3` chrI), the **limit**, and a
brainstorm of algorithms to actually get there. (Pipeline + verification: `pipeline/revdet_to_index.py`,
`index/tests/test_revdet_index.py`, `benchmark/compact_index/`. Verified end-to-end on real yeast blocks:
repair is lossless and the FM-index `count`/range matches the brute oracle.)

## The headline finding (counter to the initial hypothesis)

On yeast, **RevDet + the existing minimal repair is NOT more compact than De Bruijn — it is larger** —
because the repair forces *determinism*, and RevDet's compactness comes precisely from its
*nondeterminism*.

Measured (60 chrI blocks, a=2 sequences, l=40 columns; `data/compact_yeast_a2.csv`):

| quantity | median | range |
|---|---:|---:|
| RevDet raw nodes | 46 | 18–60 |
| De Bruijn (k=4) nodes | **39** | 19–51 |
| path-string **trie** nodes (repair determinizes to this first) | 499 | 32–24,594 |
| repaired (min-size, deterministic Wheeler) nodes | 90 | 23–3,128 |
| node ratio De Bruijn / RevDet+repair (>1 = RevDet smaller) | **0.43** | — |
| RevDet+repair smaller than De Bruijn | **1 / 60 blocks** | — |

So De Bruijn(k=4) is ~2.3× *smaller* than RevDet+repair, and even *raw* RevDet (46n) isn't smaller than
De Bruijn(k=4) (39n) at small k. The repair inflates the graph ~12× on the way through the trie.

**It gets worse with more sequences.** Repeating at a=4 (`compact_yeast_a4.csv`, 40 blocks, trie-cap
8,000): **24/40 (60%) blow past the cap and cannot be repaired at all**, and of the 16 that do repair,
RevDet+repair is **~4.5× larger** than De Bruijn(k=4) (median 145 vs 38.5 nodes; node ratio 0.22; RevDet
smaller in **0/16**). At a=7 the same picture holds (`compact_yeast_a7.csv`): **26/40 (65%) blow past the
cap**, the repairable ones are ~4.3× larger (ratio 0.23, **0/14** smaller). The gap only *widens* with
sequence count — the opposite of the hoped-for "more sequences ⇒ RevDet wins."

## Why: determinism is the enemy of compactness here

- **RevDet is a nondeterministic automaton.** Its column merging (many sequences share a column → one
  node) is what makes it small, but it branches and re-merges, so a node can have two out-edges with the
  same label — *nondeterministic*. A 2-sequence block already spells 2^(#divergent columns) recombinant
  path-strings (we saw 2⁸ = 256 from one pair), so RevDet, like De Bruijn, indexes a *superset* of the
  input sequences (recombinant-inclusive) — neither is exact-sequence membership.
- **The existing repair returns the smallest *deterministic* Wheeler graph** (`repair/minimize.py`,
  min-size = Nerode-minimal DFA of the path-string language) and gets there by **determinizing to the full
  path-string trie first** (`repair/dfa.py`), then quotienting down. Determinizing a nondeterministic,
  recombinant-rich automaton is an **exponential blow-up** (the trie), and even the minimized result is
  larger than a small-k De Bruijn graph.
- **The De Bruijn graph is already (near-)deterministic and small** for small k, because k-mers collapse
  aggressively. So among *deterministic* indexable graphs, small-k De Bruijn is hard to beat on yeast.

**Conclusion:** to beat De Bruijn on compactness, the index must keep RevDet's nondeterminism — i.e. be a
**Wheeler NFA** — or be repaired by **local node-splitting that never determinizes the whole graph**. The
deterministic trie-quotient repair is the wrong tool for *compactness* (it remains the right tool for
*lossless, provably-minimal-deterministic* repair).

## The limit (path-string trie blow-up)

`benchmark/compact_index/limit.py` maps where RevDet+repair breaks. The wall is `dfa.determinize` — it
materializes the path-string trie, whose size grows **exponentially with divergence × #sequences** (each
divergent column roughly doubles the recombinant language). Drivers:

- **divergence** (lower pairwise identity) — the dominant factor; conserved blocks stay tiny, divergent
  blocks explode;
- **#sequences (a)** and **#columns (l)** — more of either multiplies the recombination.

Measured (`limit_yeast.csv`, 180 probes, trie-cap 40,000):

| driver | trie size |
|---|---|
| identity ≥ 0.95 (conserved) | median **65**, max 930 |
| identity 0.85–0.95 | median 226 |
| identity 0.70–0.85 | median **2,525** |
| identity < 0.70 (divergent) | median 784, max **39,995** (the cap) |
| #sequences: blow-up rate past the 40k cap | a=2 **23%**, a=3 **33%**, a=4 **44%**, a≥5 → ~all |

**The repairable ceiling on yeast is ~trie ≤ 5,000** (largest repaired: trie 3,833 → 116 nodes). Yeast
*sensu stricto* species are divergent enough (~55–70% identity in many blocks) that even 2–3 sequences
frequently exceed it. As an extra correctness gate, `repair.minimize.exact == repair.exhaustive_fold`
agrees on a tiny yeast-derived RevDet graph (8 → 8 nodes). The wall is the determinization step itself
(consistent with the repair module's own ~880-trie-node `refine` ceiling), and it bounds **all**
trie-based lossless repair.

## Brainstorm: algorithms to actually get a compact Wheeler index

Ordered by expected payoff, each with the node/edge/scale tradeoff and what to prototype.

1. **Keep it nondeterministic — repair to a Wheeler NFA (WNFA).** RevDet is small *because* it's an NFA;
   a Wheeler graph need not be deterministic. Idea: find a node order + a *minimal* set of local
   duplications that makes the NFA Wheeler **without** determinizing. Expected to be far smaller than the
   deterministic minimum (often near RevDet's own size). Cost: index queries on a WNFA return a node
   *set* that may not be a single contiguous range for *all* patterns unless the WNFA is Wheeler (it is,
   by construction) — backward search still works; `locate` is subtler. **Highest payoff; recommended
   first prototype.**

2. **Trie-free targeted local split (guided by the recognizer's `-x`/`get_violations`).** Never build the
   trie. Loop: recognize → read the violating edges/axioms (`recognizer/src/graph.hpp WGViolation`) →
   split only the node(s) at the conflict (duplicate a node and partition its in/out edges by the
   incoming string that disambiguates) → re-recognize. Stops when Wheeler. Splits are O(#violations), not
   O(trie). Expected: a handful of splits on conserved data, graceful degradation on divergent. Caveat
   (from the violation study): violations are reported from the heuristic order, not an unsat core, so the
   split target is a heuristic — must re-recognize to confirm progress. Pairs naturally with (1).

3. **Partial / bounded determinization.** Determinize only the Wheeler-violating *region* (localized by
   the heuristic `[lb,ub]` ranges + violations), leaving the conserved majority of RevDet untouched.
   Bounds the blow-up to the divergent sub-blocks.

4. **Divergence-aware block windowing.** Split a too-divergent alignment region into column windows whose
   per-window trie stays under a cap, index each, and stitch. Trades one big index for several small ones;
   keeps the method usable past the single-block wall.

5. **Order-guided minimal split (improve `refine`).** Tighten `repair/minimize.py refine`'s split-set
   selection (currently splits all out-of-order head blocks) toward a provably minimal split set per
   round — smaller deterministic results, still trie-bounded.

6. **Edge-reduction post-pass (since edges matter too).** After any repair, dedup parallel edges and
   prefer partitions that minimize edges as a tie-break; report node+edge cost jointly.

## Bottom line / recommendation

The clean result to report: on yeast, **small-k De Bruijn is already the more compact deterministic
Wheeler index; RevDet+deterministic-repair loses because it destroys the nondeterminism that made RevDet
small, via an exponential trie.** The promising path to "smaller than De Bruijn" is a **Wheeler-NFA
repair** (idea 1) and/or **trie-free local splitting** (idea 2) — to be prototyped next, verified against
the same brute oracle and `repair/verify_repair.py`, and measured with `benchmark/compact_index/`.
