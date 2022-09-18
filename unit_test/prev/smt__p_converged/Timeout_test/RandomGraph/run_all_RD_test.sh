all_grps="test_grp1 test_grp2 test_grp3 test_grp4_protein test_grp5_protein"
        #../../../../bin/recognizer_p  $f -b >> ./results/all_RD_"$fbase"_out.txt

for f in $(find ../../../../graph/Random/generator_DOT_large/ -name '*.dot'); do
    echo $f
    ../../../../bin/recognizer_p $f -b >> ./results/all_Random_Graph_out.txt
done
