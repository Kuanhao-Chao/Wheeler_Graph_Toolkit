from os import listdir
from os.path import isfile, join
import os
import time
import sys
import subprocess
import pandas as pd
import math

def main(path, csv_name, txt_name):

    w = open(txt_name, 'w')
    df = pd.DataFrame()
    num_folders = len(next(os.walk(path))[1])
    
    edge_prob = .05
    for _ in range(num_folders):
        graph_path = path + '/' + str(format(float(edge_prob), '.2f')) + "edge_prob"
        onlyfiles = [f for f in listdir(graph_path) if isfile(join(graph_path, f))]
        group_start = time.time()
        time_list = []
        for file in onlyfiles:
            file_start = time.time()
            filepath = graph_path + '/' + file
            subprocess.run(["../../../bin/recognizer_p", filepath, ">", "/dev/null"])
            file_end = time.time()
            time_list.append(str(file_end-file_start))
        group_end = time.time()

        df[str(format(float(edge_prob)))] = time_list
        w.write("WG with " + str(str(format(float(edge_prob)))) + " edge_prob: " + str(group_end-group_start) + " seconds\n")
        edge_prob = format(math.fsum((float(edge_prob), .05)), '.2g')

    df.to_csv(csv_name)
    w.close()

if __name__ == "__main__":
    if(len(sys.argv) != 4):
        print("Incorrect number of arguments. Please enter the following arguments:\n" +
  "python3 valid_testing_edge_prob.py [folder w/ samples] [csv timing file name] [averages txt file name]")
    else:
        path = sys.argv[1]
        csv_name = sys.argv[2]
        avg_txt = sys.argv[3]
        main(path, csv_name, avg_txt)