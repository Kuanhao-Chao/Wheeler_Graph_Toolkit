all_grps="test_grp1 test_grp2 test_grp3 test_grp4_protein test_grp5_protein"
        #../../../../bin/recognizer_p  $f -b >> ./results/all_RD_"$fbase"_out.txt

for f in $(find ../../../../graph/Random/generator_DOT_large/ -name '*.dot'); do
    echo "$f"
    echo "Processing"
    timeout 15s ../../../../bin/recognizer $f -b -s p >> ./results/all_Random_Graph_out.txt
    if [ $? -eq 124  ]; then
        timeout 15s echo -e "-1\t0\t30000000\t$f" >> ./results/all_Random_Graph_out.txt
    fi
done
