from bad_generator import generateBadWG
import os
import sys

#remove any old samples in the directory
dir = 'bad_samples'
for f in os.listdir(dir):
    os.remove(os.path.join(dir, f))

# y = 0.0252x^2 + 0.226x + 6.2819
def calc_node_num(num):
    """Function to determine how many nodes the generator should 
    call the networkx graph generation function with, in order to 
    obtain the approximately the number of nodes the user entered """
    return (0.0252 * (num ** 2)) + (.226 * num) + 6.2819

if (len(sys.argv) != 3):
  print("Not enough arguments: provide input and output file names")
else: 
    num_graphs = int(sys.argv[1]) #number of samples
    node_count = int(sys.argv[2]) #number of nodes

    for i in range(num_graphs):
        filename = "/test_"  + str(i) + ".dot"
        num_nodes = int(calc_node_num(node_count))

        #Function parameters described below:
        #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
        generateBadWG(num_nodes,.2, False, filename, False)