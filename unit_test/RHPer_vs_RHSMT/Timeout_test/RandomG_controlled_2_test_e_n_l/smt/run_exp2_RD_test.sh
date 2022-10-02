mkdir -p ./results

# exp2
for f in $(find ../../../../../graph/RHPer_vs_RHSMT/RandomG/controlled_random_2/exp2/ -name '*.dot'); do
    echo "Running $f (Exp2)"
    timeout 1000s ../../../../../bin/recognizer $f -b -s smt -i >> ./results/all_controlled_RD_exp2_out.txt
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t2000000000\t$f" >> ./results/all_controlled_RD_exp2_out.txt
    fi
done