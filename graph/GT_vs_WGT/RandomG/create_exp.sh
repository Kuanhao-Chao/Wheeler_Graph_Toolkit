for n in {1..15}
do
    for l in {1..4}
    do
        for e in $(seq 1 $(($n)) )
        do
        # e=$n
            echo python ../../../generator/Random_generator/gen_complete_WG.py -n $n -e $e -l $l -o n_"$n"__e_"$e"__l_"$l".dot
            python ../../../generator/Random_generator/gen_complete_WG.py -n $n -e $e -l $l -o n_"$n"__e_"$e"__l_"$l".dot
        done
    done
done