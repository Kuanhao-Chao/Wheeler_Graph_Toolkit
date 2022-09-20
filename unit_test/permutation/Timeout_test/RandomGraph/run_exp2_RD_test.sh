mkdir -p ./results

# exp2
for f in $(find ../../../../graph/Random/controlled_random/exp2 -name '*.dot'); do
    echo "Running $f (Exp2)"
    timeout 1000s ../../../../bin/recognizer $f -b -s p -i >> ./results/all_controlled_RD_exp2_out.txt
    echo $?
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t1000000000\t$f"
    fi
done