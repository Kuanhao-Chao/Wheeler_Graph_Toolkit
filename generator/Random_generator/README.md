## Generator

From this directory, various Wheeler Graphs can be generated (both valid and invalid).

The most straightforward generator is `generate_WG_samples.py`. It can be used to generate Wheeler Graphs in two ways:

To generate multiple samples of a WG with a specified node count, it can be run as the following:
```
python3 generate_WG_samples.py [sample output directory] [number of samples] [node count]
```
For example, running: 
```
python3 generate_WG_samples.py ../../graph/samples 20 50
```
will produce 20 samples of valid WGs each with approximately 50 nodes, in the specified directory.

Additionally, the generator can produce multiple samples with different numbers of nodes. To do this, run as the following:
```
python3 generate_WG_samples.py [sample output directory] [number of samples] [start node] [stop node] [step]
```
For example, running: 
``` 
python3 generate_WG_samples.py ../../graph/samples 20 30 45 5 
```
will produce 20 samples, for each of 30, 35, 40, and 45 nodes. 

---

There are also various generators that produce Wheeler Graphs with specific variations, primarily used for testing our recognizer, as well as performing timing data. They include the following `generate_WG_samples_vary_edge_prob.py` and `generate_bad_WG_samples.py`. They each perform a different purpose, and can be run as the following: 
#### generate_WG_samples_vary_edge_prob.py
``` 
python3 generate_WG_samples_vary_edge_prob.py [output folder] [nodes in WG] [num samples] [start] [stop] [step]
```
This will produce WG with nodes approximately equal to the `nodes in WG` parameter, with varying probability of edges between the nodes (essentially produced graphs of varying widths/densities). 
For example, 
``` 
python3 generate_WG_samples_vary_edge_prob.py ../graph/edge_testing_DOT/50nodes 50 20 .10 .30 .05
```
will produce 20 graphs with approximately 50 nodes, for each of edge probability {.10,.15,...,.30}

#### generate_bad_WG_samples.py
``` 
python3 generate_bad_WG_samples.py [output folder] [num graphs] [nodes in WG] [num partitions]
```
This will produce INVALID WG, where the violation occurs at different levels with respect to the number of edge labels, as specified by the parameter `num partitions`. For example, given 4 partitions and an alphabet of edge labels such as 
```
[['a', 'c'],['d', 'e'],['f','h'],['i'],['j'],]
```
will produce five subfolders, where for the first folder the violation for the WG will occur in one of the edge labels ['a', 'c'], for the second folder will occur in ['d', 'e'], etc. Each subfolder will contain `num graphs` samples. 
For example, running 
``` 
python3 generate_bad_WG_samples.py ../graph/invalid 20 50 10
```
will create 10 subfolders, with 20 graphs each of approximately 50 nodes, with violations from partition 1 to 10 respectively, as indicated previously. 

---

This directory also contains a checker. Any dot file can be passed as the command line argument, and the checker will verify if the graph meets the conditions to be a WG. If it is not a WG, it will output the properties that were violated. Note the current functionality supports only graphs that contain only integer node labels.

Example 1: A valid WG would produce the following output:
```
>>> python3 checker.py ../samples/valid.dot
Inputed graph is a Wheeler Graph
Example 2: A WG that violates all three conditions would produce the following output:
```
Example 2: A WG that violates all three conditions would produce the following output:
```
>>> python3 checker.py ../samples/invalid.dot
Inputted graph is not a Wheeler Graph - the following condition(s) not met:
   * 0-indegree nodes come before others
   * a ≺ a′⟹  v < v′
   * (a = a′) ∧ (u < u′) ⟹  v ≤ v′
```