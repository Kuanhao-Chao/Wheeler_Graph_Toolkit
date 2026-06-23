#!/usr/bin/env bash
# WS1: sparse-family OLD-vs-NEW -f scaling + memory ladder.
#
# Two sweeps over a De Bruijn DNA size ladder (the regime where the A3 block FIRES, D/E~0.25),
# run SEQUENTIALLY so the wall-time-sensitive timing sweep owns an idle host before the memory sweep:
#   1) TIMING  : pre41/pre42/new, -b -f, R=3, 120s cap   -> data/ftiming_f_sparse.{raw.jsonl,csv}
#   2) MEMORY  : /usr/bin/time -v peak RSS, 3 binaries, -f, 300s cap -> data/micro.mem_ladder.csv
#
# Honest framing: both curves climb until -f hits the same z3 "unknown"/timeout wall; the gap BELOW
# the wall is the speedup, the wall itself does not move. The committed bytype De Bruijn DNA data
# (n=18..276) covers the low end; this ladder (n=290..1033) carries it across the n~832 wall.
set -u
cd "$(dirname "$0")/../.."          # repo root
ROOT="$PWD"
DATA="benchmark/report_figs/data"
LADDER="$DATA/sparse_ladder"
NEW="recognizer/bin/recognizer_linux"
PRE42="recognizer/bin/recognizer_linux_old"
PRE41="recognizer/bin/recognizer_pre41"
mark() { echo "$1" >> "$DATA/ftiming_f_sparse.log"; echo "$1"; }

mark "START_SPARSE_LADDER $(date -u +%FT%TZ)"

# ---- 1) TIMING sweep (reuse the committed ftiming.py harness) ----
mark "TIMING sweep begin"
python3 benchmark/report_figs/ftiming.py \
  --binaries "new=$NEW,pre42=$PRE42,pre41=$PRE41" \
  --corpus "$LADDER" \
  --timeout 120 --replicates 3 \
  --out "$DATA/ftiming_f_sparse" >> "$DATA/ftiming_f_sparse.log" 2>&1
mark "TIMING sweep done rc=$?"

# ---- 2) MEMORY ladder (clean peak RSS on graphs that decide within 300s) ----
# Low-end rungs from the committed corpus (same gene, DOCK4) + the new k=6 ladder.
MEMCSV="$DATA/micro.mem_ladder.csv"
echo "name,nodes,edges,binary,peak_rss_kb,status" > "$MEMCSV"
LOWEND=(
  "$DATA/../../../data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_DOCK4_orthologues_DNA_k_3_l_2000_a_8.dot"
  "$DATA/../../../data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_DOCK4_orthologues_DNA_k_4_l_2000_a_8.dot"
  "$DATA/../../../data/graph/SMT_vs_RHSMT/DeBruijnG_DNA/Human_DOCK4_orthologues_DNA_k_5_l_2000_a_8.dot"
)
RSS=$(mktemp)
mem_one() { # label binpath dot
  # NOTE: the recognizer exits 1 (valid WG) or 255 (non-WG), never 0 -- so we must NOT gate on its
  # exit code. timeout returns 124 only when it kills the process; any other rc means the recognizer
  # finished and /usr/bin/time -v wrote the peak-RSS line regardless of the recognizer's verdict code.
  local lab="$1" bin="$2" dot="$3"
  local n e rc kb
  n=$(grep -oE 'S[0-9]+' "$dot" | sort -u | wc -l)
  e=$(grep -c -- '->' "$dot")
  timeout 300 /usr/bin/time -v -o "$RSS" "$bin" "$dot" -b -f >/dev/null 2>&1
  rc=$?
  kb=$(awk -F': ' '/Maximum resident set size/{print $2}' "$RSS" 2>/dev/null)
  if [ "$rc" = "124" ] || [ -z "$kb" ]; then
    echo "$(basename "$dot"),$n,$e,$lab,,TIMEOUT" >> "$MEMCSV"
    echo "  mem $lab $(basename "$dot") n=$n -> TIMEOUT"
  else
    echo "$(basename "$dot"),$n,$e,$lab,${kb},DECISIVE" >> "$MEMCSV"
    echo "  mem $lab $(basename "$dot") n=$n -> ${kb}kb (rc=$rc)"
  fi
}
mark "MEMORY sweep begin"
for dot in "${LOWEND[@]}" "$LADDER"/*.dot; do
  [ -f "$dot" ] || { echo "  (missing $dot)"; continue; }
  for pair in "pre41:$PRE41" "pre42:$PRE42" "new:$NEW"; do
    mem_one "${pair%%:*}" "${pair##*:}" "$dot"
  done
done
rm -f "$RSS"
mark "MEMORY sweep done"

mark "DONE_SPARSE_LADDER_EXIT_0 $(date -u +%FT%TZ)"
