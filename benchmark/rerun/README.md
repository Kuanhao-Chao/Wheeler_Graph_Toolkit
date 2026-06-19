# `benchmark/rerun/` — honest benchmark re-run + correctness metrics (Phase 3)

The committed benchmark scripts under `benchmark/unit_test/**` hardcode the **macOS arm64**
`recognizer` binary (won't run on Linux) and the **old broken** `recognizer_e`, and they append into
the committed 2022/2023 result files. This directory re-runs the corpora with the **fixed Linux
binaries**, writes to a **separate** results tree, and adds the verdict-correctness analysis the
published pipeline never had. Nothing here mutates committed scripts or results.

Ground truth throughout is `verify/brute_oracle.py` (independent n! oracle).

## Scripts

### `rerun.py` — re-run the GT_vs_WGT corpora
Repoints to `recognizer/bin/recognizer_linux` + the fixed `recognizer_e`, table-driving the
per-corpus label mode (**RandomG uses `-i`; the biological corpora use string mode**). Emits
canonical 4-column rows `verdict<TAB>n<TAB>cpu<TAB>repo-relative-path`, is idempotent/resumable
(sidecar `.done`), supports `--max-n` and `--limit`, and writes under `benchmark/rerun/results/`.

```bash
# in-session: the n<=9 oracle-decidable subset of all 9 graph types, both sides (~931 graphs/side)
python3 benchmark/rerun/rerun.py --types all --sides both --max-n 9 --fresh
```

### `impact_report.py` — paper-impact assessment → `benchmark/PHASE3_IMPACT.md`
Joins OLD committed results vs NEW re-run vs the oracle on the n≤9 subset; quantifies what the bugs
changed (verdict flips, non-Wheeler graphs the old baseline could never decide). Exits nonzero if
any NEW verdict disagrees with the oracle.

### `verdict_agreement.py` — the NEW correctness metric → `benchmark/VERDICT_AGREEMENT.md`
Cross-tabulates {oracle, `recognizer_linux` SMT, `recognizer_linux` perm, `recognizer_e`} on the
real n≤9 subset **plus** a synthetic reject-heavy corpus (random non-WGs + the 16 edge cases). Exits
nonzero on any disagreement.

```bash
python3 benchmark/rerun/impact_report.py
python3 benchmark/rerun/verdict_agreement.py --synth 1500 --seed 7
```

## Deferred to offline runs (NOT run in-session)

The full sweeps are a multi-hour-to-multi-day compute job and are intentionally not run here:

- **GT_vs_WGT** — 9233 graphs × 30s timeout. `recognizer_e` over-caps on everything past n≈9 (its
  O(n!·e²) budget), so the GT column is overwhelmingly over-cap/timeout either way; the WGT
  `-s p -e` side is the cost driver. Run with no `--max-n`:
  ```bash
  nohup python3 benchmark/rerun/rerun.py --types all --sides both --timeout 30 > rerun_gt.log 2>&1 &
  ```
- **SMT_vs_RHSMT** (900 × 1000s) and **RHPer_vs_RHSMT** (≈895 large graphs, n=2000–8000, × 1000s) —
  not wired into `rerun.py` yet (they use `-s smt`/`-s smt -f` and `-s p`/`-s smt`, and Figures 4/5
  depend on the existing `…/parse_results.py` which derives `n_e_l` from the path). Add an axis
  table to `rerun.py` and preserve the `<exp>/<n>_<e>_<l>/<file>.dot` path segments so
  `parse_results.py` still works.

## Regenerating the figures

No plot reads the verdict column, and `benchmark/results/Figure_1/plot_solvers.py` is path-arg
driven (reads col2/time only), so after a full GT re-run you can regenerate Figure_1 by pointing it
at `benchmark/rerun/results/GT_vs_WGT/*/` — no code change. The verdict-agreement metric is new and
has no committed-figure counterpart.

## Important correctness notes

- **Label mode** must match per corpus or verdicts silently corrupt: RandomG = integer (`-i` /
  oracle `--int`); DeBruijn/Trie/RevDet = string (no `-i`). `recognizer_e` always ranks strings
  lexicographically.
- **Verdict encodings differ**: `recognizer_linux` col0/exit = `1` WG / `-1` not-WG;
  `recognizer_e` col0 = `1` WG / `0` not-WG / `-1` over-cap. The analysis scripts normalize both.
