#search_dir=../../multiseq_alignment/
for entry in "$1/"*
do
	old_string="../../data/multiseq_alignment/"
	new_string="../../data/graph/RevDetGraph/"
	outfile="${entry/"$old_string"/"$new_string"}"
	outfile=${outfile%.fa}.dot
	outdir=$( dirname -- "$outfile"; )
	if [ ! -d $outdir ]; then
		mkdir -p $outdir;
	fi
	echo python RevDetGraph_generator.py -o $outfile $entry 
	python RevDetGraph_generator.py -o $outfile $entry  
done
