from z3 import Int, Solver, And, Implies, Distinct
import sys
import networkx as nx

# Return nodes as z3 Ints
def parse(filename):
    nodes = set()
    edges = []
    has_incoming_edge = set()
    if filename[-4:] == '.dot':
        G = nx.DiGraph(nx.nx_pydot.read_dot(filename))
        nodes= set(Int(node) for node in list(G.nodes()) if node != '\\n')
        edges = [(Int(u), Int(v), ord(attr['label'])) 
                for (u, v, attr) in G.edges(data=True)]
        for (u, v, l) in edges:
            has_incoming_edge.update([v])
    else:
        with open(filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                u, v, w = line.split()
                u = Int(u)
                v = Int(v)
                w = int(w)
                nodes.update([u, v])
                edges.append((u,v,w))
    return nodes, edges, has_incoming_edge

filename = sys.argv[1]
nodes, edges, has_incoming_edge = parse(filename)
no_incoming_edge = nodes.difference(has_incoming_edge)

print(f'# nodes: {len(nodes)}')
print(nodes)
print(f'# edges: {len(edges)}')
print(edges)
print(f'no incoming edge: {no_incoming_edge}')

s = Solver()
# Range for nodes
for u in nodes:
    s.add(And(u > 0, u < len(nodes)+1))
# Enforce all different constraint
s.add(Distinct(*nodes))

# Nodes without incoming edge should be in front
for u in no_incoming_edge:
    s.add(u <= len(no_incoming_edge))

# Wheeler graph constraints
for i in range(len(edges)):
    for j in range(i+1, len(edges)):
        ui, vi, wi = edges[i]
        uj, vj, wj = edges[j]

        if wi == wj: s.add(Implies(ui < uj, vi <= vj))
        elif wi < wj: s.add(vi < vj)
        elif wi > wj: s.add(vi > vj)
        else: raise RuntimeError

        # Constraint 1
        # s.add(Implies(wi < wj, vi < vj))
        # Constraint 2
        # s.add(Implies(
        #     And(wi == wj, ui < uj),
        #     vi <= vj))

with open('g.smt2', 'w') as f:
    f.write(s.to_smt2())

sat = s.check()

print(sat)
if sat: print(s.model())
