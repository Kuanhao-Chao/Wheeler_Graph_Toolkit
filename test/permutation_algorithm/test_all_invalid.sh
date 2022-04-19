for file in $(find ../../graph/bad_DOT -name '*.dot');
do 
    echo "$file"
    # result=`../bin/recognizer $file`;
    result=$(../../bin/recognizer $file > /dev/null)
    echo $?
done