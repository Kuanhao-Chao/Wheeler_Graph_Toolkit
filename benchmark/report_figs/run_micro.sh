#!/usr/bin/env bash
# S4 setup/solve split + peak-RSS memory, and S5 repair blow-up dump.
set -u
cd "$(dirname "$0")/../.." || exit 1
D=benchmark/report_figs/data
mkdir -p "$D"

echo "######## S4  setup/solve split + memory (pre41/pre42/new on headline graphs) ########"
python3 benchmark/report_figs/micro.py --out "$D/micro" --replicates 3 --timeout 240 2>&1
echo "S4 done (rc=$?)"

echo "######## S5  repair blow-up distribution (1000 random DAGs) ########"
python3 repair/test_wheelerize.py --n 1000 --max-n 7 --seed 11 --dump "$D/repair_records.json" 2>&1 | tail -12
echo "S5 done (rc=$?)"
echo "ALL MICRO DONE"
