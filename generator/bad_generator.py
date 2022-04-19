import networkx as nx
from graphviz import Source
import string
import random
from itertools import islice
from checker import checker
import math


def cond1(G):
    # Fix graph for condition 1: all zero in degree nodes come before others
    zeroes = sorted(list(G.in_degree(G.nodes())))
    zerol = []
    nonzero = []
    for node, indeg in zeroes:
        if indeg == 0:
            zerol.append(node)
        else:
            nonzero.append(node)

    # print(zerol)
    # print(nonzero)

    # nx.drawing.nx_pydot.write_dot(G, "before_swap.dot")
    if len(zerol) != 0: 
        num = len(zerol)
        d = dict()
        count = 0
        for i in zerol:
            d[i] = count
            count += 1

        for i in range(len(nonzero)):
            d[nonzero[i]] = num
            num += 1

        # print(d)
        # map the old nodes to the new ones
        G = nx.relabel_nodes(G, d, copy=True)
    
    # nx.drawing.nx_pydot.write_dot(G, "after_swap.dot")
    return G 

def cond2(G, Gn):
    # Generate the alphabet for the labels
    alphabet_string = list(string.ascii_lowercase)

    edges = list(G.edges(data=True))
    num_chars = len(edges) / 4
    if num_chars < 1:
        num_chars = 1
    chars = alphabet_string[:int(num_chars)] 

    # Fix graph for condition 2
    # Add a check that # of edges is > than # of alphabet characters
    # Add edge labels
    edges = list(Gn.edges())
    edges.sort(key=lambda x: x[1])

    # Find out the length for the partitions
    num_edges = len(edges)
    alp_size = len(chars)
    step_size = math.floor(len(edges) / alp_size)
    leftover = (num_edges - step_size * (alp_size - 1))

    # Create the partitions for assigning labels
    length_to_split = []
    for i in range(alp_size - 1):
        length_to_split.append(step_size)
    length_to_split.append(leftover)

    Inputt = iter(edges)
    l = [list(islice(Inputt, elem))
         for elem in length_to_split]

    # for i in l:
    #     print(i)
    # Create a new filtered list that will shift items based on
    # if they violate condition 2
    filtered_list = [set() for i in range(len(l))]
    # by default the first partition won't violate anything bc no prev partition
    seen = set()
    for i in range(len(l)):
        # get the highest node for that partition
        for tuple in l[i]:
            if tuple not in seen:
                filtered_list[i].add(tuple)
                seen.add(tuple)
        max_out_node = l[i][-1][1]
        # check the subsequent partitions
        for j in range(i + 1, len(l)):
            for tuple in l[j]:
                # if the node matches, pull in down to the current partition
                if tuple[1] == max_out_node and tuple not in seen:
                    filtered_list[i].add(tuple)
                    seen.add(tuple)

    # Assign labels to edges based on partitions we defined
    l = filtered_list
    # print("\n")
    # for i in l:
    #   print(i)

    labels = {}
    count = 0
    for i in l:
        for edge in i:
            u = edge[0]
            v = edge[1]
            tempmap = {"label": chars[count]}
            labels[(u, v)] = tempmap
        count += 1
    nx.set_edge_attributes(Gn, labels)


def cond3(G):
    # Fix graph for condition 3. Remove any edge that violates condition 3
    edges = list(G.edges(data=True))
    d = {}
    for u, v, edge in edges:
        label = edge["label"]
        if label in d:
            l = d.get(label)
            l.append((u, v))
        else:
            d[label] = [(u, v)]

    for k, v in d.items():
        max = 0
        for out, ind in sorted(v):
            if int(ind) < int(max):
                G.remove_edge(out, ind)
            if int(ind) > int(max):
                max = ind

