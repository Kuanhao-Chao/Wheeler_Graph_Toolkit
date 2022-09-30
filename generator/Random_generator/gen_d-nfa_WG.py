import sys
import random
import argparse

def sample_with_dupl_in_range(lb, ub, num):
    return [random.randint(lb, ub) for i in range(num)]

def find_closest_breakpoint(lst, b):
    for i in range(len(lst)):
        if lst[b] != lst[b+i]:
            return b+i
        if lst[b] != lst[b-i]:
            return b-i+1
        
# Find closest index to partition
def partition_in_nodes(lst, num_edges, num_labels):
    in_nodes_grps = []
    group_size = num_edges // num_labels
    last_b = 0

    for i in range(1, num_labels):
        b = find_closest_breakpoint(lst, group_size * i)
        in_nodes_grps.append(lst[last_b:b])
        last_b = b

    in_nodes_grps.append(lst[last_b:])
    return in_nodes_grps

# For each partition, generate random sorted nodes from where directed edges originate
# If grp_size < num_nodes, then each node will have at most an edge that is labeled l
def gen_out_nodes_grp(in_nodes_grps, num_nodes, dnfa=1):
    assert dnfa > 0
    out_nodes_grps = []
    # rge = list(range(1, num_nodes+1)) * dnfa
    rge = list(range(1, num_nodes+1)) 
    for in_grp in in_nodes_grps:
        sample_rge = rge + [random.randint(1, num_nodes)] * (dnfa-1) * 3
        grp_size = len(in_grp)
        out_grp = sorted(random.sample(sample_rge, min(grp_size, num_nodes)) \
                + sample_with_dupl_in_range(1, num_nodes, grp_size - num_nodes))
        out_nodes_grps.append(out_grp)
    return out_nodes_grps

# remove edges that violates dNFA rule
def maintain_dNFA(edges, d):
    new_edges = [edges[0]]
    node_cnt = 1
    for e in edges[1:]:
        if e[0] == new_edges[-1][0] and e[2] == new_edges[-1][2]:
            node_cnt += 1
            if node_cnt <= d:
                new_edges.append(e)
        else:
            node_cnt = 1
            new_edges.append(e)
    return new_edges
        

def get_cand_edges(edges):
    edges = list(set(edges))
    edges = sorted(edges, key=lambda tup: (tup[2], tup[0], tup[1]))
    cand_edges = []
    for e1, e2 in zip(edges[:-1], edges[1:]):
        if e1[2] == e2[2]:
            if e1[1] != e2[1] and e1[0] != e2[0]:
                cand_edges.append((e1[0], e2[1], e1[2]))
            elif e1[1] == e2[1] and e2[0] - e1[0] > 1:
                cand_edges.extend([(u, e2[1], e1[2]) for u in range(e1[0] + 1, e2[0])])
    return cand_edges


def get_names(num_nodes, shuffle=True):
    names = [f'S{i}' for i in range(1, num_nodes+1)]
    if shuffle:
        random.shuffle(names)
    return names

def create_graph(names, edges, filename):
    with open(filename, 'w') as f:
        f.write('strict digraph {\n')
        for e in edges:
            out_node_name = names[e[0] - 1]
            in_node_name = names[e[1] - 1]
            label = e[2]
            f.write(f'\t{out_node_name} -> {in_node_name} [ label = {label} ];\n')
        f.write('}')

def check_graph(edges, num_nodes, num_labels, d):
    label_out_edge_cnt = [[0] * (num_nodes + 1) for i in range(num_labels)]
    for e in edges:
        u = e[0]
        l = e[2]
        label_out_edge_cnt[l][u] += 1
        # if label_out_edge_cnt[l][u] > n:
        #     print(sorted(edges))
        #     return False
    maxx = 0
    for cnt_lst in label_out_edge_cnt:
        for cnt in cnt_lst:
            maxx = max(cnt, maxx)
    return maxx

def uniquify(edges):
    return list(set(edges))

def sort(edges):
    return sorted(edges, key=lambda tup: (tup[2], tup[0], tup[1]))

def main():
    parser = argparse.ArgumentParser(description='Generate Random De-Bruijn-ish Wheeler Graphs')
    parser.add_argument('-n', '--nodes', type=int, help='Number of nodes', required=True)
    parser.add_argument('-e', '--edges', type=int, help='Number of edges', required=True)
    parser.add_argument('-l', '--labels', type=int, help='Number of edge labels', required=True)
    parser.add_argument('-r', '--root_size', type=int, default=1, help='Number of nodes without incoming edges (default: 1)')
    parser.add_argument('-dnfa', '--dnfa', type=int, default=100000, help='d-NFA (default: 100000)')
    parser.add_argument('-s', '--shuffle', action='store_true', help='Shuffle node names (default: False)')
    parser.add_argument('-o', '--outfile', type=str, default='tmp.dot', help='Output DOT filename (default: ./tmp.dot)')
    args = parser.parse_args()

    num_nodes = args.nodes
    num_edges = args.edges
    num_labels = args.labels
    root_size = args.root_size
    d = args.dnfa
    outfile_name = args.outfile

    max_num_edge = num_nodes * num_labels + num_nodes - num_labels - root_size
    assert num_edges <= max_num_edge, f'Impossible to generate WG: max # of edges = {max_num_edge}'
    assert num_edges >= num_nodes - root_size, f'Impossible to generate WG: min # of edges = {num_nodes - root_size}'

    # Sorted random nodes that directed edges are pointing to
    # Make sure the only the root nodes has zero incoming edges
    rand_in_nodes = list(range(root_size + 1, num_nodes + 1)) + \
            sample_with_dupl_in_range(root_size + 1, num_nodes, num_edges - (num_nodes - root_size))
    rand_in_nodes = sorted(rand_in_nodes)

    in_nodes_grps = partition_in_nodes(rand_in_nodes, num_edges, num_labels)
    out_nodes_grps = gen_out_nodes_grp(in_nodes_grps, num_nodes, d)
    edges = []
    for l, (out_grp, in_grp) in enumerate(zip(out_nodes_grps, in_nodes_grps)):
        edges.extend([(out_n, in_n, l) for out_n, in_n in zip(out_grp, in_grp)])
    # edge_grps = [list(zip(out_grp, in_grp)) for out_grp, in_grp in zip(out_nodes_grps, in_nodes_grps)]
    # print(edges)
    print(len(edges))
    edges = uniquify(edges)
    print(len(edges))
    edges = sort(edges)

    edges = maintain_dNFA(edges, d)
    result_n = check_graph(edges, num_nodes, num_labels, d)
    print(f'Graph is {result_n}-NFA')
    cand_edges = get_cand_edges(edges)
    edges.extend(random.sample(cand_edges, min(num_edges - len(edges), len(cand_edges))))
    print(len(edges))

    node_names = get_names(num_nodes, shuffle=args.shuffle)

    edges = sort(edges)
    create_graph(node_names, edges, outfile_name)

    result_n = check_graph(edges, num_nodes, num_labels, d)
    print(f'Graph is {result_n}-NFA')
    assert result_n <= d, f'Graph is {result_n}-NFA (want {d}-NFA)'

if __name__ == '__main__':
    main()
