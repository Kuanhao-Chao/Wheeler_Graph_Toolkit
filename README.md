# WGT: Wheeler Graph Toolkit &nbsp; <img src="https://i.imgur.com/5ou7Zu0.png" width="250"/>





WGT is the first open source Wheeler Graph suite for generating, recognizing, and visualizing Wheeler graphs. Central to WGT is "***Wheelie***", a fast Wheeler graph recognition algorithm that we proposed, which can recognize a graph with 1,000s of nodes in seconds.


<br>

## What is a Wheeler graph?

A Wheeler graph is a class of directed, edge-labeled graph that is particularly easy to index and query. It is a generalization of the Burrows-Wheeler-Transform-based FM Index [1, 2], and partly forms the basis for existing pangenome alignment tools such as vg [3, 4]. Given an edge-labeled, directed graph. It is a Wheeler graph if and only if there exists a total ordering over its nodes such that:
* 0-indegree nodes come before all other nodes in the ordering
* For all pairs of edges $(u, v)$ and $(u', v')$ labeled $a$ and $a'$ respectively:
  * $a \prec a' \rightarrow v < v'$
  * $a = a' \land u < u' \rightarrow v \leq v'$ 

$\ast$ Fun fact: the logo of WGT is a Wheeler Graph! Try it out! (assuming edges with the same color have the same label. The label of blue edges are lexicographically smaller than label of red edges.)

<details>
  <summary><b>Answer</b></summary>
  
<img src="https://i.imgur.com/76KHLme.png" width="380"/> 
</details>

<br>

## How is this repo organized?

There are three modules in WGT which are (1) a recognizer, (2) a visualizer, and (3) 5 generators, and we separate them into `recognizer/`, `visualizer/` and `recognizer/` three folders. For more details, please check the README in each folder. 

`data/` stores multiple sequence alignments in FASTA format which can be inputed to generators to create (1) tries, (2) De Bruijn graphs, and (3) reverse deterministic graphs. The folder also has all the graphs in DOT format that we used to benchmark the algorithms in the paper.

`benchmark/` stores the benchmark results. We also implemented Gibney & Thankachan's exponential algorithm [5] to the point of 3-bitarray enumaration and put the source code here.

<br>

## Citation

WGT is on *bioRxiv* now. If you use WGT in your published work, please cite


> <b>Kuan-Hao Chao*&dagger;, Pei-Wei Chen*, Sanjit A. Seshia, Ben Langmead&dagger;, "WGT: Tools and algorithms for recognizing, visualizing and generating Wheeler graphs" in [*bioRxiv*](https://doi.org/10.1101/2022.10.15.512390), 2022</b>

<br>

## Reference

[1] Gagie, T., Manzini, G., and Siren, J. (2017). Wheeler graphs: A framework for bwt-based data structures. Theoretical computer science, 698, 67–78.

[2]  Ferragina, P. and Manzini, G. (2000). Opportunistic data structures with applications. In Proceedings
41st annual symposium on foundations of computer science, pages 390–398. IEEE.

[3] Garrison, E., Siren, J., Novak, A. M., Hickey, G., Eizenga, J. M., Dawson, E. T., Jones, W., Garg, S., ´
Markello, C., Lin, M. F., Paten, B., and Durbin, R. (2018). Variation graph toolkit improves read mapping
by representing genetic variation in the reference. Nat Biotechnol, 36(9), 875–879.

[4]  Siren, J., Monlong, J., Chang, X., Novak, A. M., Eizenga, J. M., Markello, C., Sibbesen, J. A., Hickey, ´
G., Chang, P. C., Carroll, A., Gupta, N., Gabriel, S., Blackwell, T. W., Ratan, A., Taylor, K. D., Rich, S. S.,
Rotter, J. I., Haussler, D., Garrison, E., and Paten, B. (2021). Pangenomics enables genotyping of known
structural variants in 5202 diverse genomes. Science, 374(6574), abg8871.

[5] Gibney, D. and Thankachan, S. V. (2019). On the hardness and inapproximability of recognizing
wheeler graphs. arXiv preprint arXiv:1902.01960.
