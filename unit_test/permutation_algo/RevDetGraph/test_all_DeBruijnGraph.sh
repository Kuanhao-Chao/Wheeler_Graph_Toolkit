#target_dir=../../../graph/RevDetGraph/test_grp1/
target_dir=$1
echo $target_dir
for f in $target_dir*; do
    #echo "$f"
    ../../../bin/recognizer_p  $f >> all_RD_out.txt
    echo $?
done
