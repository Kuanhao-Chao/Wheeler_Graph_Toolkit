#search_dir=../../multiseq_alignment/
for entry in "$1/"*
do
    	./create_RevDetAuto.py $entry
done
