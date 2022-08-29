all_grps="test_grp4_protein"
for test_grp in $all_grps;
do
    echo "$test_grp"
    # Test DeBruijnGraph
    target_dir="../../graph/DeBruijnGraph/$test_grp/"
    echo $target_dir
    fbase="$(basename -- $target_dir)"
    echo $fbase
    for f in $target_dir*; do
        echo "$f"
        python get_node_num.py $f 
        if [[ "$?" == 1 ]]; then
            echo "Processing"
            python ../../recognizer/smt/isWheeler.py -i  $f >> ./DeBruijnGraph/all_RD_"$fbase"_out.txt
            echo $?
        fi
    done
done