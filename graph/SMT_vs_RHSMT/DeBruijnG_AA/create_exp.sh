for f in $(find ../../../multiseq_alignment/Ensembl_REST/fasta/AA/ -name '*.fa'); do
    fb="$(basename $f)"
    fout="${fb%.fa}"
    # echo "Running $fout (Exp1)"
    python ../../../generator/DeBruijnGraph_generator/DeBruijnGraph_generator.py $f
    # for k in {5..6}
    # do 
    #     # k=6
    #     for l in `seq 100 200 2000`
    #     do
    #         for a in {6..8}
    #         do
    #             # echo python ../../../generator/DeBruijnGraph_generator/DeBruijnGraph_generator.py -o "$fout"_k_"$k"_l_"$l"_a_"$a".dot -k $k -l $l -a $a $f
    #             python ../../../generator/DeBruijnGraph_generator/DeBruijnGraph_generator.py -o "$fout"_k_"$k"_l_"$l"_a_"$a".dot -k $k -l $l -a $a $f
    #         done
    #     done
    # done
done