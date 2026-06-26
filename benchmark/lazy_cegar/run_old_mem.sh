#!/bin/bash
cd /ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph/benchmark/lazy_cegar
WGT_NO_PROFILE=1 WGT_REC=/ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph/recognizer/bin/recognizer_main \
  python3 bench_lazy.py --backends smt --families complete,dnfa \
  --ns 64,128,256,512,768,1024,1536,2048,2816 \
  --timeout 600 --seed 1 --out results_lazy_old.csv > old_mem.log 2>&1
echo "OLD_MEM_DONE" >> old_mem.log
