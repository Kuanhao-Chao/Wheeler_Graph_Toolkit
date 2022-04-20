start=`date +%s`

for file in $(find ../../graph/bad_DOT -name '*.dot');
do 
    echo "$file"
    # result=`../bin/recognizer_p $file`;
    result=$(../../bin/recognizer_p $file > /dev/null)
    echo $?
done

end=`date +%s`
runtime=$((end-start))
echo $runtime