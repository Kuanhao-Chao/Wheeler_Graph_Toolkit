# Scalability limit test

How large a graph can each WGT algorithm **recognize** or **repair** within a wall-clock timeout?
`limit_test.py` climbs a geometric size ladder per (algorithm, family), runs replicate graphs under a
`timeout`, and bisects the largest size that still finishes. The reported limit is **typed**, and the
run **doubles as a large-scale differential correctness test**.

## Run

```bash
# fast smoke (T=5s, R=2, cap n=64) -- validates mechanics end to end
python3 benchmark/limit_test/limit_test.py --quick

# full run (the paper-grade sweep); long -> launch in detached tmux
python3 benchmark/limit_test/limit_test.py --timeout 600 --replicates 3 \
    --families complete,dnfa,random-dag \
    --algorithms smt,perm,full,exp,wheelerize --old-f \
    --out benchmark/limit_test/results
```

Resumable: every run is cached in `results/raw/runs.jsonl` keyed by `(family,algo,n,seed)` and skipped
on restart, so a killed/relaunched sweep loses no work. Reproducible: graphs are seeded
(`--seed`; replicate `r` uses `seed+r`).

## Algorithms × families

| algorithm    | command                                  | notes |
|--------------|------------------------------------------|-------|
| `smt`        | `recognizer_linux -b -i`                 | default range-narrowed SMT |
| `perm`       | `recognizer_linux -b -s p -i`            | permutation backend |
| `full`       | `recognizer_linux -b -f -i`              | full-range SMT (NEW sparse A2+A3 encoding) |
| `full-old`   | `recognizer_linux_old -b -f -i`          | OLD `-f` (pre-Phase-4.2); the speedup overlay |
| `exp`        | `recognizer_e`                           | exponential GT baseline (n!·e² budget) |
| `wheelerize` | `repair/wheelerize.py --int`             | string-preserving DAG repair (self-verifying) |

- **Recognize** families `complete`, `dnfa` (`gen_complete_WG.py` / `gen_d-nfa_WG.py`) are **Wheeler by
  construction**, so the truth is known and every decisive verdict is correctness-checked.
- **Fix** family `random-dag` feeds non-trivial DAGs to `wheelerize` (which verifies its own output).
- Real **FASTA** families are intentionally out of scope here (truth unknown, Biopython, messy size knob).

## What it reports

Per (algorithm, family) the limit is one of:

- **THRESHOLD(n\*)** — largest n decided within T; `n*+ε` fails by **timeout**.
- **CAPPED(reason)** — the tool gave up *before* any timeout: `exp` over-cap (`-1`/sentinel `60000000`),
  `full` **undecided** (z3 returned unknown), or `wheelerize` trie-too-large (exit 3). This is a
  **capability** cap, not a wall-clock limit — drawn hatched in the bar chart.
- **UNREACHED(≥cap)** — still passing at the per-algo cap (a lower bound).

Outcome classes are never conflated: `DECISIVE{1,-1}` / `TIMEOUT` / `CAPPED` / `UNDECIDED` / `ERR`.
A rung **passes** iff the **median** of R replicates finishes within T with a decisive (and, for
known-truth families, correct) verdict.

## Correctness (differential test)

Every decisive verdict on a Wheeler-by-construction graph must be **WG**; the brute oracle
(`verify/brute_oracle.py`, n≤9) anchors the small rungs. A detected failure is **re-run in isolation**
and only flagged if it gives a *confirmed-wrong* result every time (so transient contention failures
don't raise false alarms). Genuine failures are saved to `results/repro/` (`.dot` + `.json`) and the
process exits 1. A clean run prints `correctness failures: 0`.

## Output

```
results/raw/runs.jsonl        every replicate run (the resumable cache)
results/summary/limit_summary.csv
results/repro/                 correctness reproducers (empty on a clean run)
results/plots/*.png           figures (see below)
```

## Plots

```bash
python3 benchmark/limit_test/plot_limit.py --results benchmark/limit_test/results
```

Produces `size_vs_time__<family>.png` (median wall vs size, log-y, with the T line),
`limits_bar.png` (largest n per algorithm; hatched = capability cap), and
`old_vs_new_f__<family>.png` (the OLD-vs-NEW `-f` overlay quantifying Phase-4.2).

**Note:** the base conda `python3` has a broken numpy (conflicting installs → `numpy.__file__` is
`None`), so matplotlib fails there. Plot with an env that has a working numpy+matplotlib, e.g.
`~/miniconda3/envs/spliceai/bin/python` (numpy 1.23 / matplotlib 3.7). The core `limit_test.py` needs
no numpy and runs fine under the base `python3`.
