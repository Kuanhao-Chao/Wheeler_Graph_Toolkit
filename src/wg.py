import sys
import networkx as nx
from networkx.drawing.nx_pydot import read_dot
import os

class node:
    def __init__(self, id):
        self.id = id
        self.indeg = 0
        self.outdeg = 0
        # self.parents = None
        # self.children = None

class edge:
    def __init__(self, label, tail=node(None), head=node(None)):
        self.label = label
        self.tail = tail
        self.head = head

def main():
    # base_dir = "/home/kh.chao/Documents/Projects/Wheeler_Graph/graph"
    # g_file = sys.argv[1]
    # g_file = os.path.join(base_dir, g_file)
    # g = nx.read_dot(g_file)
    # print("g: ", g)
    
    read_dot("/home/kh.chao/Documents/Projects/Wheeler_Graph/graph/g1.dot")



    G = nx.Graph()
    G.add_edge('A', 'B', weight=4)
    G.add_edge('B', 'D', weight=2)
    G.add_edge('A', 'C', weight=3)
    G.add_edge('C', 'D', weight=4)
    print(nx.shortest_path(G, 'A', 'D', weight='weight'))


    # with open(g_file, 'r') as fr:
    #     line = fr.readline()
    #     while line:
    #         print(line)
    #         line = fr.readline()
    # e1 = edge("a", node(1), node(2))
    # e2 = edge("a", node(1), node(3))
    # e3 = edge("a", node(2), node(3))
    # e4 = edge("a", node(5), node(4))
    # e5 = edge("a", node(8), node(4))

    # e6 = edge("b", node(1), node(5))
    # e7 = edge("b", node(3), node(5))
    # e8 = edge("b", node(6), node(6))
    # e9 = edge("b", node(7), node(6))

    # e10 = edge("c", node(2), node(7))
    # e11 = edge("c", node(5), node(7))
    # e12 = edge("c", node(6), node(8))
    # e13 = edge("c", node(7), node(8))

    # e1 = edge("a", node(1), node(2))
    # e2 = edge("a", node(1), node(3))
    # e3 = edge("a", node(2), node(3))
    # e4 = edge("a", node(5), node(4))
    # e5 = edge("a", node(8), node(4))

    # e6 = edge("b", node(1), node(5))
    # e7 = edge("b", node(3), node(5))
    # e8 = edge("b", node(6), node(6))
    # e9 = edge("b", node(7), node(6))

    # e10 = edge("c", node(2), node(7))
    # e11 = edge("c", node(5), node(7))
    # e12 = edge("c", node(6), node(8))
    # e13 = edge("c", node(7), node(8))


    # e1 = edge("a", 1, 2)
    # e2 = edge("a", 1, 3)
    # e3 = edge("a", 2, 3)
    # e4 = edge("a", 5, 4)
    # e5 = edge("a", 8, 4)
    # e6 = edge("b", 1, 5)
    # e7 = edge("b", 3, 5)
    # e8 = edge("b", 6, 6)
    # e9 = edge("b", 7, 6)
    # e10 = edge("c", 2, 7)
    # e11 = edge("c", 5, 7)
    # e12 = edge("c", 6, 8)
    # e13 = edge("c", 7, 8)

    # print(e1)
    # print(e1)

if __name__ == "__main__":
    main()
