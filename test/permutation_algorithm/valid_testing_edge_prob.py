from os import listdir
from os.path import isfile, join
import os
import time
import sys
import subprocess
import pandas as pd
import math

def main(path):
    # df = pd.DataFrame() #for storing node counts
    w = open("timing_data_vary_edges_60nodes_1.txt", 'w')
    df = pd.DataFrame()

    num_node_counts = len(next(os.walk(path))[1])
    
    # node_count = str(5)
    edge_prob = .05
    for graph in range(10):
        graph_path = path + '/' + str(format(float(edge_prob), '.2f')) + "edge_prob"
        print(graph_path)
        # print(graph_path)
        onlyfiles = [f for f in listdir(graph_path) if isfile(join(graph_path, f))]
        # print(onlyfiles)
        start = time.time()
        time_list = []
        for file in onlyfiles:
            start_file = time.time()
            filepath = graph_path + '/' + file
            # print(filepath)
            subprocess.run(["../../bin/recognizer_p", filepath, ">", "/dev/null"])
            end_file = time.time()
            time_list.append(str(end_file-start_file))
            print('\n')
        end = time.time()

        df[str(format(float(edge_prob)))] = time_list
        w.write("WG with " + str(str(format(float(edge_prob)))) + " edge_prob: " + str(end-start) + " seconds\n")
        # # print(onlyfiles)
        # print('\n\n\n')
        edge_prob = format(math.fsum((float(edge_prob), .05)), '.2g')

    df.to_csv("testing_edges1.csv")
    # avg_col = df.mean(axis=0)
    # f = open("averages0.txt", "w")
    # f.write(str(avg_col))
    # f.close()

    w.close()

if __name__ == "__main__":
   main(sys.argv[1])