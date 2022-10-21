# WGT: visualizer

The visualizer is a python script using [NetworkX](https://networkx.org/) to visualize Wheeler graphs in the **bipartite representation**. It draws the ordered nodes in two replicas, with outgoing edges leaving one replica and entering the other.

<br>

## Run visualizer
To run the complete WG generator, run the following command.

```
python3 visualizer.py [-h] [-o / --ofile output file] <Wheeler graph in DOT format outputed by the recognizer>
```

Here is an example:

```
python3 visualizer.py ../data/example/out__example/graph.dot
```

You will get a 5-node Wheeler graph in the bipartite representation:

![](https://i.imgur.com/9bjZN2e.png)
