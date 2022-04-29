from bad_generator import generateBadWG
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

def generateGraphs(file_path, num_graphs, start, stop, step):
    node_count = start
    num_iter = int((stop-start) / step + 1)
    for i in range(num_iter):
        node_path = file_path + '/nodes' + str(node_count)
        if not os.path.exists(node_path):
            os.makedirs(node_path)

        for j in range(num_graphs):
            filename = node_path + "/test_"  + str(j) + ".dot"
            num_nodes = int(calc_node_num(node_count))

            #Function parameters described below:
            #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
            generateBadWG(num_nodes,.2, False, filename, False, 7, 4)
        node_count = node_count + step

if (len(sys.argv) != 6):
  print("Incorrect number of arguments. Please enter the following arguments:\n" +
  "python3 generate_bad_WG_samples.py [output folder] [number of samples] [start_node] [stop_node] [step]")
else: 
    file_path = sys.argv[1]
    num_graphs = int(sys.argv[2]) #number of samples
    start = int(sys.argv[3]) #number of nodes
    stop = int(sys.argv[4])
    step = int(sys.argv[5])
    path = makeFilePath(file_path)
    generateGraphs(path, num_graphs, start, stop, step)