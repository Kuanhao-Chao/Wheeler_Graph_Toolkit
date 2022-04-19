for file in $(find ../../graph/generator_DOT -name '*.dot');
do 
    echo "$file"
    # result=`../bin/recognizer_p $file`;
    result=$(../../bin/recognizer_p $file > /dev/null)
    echo $?
done
