#! /Users/chaokuan-hao/miniconda3/bin/python
import sys
from Bio import AlignIO
import node as n
import os

queue = []     #Initialize a queue

def main():
    fasta_file = sys.argv[1]
    k = int(sys.argv[2])
    print("Hello world")
    print("Input alignment fasta file: ", fasta_file)
    print("De Bruijn graph k = ", k)
    alignment = AlignIO.read(sys.argv[1], "fasta")
    print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    kmer_dic = {}
    kmer_set = set()

    for row_idx in range(0, seq_number, 1):
        # kmer_dic[row_idx] = set()
        print("row_idx: ", row_idx)
        row_seq = str(alignment[row_idx].seq)+"$"
        row_seq_parsed = row_seq.replace("-", "")
        # .rstrip("-") 
        print(row_seq_parsed)

        for i in range(0, len(row_seq_parsed)):
            node_kmer = row_seq_parsed[i:i+k]
            # kmer_dic[row_idx].add(node_kmer)
            kmer_set.add(node_kmer)

            print(i)
            print(node_kmer)
    print(kmer_dic)
    print(kmer_set)

    
    # Constructing all the nodes.
    node_idx = 0
    for node in kmer_set:
        new_node = n.node(node_idx, node, alignment_len)

        # if node == "$":
        #     source = new_node
        node_idx += 1
        kmer_dic[node] = new_node
    
    # Contructing the graph.
    for row_idx in range(0, seq_number, 1):
        # kmer_dic[row_idx] = set()
        print("row_idx: ", row_idx)
        row_seq = str(alignment[row_idx].seq)+"$"
        row_seq_parsed = row_seq.replace("-", "")
        # .rstrip("-") 
        print(row_seq_parsed)
        
        curr_node = ""
        prev_node = ""
        for i in range(0, len(row_seq_parsed)):
            print(i)
            node_kmer = row_seq_parsed[i:i+k]
            print("node_kmer: ", node_kmer)
            curr_node = kmer_dic[node_kmer]
            print("curr_node: ", curr_node)
            print("prev_node: ", prev_node)
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
    fw_name = "../../graph/DeBruijnGraph/DeBruijn_k_"+str(k) + "_" + os.path.basename(sys.argv[1])
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

# I need to number the node in this function
def bfs(visited, node): #function for BFS
    visited.append(node)
    queue.append(node)
    nodeID_counter = 0
    while queue:          # Creating loop to visit each node
        # print("len(queue): ", len(queue))
        m = queue.pop(0)
        # print("Dequeue") 
        m.set_nodeid(nodeID_counter)
        print("-"*m.nodecolid, m.nodelabel, "(", m.nodeid, ")") 
        nodeID_counter += 1
        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)
                # print("Appending into queue") 

def bfs_write(visited, node, fw): #function for BFS
    visited.append(node)
    queue.append(node)
    while queue:          # Creating loop to visit each node
        # print("len(queue): ", len(queue))
        m = queue.pop(0)
        # print("Dequeue") 
        # print("-"*m.nodecolid, m.nodelabel, "(", m.nodeid, ")") 
        for m_child in m.children:
            fw.write("\tS" + str(m.nodeid) + " -> S" + str(m_child.nodeid) + " [ label = "+m_child.nodelabel[0]+" ];\n")
            # fw.write("S" + str(m.nodeid) + " S" + str(m_child.nodeid) + " "+m_child.nodelabel+"\n")
            # print(m.nodeid, " -> ", m_child.nodeid)

        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)
                # print("Appending into queue") 

if __name__ == "__main__":
    main()