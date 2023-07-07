mkdir -p ./results

task(){
    timeout 30s ../../../../../benchmark/exponential_recognizer/bin/recognizer_e $1 >> ./results/GT_out.txt >> ./results/GT_out.txt
    if [ $? -eq 124  ]; then
        echo -e "-1\t0\t60000000\t$1" >> ./results/GT_out.txt
    fi
}

# exp1
for f in $(find ../../../../../data/graph/GT_vs_WGT/Trie_DNA/ -name '*.dot'); do
    echo "Running $f (Exp1)"
    task $f
done