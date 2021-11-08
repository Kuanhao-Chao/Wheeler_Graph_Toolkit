import sys
import networkx as nx
from networkx.drawing.nx_pydot import read_dot
import os

# class node:
#     def __init__(self, id):
#         self.id = id
#         self.indeg = 0
#         self.outdeg = 0
#         # self.parents = None
#         # self.children = None

# class edge:
#     def __init__(self, label, tail=node(None), head=node(None)):
#         self.label = label
#         self.tail = tail
#         self.head = head

def get_edge_label(graph):
    all_edge_labels = []
    all_edge_dic = {}
    for u,v,e in graph.edges(data=True):
        if e['label'] not in all_edge_labels:
            all_edge_labels.append(e['label'])        
            all_edge_dic[e['label']] = [(u,v)]
        else: 
            all_edge_dic[e['label']].append((u,v))
    print (all_edge_dic)
    print (all_edge_labels)
    return all_edge_dic, all_edge_labels

def get_in_deg_0_node(graph): 
    in_deg_0_node_ls = []
    for n, in_deg in graph.in_degree:
        if in_deg == 0:
            in_deg_0_node_ls.append(n)
    print(in_deg_0_node_ls)


def main():
    base_dir = "../graph/"
    g_file = sys.argv[1]
    g_file = os.path.join(base_dir, g_file)
    g = nx.DiGraph(read_dot(g_file))
    # nx.draw(g, with_labels = True, arrows=True)
    in_deg_0_node_ls = get_in_deg_0_node(g)

    if len(in_deg_0_node_ls) > 1:
        print("Not exist")

    all_edge_dic, all_edge_labels = get_edge_label(g)



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
