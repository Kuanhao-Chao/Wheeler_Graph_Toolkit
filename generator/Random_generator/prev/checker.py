import networkx as nx
import matplotlib.pyplot as plt
import graphviz
from graphviz import Source
import sys

def checker(filename):
    G = nx.drawing.nx_pydot.read_dot(filename)

    if G.has_node("\\n"):
        G.remove_node("\\n")

    indegree = [] 
    for node, ind in G.in_degree(G.nodes()):
        indegree.append((int(node), ind))

    # indegree = new_list

    indegree = sorted(indegree)
    # print(indegree)

    flag = False
    cond1 = True
    for node, indeg in indegree:
        if flag and indeg == 0:
            cond1 = False
        if indeg != 0:
            flag = True

    edges = list(G.edges(data=True))
    d = {}
    for u,v,edge in edges:
        label = edge['label']
        if label in d:
            l = d.get(label)
            l.append((int(u),int(v)))
        else:
            d[label] = [(int(u),int(v))]

    prev_max = -1
    cond2 = True
    for k,v in sorted(d.items()):
        cur_max = 0
        for (out,ind) in v:
            if (int(ind) <= int(prev_max)): #changed to cast to int
                cond2 = False
            if int(ind) > int(cur_max): #changed too
                cur_max = ind
        prev_max = cur_max

    cond3 = True

    # print(d.items())


    for k,v in d.items():
        max = 0
        # print(sorted(v))
        for out,ind in sorted(v):
            if int(ind) < int(max):
                cond3 = False
            if int(ind) > int(max): #changed to cast to int
                max = ind
    return cond1, cond2, cond3

if __name__ == "__main__":
    input_file = open(sys.argv[1], 'r')
    cond1, cond2, cond3 = checker(input_file)

    fail_message = "Inputted graph is not a Wheeler Graph - the following condition(s) not met:"
    condition1 = "\n   * 0-indegree nodes come before others"
    condition2 = "\n   * a ≺ a′⟹  v < v′"
    condition3 = "\n   * (a = a′) ∧ (u < u′) ⟹  v ≤ v′"

    if cond1 and cond2 and cond3:
        print("Inputed graph is a Wheeler Graph")

    elif not cond1 and cond2 and cond3:
        print(fail_message + condition1)
    elif cond1 and not cond2 and cond3: 
        print(fail_message + condition2)
    elif cond1 and cond2 and not cond3: 
        print(fail_message + condition3)

    elif not cond1 and not cond2 and cond3: 
        print(fail_message + condition1 + condition2)
    elif cond1 and not cond2 and not cond3: 
        print(fail_message + condition2 + condition3)
    elif not cond1 and cond2 and not cond3: 
        print(fail_message + condition1 + condition3)

    elif not cond1 and not cond2 and not cond3: 
        print(fail_message + condition1 + condition2 + condition3)

