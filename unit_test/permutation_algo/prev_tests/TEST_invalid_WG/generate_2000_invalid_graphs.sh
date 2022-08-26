 for i in `seq 86 2 120`
    do
        echo "python ../../../generator/generate_bad_WG_samples.py ../../../graph/TEST_invalid_WG/node_num_${i} 100 $i 1"
        python ../../../generator/generate_bad_WG_samples.py ../../../graph/TEST_invalid_WG/node_num_${i} 100 $i 1
 done