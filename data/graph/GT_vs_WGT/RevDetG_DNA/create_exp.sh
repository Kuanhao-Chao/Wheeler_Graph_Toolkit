for f in $(find ../../../multiseq_alignment/Ensembl_REST/fasta/DNA/ -name '*.fa'); do
    fb="$(basename $f)"
    fout="${fb%.fa}"
    # echo "Running $fout (Exp1)"
    for l in {2..41}
    do
        # for a in {4}
        # do
        a=4
        echo python ../../../../generator/RevDetGraph_generator/RevDetGraph_generator.py -o "$fout"_l_"$l"_a_"$a".dot -l $l -a $a $f
        python ../../../../generator/RevDetGraph_generator/RevDetGraph_generator.py -o "$fout"_l_"$l"_a_"$a".dot -l $l -a $a $f
        # done
    done
done
# DeBruijnGraph_generator.py [-h] [-v] [-o / --ofile FILE] [-k / --kmer k-mer length] [-l / --seqLen sequence length]