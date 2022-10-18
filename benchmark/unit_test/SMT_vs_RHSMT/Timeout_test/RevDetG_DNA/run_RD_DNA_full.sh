mkdir -p ./results

for f in $(find ../../../../graph/SMT_vs_RHSMT/RevDetG_DNA -name '*.dot'); do
    echo "Running $f (Exp1)"
    timeout 1000s ../../../../bin/recognizer $f -b -s smt -f >> ./results/RD_DNA_full_out.txt
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t2000000000\t$f" >> ./results/RD_DNA_full_out.txt
    fi
done
