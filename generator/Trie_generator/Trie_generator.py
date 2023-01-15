from pickle import TRUE
import sys
from Bio import AlignIO
import node as n
import getopt
import os

queue = []     #Initialize a queue
USAGE = '''usage: trie_generator.py [-h / --help] [-v/ --version] [-o / --ofile FILE] [-l / --seqLen sequence length] [-a / --alnNum alignment number] sequence FATA file'''

alignment_len = -1
node_idx = 0

def main(argv):
    ##############################
    ## Parsing arguments
    ##############################
    # Default parameters:
    verbose = False
    outfile = "tmp.dot"
    seqLen = -1
    alnNum = 3
    try:
        opts, args = getopt.getopt(argv, "hvo:l:a:",["ofile=", "seqLen=", "alnNum="])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)
    for opt, arg in opts:
        print(opt)
        if opt in ("-h", "--help"):
            print(USAGE)
            sys.exit()
        if opt in ("-v", "--version"):
            verbose = True
        elif opt in ("-o", "--ofile"):
            outfile = arg
        elif opt in ("-l", "--seqLen"):
            seqLen = int(arg)
        elif opt in ("-a", "--alnNum"):
            alnNum = int(arg)

    if len(args) == 0:
        print(USAGE)
        print("Please input one FASTA file")
        sys.exit(2)

    print("args: ", args)
    fasta_file = args[0]
    print("Input alignment fasta file: ", fasta_file)
    print("Output dot file: ", outfile)
    print("Sequence Length l = ", seqLen)
    print("Alignment number a = ", alnNum)
    alignment = AlignIO.read(fasta_file, "fasta")
    alignment = alignment[:alnNum]
    print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    row_seq_parsed_ls = []
    max_len = 0



    level_dict = {}
    root = n.node(node_idx, "*", alignment_len)

    for row_idx in range(0, seq_number, 1):
        row_seq = str(alignment[row_idx].seq)
        row_seq_parsed = row_seq.replace("-", "")
        if seqLen == -1 or seqLen > len(row_seq_parsed):
            seqLen = len(row_seq_parsed)
        row_seq_parsed = row_seq_parsed[:seqLen]+"$"
        print(row_seq_parsed)
        insert(root, row_seq_parsed)
        
    # print("root: ", root)
    # print_trie('', root, 0)

    ##############################
    ## Traversing the graph now. (& relabelling nodes)
    ##############################
    print("Depth first search traversing the graph now.")
    visited = [] # List for visited nodes.

    ##############################
    ## Writing out the graph into dot file
    ##############################
    # relative_filename = os.path.relpath(fasta_file, "../../multiseq_alignment/")
    # dir_name = os.path.dirname(relative_filename)
    # file_basename = os.path.basename(relative_filename)
    # new_dir_name = os.path.join(outfile, dir_name)
    # os.makedirs(new_dir_name, exist_ok = True)
    # fw_name = os.path.join(new_dir_name, "DeBruijn_k_"+str(k) + "_" + file_basename)
    # fw_name = fw_name.replace('.fasta', '.dot')
    print("outfile: ", outfile)
    try:    
        os.remove(outfile)
    except OSError:
        pass
    fw = open(outfile, "a")
    fw.write("strict digraph  {\n")
    bfs(visited, root)
    visited = []
    bfs_write(visited, root, fw) #function for BFS
    fw.write("}\n")
    fw.close()

# Number the node in this function
def bfs(visited, node):
    visited.append(node)
    queue.append(node)
    nodeID_counter = 0
    while queue:          # Creating loop to visit each node
        m = queue.pop(0)
        m.set_nodeid(nodeID_counter)
        # print("-"*m.nodecolid, m.nodelabel, "(", m.nodeid, ")") 
        nodeID_counter += 1
        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)

def bfs_write(visited, node, fw):
    visited.append(node)
    queue.append(node)
    while queue:          # Creating loop to visit each node
        m = queue.pop(0)
        for m_child in m.children:
            if m_child.nodelabel != "$":
                fw.write("\tS" + str(m.nodeid) + " -> S" + str(m_child.nodeid) + " [ label = "+m_child.nodelabel+" ];\n")

        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)


def print_trie(prefix, trie, depth):
    depth += 1
    if depth <= 1:
        print('\n>> Printing Trie...')
    else:
        # print("trie.nodelabel: ", trie.nodelabel)
        prefix += trie.nodelabel
        print(depth*' ',prefix[depth-2])

    if len(trie.children) == 0:
        return

    for node in trie.children:
        print_trie(prefix, node, depth)

    return None

def insert(root, seq):
    print(">> inserting root")
    node = root
    for s in seq:
        # print("s: ", s)
        # if len(node.children) > 0:
        for child in node.children:
            if s == child.nodelabel:
                node = child
                break
        else:
            new_node = n.node(node_idx, s, alignment_len)
            # print("new_node: ", new_node)
            node.children.append(new_node)
            node = new_node

if __name__ == "__main__":
    main(sys.argv[1:])