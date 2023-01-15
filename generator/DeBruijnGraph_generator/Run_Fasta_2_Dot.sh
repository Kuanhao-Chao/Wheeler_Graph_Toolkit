#search_dir=../../data/multiseq_alignment/Genes/<gene name>/<AA or DNA>/<paralogues or orthologues>
kmers="6"
# for d in {20,40,80,100,150,200,250,300,350,400}
END=5000
for d in $kmers
do
	for ((i=1;i<=END;i+=6))
	do
		# echo $i
		for entry in "$1/"*
		do	
			old_string="../../data/multiseq_alignment/"
			new_string="../../data/graph/DeBruijnGraph/"
			outfile="${entry/"$old_string"/"$new_string"}"
			outfile=${outfile%.fa}_k_"$d"_l_"$i".dot
			outdir=$( dirname -- "$outfile"; )
			if [ ! -d $outdir ]; then
				mkdir -p $outdir;
			fi
			echo python DeBruijnGraph_generator.py -o $outfile -k $d -l $i $entry 
			python DeBruijnGraph_generator.py -o $outfile -k $d -l $i $entry 
		done
	done
done
