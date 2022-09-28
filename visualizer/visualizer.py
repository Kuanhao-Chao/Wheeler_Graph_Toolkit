# from turtle import color
import networkx as nx
import matplotlib.pyplot as plt
import getopt
import sys
import random
import os

USAGE = '''usage: visualizer.py [-h] [-v] [-o / --ofile FILE] Valid WG DOT file'''
random.seed(1)
color_default = ["blue", "red", "green", "orange"]

# Return nodes as z3 Ints
def parse(inputfile):
    nodes = set()
    edges = []
    has_incoming_edge = set()
    global G
    G = nx.DiGraph(nx.nx_pydot.read_dot(inputfile))
    nodes= set(int(node) for node in list(G.nodes()) if node != '\\n')
    edges = [(int(u), int(v), attr['label']) 
            for (u, v, attr) in G.edges(data=True)]

    edge_labels= list(set(list(zip(*edges))[2]))
    edge_labels.sort()
    # edges = sorted(edges, key = lambda x: (x[2], x[0], x[1]))

    for (u, v, l) in edges:
        has_incoming_edge.update([v])
    return nodes, edges, edge_labels, has_incoming_edge

def main(argv):
    ##############################
    ## Parsing arguments
    ##############################
    # Default parameters:
    k = 3
    verbose = False
    outputdir = "./"
    try:
        opts, args = getopt.getopt(argv,"hvo:",["ofile="])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(USAGE)
            sys.exit()
        elif opt == '-v':
            verbose = True
        elif opt in ("-o", "--ofile"):
            outputdir = arg
    
    if not os.path.exists(outputdir):
        print("Output directory does not exist!")
        outputdir = "./"
        
    if len(args) == 0:
        print(USAGE)
        print("Please input one valid WG in DOT file")
        sys.exit(2)

    nodes, edges, edge_labels, has_incoming_edge = parse(args[0])

    print(">> Visualizing ...")
    node_num = len(nodes)
    figure_width = node_num*0.9
    f = plt.figure(figsize=(figure_width, 6), dpi=300)
    ax = f.add_subplot(1,1,1)
    color_coding = {x: color_default[idx] if idx < 4 else "#"+str(hex(random.randint(0,16777215))[2:]) for idx, x in enumerate(edge_labels)}
    print("colors: ", color_coding)
    
    for label, color in color_coding.items():
        ax.plot([0],[0],color=color,label=label)

    G=nx.DiGraph()
    x_pos = 0
    for node in nodes:
        G.add_node(str(node)+"_o",pos=(x_pos,1))
        G.add_node(str(node)+"_i",pos=(x_pos,0))
        x_pos += 1

    options = {
        "node_size": 1200,
        "node_color": "#b9ddeb",
        "width": 2,
        "font_weight": "bold",
        "with_labels": True,
    }
    for edge in edges:
        print("edge: ", edge)
        G.add_edge(str(edge[0])+"_o", str(edge[1])+"_i", color=color_coding[edge[2]])

    pos=nx.get_node_attributes(G,'pos')
    edge_colors = nx.get_edge_attributes(G,'color').values()

    nx.draw(G,pos, edge_color=edge_colors, **options)
    # Setting it to how it was looking before.
    plt.axis('off')
    f.set_facecolor('w')

    plt.legend(fontsize="x-large")
    f.tight_layout()
    # plt.show()
    # if outputfile == "":
    #     defualt_outfile=os.path.splitext(inputfile[4:])[0]+".png"
    #     plt.savefig(defualt_outfile, format="PNG")
    # else:
    outputfile = "Human_STAU2_orthologues_DNA_k_2_l_4_a_4.png"
    plt.savefig(outputfile, format="PNG")

if __name__ == "__main__":
    main(sys.argv[1:])