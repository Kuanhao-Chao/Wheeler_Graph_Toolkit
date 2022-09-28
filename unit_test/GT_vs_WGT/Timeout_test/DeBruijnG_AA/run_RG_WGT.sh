mkdir -p ./results

# exp1
for f in $(find ../../../../graph/GT_vs_WGT/DeBruijnG_AA/ -name '*.dot'); do
    echo "Running $f (Exp1)"
    timeout 10s ../../../../bin/recognizer $f -b -s p -e >> ./results/WGT_out.txt
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t20000000\t$f" >> ./results/WGT_out.txt
    fi
done
