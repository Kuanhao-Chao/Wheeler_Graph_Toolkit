for i in `seq 4 2 100`
# for i in `seq 4 2 6`
    do  
        output_dir="../../../results/TEST_correctness"
        output_file=$output_dir"/node_num_${i}.log"
        valid_count=0
        invalid_count=0
        for file in $(find ../../../graph/correctness_test/node_num_14 -name '*.dot');
        # for file in $(find ../../../graph/generator_DOT/node_num_60 -name '*.dot');
        do 
            # echo "** Testing $file ... " >> $output_file
            result=$(../../../bin/recognizer_p $file > /dev/null)
            # echo "  >> ans:$?"
            if [ $? -eq 1 ]; then
                valid_count=$((valid_count+1))
            fi

            if [ $? -eq 255 ]; then
                invalid_count=$((invalid_count+1))
                echo "(x) '$file' is not a wheeler graph!" >> $output_file
            fi
        done

        echo "" >> $output_file
        echo "*************************" >> $output_file
        echo "******** Results ********" >> $output_file
        echo "*************************" >> $output_file

        echo "The number of valid WG: ${valid_count}" >> $output_file
        echo "The number of invalid WG: ${invalid_count}" >> $output_file
 done


