import sys
from matplotlib import pyplot as plt
import itertools
import os
import re

marker = itertools.cycle(('+', 'o', '*'))
all_vars = []

for file in sys.argv[1:]:
    with open(file, 'r') as f:
        lines = f.readlines()
        nodes = [float(line.split()[1]) for line in lines]
        times = [float(line.split()[2]) for line in lines]
    all_vars.append((nodes, times, file))

gtype = os.path.basename(os.path.dirname(sys.argv[1]))

# p = re.compile(sys.argv[1])
# result = re.search("test_grp[0-9]*", sys.argv[1])
# test_case = result.group()
# print(result.group[0])
plt.rcParams['font.size'] = '16'
plt.figure(figsize=(8, 6), dpi=300)

plt.xlabel('# of nodes', fontsize=18)
plt.ylabel('time (msec)', fontsize=18)


for nodes, times, label in all_vars:
    # if "permutation_algo" in label:
    #     label_algo = "Permutation Algorithm"
    # elif "exponential_algo" in label:
    #     label_algo = "Gibney & Thankachan's Algorithm"  
    if "protein" in label:
        label_algo = "Protein alignment"
    else:
        label_algo = "DNA alignment"
    plt.scatter(nodes, times, label=label_algo, marker=next(marker), s=40)
    # plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
plt.legend()
# plt.show()
# plt.savefig(os.path.join(gtype, test_case+"_node_vs_time_plot.png"), format="PNG")
plt.savefig(os.path.join(gtype, "p_DNA_vs_Protein_time_plot.png"), format="PNG")
