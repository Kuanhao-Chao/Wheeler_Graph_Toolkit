#! /Users/chaokuan-hao/miniconda3/bin/python
from enum import unique
from Bio import AlignIO

import node as n
import sys

source = n.node(sys.maxsize, "$")
sink = n.node(0, "#")

def main():
    print("In create_RevDetAuto.py")

    alignment = AlignIO.read("./data/a1.fasta", "fasta")
    print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)

    print("Iterating the alignment from the back")

    nodeID = 1
    prev_children = {}
    curr_nodes = {}

    for col_idx in range(alignment_len-1, -1, -1):

        uniq_nodes = set(sorted(alignment[:,col_idx]))

        print("Alignment: ", alignment[:,col_idx])

        # Creating nodes for the uniq nodes.
        for uniq_node in uniq_nodes:
            if uniq_node != "-":
                new_node = n.node(nodeID, uniq_node)
                curr_nodes[uniq_node] = new_node
        print("curr_nodes: ", curr_nodes)
        print("prev_children: ", prev_children)
        print()

        # Iterating the row.
        for row_idx in range(0, seq_number, 1):
            print("row_idx: ", row_idx)

            if col_idx == alignment_len-1:
                print("Adding sink as child")
                print(alignment[row_idx, col_idx], "$")

                for curr_node in curr_nodes:
                    curr_node.add_child(source)


            elif col_idx == 0:
                print("This is the source")
                print("#", alignment[row_idx, col_idx])

            else:
                print(alignment[row_idx, col_idx], alignment[row_idx, col_idx+1])



        prev_children = {}
        prev_children = curr_nodes
        curr_nodes = {}


        nodeID += 1



    # print(alignment)
    # print(alignment[:,2])

    # records = list(SeqIO.parse("./data/a1.fasta", "fasta"))
    # print(records[0])

    # for record in SeqIO.parse("./data/a1.fasta", "fasta"):
    #     print(record.id)
    # with open("./data/a1.txt", "r") as f:
    #     lines = f.read().splitlines()
    #     print(lines)





if __name__ == "__main__":
    main()