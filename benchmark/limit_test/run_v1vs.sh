#!/bin/bash
cd /ccb/salz3/kh.chao/PR_Wheeler_Graph/PR_Wheeler_Graph/benchmark/limit_test
python3 limit_test.py \
  --algorithms old-default,new-lazy,new-smt,old-f,new-f \
  --families complete,dnfa \
  --timeout 600 --replicates 3 --max-n 65536 --seed 1 \
  --out results_v1vs_current > v1vs_600s.log 2>&1
echo "V1VS_600S_DONE" >> v1vs_600s.log
