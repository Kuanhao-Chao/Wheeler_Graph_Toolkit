for n in {3..200}
do
    for l in {1..3}
    do
        # echo "n: $n"
        start=$(($n -1))
        # var=$(seq $start $(($n)) )
        for e in $(seq $start $(($n)) )
        do
            echo python ../../../../generator/Random_generator/gen_complete_WG.py -n $n -e $e -l $l -o n_"$n"__e_"$e"__l_"$l".dot
            python ../../../../generator/Random_generator/gen_complete_WG.py -n $n -e $e -l $l -o n_"$n"__e_"$e"__l_"$l".dot
        done
    done
done
