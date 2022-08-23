for file in $(find ../../graph/generator_DOT_small -name '*.dot');
do
    echo "$file"
    # result=`../bin/recognizer $file`;
    ../../bin/recognizer_e $file
done