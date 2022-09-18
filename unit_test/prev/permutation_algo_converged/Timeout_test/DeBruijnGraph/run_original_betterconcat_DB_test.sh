all_grps="original_betterconcat"
for test_grp in $all_grps;
do
    echo "$test_grp"
    # Test DeBruijnGraph
    target_dir="../../../../graph/DeBruijnGraph/$test_grp/"
    echo $target_dir
    fbase="$(basename -- $target_dir)"
    echo $fbase
    for f in $target_dir*; do
        if [[ $f == *".dot"* ]]; then
            echo "Processing $f"
            ../../../../bin/recognizer_p  $f -b -w -r >> ./results/"$fbase"_out.txt
            echo $?
        fi
    done
done