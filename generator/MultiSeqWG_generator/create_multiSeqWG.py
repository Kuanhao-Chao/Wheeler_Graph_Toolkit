#! /Users/chaokuan-hao/miniconda3/bin/python
import sys
from Bio import AlignIO
import node as n
import digraph as dg
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
            nodes_dict[node] = int(ordering)

    print(nodes_dict)
    # Step 1: Build WG from the first sequence.
    node_idx = 0
    # col_idx = 0

    wg = dg.digraph(alignment_len)
    # all_nodes = []
    # column_nodes = {}
    tmp_dict = {}
    prev_node = None
    curr_node = None
    for col_idx in range(alignment_len):
        seq = alignment[0][col_idx]
        if (seq != "-"):
            curr_node = n.node("S"+str(col_idx), nodes_dict["S"+str(col_idx)], seq, col_idx)
            wg.col_initialize(col_idx)
            wg.add_node_firstSeq(prev_node, curr_node)
            # column_nodes[col_idx][curr_node.out_edgelabel].append(curr_node)
            # all_nodes.append(curr_node)

            tmp_dict[node_idx] = curr_node
            if prev_node != None:
                curr_node.add_parent(prev_node)
                prev_node.add_child(curr_node)
            prev_node = curr_node
            node_idx += 1
            print(seq)
            curr_node.print_node()
        else:
            wg.col_initialize(col_idx)


    wg.update_all_nodes()

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




    print("column_nodes: ", wg.column_nodes)
    
    for node in wg.all_nodes:
        node.print_node()
    # print("wg.all_nodes: ", wg.all_nodes)
    print("self.edgelabel_num", wg.edgelabel_num)

    curr_node = None
    for row_idx in range(1, seq_number):

        
        tail_seq = "-"
        tail_seq_idx = 0
        tail_node = None

        head_seq = "-"
        head_seq_idx = 0
        head_node = None

        for col_idx in range(alignment_len):
            ##########################
            # Check the tail in which column
            ##########################
            print("The node of (", row_idx, ", ", col_idx, ") ", alignment[row_idx][col_idx] )
            if alignment[row_idx][col_idx] != "-":
                tail_seq = alignment[row_idx][col_idx]
                tail_seq_idx = col_idx
            # if (tail_seq != "-"):
            #     # 1. Use the exist node.
            #     # 2. The node exist but a new node is created.
            #     # 3. The node doen't exist. Create a new one.

            #     # Modify
            #     curr_node = n.node("S"+str(col_idx), 0, tail_seq, col_idx)
            #     column_nodes[col_idx][curr_node.out_edgelabel].append(curr_node)
            # else:
            #     # column_nodes[col_idx].append(None)
            #     pass
            # print("Tail column_nodes[col_idx]: ", column_nodes[col_idx])
            

            ##########################
            # Check the head in which column
            ##########################
            if col_idx == alignment_len-1:
                # Handling the boundary case.
                pass
            else:
                head_seq = alignment[row_idx][col_idx+1]
                head_seq_idx = col_idx+1





                ##########################
                # This is the edge that is gonna be processed!!
                ##########################
                if tail_seq != "-" and head_seq != "-":
                    print(tail_seq, " (",tail_seq_idx, ")  -->  ", head_seq, " (", head_seq_idx, ")")


                    # The first column. 
                    if tail_seq_idx == 0:
                        ##########################
                        # The first column => Initialization, finding the first tail!!
                        ##########################
                        # The node is a new ACGT that hasn't been used before. => create a new node
                        if len(wg.column_nodes[tail_seq_idx][tail_seq]) == 0:
                            print("#############################")
                            print("### Condition 1 : First column. Creating a new node!")
                            print("#############################")
                            # print("tail_seq_idx: ", tail_seq_idx, ";   column_nodes[tail_seq_idx]: ", column_nodes[tail_seq_idx])
                            
                            print("wg.edgelabel_num: ", wg.edgelabel_num)
                            new_tail_order = 1
                            # print("new_tail_order: ", new_tail_order)
                            tail_node = n.node("S"+str(row_idx)+str(tail_seq_idx), new_tail_order, tail_seq, tail_seq_idx)
                            
                            # update all the node with ordering bigger or equal to the 'new_tail_order'
                            wg.add_root_node(tail_node)

                            # This is for check printing!!
                            wg.print_all_nodes()
                    
                        # The node is a created ACGT. => must can be collapsed. => get the created node.
                        elif len(wg.column_nodes[tail_seq_idx][tail_seq]) == 1:
                            print("#############################")
                            print("### Condition 2 : First column. Reusing the node!!")
                            print("#############################")
                            tail_node = wg.column_nodes[tail_seq_idx][tail_seq][0]
                        print("tail_node: ", tail_node.out_edgelabel)
                        wg.finding_head(row_idx, tail_node, tail_seq_idx, tail_seq, head_node, head_seq_idx, head_seq)


                    # Not the first column. 
                    elif tail_seq_idx !=0:
                        ##########################
                        # Tail will be the previous head.
                        ##########################
                        # Tail node has already be decided while processing previous head node.
                        wg.finding_head(row_idx, tail_node, tail_seq_idx, tail_seq, head_node, head_seq_idx, head_seq)

                    # tail_node.print_node()
                    # head_node.print_node()
                    tail_node = head_node
                    # wg.print_all_nodes()
                    print("wg.edgelabel_num: ", wg.edgelabel_num)






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
        print("\n\n")


    print("column_nodes: ", wg.column_nodes)
    print("edgelabel_num: ", wg.edgelabel_num)

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

# def finding_head(nodes, wg, row_idx, tail_node, tail_seq_idx, tail_seq, head_node, head_seq_idx, head_seq):




if __name__ == "__main__":
    main()