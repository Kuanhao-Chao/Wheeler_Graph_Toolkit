#! /Users/chaokuan-hao/miniconda3/bin/python
import sys
from Bio import AlignIO
import node as n
import os

queue = []     #Initialize a queue

def main():
    fasta_file = sys.argv[1]
    print("Hello world")
    print("Input alignment fasta file: ", fasta_file)
    alignment = AlignIO.read(sys.argv[1], "fasta")
    print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    print("alignment_len: ", alignment_len)
    print("seq_number: ", seq_number)

    # Step 1: Build WG from the first sequence.
    node_idx = 0
    seq_idx = 0

    node_dict = {}
    prev_node = None
    curr_node = None
    for i in alignment[0]:
        if (i is not "-"):
            curr_node = n.node("S_0_"+str(seq_idx), node_idx, i, seq_idx)
            node_dict[node_idx] = curr_node
            if prev_node is not None:
                curr_node.add_parent(prev_node)
                prev_node.add_child(curr_node)
            prev_node = curr_node
            node_idx += 1
            print(i)
        seq_idx += 1

    curr_node = n.node("S_$", -1, "$", seq_idx+1)
    curr_node.add_parent(prev_node)
    prev_node.add_child(curr_node)
    node_dict["$"] = curr_node


    ##############################
    ## Traversing the graph now. (& relabelling nodes)
    ##############################
    print("Depth first search traversing the graph now.")
    visited = [] # List for visited nodes.

    ##############################
    ## Writing out the graph into dot file
    ##############################
    relative_filename = os.path.relpath(sys.argv[1], "../../multiseq_alignment/")
    dir_name = os.path.dirname(relative_filename)
    file_basename = os.path.basename(relative_filename)
    new_dir_name = os.path.join("../../graph/multiSeqWG", dir_name)
    os.makedirs(new_dir_name, exist_ok = True)
    fw_name = os.path.join(new_dir_name, "multiSeqWG_" + file_basename)
    fw_name = fw_name.replace('.fasta', '.dot')
    print("fw_name: ", fw_name)
    try:    
        os.remove(fw_name)
    except OSError:
        pass
    fw = open(fw_name, "a")
    fw.write("strict digraph  {\n")
    bfs(visited, node_dict[0])
    visited = []
    bfs_write(visited, node_dict[0], fw) #function for BFS
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
        m.set_nodeorder(nodeID_counter)
        if len(m.children) > 0:
            print("="*m.nodecolid, m.nodeid, "  ---[", m.out_edgelabel, "]--->  ", m.children[0].nodeid , " (", m.nodeorder, ")") 
        else:
            print("="*m.nodecolid, m.nodeid, " (", m.nodeorder, ")") 

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
            if m_child.nodeid != "S$":
                fw.write("\t" + m.nodeid + " -> " + m_child.nodeid + " [ label = "+m.out_edgelabel+" ];\n")
            # print(m.nodeid, " -> ", m_child.nodeid)

        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)
                # print("Appending into queue") 

if __name__ == "__main__":
    main()