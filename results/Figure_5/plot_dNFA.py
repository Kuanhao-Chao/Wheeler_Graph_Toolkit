from posixpath import basename
import sys
from matplotlib import pyplot as plt
import itertools
import os
import re
import numpy as np

marker = itertools.cycle(('o', '*'))
labels = itertools.cycle(('Permutation'))
all_vars = []

for file in sys.argv[1:]:
    with open(file, 'r') as f:
        lines = f.read().splitlines() 
        # print(lines)
        ans = np.array([float(line.split("\t")[0]) for line in lines])
        selector = np.array(ans)== 1.0

        times =  np.array([float(line.split("\t")[2]) for line in lines])[selector]
        ns = np.array([float(line.split("\t")[4]) for line in lines])[selector]
        es = np.array([float(line.split("\t")[5]) for line in lines])[selector]
        ls = np.array([float(line.split("\t")[6]) for line in lines])[selector]
        densities = np.array([float(line.split("\t")[7]) for line in lines])[selector]
        ds = np.array([float(line.split("\t")[8]) for line in lines])[selector]

        # print("times: ", times)
        # print("ns: ", ns)
        # print("es: ", es)
        # print("ls: ", ls)
        # print("densities: ", densities)
        all_vars.append((ans, times, ns, es, ls, densities, ds))


plt.figure(figsize=(8, 6), dpi=300)

plt.xlabel(r'$d$-NFA')
plt.ylabel(r'WGT recognizer time ($\mu s$)')
for ans, times, ns, es, ls, densities, ds in all_vars:
    plt.scatter(ds, times, label=next(labels), marker=next(marker))
    # plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
plt.legend()
# plt.show()
plt.savefig(os.path.join("per__dNFA.png"), format="PNG")
# plt.savefig(os.path.join("per_vs_smt__dNFA.png"), format="PNG")

# python plot_exp1.py ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/smt/results/parsed_all_controlled_RD_exp1_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/permutation/results/parsed_all_controlled_RD_exp1_out.txt