from pickle import TRUE
import sys
from Bio import AlignIO
import node as n
import getopt
import os

queue = []     #Initialize a queue
USAGE = '''usage: DeBruijnGraph_generator.py [-h] [-v] [-o / --ofile FILE] [-k / --kmer kmer_int] sequence FATA file'''

def main(argv):
    ##############################
    ## Parsing arguments
    ##############################
    # Default parameters:
    k = 3
    verbose = False
    outputdir = "./"
    try:
        opts, args = getopt.getopt(argv,"hvo:k:",["ofile=", "kmer="])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(USAGE)
            sys.exit()
        elif opt == '-v':
            verbose = True
        elif opt in ("-o", "--ofile"):
            outputdir = arg
        elif opt in ("-k", "--kmer"):
            k = arg
    
    if not os.path.exists(outputdir):
        print("Output directory does not exist!")
        outputdir = "./"
        
    if len(args) == 0:
        print(USAGE)
        print("Please input one FASTA file")
        sys.exit(2)

    fasta_file = args[0]
    print("Input alignment fasta file: ", fasta_file)
    print("Output dot file: ", outputdir)
    print("De Bruijn graph k = ", k)
    alignment = AlignIO.read(fasta_file, "fasta")
    print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    kmer_dic = {}
    kmer_set = set()

    for row_idx in range(0, seq_number, 1):
        row_seq = str(alignment[row_idx].seq)+"$"
        row_seq_parsed = row_seq.replace("-", "")

        for i in range(0, len(row_seq_parsed)):
            node_kmer = row_seq_parsed[i:i+k]
            kmer_set.add(node_kmer)

    # Constructing all the nodes.
    node_idx = 0
    for node in kmer_set:
        new_node = n.node(node_idx, node, alignment_len)
        node_idx += 1
        kmer_dic[node] = new_node
    
    # Contructing the graph.
    for row_idx in range(0, seq_number, 1):
        row_seq = str(alignment[row_idx].seq)+"$"
        row_seq_parsed = row_seq.replace("-", "")
        curr_node = ""
        prev_node = ""
        for i in range(0, len(row_seq_parsed)):
            node_kmer = row_seq_parsed[i:i+k]
            curr_node = kmer_dic[node_kmer]
            # Link current node to prev_node
            if prev_node != "":
                curr_node.add_child(prev_node)
                prev_node.add_parent(curr_node)
            prev_node = curr_node



    ##############################
    ## Traversing the graph now. (& relabelling nodes)
    ##############################
    print("Depth first search traversing the graph now.")
    visited = [] # List for visited nodes.

    ##############################
    ## Writing out the graph into dot file
    ##############################
    relative_filename = os.path.relpath(fasta_file, "../../multiseq_alignment/")
    dir_name = os.path.dirname(relative_filename)
    file_basename = os.path.basename(relative_filename)
    new_dir_name = os.path.join(outputdir, dir_name)
    os.makedirs(new_dir_name, exist_ok = True)
    fw_name = os.path.join(new_dir_name, "DeBruijn_k_"+str(k) + "_" + file_basename)
    fw_name = fw_name.replace('.fasta', '.dot')
    print("fw_name: ", fw_name)
    try:    
        os.remove(fw_name)
    except OSError:
        pass
    fw = open(fw_name, "a")
    fw.write("strict digraph  {\n")
    bfs(visited, kmer_dic["$"])
    visited = []
    bfs_write(visited, kmer_dic["$"], fw) #function for BFS
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
        print("-"*m.nodecolid, m.nodelabel, "(", m.nodeid, ")") 
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
            fw.write("\tS" + str(m.nodeid) + " -> S" + str(m_child.nodeid) + " [ label = "+m_child.nodelabel[0]+" ];\n")

        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)

if __name__ == "__main__":
    main(sys.argv[1:])