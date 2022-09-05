#! /Users/chaokuan-hao/miniconda3/bin/python
from z3 import Int, Solver, And, Implies, Distinct, sat, unsat, SolverFor
import sys
import networkx as nx
import os
import getopt
from time import process_time_ns

# Return nodes as z3 Ints
def parse_input(inputfile):
    nodes = set()
    edges = []
    has_incoming_edge = set()
    if inputfile[-4:] == '.dot':
        global G
        G = nx.DiGraph(nx.nx_pydot.read_dot(inputfile))
        nodes= set(Int(node) for node in list(G.nodes()) if node != '\\n')
        edges = [(Int(u), Int(v), ord(attr['label'])) 
                for (u, v, attr) in G.edges(data=True)]
        for (u, v, l) in edges:
            has_incoming_edge.update([v])
    else:
        with open(inputfile, 'r') as f:
            lines = f.readlines()
            for line in lines:
                u, v, w = line.split()
                u = Int(u)
                v = Int(v)
                w = int(w)
                nodes.update([u, v])
                edges.append((u,v,w))
    return nodes, edges, has_incoming_edge

def parse_group(groupfile):
    if groupfile is None:
        return None
    grp_dict = {}
    with open(groupfile, 'r') as f:
        lines = f.readlines()
        for line in lines:
            u, lb, ub = line.split()
            rge = (int(lb)-1, int(ub))
            if rge not in grp_dict:
                grp_dict[rge] = []
            grp_dict[rge].append(Int(u))
    group_info = [(us, rge) for rge, us in grp_dict.items()]
    # print(group_info)
    # assert False
    return group_info


def main(argv):
    # in microseconds.
    time_start = process_time_ns() / (10 ** 3)
    inputfile_given = False
    inputfile = None
    outputfile = None
    groupfile = None
    verbose = False

    ##############################
    ## Parsing arguments
    ##############################
    try:
        opts, args = getopt.getopt(argv,"hvi:o:g:",["ifile=","ofile=","gfile="])
    except getopt.GetoptError:
        print('isWheeler.py -i <inputfile> [-o <outputfile> | -g <groupfile> | -v]')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('isWheeler.py -i <inputfile> [-o <outputfile> | -g <groupfile> | -v]')
            # print('isWheeler.py -i <inputfile> -o <outputfile> -v')
            sys.exit()
        elif opt == '-v':
            verbose = True
        elif opt in ("-i", "--ifile"):
            inputfile = arg
            inputfile_given = True
        elif opt in ("-o", "--ofile"):
            outputfile = arg
        elif opt in ("-g", "--gfile"):
            groupfile = arg
    if not inputfile_given:
        print("-i / --ifile was not given")
        print('isWheeler.py -i <inputfile> [-o <outputfile> | -g <groupfile> | -v]')
        # print('isWheeler.py -i <inputfile> -o <outputfile> -v')
        sys.exit(2)

    nodes, edges, has_incoming_edge = parse_input(inputfile)
    group_info = parse_group(groupfile)
    # Default: all no nodes are grouped (all nodes are in one group)
    if group_info is None:
        group_info = [(nodes, (0, len(nodes)))]
    no_incoming_edge = nodes.difference(has_incoming_edge)

    # print(f'# nodes: {len(nodes)}')
    # print(nodes)
    # print(f'# edges: {len(edges)}')
    # print(edges)
    # print(f'no incoming edge: {no_incoming_edge}')

    ##############################
    ## Adding Wheeler graph constraints
    ##############################
    # s = Solver()
    s = SolverFor('QF_IDL')
    # if group_info is None:
    #     # 1. Range for nodes
    #     for u in nodes:
    #         s.add(And(u > 0, u <= len(nodes)))
    #     # 2. Enforce all different constraint
    #     s.add(Distinct(*nodes))
    # else:
    for us, (lb, ub) in group_info:
        for u in us:
            s.add(And(u > lb, u <= ub))
        s.add(Distinct(*us))

    # 3. Nodes without incoming edge should be in front
    for u in no_incoming_edge:
        s.add(u <= len(no_incoming_edge))

    # 4. 2 monotonicity properties
    for i in range(len(edges)):
        # for j in range(len(edges)):
        for j in range(i+1, len(edges)):
            if i != j:
                ui, vi, wi = edges[i]
                uj, vj, wj = edges[j]

                ##############################
                ## Approach 1:
                ##############################
                if wi == wj: 
                    s.add(Implies(ui < uj, vi <= vj))
                    s.add(Implies(ui > uj, vi >= vj))
                # NOTE: Comment out lines below????
                # elif wi < wj: s.add(vi < vj)
                # elif wi > wj: s.add(vi > vj)
                # else: raise RuntimeError

                ##############################
                ## Approach 2:
                ##############################
                # # Constraint 1
                # s.add(Implies(wi < wj, vi < vj))
                # # Constraint 2
                # s.add(Implies(
                #     And(wi == wj, ui < uj),
                #     vi <= vj))
    if verbose:
        with open('g.smt2', 'w') as f:
            f.write(s.to_smt2())

    sat = s.check()

    # Print out the node ordering if the given graph is wheeler..

    mapping = {}
    print(sat, end = "\t")

    if sat.r == 1: 
        model = s.model()
        if verbose:
            print(model)
        if outputfile is not None:
            for node in model:
                node_orignal_str = str(node)
                node_new_str = model[node]
                mapping[node_orignal_str] = node_new_str

            ##############################
            ## Relabel nodes & write out the new graph. 
            ##  Sorting order:
            ##    1. first node -> 2. second node -> 3. edge label
            ##############################    
            G_new = nx.relabel_nodes(G, mapping)
            edges_new = sorted(G_new.edges(data=True), key=lambda t: int(str(t[0])))
            edges_new = sorted(edges_new, key=lambda t: int(str(t[1])))
            edges_new = sorted(edges_new, key=lambda t: t[2].get('label'))

            # print(edges_new)
            if not os.path.isfile(outputfile):
                outputfile = "./tmp_" + os.path.basename(inputfile)
            try:    
                os.remove(outputfile)
            except OSError:
                pass
            fw = open(outputfile, "a")
            fw.write("strict digraph  {\n")

            for edge_new in edges_new:
                fw.write("\t" + str(edge_new[0]) + " -> " + str(edge_new[1]) + " [ label = "+edge_new[2].get('label')+" ];\n")
            fw.write("}\n")
            fw.close()

    # Only report if the given graph is wheeler.
    time_end = process_time_ns() / (10 ** 3)

    print(len(nodes), end="\t")
    print(time_end - time_start, end="\t")
    print(inputfile)
    if sat.r == 1:
        sys.exit(1)
    elif sat.r == -1: 
        sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
