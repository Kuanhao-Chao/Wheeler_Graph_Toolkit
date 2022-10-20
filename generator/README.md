## Random Generators
In the `./Random_generator` directory, we provide a __complete WG generator__ and a __d-NFA WG generator__.

To run the complete WG generator, run the following command.
```
python3 gen_complete_WG.py -n <num_nodes> -e <num_edges> -l <num_labels> [-c | -o <filename>] 
```
Add the `-c` flag if complete WGs are desired. If `-c` is specified the number of edges will be overwritten by the largest possible number of edges given number of nodes and labels. 

To run the d-NFA WG generator, run the command below.
```
python3 gen_d-nfa_WG.py -n <num_nodes> -e <num_edges> -l <num_labels> [-d <d> | -o <filename>] 
```
where `d` is the maximum number of outgoing edges with the same label at each node. 

The default output filename for both generators are `tmp.dot`. Use the `-h` flag for more info about both generators.
