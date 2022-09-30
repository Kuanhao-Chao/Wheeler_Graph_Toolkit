import requests, sys
import json
import random

def main():
  GENE_NAME = 50

  f = open("./Ensembl_all_geneID.txt", "r")
  lines = f.read().splitlines()
  genes = random.choices(lines, k=GENE_NAME)
  print(genes)

  # for gene in genes:
  #   for type in ["msa_dna", "msa_pep"]:
  #     # print(type)
      # target = "http://useast.ensembl.org/Homo_sapiens/Download/DataExport?cdb=compara;component=ComparaOrthologs;compression=uncompressed;data_action=Compara_Ortholog;data_type=Gene;db=core;export_action=Orthologs;file=temporary/2022_09_26/session_60346853/MMYSPUTYBCSbGBDKGUAAAMXN/Human_IDS_orthologues.fa;filename=Human_IDS_orthologues.fa;format=FASTA;g=ENSG00000010404;name=Human_IDS_orthologues;seq_type_FASTA=msa_dna"

      # "http://useast.ensembl.org/Homo_sapiens/Download/DataExport?cdb=compara;component=ComparaOrthologs;compression=uncompressed;data_action=Compara_Ortholog;data_type=Gene;db=core;export_action=Orthologs;file=temporary/2022_09_26/session_60346853/MMYSYAGNSUdEICUSaYAAAMAN/Human_IDS_orthologues.fa;filename=Human_IDS_orthologues.fa;format=FASTA;g=ENSG00000010404;name=Human_IDS_orthologues;r=X:149476988-149521096;seq_type_FASTA=msa_pep"
    # r = requests.get(target, allow_redirects=True)
    # open('Human_IDS_orthologues.fa', 'wb').write(r.content)


if __name__ == "__main__":
  main()

