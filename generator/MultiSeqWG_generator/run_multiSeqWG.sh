python firstseq_2_dot_multiSeqWG.py ../../multiseq_alignment/a$1.fasta

../../bin/recognizer_p ../../graph/multiSeqWG/multiSeqWG_a$1.dot -w --outDir ../../graph/multiSeqWG/

python create_multiSeqWG.py ../../multiseq_alignment/a$1.fasta ../../graph/multiSeqWG/__multiSeqWG_a$1/nodes.txt

../../bin/recognizer_p ../../graph/multiSeqWG/a$1.dot -b
