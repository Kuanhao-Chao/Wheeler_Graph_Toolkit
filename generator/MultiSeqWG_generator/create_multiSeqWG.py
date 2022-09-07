#! /Users/chaokuan-hao/miniconda3/bin/python
import sys
from Bio import AlignIO
import node as n
import os

queue = []     #Initialize a queue

def main():
    fasta_file = sys.argv[1]
    nodemapping_file = sys.argv[2]
    print("Hello world")
    print("Input alignment fasta file: ", fasta_file)
    print("Node converting file: ", nodemapping_file)
    alignment = AlignIO.read(sys.argv[1], "fasta")
    print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    print("alignment_len: ", alignment_len)
    print("seq_number: ", seq_number)

    nodes_dict = {}
    with open(nodemapping_file, "r") as f:
        lines = f.read().splitlines() 
        for line in lines:
            node, ordering = line.split("\t")
            nodes_dict[node] = ordering

    print(nodes_dict)
    # Step 1: Build WG from the first sequence.
    node_idx = 0
    # col_idx = 0


    column_nodes = {}
    tmp_dict = {}
    prev_node = None
    curr_node = None
    for col_idx in range(alignment_len):
        seq = alignment[0][col_idx]
        if (seq != "-"):
            curr_node = n.node("S"+str(col_idx), nodes_dict["S"+str(col_idx)], seq, col_idx)

            column_nodes[col_idx] = [curr_node]

            tmp_dict[node_idx] = curr_node
            if prev_node != None:
                curr_node.add_parent(prev_node)
                prev_node.add_child(curr_node)
            prev_node = curr_node
            node_idx += 1
            print(seq)
        else:
            column_nodes[col_idx] = [None]

    curr_node = n.node("S$", -1, "$", col_idx+1)
    curr_node.add_parent(prev_node)
    prev_node.add_child(curr_node)
    tmp_dict["$"] = curr_node

    ##############################
    ## Traversing the graph now. (& relabelling nodes)
    ##############################
    print("Depth first search traversing the graph now.")
    visited = [] # List for visited nodes.
    bfs(visited, tmp_dict[0])


    print("column_nodes: ", column_nodes)

    curr_node = None
    for row_idx in range(1, seq_number):
        for col_idx in range(alignment_len):
            
            ##########################
            # Check the tail node.
            ##########################
            tail_seq = alignment[row_idx][col_idx]
            print("The node of (", row_idx, ", ", col_idx, ") ", tail_seq )
            if (tail_seq != "-"):
                # 1. Use the exist node.
                # 2. The node exist but a new node is created.
                # 3. The node doen't exist. Create a new one.

                # Modify
                curr_node = n.node("S"+str(col_idx), 0, tail_seq, col_idx)


                column_nodes[col_idx].append(curr_node)
            else:
                column_nodes[col_idx].append(None)
            print("Tail column_nodes[col_idx]: ", column_nodes[col_idx])
            
            ##########################
            # Check the head node.
            ##########################
            if col_idx == alignment_len-1:
                pass
            else:
                head_seq = alignment[row_idx][col_idx+1]
                print("Head column_nodes[col_idx+1]: ", column_nodes[col_idx+1])

                if (tail_seq != "-"):
                    pass
                else:
                    


                # Check if the sequence is used at this position.
                head_seq_used = False
                for node_itr in column_nodes[col_idx+1]:
                    print("node_itr: ", node_itr)
                    if (node_itr != None):
                        print("head_seq: ", head_seq, ";  node_itr.out_edgelabel: ", node_itr.out_edgelabel)
                        if head_seq == node_itr.out_edgelabel:
                            head_seq_used = True
                            print("True")

                # The head seq has not been used.
                if not head_seq_used:
                    print("Current used: ", column_nodes[col_idx+1])
                    print("head_seq: ", head_seq)



            #     print(seq)
            #     print("(", row_idx, ", ", col_idx, ")")
                # print(nodes_dict["S"+str(col_idx)])
                # curr_node = n.node("S"+str(col_idx), nodes_dict["S"+str(col_idx)], i, col_idx)
                # if prev_node != None:
                #     curr_node.add_parent(prev_node)
                #     prev_node.add_child(curr_node)
                # prev_node = curr_node
                # node_idx += 1
                # print(i)
        print()


# I need to number the node in this function
def bfs(visited, node): #function for BFS
    visited.append(node)
    queue.append(node)
    nodeID_counter = 0
    while queue:          # Creating loop to visit each node
        # print("len(queue): ", len(queue))
        m = queue.pop(0)
        # print("Dequeue") 
        if len(m.children) > 0:
            print("="*m.nodecolid, m.nodeid, "(", m.nodeorder, ")  ---[", m.out_edgelabel, "]--->  ", m.children[0].nodeid , " (", m.children[0].nodeorder, ")") 
        else:
            print("="*m.nodecolid, m.nodeid, " (", m.nodeorder, ")") 

        nodeID_counter += 1
        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)
                # print("Appending into queue") 


if __name__ == "__main__":
    main()