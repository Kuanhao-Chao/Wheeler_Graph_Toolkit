import requests, sys
import random 
def main(): 

  chroms_len = { "1":248956422, "2": 242193529, "3":	198295559, "4":	190214555, "5":	181538259, "6":	170805979, "7":	159345973,"8":	145138636,"9":	138394717,"10":	133797422,"11":	135086622,"12":	133275309,"13":	114364328,"14":	107043718,"15":	101991189,"16":	90338345,"17":	83257441,"18":	80373285,"19":	58617616,"20":	64444167,"21":	46709983,"22":	50818468,"X":	156040895,"Y":	57227415}

  print(chroms_len)
  nums = list(range(1,23))

  chroms = [str(num) for num in nums]
  chroms.append("X")
  chroms.append("Y")

  for i in range(50):
    chrom = random.choice(chroms)
    start = random.randint(1, chroms_len[chrom])
    end = start+15
    print(">> start: ", chrom, ": ", start, "-", end)
    ofa = "./"
    server = "https://rest.ensembl.org"
    ext = "/alignment/region/homo_sapiens/"+chrom+":"+str(start)+"-" + str(end) + "?species_set_group=mammals"
    
    r = requests.get(server+ext, headers={ "Content-Type" : "application/json"})
    

    ofa = "fasta/" + chrom + "_" + str(start) + "_" + str(end) + ".fa"
    fw = open(ofa, "a")

    if not r.ok:
      r.raise_for_status()
      sys.exit()
    
    js_decoded = r.json()

    for key in js_decoded[0]['alignments']:
      fw.write(">"+key['species'] + "\n")
      fw.write(key['seq'] + "\n")

if __name__== "__main__":
  main()

 