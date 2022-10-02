for n in `seq 2000 500 8000`
do
    mkdir -p "$n"_8000_4
    for r in {1..10}
    do
        echo python ../../../../../generator/Random_generator/gen_complete_WG.py -n "$n" -e 8000 -l 4 -o "$n"_8000_4/"$r".dot
        python ../../../../../generator/Random_generator/gen_complete_WG.py -n "$n" -e 8000 -l 4 -o "$n"_8000_4/"$r".dot
    done
done