# Phase 3 — Verdict-agreement metric (NEW)

The benchmark plots are all timing-only — no figure reads the verdict column. This is the missing **correctness** metric: every decider's verdict vs the brute-force oracle (`verify/brute_oracle.py`, ground truth). A disagreement is a recognizer bug.

Deciders: **SMT** = `recognizer_linux` (default), **PERM** = `recognizer_linux -s p`, **EXP** = rebuilt `recognizer_e` (over-cap graphs counted as undecided).

## REAL — n≤9 GT_vs_WGT benchmark graphs (931: 924 WG, 7 non-WG)
Mostly *constructed Wheeler* graphs → exercises the ACCEPT path on real biological inputs.

| decider | agree/decided | disagree | undecided |
|---|--:|--:|--:|
| SMT | 931/931 | 0 | 0 |
| PERM | 931/931 | 0 | 0 |
| EXP | 931/931 | 0 | 0 |

## SYNTH — random + edge cases (1516: 379 WG, 1137 non-WG)
Self-loops, parallel edges, a real WG/non-WG mix, and the 16 curated edge cases → exercises the REJECT path and the `-s p -e` always-accept bug (#2).

| decider | agree/decided | disagree | undecided |
|---|--:|--:|--:|
| SMT | 1516/1516 | 0 | 0 |
| PERM | 1516/1516 | 0 | 0 |
| EXP | 1516/1516 | 0 | 0 |

## Result

**Zero disagreements** across 2447 graphs (1303 Wheeler, 1144 non-Wheeler). Every decider matches the oracle on every graph it decided — across both the accept-heavy real corpora and the reject-heavy synthetic corpus. ✓
