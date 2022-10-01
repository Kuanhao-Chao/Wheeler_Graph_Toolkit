import networkx as nx
import sys


def parse_input(inputfile):
    nodes = set()
    edges = []
    n_labels = -1
    assert inputfile[-4:] == '.dot'
    G = nx.DiGraph(nx.nx_pydot.read_dot(inputfile))
    nodes = list(G.nodes())
    nodes.remove('\\n')
    edges = [(u, v, int(attr['label'])) 
            for (u, v, attr) in G.edges(data=True)]
    n_labels = max([e[2] for e in edges]) + 1
    return nodes, edges, n_labels


def main(argv):
    for arg in argv:
        nodes, edges, n_labels = parse_input(arg)

        d = [ {u: 0 for u in nodes} for i in range(n_labels) ]
        n = 0
        uu = None
        for e in edges:
            u = e[0]
            l = e[2]
            d[l][u] += 1
            if d[l][u] > n:
                uu = u
                n = d[l][u]

        print(n, uu)


if __name__ == '__main__':
    main(sys.argv[1:])
