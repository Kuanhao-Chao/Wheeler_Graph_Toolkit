all_grps="mini_test_grp3"
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
        echo "Processing"
        timeout 500s ../../../../bin/recognizer_e  $f >> ./results/"$fbase"_out.txt
        echo $?
    done
done
