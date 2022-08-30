all_grps="test_grp5_protein"
for test_grp in $all_grps;
do
    # Test DeBruijnGraph
    target_dir="../../graph/DeBruijnGraph/$test_grp/"
    fbase="$(basename -- $target_dir)"
    for f in $target_dir*; do
        echo "$f"
        python get_node_num_DB_protein.py $f
        if [[ "$?" == 1 ]]; then
            echo "Processing"
            ../../bin/recognizer_p  $f >> ./DeBruijnGraph/all_DB_"$fbase"_out.txt
        fi
    done
done
