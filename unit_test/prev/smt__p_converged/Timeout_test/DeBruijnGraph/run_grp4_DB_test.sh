all_grps="test_grp4_protein"
for test_grp in $all_grps;
do
    echo "$test_grp"
    # Test DeBruijnGraph
    target_dir="../../../../graph/DeBruijnGraph/$test_grp/"
    echo $target_dir
    fbase="$(basename -- $target_dir)"
    echo $fbase
    for f in $target_dir*; do
        if [[ $f == *"DeBruijn_k_10"* ]]; then
            echo "$f"
            echo "Processing"
            timeout 500s ../../../../bin/recognizer_p  $f -b >> ./results/"$fbase"_out.txt
            if [ $? -eq 124  ]; then
                echo -e "-1\t0\t1000000000\t$f"
            fi
        fi
    done
done
