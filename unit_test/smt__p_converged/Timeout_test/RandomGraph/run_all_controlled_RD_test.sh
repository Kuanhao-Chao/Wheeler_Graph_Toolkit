mkdir -p ./results

# exp1
for f in $(find ../../../../graph/Random/controlled_random/exp1 -name '*.dot'); do
    echo Running $f
    ../../../../bin/recognizer $f -b >> ./results/all_controlled_RD_exp1_out.txt
done

# exp2
for f in $(find ../../../../graph/Random/controlled_random/exp2 -name '*.dot'); do
    echo Running $f
    ../../../../bin/recognizer $f -b >> ./results/all_controlled_RD_exp2_out.txt
done

# exp3
for f in $(find ../../../../graph/Random/controlled_random/exp3 -name '*.dot'); do
    echo Running $f
    ../../../../bin/recognizer $f -b >> ./results/all_controlled_RD_exp3_out.txt
done

