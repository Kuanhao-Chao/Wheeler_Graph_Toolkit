#target_dor=../../../graph/RevDetGraph/test_grp1/
target_dir=$1
echo $target_dir
for f in $target_dir*; do
    #echo "$f"
    python ../../../recognizer/smt/isWheeler.py -i  $f >> all_RD_new_out.txt
    echo $?
done
