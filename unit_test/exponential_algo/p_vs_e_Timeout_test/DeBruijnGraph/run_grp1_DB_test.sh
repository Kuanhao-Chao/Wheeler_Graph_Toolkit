all_grps="mini_test_grp1"
for test_grp in $all_grps;
do
    echo "$test_grp"
    # Test DeBruijnGraph
    target_dir="../../../../graph/DeBruijnGraph/$test_grp/"
    echo $target_dir
    fbase="$(basename -- $target_dir)"
    echo $fbase
    for f in $target_dir*; do
        if [[ $f == *"DeBruijn_k_4"* ]]; then
            echo "$f"
            echo "Processing"
            timeout 500s ../../../../bin/recognizer_e  $f >> ./results/"$fbase"_out.txt
            echo $?
        fi
    done
done
