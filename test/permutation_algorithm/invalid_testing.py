from os import listdir
from os.path import isfile, join
import os
import time
import sys
import subprocess
import pandas as pd

def main(path):
    # df = pd.DataFrame() #for storing node counts
    w = open("timing_data_100_nodes.txt", 'w')

    num_partitions = len(next(os.walk(path))[1])
    
    for partition in range(num_partitions):
        partition_path = path + '/partition' + str(partition) 
        # print(partition_path)
        onlyfiles = [f for f in listdir(partition_path) if isfile(join(partition_path, f))]
        
        start = time.time()
        for file in onlyfiles:
            filepath = partition_path + '/' + file
            print(filepath)
            subprocess.run(["../../bin/recognizer_p", filepath, ">", "/dev/null"])
            print('\n')
        end = time.time()
        w.write("Invalid WG at partition " + str(partition) + ": " + str(end-start) + " seconds\n")
        # print(onlyfiles)
        # print('\n\n\n')
    
    # df.to_csv("testing1.csv")


if __name__ == "__main__":
   main(sys.argv[1])