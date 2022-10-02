from posixpath import basename
import sys
import matplotlib 
from matplotlib import pyplot as plt
import itertools
import os
import numpy as np
import pandas as pd

marker = itertools.cycle(('+', 'o', '*', '-'))
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
        # print("times: ", times)
        # print("ns: ", ns)
        # print("es: ", es)
        # print("ls: ", ls)
        # print("densities: ", densities)
        all_vars.append((times, ns, es, ls, densities))


# # gtype = os.path.basename(os.path.dirname(sys.argv[1]))
# gtype = "smt__p_converged"

# # p = re.compile(sys.argv[1])
# result = re.search("test_grp[0-9]*", sys.argv[1])
# if not result:
#     test_case = "original_betterconcat"


font = {'size'   : 8}
matplotlib.rc('font', **font)
# fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(8, 6), dpi=300, gridspec_kw={'height_ratios': [4, 1]})

# ax[0].set_xlabel('Label group density')
ax[0].set_ylabel(r'WGT recognizer time ($\mu s$)')
ax[1].set_xlabel('Label group density')
ax[1].set_ylabel(r'Number of timeout cases')
counter = 0
for times, ns, es, ls, densities in all_vars:
    scatters = ax[0].scatter(densities, times, label=next(labels), marker=next(marker), alpha=0.6)
    # print(times)
    df = pd.DataFrame({'densities': densities, 'times': times})
    df["timeout"] = df['times'] == 2000000000.0
    df = df.groupby(densities).sum()
    df['densities'] = np.unique(densities)
    print(df)
    w = 60
    bars = ax[1].bar(df['densities']+w*counter-w/2, df['timeout'], label=next(labels), width = w)
    ax[1].bar_label(bars, fontsize=6)
    ax[1].margins(y=0.2)
    counter += 1


handles, labels = ax[1].get_legend_handles_labels()
fig.legend(handles, ["SMT", "Permutation"], loc='upper center')
plt.savefig(os.path.join("per_vs_smt__exp1_density.png"), format="PNG")

# python plot_exp1.py ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/smt/results/parsed_all_controlled_RD_exp1_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/permutation/results/parsed_all_controlled_RD_exp1_out.txt