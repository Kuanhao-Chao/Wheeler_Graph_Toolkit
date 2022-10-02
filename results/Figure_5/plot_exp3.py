from posixpath import basename
import sys
import matplotlib 
from matplotlib import pyplot as plt
import itertools
import os
import numpy as np
import pandas as pd

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


# plt.figure(figsize=(8, 6), dpi=300)

# plt.xlabel(r'$\dfrac{\sigma}{\sigma_{base}} (\dfrac{e}{e_{base}}) ratio$')
# plt.ylabel(r'WGT recognizer time ($\mu s$)')
# for times, ns, es, ls, densities in all_vars:
#     e_min = min(es)
#     es_ratio = np.array(es)/e_min
#     plt.scatter(es_ratio, times, label=next(labels), marker=next(marker), alpha=0.6)
#     # plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
# plt.legend()
# # plt.show()
# plt.savefig(os.path.join("per_vs_smt__exp3_sigmaratio.png"), format="PNG")



font = {'size'   : 8}
matplotlib.rc('font', **font)
# fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(8, 6), dpi=300, gridspec_kw={'height_ratios': [3, 1]})

# ax[0].set_xlabel('Label group density')
ax[0].set_ylabel(r'WGT recognizer time ($\mu s$)')
ax[1].set_xlabel('Label group density')
ax[1].set_ylabel(r'Number of timeout cases')
counter = 0
for times, ns, es, ls, densities in all_vars:
    e_min = min(es)
    es_ratio = np.array(es)/e_min
    print(es_ratio)

    scatters = ax[0].scatter(es_ratio, times, label=next(labels), marker=next(marker), alpha=0.6)
    # print(times)
    df = pd.DataFrame({'es_ratio': es_ratio, 'times': times})
    df["timeout"] = df['times'] == 2000000000.0
    df = df.groupby(es_ratio).sum()
    df['es_ratio_uniq'] = np.unique(es_ratio)
    print(df)
    w = 0.3
    # bars = ax[1].bar(df['es_ratio']+1*counter-0.5, df['timeout'], label=next(labels), width = 1)
    bars = ax[1].bar(df['es_ratio_uniq']+w*counter-w/2, df['timeout'], label=next(labels), width = w)

    ax[1].bar_label(bars, fontsize=6)
    ax[1].margins(y=0.2)
    counter += 1


handles, labels = ax[1].get_legend_handles_labels()
fig.legend(handles, ["SMT", "Permutation"], loc='upper center')
plt.savefig(os.path.join("per_vs_smt__exp3_sigmaratio.png"), format="PNG")

# python plot_exp3.py  ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/smt/results/parsed_all_controlled_RD_exp3_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_controlled_test_e_n_l/permutation/results/parsed_all_controlled_RD_exp3_out.txt