#!/usr/bin/env bash
# S1+S2 correctness sweeps for the report. Reject-heavy random corpus through the OLD buggy binary
# and the NEW binary (all 4 backends), plus the unsound vs honest exponential recognizer.
# These intentionally exit 1 when they find the OLD bugs, so do NOT set -e.
set -u
cd "$(dirname "$0")/../.." || exit 1
D=benchmark/report_figs/data
mkdir -p "$D"
PY=python3

echo "######## S1a  OLD buggy recognizer (expect perm/perm-e false-accepts) ########"
WGT_REC=recognizer_buggy $PY verify/difftest.py --random 6000 --positives 0 --max-n 6 \
    --seed 11 --modes smt,perm,perm-e,full > "$D/corr_buggy.log" 2>&1
echo "  -> $D/corr_buggy.log (rc=$?)"

echo "######## S1b  NEW recognizer (expect 0 false verdicts) ########"
WGT_REC=recognizer_linux $PY verify/difftest.py --random 6000 --positives 0 --max-n 6 \
    --seed 11 --modes smt,perm,perm-e,full > "$D/corr_new.log" 2>&1
echo "  -> $D/corr_new.log (rc=$?)"

# Note: --max-n 3 keeps every graph inside the OLD unsound binary's tiny 2^(e+n) enumeration cap,
# so it actually produces a verdict (larger graphs over-cap to -1 and, pathologically, can spin for
# ~minutes near the cap boundary). 2500 random graphs is plenty for a clean false-accept rate.
echo "######## S2a  UNSOUND exponential (--encoding old; expect false-accept = all non-WG) ########"
WGT_EXP=recognizer_e_unsound $PY verify/difftest_exp.py --random 2500 --positives 0 --max-n 3 \
    --seed 11 --encoding old > "$D/exp_unsound.log" 2>&1
echo "  -> $D/exp_unsound.log (rc=$?)"

echo "######## S2b  HONEST exponential (--encoding new; expect 0 mismatches) ########"
WGT_EXP=recognizer_e $PY verify/difftest_exp.py --random 2500 --positives 0 --max-n 3 \
    --seed 11 --encoding new > "$D/exp_honest.log" 2>&1
echo "  -> $D/exp_honest.log (rc=$?)"

echo "ALL CORRECTNESS SWEEPS DONE"
