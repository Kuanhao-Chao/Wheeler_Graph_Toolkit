start=`date +%s`

#for file in $(find ../../../generator/testing_bad_samples -name '*.dot');
for file in $(find ../../../graph/bad_DOT -name '*.dot');
do 
    echo "$file"
    # result=$(../../bin/recognizer_p $file > /dev/null)
    result=$(../../../bin/recognizer_p $file)
    echo $?
done

end=`date +%s`
runtime=$((end-start))
echo $runtime