def redoCondOne(G):
    # FIXING NEW CASES OF ZERO IN DEGREE
    highest_zero_node = -1
    zeroes = sorted(list(G.in_degree(G.nodes())))
    zerol = []
    stop = False
    for node, indeg in zeroes:
        if indeg == 0 and not stop:
            zerol.append(int(node))
            highest_zero_node = node
        elif indeg == 0:
            zerol.append(int(node))
        else:
            stop = True

    to_delete = list(filter(lambda high: high > highest_zero_node, zerol))
    
    # count = 0 

    while (len(to_delete) > 0):
        # nx.drawing.nx_pydot.write_dot(G, ("print" + str(count) + ".dot"))
        for node in to_delete:
            G.remove_node(node)

        zeroes = sorted(list(G.in_degree(G.nodes())))
        zerol = []
        stop = False
        for node, indeg in zeroes:
            if indeg == 0 and not stop:
                zerol.append(int(node))
                highest_zero_node = node
            elif indeg == 0:
                zerol.append(int(node))
            else:
                stop = True

        to_delete = list(filter(lambda high: high > highest_zero_node, zerol))
        # count = count + 1
    
    # print(list(G.edges(data=True)))
    # nx.drawing.nx_pydot.write_dot(G, ("print" + str(count) + ".dot"))


def makeBad(G):
    edges = list(G.edges(data=True))
    d = {}
    for u, v, edge in edges:
        label = edge["label"]
        if label in d:
            l = d.get(label)
            l.append((u, v))
        else:
            d[label] = [(u, v)]

    alphabet = list(sorted(d.keys()))
    alphabet_size = len(alphabet)
    
    # print(alphabet)
    partition_selected = 3
    partitions = 8

    if(alphabet_size/partitions < 1):
        # sys.exit("ERROR: too many partitions for alphabet size")
        return

    split_alphabet = list(split(alphabet, partitions))
    # print(split_alphabet)

    mutate_range = split_alphabet[partition_selected]
    mutate_index = random.randint(0,len(mutate_range)-1)
    mutate_letter = mutate_range[mutate_index]
    # print(mutate_letter)

    # print(d[mutate_letter])
    edge_to_alter_index = random.randint(0,len(d[mutate_letter])-1)
    edge_to_alter = d[mutate_letter][edge_to_alter_index]
    start = edge_to_alter[0]
    end = edge_to_alter[1]
    G.remove_edge(start, end)

    random_node = list(G.nodes())[random.randint(0,len(list(G.nodes()))-1)]
    # print(list(G.nodes()))
    # print(random_node)
    G.add_edge(start, random_node, label=mutate_letter)
    # print(start, end)

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def generateBadWG(num_nodes, edge_prob, visualize, output_file, randomize):

    #Create a correct random graph
    G = nx.gnp_random_graph(num_nodes, edge_prob, directed=True)
    Gn = cond1(G)
    cond2(G,Gn)
    cond3(Gn)
    redoCondOne(Gn)

    # edit one of the edges at a particular partition to violate conditions 
    makeBad(Gn)

    # Check the graph to ensure a condition was violated
    output_file_samples = "bad_samples" + output_file
    nx.drawing.nx_pydot.write_dot(Gn, output_file_samples)
    con1, con2, con3 = checker(output_file_samples)

    # continue producing graphs until an incorrect one is produced
    while con2 and con3:
        makeBad(Gn)
        nx.drawing.nx_pydot.write_dot(Gn, output_file_samples)
        _, con2, con3 = checker(output_file_samples)
        
    print(str(con1) + str(con2) + str(con3))

    #if this option is selected, the graph pdf will be opened
    if visualize:
        s = Source.from_file(output_file)
        print(s.view())

    #if this option is selected, the node labels will be shuffled 
    #and converted to strings
    #For testing purposes, the valid graph before the node shuffle will be 
    #stored, along with the new shuffled graph
    if randomize: 
        output_file_before = "before_shuffle"  + output_file
        nx.drawing.nx_pydot.write_dot(Gn, output_file_before)
        num_nodes = len(Gn.nodes())
        new_list = list(range(0,num_nodes))
        random.shuffle(new_list)
        
        string_list = []
        for i in new_list:
            val = "S" + str(i)
            string_list.append(val)

        new_labels = {}
        curr_nodes = list(Gn.nodes)
        for i in curr_nodes:
            new_labels[i] = string_list.pop(0)

        Gn = nx.relabel_nodes(Gn, new_labels)
        output_file_after = "after_shuffle" + output_file
        nx.drawing.nx_pydot.write_dot(Gn, output_file_after)