from generator import generateWG
import math
import os
import sys

#remove any old samples in the directory
# dir = 'samples'
# for f in os.listdir(dir):
#     os.remove(os.path.join(dir, f))

# y = 0.0252x^2 + 0.226x + 6.2819
def calc_node_num(num):
    """Function to determine how many nodes the generator should 
    call the networkx graph generation function with, in order to 
    obtain the approximately the number of nodes the user entered """
    return (0.0252 * (num ** 2)) + (.226 * num) + 6.2819

# if (len(sys.argv) != 3):
#   print("Not enough arguments: provide input and output file names")
# else: 
#     num_graphs = int(sys.argv[1]) #number of samples
#     node_count = int(sys.argv[2]) #number of nodes

#     for i in range(num_graphs):
#         filename = "/test_"  + str(i) + ".dot"
#         num_nodes = int(calc_node_num(node_count))

#         #Function parameters described below:
#         #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
#         generateWG(num_nodes,.2, False, filename, False)

if (len(sys.argv) != 3):
  print("Not enough arguments: provide input and output file names")
else: 
    file_path = sys.argv[1]

    num_graphs = int(sys.argv[2]) #number of samples

    if not os.path.exists(file_path):
        os.makedirs(file_path)
    edge_prob = .05

    #make graphs with 60 nodes from .05 to .4 edge prob
    for i in range(10):
        graph_path = file_path + '/' + str(format(float(edge_prob), '.2f')) + 'edge_prob'
        if not os.path.exists(graph_path):
            os.makedirs(graph_path)

        for j in range(num_graphs):
            filename = graph_path + "/test_"  + str(j) + ".dot"
            print(filename)
            num_nodes = int(calc_node_num(60))

            #Function parameters described below:
            #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
            generateWG(num_nodes, float(edge_prob), False, filename, False)
            # print("Done with graph " + str(j))
        print("Done with graphs: " + str(edge_prob) + '\n')
        edge_prob = format(math.fsum((float(edge_prob), .05)), '.2g')
        
