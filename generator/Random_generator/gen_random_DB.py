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
def gen_out_nodes_grp(in_nodes_grps, num_nodes):
    out_nodes_grps = []
    for in_grp in in_nodes_grps:
        grp_size = len(in_grp)
        out_grp = sorted(random.sample(range(1, num_nodes+1), min(grp_size, num_nodes)) \
                + sample_with_dupl_in_range(1, num_nodes, grp_size - num_nodes))
        out_nodes_grps.append(out_grp)
    return out_nodes_grps

def get_names(num_nodes, shuffle=True):
    names = [f'S{i}' for i in range(1, num_nodes+1)]
    if shuffle:
        random.shuffle(names)
    return names

def create_graph(names, edge_grps, filename):
    with open(filename, 'w') as f:
        f.write('strict digraph {\n')
        for i, edge_grp in enumerate(edge_grps):
            for edge in edge_grp:
                out_node_name = names[edge[0] - 1]
                in_node_name = names[edge[1] - 1]
                f.write(f'\t{out_node_name} -> {in_node_name} [ label = {i} ];\n')
        f.write('}')


def main():
    parser = argparse.ArgumentParser(description='Generate Random De-Bruijn-ish Wheeler Graphs')
    parser.add_argument('-n', '--nodes', type=int, help='Number of nodes', required=True)
    parser.add_argument('-e', '--edges', type=int, help='Number of edges', required=True)
    parser.add_argument('-l', '--labels', type=int, help='Number of edge labels', required=True)
    parser.add_argument('-r', '--root_size', type=int, default=1, help='Number of nodes without incoming edges (default: 1)')
    parser.add_argument('-s', '--shuffle', action='store_true', help='Shuffle node names (default: False)')
    parser.add_argument('-o', '--outfile', type=str, default='tmp.dot', help='Output DOT filename (default: ./tmp.dot)')
    args = parser.parse_args()

    num_nodes = args.nodes
    num_edges = args.edges
    num_labels = args.labels
    root_size = args.root_size
    outfile_name = args.outfile

    # Sorted random nodes that directed edges are pointing to
    # Make sure the only the root nodes has zero incoming edges
    rand_in_nodes = list(range(root_size + 1, num_nodes + 1)) + \
            sample_with_dupl_in_range(root_size + 1, num_nodes, num_edges - (num_nodes - root_size))
    rand_in_nodes = sorted(rand_in_nodes)

    in_nodes_grps = partition_in_nodes(rand_in_nodes, num_edges, num_labels)
    out_nodes_grps = gen_out_nodes_grp(in_nodes_grps, num_nodes)
    edge_grps = [list(zip(out_grp, in_grp)) for out_grp, in_grp in zip(out_nodes_grps, in_nodes_grps)]

    node_names = get_names(num_nodes, shuffle=args.shuffle)

    create_graph(node_names, edge_grps, outfile_name)

if __name__ == '__main__':
    main()
