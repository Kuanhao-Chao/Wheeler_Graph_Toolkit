#target_dir=../../../graph/DeBruijnGraph/test_grp1/
target_dir=$1
echo $target_dir
for f in $target_dir*; do
    #echo "$f"
    ../../../bin/recognizer_p  $f >> all_DB_out.txt
    echo $?
done
