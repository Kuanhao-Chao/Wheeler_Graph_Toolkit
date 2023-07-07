mkdir -p ./results

# exp1
for f in $(find ../../../../../data/graph/GT_vs_WGT/RevDetG_DNA/ -name '*.dot'); do
    echo "Running $f (Exp1)"
    timeout 30s ../../../../../recognizer/bin/recognizer $f -b -s p -e >> ./results/WGT_out.txt
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t60000000\t$f" >> ./results/WGT_out.txt
    fi
done