# Adversarial correctness audit — the Wheeler-graph index + species/position pattern matching

An exhaustive, adversarial audit of every pattern-matching algorithm in `index/` against **independent**
brute-force ground truth (never trusting the index): `index/locate_oracle.locate_brute` (its own inlined
ungap/cap + coordinate transform), `index/oracle.reachable`, `verify/brute_oracle.is_wheeler`
(all-permutations, n≤9), and per-auditor *from-scratch* reimplementations (brute cyclic-rotation suffix
sort, brute substring scan, hand-built ISA, an independently-written coordinate transform). Run as a
fan-out of 8 auditors, each independently re-attacked by a refuter with harder generators. Every gate is
a durable test under `index/tests/test_audit_*.py` (run via `~/miniconda3/envs/myenv/bin/python -m pytest
index/tests`).

## Result: 1 bug found and fixed; all other algorithms robust

| # | algorithm | independent grounds | adversarial coverage | verdict |
|---|---|---|---|---|
| A | `SuffixIndex` core — `build_text/build_sa/build_bwt/C/_rank/lf/recover_pos/backward_search/count` | brute cyclic-SA, brute BWT/DOC/C/rank, hand ISA, brute substring scan | ~2,000 random multi-doc trials × `s∈{1,2,4,8,n,n+5,2n,10⁶}`; full `_rank` table; `recover_pos(i)==SA[i]` ∀i (incl. s=10⁶ → O(n) walk); cross-doc joins; degenerate `a∈{0,1}`/`[""]`/all-gap/`Σlen=0`; homopolymer A·200; `\|T\|∈{63..193}` block boundaries; identical docs | **robust** |
| B | r-index `phi` / `_backward_toehold` / `locate_phi` / `recover_pos` under `sample='runs'` | hand ISA vs `build_sa_brute`; brute scan; `locate_brute` | `phi(p)==SA[(ISA[p]−1)%n]` ∀p over 3,000+ instances (wrap-focus p∈{0,n−1, SA-pos-0}); `recover_pos==SA` under **runs** (the previously-untested gap); toehold `==SA[hi−1]` (~3,000 instances + 409 yeast patterns); `locate_phi==locate(rate)==brute`; >160k assertions. **Cyclic-wrap `k=−1` branch proven structurally unreachable** (the unique-largest separator `a−1` forces SA-position-0 to be a run head, so 0 is always a φ key) — 0/5,000 counterexamples | **robust** |
| C | genomic coordinate transform / ± strand / alphabet boundaries | `locate_brute` (own transform) **and** an independently-written transform; **genome-anchored** both strands (for `−`: revcomp(G[a:b])==P) | ~1.6M cases: hand-derived `−` tuples; 2,000-trial genome-anchored `±` checks; off-alphabet `N/n/Z/z/*/-/ /$/''` → `[]`; 4,000 blocks × 5 `s` × 2 modes ≈ 1.52M queries; boundaries `start=0`, `pos=0`, `pos=len−m`; 1,966 real sacCer3 `+` hits anchored to chrI | **robust** |
| D | `PangenomeIndex` w-mer prefilter `_block_wmers/_survives` + router `build_global/locate_routed` | `∪ locate_brute` over blocks **and** a from-scratch `_block_wmers` reimpl | 28 real chrI blocks, `w∈{1,2,4,8,30}`, ~220 patterns/w: `locate==locate_routed==∪oracle` ∀P; **soundness** — for every block truly containing P, `_survives` returned True (a true container was **never** dropped); `_block_wmers` exactly matched the reimpl; `w>\|P\|` fallback + all-w-mers-absent → empty | **robust** |
| E | `DAWG` (suffix automaton) — `count/locate/edges`, Wheeler-ness | brute substring scan; `is_wheeler` (all perms); `locate_brute` | exact `locate==brute` on random + clone-forcing repeat-heavy blocks; `is_wheeler` on all single-doc strings len 1–5; genomic via coords | **1 bug → fixed** |
| F | `WGIndex` (De Bruijn FM over recognizer I/O/L) — `count`, range contiguity, `from_iol/from_edges` | own brute reach **and** `oracle.reachable` | example (121 patterns, `count("")==(1,6,5)`); **2,067,185** patterns over **8,000** random graphs (alphabets 1/2/3/6, self-loops, parallel edges) relabeled to a brute-valid Wheeler order; 8 real recognized yeast blocks; `from_iol().iol()==from_graph_dot().iol()` | **robust** |
| G | C++ `wg_suffix` parity incl. block-rank (BLOCK=64) boundaries | Python `SuffixIndex` + brute | block-rank index hand-derived for every `rnk(c,i)`; `\|T\|∈{64,128,192}` exhaustive (all strings len 1–5 × 5 doc layouts × 4 `s` = 27,280 cases) C++==brute; `s∈{1,n,n+5,n+50}`; `--info` parity; genomic via `--coords` == `locate_brute` | **robust** |
| H | cross-engine determinism — `{Py rate s∈{1,4}, Py runs, DAWG}` occurrence-set identity | brute scan + `locate_brute` | 400-trial / 11,088-query core stress (all engines identical) + 2,770 real chrI genomic queries; the one disagreement was the empty-pattern `count` (DIM E, now fixed) | **robust** |

## The one bug (fixed)

**`DAWG.count("")` returned `len(text)` (root-state endpos) while `DAWG.locate("")==[]` and
`SuffixIndex.count("")==0`.** The empty-pattern `count`/`locate` contract broke and disagreed across
engines. Impact is confined to the degenerate empty query (no real DNA occurrence set is affected —
`locate` already guarded `m==0`). **Fix:** `DAWG.count` now returns `0` for the empty pattern
(`index/dawg.py`). Regression tests: `test_audit_dawg.test_empty_pattern_*`,
`test_audit_crossengine_stress.test_empty_pattern_count_consistent_across_engines`.

## Conventions confirmed intentional (non-bugs)

- `count("")==0` / `backward_search("")==(0,0)`; off-alphabet (incl. `N`, lowercase that upper-cases to an
  absent string) → empty range; these are consistent across `SuffixIndex`/`DAWG`/`WGIndex` and `locate`.
- The raw `SuffixIndex(seqs)` constructor requires ungapped/upper/ACGT rows; the real entry point
  `from_fasta` enforces this via `_ungap_cap` — passing lowercase directly raises `KeyError` (a
  precondition, not a defect).
- `a=0` (no documents) is a harmless empty index (`n=0`, `count==0`, no crash).
- The C++ port has **no `runs`/φ mode** (rate-sample only); correctness is transitive (Python runs ==
  Python rate == C++ rate == oracle), not a gap in answers.

## Takeaway

Across **>4 million independently-verified cases**, every species/position pattern-matching algorithm —
the suffix multi-string BWT (SA/BWT/LF/φ/toehold), the genomic coordinate transform (both strands), the
pangenome w-mer router (sound), the DAWG, the De Bruijn `WGIndex`, and the C++ port — agrees exactly with
the independent oracle. One degenerate empty-pattern inconsistency was found and fixed. The index is
correctness-hardened for the scale/memory work that follows.
