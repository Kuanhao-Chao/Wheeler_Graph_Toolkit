import sys
import random
import argparse

def gen_in_node_range(num_nodes, num_labels, root_size):
    grp_size = (num_nodes - root_size) / num_labels
    start = root_size + 1
    ranges = []
    for i in range(num_labels-1):
        # gap = int(grp_size * (1 + random.uniform(-0.05, 0.05))) - 1
        gap = int(grp_size) - 1
        ranges.append((start, start + gap))
        start += gap + 1
    ranges.append((start, num_nodes))
    return ranges

def split_int(total, group):
    arr = [total // group for i in range(group)]
    arr[-1] += total - sum(arr)
    return arr

def gen_down(up, start, end, num_node):
    down = [start]
    split_indices = []
    prev = up[0]

    for i, elem in enumerate(up[1:]):
        if elem != prev:
            down.append(down[-1])
            split_indices.append(i + 1)
        else: # elem == prev
            down.append(down[-1] + 1)
        prev = elem

    assert down[-1] <= end

    sample_size = end - down[-1]
    sample_index = random.sample(split_indices, sample_size)
    sample_index = sorted(sample_index)

    increm = 0
    it = 0
    for i in range(len(down)):
        if it < len(sample_index) and i == sample_index[it]:
            increm += 1
            it += 1
        down[i] += increm

    assert down[-1] == end

    return down

def sum_to(n):
    return sum(list(range(n+1)))

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
        
def uniquify(edges):
    return list(set(edges))

def sort(edges):
    return sorted(edges, key=lambda tup: (tup[2], tup[0], tup[1]))


def main():
    parser = argparse.ArgumentParser(description='Generate Random d-NFA Wheeler Graphs')
    parser.add_argument('-n', '--nodes', type=int, help='Number of nodes', required=True)
    parser.add_argument('-e', '--edges', type=int, help='Number of edges', required=True)
    parser.add_argument('-l', '--labels', type=int, help='Number of edge labels', required=True)
    parser.add_argument('-r', '--root_size', type=int, default=1, help='Number of nodes without incoming edges (default: 1)')
    parser.add_argument('-d', '--dnfa', type=int, default=100000, help='d-NFA (default: 100000)')
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
    assert d is None or d > 0

    nodes = list(range(1, num_nodes+1))
    edges = []

    in_node_ranges = gen_in_node_range(num_nodes, num_labels, root_size)

    num_edges_per_label = split_int(num_edges, num_labels)

    for l, (in_node_range, num_edge) in enumerate(zip(in_node_ranges, num_edges_per_label)):
        start, end = in_node_range 
        num_node = end - start + 1
        assert num_edge >= num_node

        num_node_per_d = [-1] * d

        bound1 = num_edge / sum_to(d)
        bound2 = (num_node - 1) / sum_to(d - 1) if d > 1 else 1

        if bound1 < bound2:
            num_node_per_d = [int(bound1)] * d
            num_node_per_d[-1] += num_edge - int(bound1) * sum_to(d)
        elif bound2 < bound1:
            num_node_per_d = [int(bound2)] * (d - 1)
            num_node_per_d.append( num_edge - int(bound2) * (sum_to(d) - 1) )
        assert bound1 != bound2

        num_out_nodes = sum(num_node_per_d)
        assert num_out_nodes <= num_nodes

        # Generate up
        up = []
        a1 = random.sample(nodes, num_out_nodes)
        
        for i, num in enumerate(num_node_per_d):
            a2 = random.sample(a1, num)
            up += a2 * (d - i)
            for elem in a2:
                a1.remove(elem)
        
        up = sorted(up)
        down = gen_down(up, start, end, num_node)

        edges += [(a, b, l) for a, b in zip(up, down)]

    edges = uniquify(edges)
    edges = sort(edges)

    node_names = get_names(num_nodes, shuffle=args.shuffle)

    create_graph(node_names, edges, outfile_name)

if __name__ == '__main__':
    main()
