#target_dir=../../../graph/RevDetGraph/test_grp1/
target_dir=$1
echo $target_dir
fbase="$(basename -- $target_dir)"
for f in $target_dir/*; do
    #echo "$fbase"
    ../../../bin/recognizer_p  $f >> all_RD_"$fbase"_out.txt
    echo $?
done
