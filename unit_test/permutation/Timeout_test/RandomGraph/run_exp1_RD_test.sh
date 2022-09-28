mkdir -p ./results

# exp1
for f in $(find ../../../../graph/Random/controlled_random/exp1 -name '*.dot'); do
    echo "Running $f (Exp1)"
    timeout 1000s ../../../../bin/recognizer $f -b -s p -i >> ./results/all_controlled_RD_exp1_out.txt
    echo $?
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t2000000000\t$f" >> ./results/all_controlled_RD_exp1_out.txt
    fi
done
