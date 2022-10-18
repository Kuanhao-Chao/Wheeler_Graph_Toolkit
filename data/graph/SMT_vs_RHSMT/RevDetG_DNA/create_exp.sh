for f in $(find ../../../multiseq_alignment/Ensembl_REST/fasta/DNA/ -name '*.fa'); do
    fb="$(basename $f)"
    fout="${fb%.fa}"
    # echo "Running $fout (Exp1)"
    for l in `seq 100 200 500`
    do
        for a in {4..6}
        do
            # echo python ../../../generator/RevDetGraph_generator/RevDetGraph_generator.py -o "$fout"_l_"$l"_a_"$a".dot -l $l -a $a $f
            python ../../../generator/RevDetGraph_generator/RevDetGraph_generator.py -o "$fout"_l_"$l"_a_"$a".dot -l $l -a $a $f
        done
    done
done