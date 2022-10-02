#! /Users/chaokuan-hao/miniconda3/bin/python 

# Usage: python create_multiseq_alignment.py <root_fasta> <output_dir>

from Bio import AlignIO, SeqIO
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio.Align import MultipleSeqAlignment
# from Bio.Alphabet import generic_dna

import sys
import os

queue = []     #Initialize a queue

def main():
    alignment = AlignIO.read(sys.argv[1], "fasta")
    fwdir = sys.argv[2]
    # print("alignment", alignment)
    alignment_len = alignment.get_alignment_length()
    seq_number = len(alignment)
    print("alignment_len: ", alignment_len)
    print("seq_number: ", seq_number)
    print("alignment: ", alignment)

    # if alignment_len > 200:
    #     alignment_len = 200

    try:    
        os.remove(fwdir)
    except OSError:
        pass
    os.makedirs(fwdir)

    # for i in range(5, alignment_len+1-38, 1):
    #     print(alignment[:, 38:i+38].get_alignment_length())
    #     fwname = os.path.join(fwdir, "a"+str(i)+".fasta")
    #     SeqIO.write(alignment[:, 38:i+38], fwname, "fasta")

    # for i in range(1, 10, 1):
    #     print(alignment[:, 38:i+38].get_alignment_length())
    #     fwname = os.path.join(fwdir, "a"+str(i)+".fasta")
    #     SeqIO.write(alignment[:, 38:i+38], fwname, "fasta")
    
    print(alignment[:, 0:10000].get_alignment_length())
    fwname = os.path.join(fwdir, "a"+str(10000)+".fasta")
    SeqIO.write(alignment[:, 0:10000], fwname, "fasta")


if __name__ == "__main__":
    main()