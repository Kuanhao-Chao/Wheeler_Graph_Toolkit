## Unit Tests for Permutation Algorithm
There are various scripts within this folder for analyzing the permutation algorithm for recognizing WG. 

---

First is `valid_testing.py`. This is meant to be used in conjunction with the WG generator. It will take a parent directory and two file names as its arguments, and perform a timing analysis on the recognizer. 

For example, from within the generator folder you can run: 
```
python3 generate_WG_samples.py ../graph/samples 20 5 30 5
```
This will produce the following folders within `samples` {5,10,15,20,25,30}nodes, each containing 20 samples. 

You can then run the following from the `unit_tests` folder. 
```
python3 valid_testing.py [folder w/ samples] [csv timing file name] [averages txt file name]
```
For example, running: 
```
python3 valid_testing.py ../../../graph/samples csv_name.csv txt_name.txt
```
will produce timing date for each of the subfolders that were generated above. 

---

There is also an `invalid_testing.py`, similarly meant to be used in conjunction with the bad generator that produces violations at specific partitions for different edge labels.

For example, from within the generator folder you can run: 
```
python3 generate_bad_WG_samples.py ../graph/samples 20 20 10
```
This will produce the following folders within `samples` partition{0,1,...,9}, each containing 20 samples with approximately 20 samples. 

You can then run the following from the `unit_tests` folder. 
```
python3 invalid_testing.py [folder w/ samples] [csv timing file name] [averages txt file name]
```
For example, running: 
```
python3 invalid_testing.py ../../../graph/samples csv_name.csv txt_name.txt
```
will produce timing date for each of the partitions that were generated above. 