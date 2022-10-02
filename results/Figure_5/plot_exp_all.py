from posixpath import basename
import sys
import matplotlib 
from matplotlib import pyplot as plt
import itertools
import os
import numpy as np
import pandas as pd

markers = ['+', 'o', '*']
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

bar_font = 5
axis_fontsize = 11
top_padding = 20
font = {'size'   : 8}
matplotlib.rc('font', **font)
# fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
fig, ax = plt.subplots(nrows=2, ncols=3, figsize=(22, 6), dpi=300, gridspec_kw={'height_ratios': [4.5, 1]}, sharey='row')

# ax[0].set_xlabel('Label group density')
ax[0][0].set_ylabel(r'WGT recognizer time ($\mu s$)', labelpad=12, fontsize=axis_fontsize)
# ax[1].set_xlabel('Label group density')
ax[1][0].set_ylabel(r'Timeout case count', labelpad=18, fontsize=axis_fontsize)
counter = 0

timeout_line_handle=""
for times, ns, es, ls, densities in all_vars:
    idx = counter // 2
    if (idx == 0):
        # scatters = ax[0][idx].scatter(ns, times, label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        df = pd.DataFrame({'ns': ns, 'times': times})
        df["timeout"] = df['times'] == 2000000000.0
        df['times'] = df['times'].replace([2000000000.0], 1000000000.0)
        scatters = ax[0][idx].scatter(ns, df['times'], label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        ax[0][idx].axhline(y=1000000000.0, color='red', linestyle='--')
        df = df.groupby(ns).sum()
        df['ns_uniq'] = np.unique(ns)
        print(df)
        w = 130
        bars = ax[1][idx].bar(df['ns_uniq']+w*(counter-idx*2)-w/2, df['timeout'], label=next(labels), width = w)
        ax[1][idx].bar_label(bars, fontsize=bar_font)
        ax[1][idx].margins(y=0.2)
        ax[1][idx].set_xlabel(r'Number of nodes', labelpad=18, fontsize=axis_fontsize)
        ax[0][idx].set_title(r'Fix $e = 8000$, $\sigma = 4$', pad = top_padding, fontsize=axis_fontsize)
    elif idx == 1:
        df = pd.DataFrame({'densities': densities, 'times': times})
        df["timeout"] = df['times'] == 2000000000.0
        df['times'] = df['times'].replace([2000000000.0], 1000000000.0)
        scatters = ax[0][idx].scatter(densities, df['times'], label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        timeout_line_handle = ax[0][idx].axhline(y=1000000000.0, color='red', linestyle='--')
        df = df.groupby(densities).sum()
        df['densities_uniq'] = np.unique(densities)
        print(df)
        w = 60
        bars = ax[1][idx].bar(df['densities_uniq']+w*counter-w/2, df['timeout'], label=next(labels), width = w)
        ax[1][idx].bar_label(bars, fontsize=bar_font)
        ax[1][idx].margins(y=0.2)
        ax[1][idx].set_xlabel(r'Label Density ($e / \sigma$)', labelpad=18, fontsize=axis_fontsize)
        ax[0][idx].set_title(r'Fix $n = 4000$, $e = 20000$', pad = top_padding, fontsize=axis_fontsize)
    elif idx == 2:
        e_min = min(es)
        es_ratio = np.array(es)/e_min
        print(es_ratio)

        # scatters = ax[0][idx].scatter(es_ratio, times, label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        # print(times)
        df = pd.DataFrame({'es_ratio': es_ratio, 'times': times})
        df["timeout"] = df['times'] == 2000000000.0
        df['times'] = df['times'].replace([2000000000.0], 1000000000.0)
        scatters = ax[0][idx].scatter(es_ratio, df['times'], label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        ax[0][idx].axhline(y=1000000000.0, color='red', linestyle='--')
        df = df.groupby(es_ratio).sum()
        df['es_ratio_uniq'] = np.unique(es_ratio)
        print(df)
        w = 0.45
        bars = ax[1][idx].bar(df['es_ratio_uniq']+w*(counter-idx*2)-w/2, df['timeout'], label=next(labels), width = w)

        ax[1][idx].bar_label(bars, fontsize=bar_font)
        ax[1][idx].margins(y=0.2)
        ax[1][idx].set_xlabel(r'$\sigma / \sigma_{min} ratio$', labelpad=18, fontsize=axis_fontsize)
        ax[0][idx].set_title(r'Fix $n = 2000$, $e / \sigma = 2000$', pad = top_padding, fontsize=axis_fontsize)

    counter += 1

# plt.setp(ax[:, 0], ylabel='y axis label')

handles, labels = ax[1][0].get_legend_handles_labels()
print("handles: ", handles)
handles.append(timeout_line_handle)
fig.legend(handles, ["SMT", "Permutation", "Timeout line"], loc='upper right', bbox_to_anchor=(0.9,0.99))
# fig.text(0.5, 0.04, 'common xlabel', ha='center', va='center')
plt.savefig(os.path.join("per_vs_smt__exp_all.png"), format="PNG")


# python plot_exp_all.py ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/smt/results/parsed_all_controlled_RD_exp1_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/permutation/results/parsed_all_controlled_RD_exp1_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/smt/results/parsed_all_controlled_RD_exp2_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/permutation/results/parsed_all_controlled_RD_exp2_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/smt/results/parsed_all_controlled_RD_exp3_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/permutation/results/parsed_all_controlled_RD_exp3_out.txt