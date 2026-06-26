#!/bin/bash
cd /ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph/benchmark/lazy_cegar
python3 bench_lazy.py --timeout 600 \
  --backends smt,lazy \
  --families complete,dnfa \
  --ns 1024,1536,2048,2816,4096,6144,8192,12288,16384,24576,32768 \
  --out results_lazy_ceiling.csv > ceiling.log 2>&1
echo "CEILING_DONE" >> ceiling.log
