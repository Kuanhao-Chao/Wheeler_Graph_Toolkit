for f in ../graph/correctness_test/node_num_100/*; do
    echo "$f"
    python isWheeler.py $f
    echo $?
done
