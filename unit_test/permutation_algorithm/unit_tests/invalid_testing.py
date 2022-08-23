from os import listdir
from os.path import isfile, join
import os
import time
import sys
import subprocess
import pandas as pd

def main(path, csv_name, txt_name):
    df = pd.DataFrame() #for storing timing data for each partition
    w = open(txt_name, 'w')

    num_partitions = len(next(os.walk(path))[1])
    
    for partition in range(num_partitions):
        partition_path = path + '/partition' + str(partition) 
        onlyfiles = [f for f in listdir(partition_path) if isfile(join(partition_path, f))]
        
        start = time.time()
        time_list = []
        for file in onlyfiles:
            start_file = time.time()
            filepath = partition_path + '/' + file
            subprocess.run(["../../../bin/recognizer_p", filepath, ">", "/dev/null"])
            end_file = time.time()
            time_list.append(str(end_file-start_file))
        end = time.time()
        df[str("partition: " + str(partition))] = time_list
        w.write("Invalid WG at partition " + str(partition) + ": " + str(end-start) + " seconds\n")

    df.to_csv(csv_name)


if __name__ == "__main__":
    if(len(sys.argv) != 4):
        print("Incorrect number of arguments. Please enter the following arguments:\n" +
  "python3 invalid_testing.py [folder w/ samples] [csv timing file name] [averages txt file name]")
    else:
        path = sys.argv[1]
        csv_name = sys.argv[2]
        avg_txt = sys.argv[3]
        main(path, csv_name, avg_txt)