#target_dir=../../../graph/DeBruijnGraph/test_grp1/
target_dir=$1
echo $target_dir
for f in $target_dir*; do
    #echo "$f"
    python ../../../recognizer/smt/isWheeler.py -i  $f >> all_DB_new_out.txt
    echo $?
done
