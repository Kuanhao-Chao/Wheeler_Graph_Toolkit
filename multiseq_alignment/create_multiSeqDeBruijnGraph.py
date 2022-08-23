#! /Users/chaokuan-hao/miniconda3/bin/python
import sys
from Bio import AlignIO
import node as n

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
        kmer_dic[row_idx] = set()
        print("row_idx: ", row_idx)
        row_seq = str(alignment[row_idx].seq)
        row_seq_parsed = row_seq.replace("-", "")
        # .rstrip("-") 
        print(row_seq_parsed)

        for i in range(0, len(row_seq_parsed)):
            node_kmer = row_seq_parsed[i:i+k]
            kmer_dic[row_idx].add(node_kmer)
            kmer_set.add(node_kmer)

            print(i)
            print(node_kmer)
    print(kmer_dic)
    print(kmer_set)

    for node in kmer_set:
        new_node = n.node(0, node, alignment_len)



if __name__ == "__main__":
    main()