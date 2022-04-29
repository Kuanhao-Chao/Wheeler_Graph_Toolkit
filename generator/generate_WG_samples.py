from generator import generateWG
import os
import sys

# y = 0.0252x^2 + 0.226x + 6.2819
def calc_node_num(num):
    """Function to determine how many nodes the generator should 
    call the networkx graph generation function with, in order to 
    obtain the approximately the number of nodes the user entered """
    return (0.0252 * (num ** 2)) + (.226 * num) + 6.2819

def generateSingle(file_path, num_graphs, node_count):
    for i in range(num_graphs):
        filename = file_path + "/test_"  + str(i) + ".dot"
        num_nodes = int(calc_node_num(node_count))

        #Function parameters described below:
        #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
        generateWG(num_nodes,.2, False, filename, False)

def generateMultiple(file_path, num_graphs, start, stop, step):
    node_count = start
    num_iter = int((stop-start) / step + 1)
    #make graphs from 5 to 80 nodes
    for _ in range(num_iter):
        graph_path = file_path + '/' +str(node_count) + 'nodes'
        if not os.path.exists(graph_path):
            os.makedirs(graph_path)

        for j in range(num_graphs):
            filename = graph_path + "/test_"  + str(j) + ".dot"
            num_nodes = int(calc_node_num(node_count))

            #Function parameters described below:
            #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
            generateWG(num_nodes,.2, False, filename, False, None, None)
        node_count = node_count + step
        

def generateMultipleRandom(file_path, num_graphs, start, stop, step):
    node_count = start
    num_iter = int((stop-start) / step + 1)
    #make graphs from 5 to 80 nodes
    for _ in range(num_iter):
        graph_path = file_path + '/' +str(node_count) + 'nodes'
        if not os.path.exists(graph_path):
            os.makedirs(graph_path)
            os.makedirs(graph_path + "/before_shuffle")
            os.makedirs(graph_path + "/after_shuffle")

        for j in range(num_graphs):
            filename = graph_path + "/test_"  + str(j) + ".dot"
            num_nodes = int(calc_node_num(node_count))

            #Function parameters described below:
            #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
            generateWG(num_nodes,.2, False, filename, True, graph_path, j)
        node_count = node_count + step


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


if __name__ == "__main__":
    if(len(sys.argv) != 4 and len(sys.argv) != 6 and len(sys.argv) != 7):
        print("Incorrect number of arguments. Please run as one the following arguments:\n" +
  "python3 generate_WG_samples.py [folder for samples] [number of samples] [node count]\n" + 
  "python3 generate_WG_samples.py [folder for samples] [number of samples] [start_node] [stop_node] [step] [-r (optional)] \n")

    file_path = sys.argv[1]

    if(len(sys.argv) == 4):
        num_graphs = int(sys.argv[2])
        nodes_in_graph = int(sys.argv[3])
        path = makeFilePath(file_path)
        generateSingle(path, num_graphs, nodes_in_graph)

    # if(len(sys.argv) == 6):
    else:
        num_graphs = int(sys.argv[2])
        start = int(sys.argv[3])
        stop = int(sys.argv[4])
        step = int(sys.argv[5])
        if((stop-start) % step != 0 or start > stop or step < 1 or start < 0):
            print("Please enter valid start, stop, and step increments")
        else:
            path = makeFilePath(file_path)
            if(len(sys.argv)) == 6:
                generateMultiple(path, num_graphs, start, stop, step)
            elif (len(sys.argv) == 7):
                generateMultipleRandom(path, num_graphs, start, stop, step)

