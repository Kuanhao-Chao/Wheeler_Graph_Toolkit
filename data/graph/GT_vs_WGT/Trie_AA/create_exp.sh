for f in $(find ../../../multiseq_alignment/Ensembl_REST/fasta/AA/ -name '*.fa'); do
    fb="$(basename $f)"
    fout="${fb%.fa}"
    # echo "Running $fout (Exp1)"
    # for l in {2..10}
    for l in {1..201..20}
    do
        for a in {3..5}
        do
            echo python ../../../../generator/Trie_generator/Trie_generator.py -o "$fout"_l_"$l"_a_"$a".dot -l $l -a $a $f
            python ../../../../generator/Trie_generator/Trie_generator.py -o "$fout"_l_"$l"_a_"$a".dot -l $l -a $a $f
        done
    done
done
# DeBruijnGraph_generator.py [-h] [-v] [-o / --ofile FILE] [-k / --kmer k-mer length] [-l / --seqLen sequence length]