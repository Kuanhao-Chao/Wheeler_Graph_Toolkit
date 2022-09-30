mkdir -p ./results

# exp3
for f in $(find ../../../../graph/Random/controlled_random/exp3 -name '*.dot'); do
    echo "Running $f (Exp3)"
    timeout 1000s ../../../../bin/recognizer $f -b -s p -i >> ./results/all_controlled_RD_exp3_out.txt
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t2000000000\t$f" >> ./results/all_controlled_RD_exp3_out.txt
    fi
done

