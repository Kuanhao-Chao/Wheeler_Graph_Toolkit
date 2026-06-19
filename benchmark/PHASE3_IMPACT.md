# Phase 3 — Paper-impact assessment (GT_vs_WGT)

Ground truth: `verify/brute_oracle.py` (enumerates all n! orderings). Scope: the **n≤9 oracle-decidable subset** of each GT_vs_WGT corpus. OLD = committed 2022/2023 results (broken binaries); NEW = re-run with the fixed `recognizer_linux` and `recognizer_e` (`benchmark/rerun/`).

- **OLD GT** = broken `recognizer_e`: reported `0` ("Wheeler") for *every* graph it finished — no non-Wheeler verdict existed.
- **OLD WGT** = `recognizer -s p -e` with bugs #1/#2: exhaustive mode unconditionally accepted (reported `1`).
- A **false-accept** is a graph the oracle calls NOT_WG that OLD reported as WG.

## Per-corpus (n≤9 subset)

| corpus | graphs | WG | non-WG | NEW-GT=oracle | NEW-WGT=oracle | OLD-GT timeout | OLD-GT decided | non-WG rescued | OLD-GT f-accept | OLD-WGT f-accept |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| DeBruijnG_AA | 100 | 100 | 0 | 100/100 | 100/100 | 0 | 100 | 0 | 0 | 0 |
| DeBruijnG_DNA | 100 | 100 | 0 | 100/100 | 100/100 | 0 | 100 | 0 | 0 | 0 |
| DeBruijnGNC_AA | 100 | 100 | 0 | 100/100 | 100/100 | 0 | 100 | 0 | 0 | 0 |
| DeBruijnGNC_DNA | 100 | 100 | 0 | 100/100 | 100/100 | 0 | 100 | 0 | 0 | 0 |
| RandomG | 38 | 38 | 0 | 38/38 | 38/38 | 18 | 20 | 0 | 0 | 0 |
| RevDetG_AA | 170 | 170 | 0 | 170/170 | 170/170 | 79 | 91 | 0 | 0 | 0 |
| RevDetG_DNA | 173 | 166 | 7 | 173/173 | 173/173 | 60 | 113 | 7 | 0 | 0 |
| Trie_AA | 75 | 75 | 0 | 75/75 | 75/75 | 2 | 73 | 0 | 0 | 0 |
| Trie_DNA | 75 | 75 | 0 | 75/75 | 75/75 | 0 | 75 | 0 | 0 | 0 |
| **TOTAL** | **931** | 924 | 7 | **931/931** | **931/931** | 159 | 772 | **7** | 0 | 0 |

## Findings

- **Correctness restored.** On the 931-graph decidable subset (924 Wheeler, 7 non-Wheeler), the fixed `recognizer_e` agrees with the oracle on **931/931** and the fixed `recognizer -s p -e` on **931/931**.
- **OLD GT could never identify a non-Wheeler graph.** The broken `recognizer_e` had no non-Wheeler verdict — its only outputs were "Wheeler" (`0`) or timeout (`-1`). It timed out on **159/931** of the subset (its `2^(e+n)≤10000` cap), including **all 7 non-Wheeler graphs**. The fixed `recognizer_e` now decides those 7 non-Wheeler graphs correctly — verdicts the old baseline was structurally incapable of producing.
- **Observed false-accepts (oracle=NOT_WG, OLD reported WG):** GT 0, WGT 0. These are 0 here only because OLD GT *timed out* on every non-Wheeler graph (never reaching a verdict), and the 7 non-Wheeler graphs were all rejected by the WGT heuristic at steps 1–2, before the buggy `-e` exhaustive phase. The `-s p -e` always-accept bug (#2) corrupts a non-Wheeler graph only when it survives the heuristic to the exhaustive solver; that path is exercised — and the bug caught — by the synthetic corpus in Phase 1 (`verify/difftest.py`/`edgecases.py`).
- **Non-Wheeler graphs the fix newly classifies (OLD GT timed out, NEW GT + oracle = NOT_WG):**
    - RevDetG_DNA/Human_BTBD17_orthologues_DNA_l_6_a_4.dot
    - RevDetG_DNA/Human_BTBD17_orthologues_DNA_l_7_a_4.dot
    - RevDetG_DNA/Human_FAM53A_orthologues_DNA_l_7_a_4.dot
    - RevDetG_DNA/Human_LCP1_orthologues_DNA_l_7_a_4.dot
    - RevDetG_DNA/Human_TRAM1_orthologues_DNA_l_6_a_4.dot
    - RevDetG_DNA/Human_TRPC1_orthologues_DNA_l_6_a_4.dot
    - RevDetG_DNA/Human_TRPC1_orthologues_DNA_l_7_a_4.dot

## Caveats
- The GT_vs_WGT corpora are mostly *constructed* Wheeler graphs, so the decidable subset is WG-heavy; the non-Wheeler instances here come from the RevDet/De-Bruijn corpora. The synthetic mixed corpus in `benchmark/VERDICT_AGREEMENT.md` (random non-WGs + edge cases) exercises the reject path — and bug #2 — far more thoroughly.
- `recognizer_e`'s O(n!·e²) budget decides only n≲9 graphs; the full corpora are dominated by larger graphs it (correctly) over-caps on. This report covers exactly the subset where a head-to-head verdict comparison is meaningful. The original baseline's `2^(e+n)≤10000` cap was *also* tiny, so neither baseline ever decided the large graphs — the published Figure_1 GT line was overwhelmingly timeouts (e.g. RandomG: 1163/1183).
