from bad_generator import generateBadWG
import os
import sys

#remove any old samples in the directory


# y = 0.0252x^2 + 0.226x + 6.2819
def calc_node_num(num):
    """Function to determine how many nodes the generator should 
    call the networkx graph generation function with, in order to 
    obtain the approximately the number of nodes the user entered """
    return (0.0252 * (num ** 2)) + (.226 * num) + 6.2819

if (len(sys.argv) != 5):
  print("Not enough arguments: provide input and output file names")
else: 
    file_path = sys.argv[1]

    # dir = file_path
    # for f in os.listdir(dir):
    #     os.remove(os.path.join(dir, f))

    num_graphs = int(sys.argv[2]) #number of samples
    node_count = int(sys.argv[3]) #number of nodes
    total_partitions = int(sys.argv[4])

    if not os.path.exists(file_path):
        os.makedirs(file_path)

    for i in range(total_partitions):
        partition_path = file_path + '/partition' + str(i)
        if not os.path.exists(partition_path):
            os.makedirs(partition_path)

        for j in range(num_graphs):
            filename = partition_path + "/test_"  + str(j) + ".dot"
            num_nodes = int(calc_node_num(node_count))

            #Function parameters described below:
            #generateWG(num_nodes, edge_prob, print_graph?, filename, random_nodes?)
            generateBadWG(num_nodes,.2, False, filename, False, total_partitions, int(i))
            # print("Done with graph " + str(j))
        print("Done with partition: " + str(i))