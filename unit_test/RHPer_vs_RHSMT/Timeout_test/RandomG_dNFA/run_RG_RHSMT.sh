mkdir -p ./results

# exp1
for d in {1..8}; do
    for f in $(find ../../../../graph/RHPer_vs_RHSMT/RandomG/d-nfa/"$d"-nfa -name '*.dot')
    do
        # echo "Running $f (Exp1)"
        echo "timeout 1000s ../../../../bin/recognizer $f -b -s smt -i --outDir ./results/SMT/$d-NFA -r >> ./results/RHSMT_out.txt"
        timeout 1000s ../../../../bin/recognizer $f -b -s smt -i -o ./results/SMT/$d-NFA -r >> ./results/RHSMT_out.txt
        if [ $? -eq 124  ]; then
            echo -e "-1\t0\t2000000000\t$f" >> ./results/RHSMT_out.txt
        fi
    done
done
