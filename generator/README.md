## De Bruijn graph generator

To generate a De Bruijn graph (in DOT format) from a FASTA file, run `DeBruijnGraph_generator.py` in the `./DeBruijnGraph_generator` directory.

```
usage: 

    DeBruijnGraph_generator.py [-h / --help] [-v/ --version] [-o / --ofile FILE] [-k / --kmer k-mer length] [-l / --seqLen sequence length] [-a / --alnNum alignment number] sequence FATA file
```


```
Optional arguments

    -h / --help    :    print the usage of "DeBruijnGraph_generator.py".
    -v / --version :    print the version of the program.
    -o / --ofile   :    the name of the output file. Default is "tmp.dot"
    -k / --kmer    :    the k-mer length. Default is "3".
    -l / --seqLen  :    Maximum sequence length for each entry in the FASTA file. Default is the full sequence length.
    -a / --alnNum  :    The number of alignments (sequences) used for creating the De Bruijn graph. Default is "3".
```
---

## Reverse deterministic graph generator

To generate a reverse deterministic graph (in DOT format) from a FASTA file, run `RevDetGraph_generator.py` in the `./RevDetGraph_generator` directory.

```
usage: 

    RevDetGraph.py [-h / --help] [-v/ --version] [-o / --ofile FILE] [-l / --seqLen sequence length] [-a / --alnNum alignment number] multilple sequence alignments (MSA) FASTA file```
```


```
Optional arguments

    -h / --help    :    print the usage of "DeBruijnGraph_generator.py".
    -v / --version :    print the version of the program.
    -o / --ofile   :    the name of the output file. Default is "tmp.dot"
    -l / --seqLen  :    Maximum sequence length for each entry in the FASTA file. Default is the full sequence length.
    -a / --alnNum  :    The number of alignments (sequences) used for creating the De Bruijn graph. Default is "3".
```

---

## Trie generator

To generate a trie (in DOT format) from a FASTA file, run `Trie_generator.py` in the `./Trie_generator` directory.

```
usage: 

    Trie_generator.py [-h / --help] [-v/ --version] [-o / --ofile FILE] [-l / --seqLen sequence length] [-a / --alnNum alignment number] multilple sequence alignments (MSA) FASTA file```
```

```
Optional arguments

    -h / --help    :    print the usage of "DeBruijnGraph_generator.py".
    -v / --version :    print the version of the program.
    -o / --ofile   :    the name of the output file. Default is "tmp.dot"
    -l / --seqLen  :    Maximum sequence length for each entry in the FASTA file. Default is the full sequence length.
    -a / --alnNum  :    The number of alignments (sequences) used for creating the De Bruijn graph. Default is "3".
```

---


## Random generators
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
