from os import listdir
from os.path import isfile, join
import os
from re import sub
import time
import sys
import subprocess
import pandas as pd

def main(path, csv_name, txt_name):
    df = pd.DataFrame() #for storing node counts
    w = open(txt_name, 'w')
    graph_paths = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]

    for i in range(len(graph_paths)):
        graph_path = path + '/' + graph_paths[i]
        onlyfiles = [f for f in listdir(graph_path) if isfile(join(graph_path, f))]
        start = time.time()
        time_list = []
        for file in onlyfiles:
            start_file = time.time()
            filepath = graph_path + '/' + file
            # print(filepath)
            subprocess.run(["../../../bin/recognizer_p", filepath, ">", "/dev/null"])
            end_file = time.time()
            time_list.append(str(end_file-start_file))
        end = time.time()

        df[str(graph_paths[i])] = time_list
        w.write("WG with " + str(graph_paths[i])  + str(end-start) + " seconds\n")

    df.to_csv(csv_name)
    w.close()

if __name__ == "__main__":
    if(len(sys.argv) != 4):
        print("Incorrect number of arguments. Please enter the following arguments:\n" +
  "python3 valid_testing.py [folder w/ samples] [csv timing file name] [averages txt file name]")
    else:
        path = sys.argv[1]
        csv_name = sys.argv[2]
        avg_txt = sys.argv[3]
        main(path, csv_name, avg_txt)