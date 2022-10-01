import sys

'''
Assumptions:
    1. nodes start with S and followed by numbers, and labels are ints
    2. file start with 1st line "strict digraph {" and ends with last line "}",
       with all other lines of the form "S1 -> S2 [ label = 0 ]"
'''
def parse_file(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()[1:-1]
    lines = [line.split() for line in lines]
    edges = [(int(line[0][1:]), int(line[2][1:]), int(line[-2])) for line in lines]
    return sort(edges)

def sort(edges):
    return sorted(edges, key=lambda tup: (tup[2], tup[0], tup[1]))

def check_WG(filename):
    print(f'Checking {filename}...')
    edges = parse_file(filename)
    max_node = max([e[0] for e in edges] + [e[1] for e in edges])
    has_in = [0] * (max_node + 1)
    # fw = open("tmp.dot", "a")
    # fw.write("strict digraph {\n")
    # for e in edges:
    #     fw.write("\t"+str(e[0])+" -> " + str(e[1]) + " [ label = " + str(e[2]) + " ];\n")
    # fw.write("}")

    for e1 in edges:
        for e2 in edges:
            if e1 == e2: continue
            e_pair_str = f'{e1}, {e2}'
            u1, v1, l1 = e1
            u2, v2, l2 = e2
            has_in[v1] = 1
            has_in[v2] = 1
            if l1 < l2:
                assert v1 < v2, e_pair_str
            elif l2 < l1:
                assert v2 < v1, e_pair_str
            else:
                if u1 < u2:
                    assert v1 <= v2, e_pair_str
                elif u2 < u1:
                    assert v2 <= v1, e_pair_str

    for i in range(2, len(has_in)):
        if has_in[i] == 0:
            assert False, f'{i} does not have incoming edge'

    print(f'{filename} pass!')
    


def main(argv):
    for arg in argv:
        check_WG(arg)

if __name__ == '__main__':
    main(sys.argv[1:])
