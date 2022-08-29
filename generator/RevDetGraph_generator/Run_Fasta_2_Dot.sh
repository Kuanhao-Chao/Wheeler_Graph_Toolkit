#search_dir=../../multiseq_alignment/
for entry in "$1/"*
do
    	python create_RevDetAuto.py $entry
done
