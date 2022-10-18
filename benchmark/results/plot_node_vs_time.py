from posixpath import basename
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
    all_vars.append((nodes, times, basename(file)))

# gtype = os.path.basename(os.path.dirname(sys.argv[1]))
gtype = "smt__p_converged"

# p = re.compile(sys.argv[1])
result = re.search("test_grp[0-9]*", sys.argv[1])
if not result:
    test_case = "original_betterconcat"
plt.figure(figsize=(12, 6), dpi=300)

plt.xlabel('# of nodes')
plt.ylabel('time (msec)')



for nodes, times, label in all_vars:
    plt.scatter(nodes, times, label=label, marker=next(marker))
    # plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
plt.legend()
# plt.show()
plt.savefig(os.path.join(gtype, test_case+"_node_vs_time_plot.png"), format="PNG")
# plt.savefig(os.path.join(gtype, "p_vs_e_node_vs_time_plot.png"), format="PNG")
# plt.savefig(os.path.join(gtype, test_case+"_node_vs_time_plot.png"), format="PNG")