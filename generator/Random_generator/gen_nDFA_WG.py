import sys
import random
import argparse

def gen_in_node_range(num_nodes, num_labels, root_size):
    grp_size = (num_nodes - root_size) / num_labels
    start = root_size + 1
    ranges = []
    for i in range(num_labels-1):
        gap = int(grp_size * (1 + random.uniform(-0.05, 0.05))) - 1
        ranges.append((start, start + gap))
        start += gap + 1
    ranges.append((start, num_nodes))
    return ranges

def gen_n_nums_sum_to_M(n, M):
    nums = [0] * n
    for i in range(M):
        nums[random.randrange(n)] += 1
    assert sum(nums) == M
    return nums

def gen_complete_WG(in_node_range, num_nodes, root_size):
    out_node2edge = {i : [] for i in range(1, num_nodes + 1)}
    in_node2edge = {i : [] for i in range(root_size + 1, num_nodes + 1)}
    dst = root_size + 1
    for label, rge in enumerate(in_node_range):
        lb, ub = rge
        num_out_edges = gen_n_nums_sum_to_M(num_nodes, ub - lb)
        for i, num in enumerate(num_out_edges):
            src = i + 1
            edge = (src, dst, label)
            out_node2edge[src].append(edge)
            in_node2edge[dst].append(edge)
            for j in range(num):
                dst += 1
                edge = (src, dst, label)
                out_node2edge[src].append(edge)
                in_node2edge[dst].append(edge)
        dst += 1

    return out_node2edge, in_node2edge

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
        
def check_graph(edges, num_nodes, n):
    out_edge_count =[0] * (num_nodes + 1)
    for e in edges:
        u = e[0]
        out_edge_count[u] += 1
        if out_edge_count[u] > n:
            print(sorted(edges))
            return False
    return True
    
def rand_choice_and_remove(arr):
    assert len(arr) > 0
    i = random.randrange(len(arr))
    rand_elem = arr[i]
    last_elem = arr.pop()
    if i != len(arr):
        arr[i] = last_elem
    return rand_elem


def main():
    parser = argparse.ArgumentParser(description='Generate n-DFA Wheeler Graphs')
    parser.add_argument('-n', '--nodes', type=int, help='Number of nodes', required=True)
    parser.add_argument('-e', '--edges', type=int, help='Number of edges', required=True)
    parser.add_argument('-l', '--labels', type=int, help='Number of edge labels', required=True)
    parser.add_argument('-r', '--root_size', type=int, default=1, help='Number of nodes without incoming edges (default: 1)')
    parser.add_argument('-ndfa', '--ndfa', type=int, default=100000, help='n-DFA (default: 100000)')
    parser.add_argument('-s', '--shuffle', action='store_true', help='Shuffle node names (default: False)')
    parser.add_argument('-o', '--outfile', type=str, default='tmp.dot', help='Output DOT filename (default: ./tmp.dot)')

    args = parser.parse_args()

    num_nodes = args.nodes
    num_edges = args.edges
    num_labels = args.labels
    root_size = args.root_size
    n = args.ndfa
    outfile_name = args.outfile
    
    max_num_edge = min(n * num_nodes, num_nodes * num_labels + num_nodes - num_labels - root_size)
    assert num_edges <= max_num_edge, f'Impossible to generate WG: max # of edges = {max_num_edge}'
    assert num_edges >= num_nodes - root_size, f'Impossible to generate WG: min # of edges = {num_nodes - root_size}'

    in_node_range = gen_in_node_range(num_nodes, num_labels, root_size)

    out_node2edge, in_node2edge = gen_complete_WG(in_node_range, num_nodes, root_size)
    # assert len(all_edges) == max_num_edge

    out_edge_count =[0] * (num_nodes + 1)
    sampled_edges = set() 
    fail = True
    fail_cnt = 0

    # Make sure all non-root nodes has at least an incoming edge
    while fail:
        print(f'fail count: {fail_cnt}', end='\r')
        fail_cnt += 1
        fail = False
        sampled_edges.clear()
        for _, edge_vec in in_node2edge.items():
            rand_edge, u = None, None
            while True: 
                if len(edge_vec) == 0:
                    fail = True
                    break
                rand_edge = rand_choice_and_remove(edge_vec)
                u = rand_edge[0]
                if out_edge_count[u] < n: break
            if fail: break
            out_edge_count[u] += 1
            out_node2edge[u].remove(rand_edge)
            sampled_edges.add(rand_edge)
    print(f'fail count: {fail_cnt}')


    while len(sampled_edges) < num_edges:
        out_node = random.randrange(1, num_nodes + 1)
        if out_edge_count[out_node] >= n: continue
        edge_vec = out_node2edge[out_node]
        if len(edge_vec) == 0: continue
        rand_edge = rand_choice_and_remove(edge_vec)
        sampled_edges.add(rand_edge)
        out_edge_count[out_node] += 1

    assert check_graph(sampled_edges, num_nodes, n)

    node_names = get_names(num_nodes, shuffle=args.shuffle)

    # sampled_edges = sorted(sampled_edges)
    create_graph(node_names, sampled_edges, outfile_name)

if __name__ == '__main__':
    main()
