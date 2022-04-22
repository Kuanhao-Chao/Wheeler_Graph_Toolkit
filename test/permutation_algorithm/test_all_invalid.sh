for file in $(find ../../graph/bad_DOT -name '*.dot');
do 
    echo "$file"
    # result=`../bin/recognizer_p $file`;
    # result=$(../../bin/recognizer_p $file > /dev/null)
    result=$(../../bin/recognizer_p $file)
    echo $?
done
