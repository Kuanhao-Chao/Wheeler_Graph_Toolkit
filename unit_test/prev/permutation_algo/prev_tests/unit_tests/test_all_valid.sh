for file in $(find ../../../generator/samples -name '*.dot');
#for file in $(find ../../../graph/generator_DOT -name '*.dot');
#for file in $(find /Users/chaokuan-hao/Documents/Projects/Genomics-Final-Project/generator/random_node_samples '*.dot');
do 
    echo "$file"
    result=$(../../../bin/recognizer_p $file > /dev/null)
    echo $?
done
