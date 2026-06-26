#!/bin/bash
cd /ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph
python3 benchmark/report_figs/micro.py --out benchmark/report_figs/data/micro_oldnew --replicates 3 --timeout 240 > benchmark/report_figs/micro_oldnew.log 2>&1
echo "MICRO_OLDNEW_DONE" >> benchmark/report_figs/micro_oldnew.log
