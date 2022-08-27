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

    try:    
        os.remove(fwdir)
    except OSError:
        pass
    os.makedirs(fwdir)

    for i in range(5, alignment_len+1, 1):
        print(alignment[:, :i].get_alignment_length())
        fwname = os.path.join(fwdir, "a"+str(i)+".fasta")
        SeqIO.write(alignment[:, :i], fwname, "fasta")

if __name__ == "__main__":
    main()
