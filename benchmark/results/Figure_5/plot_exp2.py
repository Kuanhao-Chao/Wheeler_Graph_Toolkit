from posixpath import basename
import sys
from matplotlib import pyplot as plt
import itertools
import os
import re

marker = itertools.cycle(('+', 'o', '*'))
labels = itertools.cycle(('SMT', 'Permutation'))
all_vars = []

for file in sys.argv[1:]:
    with open(file, 'r') as f:
        lines = f.read().splitlines() 
        # print(lines)
        times = [float(line.split("\t")[2]) for line in lines]
        ns = [float(line.split("\t")[4]) for line in lines]
        es = [float(line.split("\t")[5]) for line in lines]
        ls = [float(line.split("\t")[6]) for line in lines]
        densities = [float(line.split("\t")[7]) for line in lines]
        print("times: ", times)
        print("ns: ", ns)
        print("es: ", es)
        print("ls: ", ls)
        print("densities: ", densities)
        all_vars.append((times, ns, es, ls, densities))


# # gtype = os.path.basename(os.path.dirname(sys.argv[1]))
# gtype = "smt__p_converged"

# # p = re.compile(sys.argv[1])
# result = re.search("test_grp[0-9]*", sys.argv[1])
# if not result:
#     test_case = "original_betterconcat"


plt.figure(figsize=(8, 6), dpi=300)

plt.xlabel('Graph size')
plt.ylabel(r'WGT recognizer time ($\mu s$)')
for times, ns, es, ls, densities in all_vars:
    plt.scatter(ns, times, label=next(labels), marker=next(marker), alpha=0.6)
    # plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
plt.legend()
# plt.show()
plt.savefig(os.path.join("per_vs_smt__exp2_graphsize.png"), format="PNG")

# python plot_exp2.py ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/smt/results/parsed_all_controlled_RD_exp2_out.txt  ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/permutation/results/parsed_all_controlled_RD_exp2_out.txt