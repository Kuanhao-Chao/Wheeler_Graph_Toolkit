import sys
import os

def main():
    base_dir = sys.argv[1]
    fs = os.listdir(sys.argv[1])

    for fname in fs:
        fo_name = os.path.join(base_dir, "parsed_"+fname)
        fout = open(fo_name, 'a')
        with open(os.path.join(base_dir,fname)) as f:
            lines = f.read().splitlines() 
            for line in lines:
                base_fname = line.split("\t")[-1].split("/")[-1]
                n, e, l = line.split("\t")[-1].split("/")[-2].split("_")
                # print("n, e, l: ", n, e, l)
                density = float(e)/float(l)
                fout.write(line+"\t"+str(n)+"\t"+str(e)+"\t"+str(l)+"\t"+str(density)+"\t"+base_fname + "\n")
            fout.close()

if __name__ == "__main__":
    main()