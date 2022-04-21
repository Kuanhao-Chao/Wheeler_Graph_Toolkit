from os import listdir
from os.path import isfile, join
import os
import time
import sys
import subprocess
import pandas as pd

def main(path):
    # df = pd.DataFrame() #for storing node counts
    w = open("timing_data_valid_WG_exponential_0.txt", 'w')
    df = pd.DataFrame()

    num_node_counts = len(next(os.walk(path))[1])
    
    node_count = str(5)
    for graph in range(2):
        # p = open("timing_trial0/timing_data_" + str(node_count) + "_nodes" + ".txt", 'w')
        graph_path = path + '/' + str(node_count) + "nodes"
        print(graph_path)
        # print(graph_path)
        onlyfiles = [f for f in listdir(graph_path) if isfile(join(graph_path, f))]
        # print(onlyfiles)
        start = time.time()
        time_list = []
        for file in onlyfiles:
            start_file = time.time()
            filepath = graph_path + '/' + file
            print(filepath)
            subprocess.run(["../../bin/recognizer_e", filepath, ">", "/dev/null"])
            end_file = time.time()
            # p.write(str(end_file-start_file) + '\n')
            time_list.append(str(end_file-start_file))
            print('\n')
        end = time.time()

        df[str(node_count)] = time_list
        w.write("WG with " + str(node_count) + " nodes: " + str(end-start) + " seconds\n")
        # print(onlyfiles)
        print('\n\n\n')
        node_count = str(int(node_count) + 5)
    # df.to_csv("testing1.csv")

    df.to_csv("testing1.csv")
    avg_col = df.mean(axis=0)
    f = open("averages0.txt", "w")
    f.write(str(avg_col))
    f.close()

    w.close()

if __name__ == "__main__":
   main(sys.argv[1])