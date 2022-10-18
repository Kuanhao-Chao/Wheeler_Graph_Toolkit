mkdir -p ./results

for f in $(find ../../../../graph/SMT_vs_RHSMT/DeBruijnG_AA -name '*.dot'); do
    echo "Running $f (Exp1)"
    timeout 1000s ../../../../bin/recognizer $f -b -s smt >> ./results/DB_AA_restrict_out.txt
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t2000000000\t$f" >> ./results/DB_AA_restrict_out.txt
    fi
done
