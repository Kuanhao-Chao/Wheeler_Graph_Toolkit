#! /Users/chaokuan-hao/miniconda3/bin/python
from enum import unique
import getopt
from Bio import AlignIO
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio.Align import MultipleSeqAlignment
# from Bio.Alphabet import generic_dna

import node as n
import sys
import os
queue = []     #Initialize a queue
USAGE = '''usage: RevDetGraph.py [-h / --help] [-v/ --version] [-o / --ofile FILE] [-l / --seqLen sequence length] [-a / --alnNum alignment number] multilple sequence alignments (MSA) FASTA file'''

def main(argv):
    ##############################
    ## Parsing arguments
    ##############################
    # Default parameters:
    k = 3
    verbose = False
    outfile = "tmp.dot"
    seqLen = -1
    alnNum = 3
    try:
        opts, args = getopt.getopt(argv,"hvo:l:a:",["ofile=", "seqLen=", "alnNum="])
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
        elif opt in ("-l", "--seqLen"):
            seqLen = int(arg)
        elif opt in ("-a", "--alnNum"):
            alnNum = int(arg)

    # if not os.path.exists(outfile):
    #     print("Output directory does not exist!")
    #     outfile = "./"
    
    if len(args) == 0:
        print(USAGE)
        print("Please input one FASTA file")
        sys.exit(2)

    alignment = AlignIO.read(args[0], "fasta")
    alignment = alignment[:alnNum]
    print("outfile: ", outfile)
    print("seqLen: ", seqLen)
    print("alignment\n", alignment)
    alignment_len = alignment.get_alignment_length()
    if seqLen > alignment_len:
        seqLen = alignment_len
    print("seqLen: ", seqLen)
    seq_number = len(alignment)
    source = n.node(sys.maxsize, "#", 0)
    mid_curr_node = None
    sink = n.node(0, "$", alignment_len)

    nodeID = 1
    prev_nodes = {}
    curr_nodes = {}
    preceding_nodes = {}
    preceding_nodes_pos = {}
    first_nongap_nodes = {}
    seqLen_counter = 0

    for col_idx in range(alignment_len-1, -1, -1):
        uniq_nodes = set(sorted(alignment[:,col_idx]))
        #############################
        ## Creating nodes for the uniq nodes.
        #############################
        for uniq_node in uniq_nodes:
            if uniq_node != "-":
                new_node = n.node(nodeID, uniq_node, col_idx)
                curr_nodes[(col_idx, uniq_node)] = new_node
        # print("curr_nodes: ", curr_nodes)
        if len(curr_nodes) >= 1:
            seqLen_counter += 1
        # Iterating the row.
        for row_idx in range(0, seq_number, 1):
            #############################
            ## The first node selection 
            ##  1. not "-" => go find the second node.
            #############################
            if (alignment[row_idx, col_idx] != "-"):
                mid_curr_node = curr_nodes[(col_idx, alignment[row_idx, col_idx])]

                # Handling sink
                if col_idx == alignment_len-1:
                    # print("\tAdding sink as child")
                    mid_curr_node.add_child(sink)
                    sink.add_parent(mid_curr_node)

                elif col_idx < alignment_len-1:
                    #############################
                    ## The second node selection 
                    ##     1. "-" => skip to the next one.
                    #############################
                    # Get previous non-gap node.
                    sec_nongap_node_offset = 1
                    while ((col_idx+sec_nongap_node_offset) < alignment_len and alignment[row_idx, col_idx+sec_nongap_node_offset] == "-"): 
                        sec_nongap_node_offset += 1

                    #############################
                    ## The second node selection 
                    ##     1. not "-" => select this as the second node.
                    #############################
                    if (col_idx+sec_nongap_node_offset) < alignment_len:
                        if verbose: print("\t\t(col_idx+sec_nongap_node_offset, alignment[row_idx, col_idx+sec_nongap_node_offset]): ", (col_idx+sec_nongap_node_offset, alignment[row_idx, col_idx+sec_nongap_node_offset]))
                        mid_prev_node = prev_nodes[(col_idx+sec_nongap_node_offset, alignment[row_idx, col_idx+sec_nongap_node_offset])]
                        if verbose: print("\t\tFirst nongap node: ", alignment[row_idx, col_idx], ";  Second nongap node: ", alignment[row_idx, col_idx+sec_nongap_node_offset])
                    else:
                        mid_prev_node = sink
                    if verbose:
                        print("\t\t>> mid_curr_node: ", mid_curr_node.nodelabel)
                        print("\t\t>> mid_prev_node: ", mid_prev_node.nodelabel)
                    mid_curr_node.add_child(mid_prev_node)
                    mid_prev_node.add_parent(mid_curr_node)


                #############################
                ## Searching for the preceding nongap node.!!
                ##   Only do the search if it's not "-".
                #############################
                preceding_nongap_node_offset = 1
                while (col_idx-preceding_nongap_node_offset > 0 and alignment[row_idx, col_idx-preceding_nongap_node_offset] == "-"):
                    preceding_nongap_node_offset += 1

                # (column_idx, sequence)
                if alignment[row_idx, col_idx-preceding_nongap_node_offset] not in preceding_nodes.keys():
                    preceding_nodes[alignment[row_idx, col_idx-preceding_nongap_node_offset]] = [col_idx-preceding_nongap_node_offset]
                    preceding_nodes_pos[alignment[row_idx, col_idx-preceding_nongap_node_offset]+"_pos"] = [row_idx]

                else:
                    preceding_nodes[alignment[row_idx, col_idx-preceding_nongap_node_offset]].append(col_idx-preceding_nongap_node_offset)
                    preceding_nodes_pos[alignment[row_idx, col_idx-preceding_nongap_node_offset]+"_pos"].append(row_idx)

            #############################
            ## The first node selection 
            ##  1. "-" => go find the prev_nongap node, and 
            ##     add it into the prev_nodes list so that I 
            ##     can retreive it back later.
            #############################
            elif (alignment[row_idx, col_idx] == "-"):
                # Here I need to retrieve back the previous non-gap node.
                first_nongap_node_offset = 1
                while ((col_idx+first_nongap_node_offset) < alignment_len and alignment[row_idx, col_idx+first_nongap_node_offset] == "-"): 
                    first_nongap_node_offset += 1
                    if verbose: print("\t\tSkipping 2nd node gap!!")
                #############################
                ## this first_nongap_node should be kept in the 'prev_nodes' dictionary
                #############################
                if (col_idx+first_nongap_node_offset) < alignment_len:
                    first_nongap_node = prev_nodes[(col_idx+first_nongap_node_offset, alignment[row_idx, col_idx+first_nongap_node_offset])]
                    if verbose: print("\t\t", col_idx+first_nongap_node_offset, "(", alignment[row_idx, col_idx+first_nongap_node_offset], ") is kept!!")
                    first_nongap_nodes[(col_idx+first_nongap_node_offset, alignment[row_idx, col_idx+first_nongap_node_offset])] = first_nongap_node
                    if verbose: print("\t\tfirst_nongap_nodes: ", first_nongap_nodes)

        if verbose:
            print("\t>> Before update curr_nodes: ", curr_nodes)
            print("\t>> Before update prev_nodes: ", prev_nodes)
            print("\t>> Before update preceding_nodes: ", preceding_nodes)
            print("\t>> Before update preceding_nodes_pos: ", preceding_nodes_pos)
            print()

        prev_nodes = {}
        # Move the curr_nodes into prev_nodes.
        prev_nodes = curr_nodes
        # Move the first_nongap_nodes into prev_nodes
        for key, value in first_nongap_nodes.items():
            if verbose: print("\t\t Moving first_nongap_nodes into prev_nodes: ", key, value)
            prev_nodes[key] = value
        first_nongap_nodes = {}
        curr_nodes = {}
        #############################
        ## This part is to change the alignment strings!!
        #############################
        for key, all_pos in preceding_nodes.items():
            if verbose: print("key: ", key, "  all_pos: ", all_pos)
            right_most_pos = max(all_pos)
            if verbose: print("max(all_pos): ", right_most_pos)

            for row_idx, row in enumerate(preceding_nodes_pos[key+"_pos"]):
                if verbose:
                    print("row: ", row)
                    print("alignment[row]: ", right_most_pos, "  ", alignment[row, right_most_pos])
                    print("alignment[row] (original): ", all_pos[row_idx], "  ", alignment[row, all_pos[row_idx]])

                # Change the alignment strings
                if (right_most_pos != all_pos[row_idx]):
                    new_seq = str(alignment[row].seq)
                    tmp = new_seq[right_most_pos]
                    new_seq = new_seq[:right_most_pos] + new_seq[all_pos[row_idx]] + new_seq[right_most_pos+1:]
                    new_seq = new_seq[:all_pos[row_idx]] + tmp + new_seq[all_pos[row_idx]+1:]
                    # Reconstructing the alignment
                    new_seq_biopython = SeqRecord(Seq(new_seq))
                    new_alignment = MultipleSeqAlignment(alignment[:row])
                    new_alignment.extend([new_seq_biopython])
                    new_alignment.extend(alignment[row+1:])
                    alignment = new_alignment
        preceding_nodes = {}
        preceding_nodes_pos = {}
        if verbose:
            print("\t>> After update curr_nodes: ", curr_nodes)
            print("\t>> After update prev_nodes: ", prev_nodes)
            print("\t>> After update preceding_nodes: ", preceding_nodes)
            print("\t>> Before update preceding_nodes_pos: ", preceding_nodes_pos)
        nodeID += 1

        if seqLen_counter == seqLen-1:
            break

    # Adding source as the parent.
    if verbose:
        print("\tAdding source as parent")
    source.add_child(mid_curr_node)
    if verbose:
        print("\t\tsource: ", source.nodelabel)
        print("\t\tmid_curr_node: ", mid_curr_node.nodelabel)
    mid_curr_node.add_parent(source)


    ##############################
    ## Traversing the graph now. (& relabelling nodes)
    ##############################
    print("Depth first search traversing the graph now.")
    visited = [] # List for visited nodes.

    ##############################
    ## Writing out the graph into dot file
    ##############################
    # relative_filename = os.path.relpath(args[0], "../../multiseq_alignment/")
    # dir_name = os.path.dirname(relative_filename)
    # file_basename = os.path.basename(relative_filename)
    # new_dir_name = os.path.join(outfile, dir_name)
    # os.makedirs(new_dir_name, exist_ok = True)
    # fw_name = os.path.join(new_dir_name, "RevDet_" + file_basename)
    # fw_name = fw_name.replace('.fasta', '.dot')
    try:    
        os.remove(outfile)
    except OSError:
        pass
    fw = open(outfile, "a")
    fw.write("strict digraph  {\n")
    bfs(visited, source)
    visited = []
    bfs_write(visited, source, fw) #function for BFS
    fw.write("}\n")
    fw.close()

# I need to number the node in this function
def bfs(visited, node): #function for BFS
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

def bfs_write(visited, node, fw): #function for BFS
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

if __name__ == "__main__":
    main(sys.argv[1:])