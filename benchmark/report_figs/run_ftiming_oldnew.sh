#!/bin/bash
cd /ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph
python3 benchmark/report_figs/ftiming.py \
  --binaries pre41=recognizer/bin/recognizer_main,new=recognizer/bin/recognizer_linux \
  --corpus data/graph/SMT_vs_RHSMT/DeBruijnG_DNA,data/graph/SMT_vs_RHSMT/DeBruijnG_AA,data/graph/SMT_vs_RHSMT/RevDetG_DNA,data/graph/SMT_vs_RHSMT/RevDetG_AA \
  --timeout 120 --replicates 3 \
  --out benchmark/report_figs/data/ftiming_oldnew > benchmark/report_figs/ftiming_oldnew.log 2>&1
echo "FTIMING_OLDNEW_DONE" >> benchmark/report_figs/ftiming_oldnew.log
