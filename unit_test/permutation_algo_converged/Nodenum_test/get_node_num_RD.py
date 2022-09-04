#! /Users/chaokuan-hao/miniconda3/bin/python
import sys
import networkx as nx
import os

# Return nodes as z3 Ints
def parse(inputfile):
    nodes = set()
    if inputfile[-4:] == '.dot':
        global G
        G = nx.DiGraph(nx.nx_pydot.read_dot(inputfile))
        nodes= set(node for node in list(G.nodes()) if node != '\\n')
    return nodes

def main():
    # in microseconds.
    inputfile_given = False
    inputfile = ''
    outputfile = ''
    verbose = False

    ##############################
    ## Parsing arguments
    ##############################
    inputfile = sys.argv[1]
    nodes = parse(inputfile)
    if len(nodes) > 1000:
        sys.exit(-1)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()