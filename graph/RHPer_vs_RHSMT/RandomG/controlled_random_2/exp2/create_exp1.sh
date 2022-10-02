for l in {5..20}
do
    mkdir -p 4000_20000_"$l"
    for r in {1..10}
    do
        echo python ../../../../../generator/Random_generator/gen_complete_WG.py -n 4000 -e 20000 -l $l -o 4000_20000_"$l"/"$r".dot
        python ../../../../../generator/Random_generator/gen_complete_WG.py -n 4000 -e 20000 -l $l -o 4000_20000_"$l"/"$r".dot
    done
done