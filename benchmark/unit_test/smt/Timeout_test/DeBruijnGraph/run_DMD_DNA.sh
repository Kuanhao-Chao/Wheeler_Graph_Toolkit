grp="DMD"
source="DNA"

# Test DeBruijnGraph
target_dir="../../../../graph/DeBruijnGraph/Genes/$grp/$source/"
echo $target_dir
fbase="$(basename -- $target_dir)"
echo $fbase
for f in $target_dir*; do
    if [[ $f == *".dot"* ]]; then
        echo "Processing $f"
        timeout 500s ../../../../bin/recognizer $f -b >> ./results/"$fbase"_out.txt
        echo $?
        if [ $? -eq 124  ]; then
            echo -e "-1\t0\t1000000000\t$f"
        fi
    fi
done
