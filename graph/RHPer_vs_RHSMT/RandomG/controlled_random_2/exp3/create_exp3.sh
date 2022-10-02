for l in `seq 1 1 20`
do
    e=$((2000*$l))
    echo $e
    mkdir -p 2000_"$e"_"$l"
    for r in {1..10}
    do
        echo python ../../../../../generator/Random_generator/gen_complete_WG.py -n 2000 -e "$e" -l "$l" -o 2000_"$e"_"$l"/"$r".dot
        python ../../../../../generator/Random_generator/gen_complete_WG.py -n 2000 -e "$e" -l "$l" -o 2000_"$e"_"$l"/"$r".dot
    done
done