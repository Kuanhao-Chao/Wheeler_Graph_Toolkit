all_grps="test_grp1 test_grp2 test_grp3 test_grp4_protein test_grp5_protein"
for test_grp in $all_grps;
do
    echo "$test_grp"
    # Test RevDetGraph
    target_dir="../../../../graph/RevDetGraph/$test_grp/"
    echo $target_dir
    fbase="$(basename -- $target_dir)"
    echo $fbase
    for f in $target_dir*; do
        echo "$f"
        ../../../../bin/recognizer_p  $f -b >> ./results/all_RD_"$fbase"_out.txt
        echo $?
    done
done
