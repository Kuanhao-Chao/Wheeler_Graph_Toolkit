#!/usr/bin/env bash
# WS1b: -f peak-RSS memory ladder over the De Bruijn DNA graphs that DECIDE within a 150 s budget
# (the timed-out large rungs give no clean finished-process RSS, so they are excluded).
#
# Key correctness note: the recognizer exits 1 (valid WG) or 255 (non-WG), NEVER 0. So we must read
# peak RSS from /usr/bin/time -v's output file regardless of the recognizer's exit code, and treat
# only `timeout`'s rc=124 as a real timeout.
set -u
cd "$(dirname "$0")/../.."          # repo root
DATA="benchmark/report_figs/data"
DG="data/graph/SMT_vs_RHSMT/DeBruijnG_DNA"
LADDER="$DATA/sparse_ladder"
NEW="recognizer/bin/recognizer_linux"
PRE42="recognizer/bin/recognizer_linux_old"
PRE41="recognizer/bin/recognizer_pre41"
MEMCSV="$DATA/micro.mem_ladder.csv"
RSS=$(mktemp)

# Decided-within-budget ladder: committed k=3/4/5 (n=21/74/273) + k=6 small/mid rungs (n≈290..721).
GRAPHS=(
  "$DG/Human_DOCK4_orthologues_DNA_k_3_l_2000_a_8.dot"
  "$DG/Human_DOCK4_orthologues_DNA_k_4_l_2000_a_8.dot"
  "$DG/Human_DOCK4_orthologues_DNA_k_5_l_2000_a_8.dot"
  "$LADDER/DOCK4_DNA_k_6_l_50_a_8.dot"
  "$LADDER/DOCK4_DNA_k_6_l_80_a_8.dot"
  "$LADDER/DOCK4_DNA_k_6_l_120_a_8.dot"
  "$LADDER/DOCK4_DNA_k_6_l_160_a_8.dot"
  "$LADDER/DOCK4_DNA_k_6_l_220_a_8.dot"
)

echo "name,nodes,edges,binary,peak_rss_kb,status" > "$MEMCSV"
echo "MEM_LADDER_START $(date -u +%FT%TZ)"
for dot in "${GRAPHS[@]}"; do
  [ -f "$dot" ] || { echo "  (missing $dot)"; continue; }
  n=$(grep -oE 'S[0-9]+' "$dot" | sort -u | wc -l)
  e=$(grep -c -- '->' "$dot")
  for pair in "pre41:$PRE41" "pre42:$PRE42" "new:$NEW"; do
    lab="${pair%%:*}"; bin="${pair##*:}"
    timeout 150 /usr/bin/time -v -o "$RSS" "$bin" "$dot" -b -f >/dev/null 2>&1
    rc=$?
    kb=$(awk -F': ' '/Maximum resident set size/{print $2}' "$RSS" 2>/dev/null)
    if [ "$rc" = "124" ] || [ -z "$kb" ]; then
      echo "$(basename "$dot"),$n,$e,$lab,,TIMEOUT" >> "$MEMCSV"
      echo "  $lab n=$n e=$e -> TIMEOUT"
    else
      echo "$(basename "$dot"),$n,$e,$lab,$kb,DECISIVE" >> "$MEMCSV"
      echo "  $lab n=$n e=$e -> $((kb/1000)) MB (rc=$rc)"
    fi
  done
done
rm -f "$RSS"
echo "DONE_MEM_LADDER_EXIT_0 $(date -u +%FT%TZ)"
