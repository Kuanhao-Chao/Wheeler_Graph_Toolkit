from generator import generateWG
import math
import os
import sys

# y = 0.0252x^2 + 0.226x + 6.2819
def calc_node_num(num):
    """Function to determine how many nodes the generator should 
    call the networkx graph generation function with, in order to 
    obtain the approximately the number of nodes the user entered """
    return (0.0252 * (num ** 2)) + (.226 * num) + 6.2819


def makeFilePath(file_path):
    #file path does not exist
    if not os.path.exists(file_path):
        os.makedirs(file_path)
        return file_path
    #file path does exist, make a new folder so we don't accidentally overwrite any files
    else:
        path_update = 1
        new_path = file_path
        while os.path.exists(new_path):
            new_path = file_path + '_' + str(path_update)
            path_update = path_update + 1
        os.makedirs(new_path)
        return new_path

def generateGraphs(file_path, node_count, num_graphs, start, stop, step):
    #make graphs with 'node_count' nodes from .05 to .4 edge prob
    edge_prob = start
    num_iter = int((stop-start)/step)

    num_nodes = int(calc_node_num(node_count))
    for _ in range(num_iter+1):
        graph_path = file_path + '/' + str(format(float(edge_prob), '.2f')) + '_edge_prob'
        if not os.path.exists(graph_path):
            os.makedirs(graph_path)

        for j in range(num_graphs):
            filename = graph_path + "/test_"  + str(j) + ".dot"
            #Function parameters described below:
            #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
            generateWG(num_nodes, float(edge_prob), False, filename, False)
        edge_prob = format(math.fsum((float(edge_prob), step)), '.2g')

if (len(sys.argv) != 7):
  print("Incorrect number of arguments. Please enter the following arguments:\n" +
  "python3 generate_WG_samples_vary_edge_prob.py [output folder] [nodes in WG] [num samples] [start] [stop] [step]")
else: 
    file_path = sys.argv[1] #path to store the samples in
    node_count = int(sys.argv[2])
    num_graphs = int(sys.argv[3]) #number of samples
    start = float(sys.argv[4])
    stop = float(sys.argv[5])
    step = float(sys.argv[6])
    file_name = makeFilePath(file_path)
    generateGraphs(file_name, node_count, num_graphs, start, stop, step)



    
