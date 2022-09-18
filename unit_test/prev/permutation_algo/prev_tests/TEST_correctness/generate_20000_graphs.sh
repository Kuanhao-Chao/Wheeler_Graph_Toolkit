 for i in `seq 4 2 100`
    do
        python ../../../generator/generate_WG_samples.py ../../../graph/correctness_test/node_num_${i} 1000 $i
 done