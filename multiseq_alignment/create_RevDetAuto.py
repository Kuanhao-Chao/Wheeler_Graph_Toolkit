#! /Users/chaokuan-hao/miniconda3/bin/python
from enum import unique
from Bio import AlignIO

import node as n
import sys

queue = []     #Initialize a queue

def main():
    print("In create_RevDetAuto.py")

    alignment = AlignIO.read("./align/a1.fasta", "fasta")
    print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    source = n.node(sys.maxsize, "#", 0)
    sink = n.node(0, "$", alignment_len)

    print("Iterating the alignment from the back")

    nodeID = 1
    prev_nodes = {}
    curr_nodes = {}
    first_nongap_nodes = {}

    for col_idx in range(alignment_len-1, -1, -1):

        uniq_nodes = set(sorted(alignment[:,col_idx]))

        print("Alignment: ", alignment[:,col_idx])

        # Creating nodes for the uniq nodes.
        for uniq_node in uniq_nodes:
            if uniq_node != "-":
                new_node = n.node(nodeID, uniq_node, col_idx)
                curr_nodes[(col_idx, uniq_node)] = new_node
            # elif uniq_node == "-":
            #     # Here I need to retrieve back the previous non-gap node.
            #     pass


        # Adding sink as child
        if col_idx == alignment_len-1:
            print("Adding sink as child")
            # print(alignment[row_idx, col_idx], "$")

            for curr_node_key, curr_node in curr_nodes.items():
                curr_node.add_child(sink)
                sink.add_parent(curr_node)

        # Adding source as parent
        # elif col_idx == 0:

        # Intermediate nodes.
        else:
            # Iterating the row.
            for row_idx in range(0, seq_number, 1):
                print("row_idx: ", row_idx)            

                #############################
                ## The first node selection 
                ##  1. not "-" => go find the second node.
                #############################
                if (alignment[row_idx, col_idx] != "-"):
                    mid_curr_node = curr_nodes[(col_idx, alignment[row_idx, col_idx])]


                    #############################
                    ## The second node selection 
                    ##     1. "-" => skip to the next one.
                    #############################
                    # Get previous non-gap node.
                    sec_nongap_node_offset = 1

                    while (alignment[row_idx, col_idx+sec_nongap_node_offset] == "-"): 
                        sec_nongap_node_offset += 1
                        print("Skipping gap!!")

                    #############################
                    ## The second node selection 
                    ##     1. not "-" => select this as the second node.
                    #############################
                    print("(col_idx+sec_nongap_node_offset, alignment[row_idx, col_idx+sec_nongap_node_offset]): ", (col_idx+sec_nongap_node_offset, alignment[row_idx, col_idx+sec_nongap_node_offset]))
                    mid_prev_node = prev_nodes[(col_idx+sec_nongap_node_offset, alignment[row_idx, col_idx+sec_nongap_node_offset])]

                    print("First: ", alignment[row_idx, col_idx], alignment[row_idx, col_idx+sec_nongap_node_offset])
                    print(">> mid_curr_node: ", mid_curr_node.nodelabel)
                    print(">> mid_prev_node: ", mid_prev_node.nodelabel)
                    mid_curr_node.add_child(mid_prev_node)
                    mid_prev_node.add_parent(mid_curr_node)


                #############################
                ## The first node selection 
                ##  1. "-" => go find the prev_nongap node, and 
                ##     add it into the prev_nodes list so that I 
                ##     can retreive it back later.
                #############################
                elif (alignment[row_idx, col_idx] == "-"):
                    # Here I need to retrieve back the previous non-gap node.
                    first_nongap_node_offset = 1
                    while (alignment[row_idx, col_idx+first_nongap_node_offset] == "-"): 
                        first_nongap_node_offset += 1
                        print("Skipping gap!!")

                    # this first_nongap_node should be kept in the 'prev_nodes' dictionary

                    #############################
                    ## this first_nongap_node should be kept in the 'prev_nodes' dictionary
                    #############################
                    first_nongap_node = prev_nodes[(col_idx+first_nongap_node_offset, alignment[row_idx, col_idx+first_nongap_node_offset])]

                    print(col_idx+first_nongap_node_offset, "(", alignment[row_idx, col_idx+first_nongap_node_offset], ") is kept!!")

                    first_nongap_nodes[(col_idx+first_nongap_node_offset, alignment[row_idx, col_idx+first_nongap_node_offset])] = first_nongap_node

                    print("first_nongap_nodes: ", first_nongap_nodes)
                

        if col_idx == 0:
            # Adding source as parent
            print("Adding source as parent")
            # print("#", alignment[row_idx, col_idx])
            for curr_node_key, curr_node in curr_nodes.items():
                curr_node.add_parent(source)
                source.add_child(curr_node)

        print(">> Before update curr_nodes: ", curr_nodes)
        print(">> Before update prev_nodes: ", prev_nodes)
        print()


        prev_nodes = {}

        # Move the curr_nodes into prev_nodes.
        prev_nodes = curr_nodes

        # Move the first_nongap_nodes into prev_nodes
        for key, value in first_nongap_nodes.items():
            print("first_nongap_nodes: ", key, value)
            prev_nodes[key] = value

        first_nongap_nodes = {}
        curr_nodes = {}

        print(">> After update curr_nodes: ", curr_nodes)
        print(">> After update prev_nodes: ", prev_nodes)

        nodeID += 1


    print(alignment)
    ##############################
    ## Traversing the graph now.
    ##############################
    print("Depth first search traversing the graph now.")
    visited = [] # List for visited nodes.

    fw = open("./dot/output.dot", "a")
    fw.write("strict digraph  {\n")
    bfs(visited, source)
    visited = []
    bfs_write(visited, source, fw) #function for BFS
    fw.write("}\n")
    fw.close()
    

    ##############################
    ## Writing out the graph into dot file
    ##############################
    


# I need to number the node in this function as well 
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


        # for m_child in m.children:
        #     fw.write("\tS" + str(m.nodeid) + " -> S" + str(m_child.nodeid) + " [ label = "+m.nodelabel+" ];\n")
        #     print(m.nodeid, " -> ", m_child.nodeid)

        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)
                # print("Appending into queue") 



# I need to number the node in this function as well 
def bfs_write(visited, node, fw): #function for BFS
    visited.append(node)
    queue.append(node)
    
    nodeID_counter = 0
    while queue:          # Creating loop to visit each node
        # print("len(queue): ", len(queue))
        m = queue.pop(0)
        # print("Dequeue") 
        # m.set_nodeid(nodeID_counter)
        print("-"*m.nodecolid, m.nodelabel, "(", m.nodeid, ")") 

        # nodeID_counter += 1


        for m_child in m.children:
            fw.write("\tS" + str(m.nodeid) + " -> S" + str(m_child.nodeid) + " [ label = "+m_child.nodelabel+" ];\n")
            # fw.write("S" + str(m.nodeid) + " S" + str(m_child.nodeid) + " "+m_child.nodelabel+"\n")
            print(m.nodeid, " -> ", m_child.nodeid)

        for child in m.children:
            if child not in visited:
                visited.append(child)
                queue.append(child)
                # print("Appending into queue") 

if __name__ == "__main__":
    main()