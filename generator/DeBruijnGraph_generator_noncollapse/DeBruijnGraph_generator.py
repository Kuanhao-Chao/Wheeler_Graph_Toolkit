from pickle import TRUE
import sys
from Bio import AlignIO
import node as n
import getopt
import os

queue = []     #Initialize a queue
USAGE = '''usage: DeBruijnGraph_generator.py [-h] [-v] [-o / --ofile FILE] [-k / --kmer k-mer length] [-l / --nodeLen sequence length] [-a / --alnNum alignment number] sequence FATA file'''

def main(argv):
    ##############################
    ## Parsing arguments
    ##############################
    # Default parameters:
    k = 3
    verbose = False
    outfile = "tmp.dot"
    nodeLen = -1
    alnNum = 3
    try:
        opts, args = getopt.getopt(argv,"hvo:k:l:a:",["ofile=", "kmer=", "nodeLen=", "alnNum="])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(USAGE)
            sys.exit()
        if opt in ("-v", "--version"):
            verbose = True
        elif opt in ("-o", "--ofile"):
            outfile = arg
        elif opt in ("-k", "--kmer"):
            k = int(arg)
        elif opt in ("-l", "--nodeLen"):
            nodeLen = int(arg)
        elif opt in ("-a", "--alnNum"):
            alnNum = int(arg)

    if len(args) == 0:
        print(USAGE)
        print("Please input one FASTA file")
        sys.exit(2)

    k = k -1
    fasta_file = args[0]
    # print("Input alignment fasta file: ", fasta_file)
    # print("Output dot file: ", outfile)
    # print("De Bruijn graph k = ", k)
    # print("Sequence Length l = ", nodeLen)
    # print("Alignment number a = ", alnNum)
    alignment = AlignIO.read(fasta_file, "fasta")
    alignment = alignment[:alnNum]
    # print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    node_idx = 0
    dollar_node = ""

    # Contructing the graph.
    kmer_set = set()
    kmer_dic = {}
    node_idx = 0

    dollar_node = n.node(node_idx, "$", alignment_len)
    node_idx += 1

    stop_lcl_seqLen = alignment_len

    for row_idx in range(0, seq_number, 1):
        lcl_node_count = 0
        # print(">> row_idx: ", row_idx)
        row_seq = str(alignment[row_idx].seq)

        # row_seq_removed = row_seq.replace("-", "")
        # print("row_seq_removed: ", row_seq_removed)
        # row_seq_parsed = row_seq.replace("-", "")
        curr_node = ""
        prev_node = ""
        lcl_seqLen = len(row_seq)
        ungapped_seqLen = len(row_seq.replace("-", ""))
        if nodeLen == -1 or nodeLen > ungapped_seqLen:
            nodeLen = ungapped_seqLen
        # else:
        #     nodeLen
        row_seq = row_seq[:lcl_seqLen]+"$"

        # print("lcl_seqLen: ", lcl_seqLen)

        
        non_gap_idx = 0
        non_gap_k_count = 0
        idx_ls = ()
        node_kmer = ""
        next_i = 0
        i_base = 0
        while i_base < lcl_seqLen and i_base < stop_lcl_seqLen and lcl_node_count < nodeLen:
        # for i in range(0, lcl_seqLen+1):
            # print("i_base          : ", i_base)
            # print("non_gap_idx     : ", non_gap_idx)
            # print("non_gap_k_count : ", non_gap_k_count)
            # print("row_seq[i_base+non_gap_idx]: ", row_seq[i_base+non_gap_idx])

            while non_gap_k_count <= k:

                if non_gap_k_count == 1 and row_seq[i_base+non_gap_idx] != "-":
                    next_i = i_base+non_gap_idx

                if non_gap_k_count == k:
                    break
                #     print("next_i: ", next_i)

                # print("non_gap_idx     : ", non_gap_idx)
                # print("non_gap_k_count : ", non_gap_k_count)

                if i_base+non_gap_idx >= lcl_seqLen:
                    break

                if row_seq[i_base+non_gap_idx] == "-":
                    non_gap_idx += 1
                else:
                    node_kmer = node_kmer + row_seq[i_base+non_gap_idx]
                    idx_ls += (i_base+non_gap_idx, )

                    # append(i+non_gap_idx)
                    non_gap_k_count += 1
                    non_gap_idx += 1
            
            lcl_node_count += 1
            non_gap_idx = 0
            i_base = next_i
            # print("i_base: ", i_base)

            # print("\tidx_ls      : ", idx_ls)
            # print("\tnode_kmer   : ", node_kmer)
            # idx_ls += (node_kmer, )

            if (idx_ls, node_kmer) in kmer_dic.keys():
                new_node = kmer_dic[(idx_ls, node_kmer)]
            else:
                new_node = n.node(node_idx, node_kmer, alignment_len)
            curr_node = new_node

            if prev_node != "":
                curr_node.add_child(prev_node)
                prev_node.add_parent(curr_node)

            prev_node = curr_node

            # print("Current i_base          : ", i_base)
            if i_base == lcl_seqLen or lcl_node_count == nodeLen:
                # print("Inside 'i_base == lcl_seqLen-1'")
                dollar_node.add_child(prev_node)
                prev_node.add_parent(dollar_node)
                if i_base < stop_lcl_seqLen:
                    stop_lcl_seqLen = i_base


            node_idx += 1
            kmer_dic[(idx_ls, node_kmer)] = new_node

            key = (idx_ls, node_kmer)
            kmer_set.add(key)
            # [key] = node_kmer
            idx_ls = ()
            node_kmer = ""
            non_gap_k_count = 0
        # print("kmer_set: ", kmer_set)
        # print("kmer_set: ", len(kmer_set))
        # print("kmer_dic: ", kmer_dic)
        # print("kmer_dic: ", len(kmer_dic))



    # node_idx = 0

    # kmer_dic = {}
    # for idx_ls, node in kmer_set:
    #     print("idx_ls : ", idx_ls)
    #     print("node   : ", node)

    #     new_node = n.node(node_idx, node, alignment_len)
    #     node_idx += 1
    #     kmer_dic[(idx_ls, node)] = new_node
    


            # # while non_gap_idx >= k:
            # #     if row_seq[i+non_gap_idx] != "-":



            # while row_seq[i+dest_idx] != "-":
                
            # node_kmer = row_seq[i:i+k]

#             if node_kmer == "$":
#                 if dollar_node == "":
#                     curr_node = n.node(node_idx, node_kmer, alignment_len)
#                     dollar_node = curr_node
#                     # print("curr_node: ", curr_node)
#                 else:
#                     curr_node = dollar_node
#             else:
#                 curr_node = n.node(node_idx, node_kmer, alignment_len)
#                 node_idx += 1
#             # print("node_kmer: ", node_kmer)
        

#             # Link current node to prev_node
#             if prev_node != "":
#                 curr_node.add_child(prev_node)
#                 prev_node.add_parent(curr_node)
#             prev_node = curr_node



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
    bfs(visited, dollar_node)
    visited = []
    bfs_write(visited, dollar_node, fw) #function for BFS
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
            fw.write("\tS" + str(m.nodeid) + " -> S" + str(m_child.nodeid) + " [ label = "+m_child.nodelabel[0]+" ];\n")

        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)

if __name__ == "__main__":
    main(sys.argv[1:])