all_grps="test_grp6_protein_RevDet"
for test_grp in $all_grps;
do
    echo "$test_grp"
    # Test RevDetGraph
    target_dir="../../graph/RevDetGraph/$test_grp/"
    echo $target_dir
    fbase="$(basename -- $target_dir)"
    echo $fbase
    for f in $target_dir*; do
        echo "$f"
        python get_node_num_RD.py $f 
        if [[ "$?" == 1 ]]; then
            echo "Processing"
            ../../bin/recognizer_p  $f >> ./RevDetGraph/all_RD_"$fbase"_out.txt
            echo $?
        fi
    done
done