for f in $(find ../../../multiseq_alignment/Ensembl_REST/fasta/AA/ -name '*.fa'); do
    fb="$(basename $f)"
    fout="${fb%.fa}"
    # echo "Running $fout (Exp1)"
    for k in {3..9..2}
    do
        for l in {1..201..20}
        do
            # for a in {4}
            # # do
            a=4
            echo python ../../../../generator/DeBruijnGraph_generator_noncollapse/DeBruijnGraph_generator.py -o "$fout"_k_"$k"_l_"$l"_a_"$a".dot -k $k -l $l -a $a $f
            # -l $l
            python ../../../../generator/DeBruijnGraph_generator_noncollapse/DeBruijnGraph_generator.py -o "$fout"_k_"$k"_l_"$l"_a_"$a".dot -k $k -l $l -a $a $f
        # -l $l
        # done
        done
    done
done
# DeBruijnGraph_generator.py [-h] [-v] [-o / --ofile FILE] [-k / --kmer k-mer length] [-l / --seqLen sequence length]