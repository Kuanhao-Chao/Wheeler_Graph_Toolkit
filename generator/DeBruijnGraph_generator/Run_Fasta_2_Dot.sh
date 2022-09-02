#search_dir=../../multiseq_alignment/
#for d in {1,2,3,4,5,6,7,8,9,10}
for d in {3,4}
do
	for entry in "$1/"*
	do
    		#echo ./create_multiSeqDeBruijnGraph.py $entry $d
    		python create_multiSeqDeBruijnGraph.py $entry $d
	done
done
