#target_dir=../../../graph/DeBruijnGraph/test_grp1/
#target_dir=$1
#echo $target_dir
#for f in $target_dir*; do
#    #echo "$f"
#    #../../../bin/recognizer_p  $f >> all_DB_out.txt
#    echo $?
#done


while read p; do
    IFS=$'\t' read -ra ADDR <<< "$p"
    echo "${ADDR[3]}"
    ../../../bin/recognizer_p  ${ADDR[3]} >> all_DB_out_less_100_nodes.txt

done <smt_all_DB_out_less_60_nodes.txt
