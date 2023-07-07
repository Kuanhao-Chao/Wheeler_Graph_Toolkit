from posixpath import basename
import sys
import matplotlib 
from matplotlib import pyplot as plt
import itertools
import os
import numpy as np
import pandas as pd
import matplotlib.transforms as mtransforms

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

bar_font = 7
axis_fontsize = 14
top_padding = 20
font = {'size'   : 14}
matplotlib.rc('font', **font)
# fig, axs = plt.subplots(figsize=(8, 6), dpi=300)

fig, axs = plt.subplot_mosaic([['A', 'B', 'C'],['A_2','B_2','C_2']], constrained_layout=True, figsize=(18, 6), dpi=300, gridspec_kw={'height_ratios': [4.5, 1]})

ax_counter = 0
for label, ax in axs.items():
    if ax_counter == 3: break
    # label physical distance to the left and up:
    trans = mtransforms.ScaledTranslation(-35/72, 17/72, fig.dpi_scale_trans)
    print(trans)
    ax.text(0.0, 1.0, label, transform=ax.transAxes + trans,
            fontsize=30, va='bottom', fontfamily='serif', fontweight='bold')
    ax_counter += 1

# fig, axs = plt.subplots(nrows=2, ncols=3, figsize=(22, 6), dpi=300, gridspec_kw={'height_ratios': [4.5, 1]}, sharey='row')

axs['A'].set_ylabel(r'recognition time ($\mu s$)', labelpad=26, fontsize=axis_fontsize)
axs['A_2'].set_ylabel(r'Timeout count', labelpad=28, fontsize=axis_fontsize)
counter = 0

timeout_line_handle=""
for times, ns, es, ls, densities in all_vars:
    idx = counter // 2
    if (idx == 0):
        # scatters = axs[0][idx].scatter(ns, times, label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        df = pd.DataFrame({'ns': ns, 'times': times})
        df["timeout"] = df['times'] == 2000000000.0
        df['times'] = df['times'].replace([2000000000.0], 1010000000.0)
        scatters = axs['A'].scatter(ns, df['times'], label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        axs['A'].axhline(y=1000000000.0, color='red', linestyle='--')
        df = df.groupby(ns).sum()
        df['ns_uniq'] = np.unique(ns)
        print(df)
        w = 130
        bars = axs['A_2'].bar(df['ns_uniq']+w*(counter-idx*2)-w/2, df['timeout'], label=next(labels), width = w)
        axs['A_2'].bar_label(bars, fontsize=bar_font)
        axs['A_2'].margins(y=0.25)
        axs['A_2'].set_xlabel(r'Number of nodes', labelpad=18, fontsize=axis_fontsize)
        axs['A'].set_title(r'Fix $e = 8000$, $\sigma = 4$', pad = top_padding, fontsize=axis_fontsize)
    elif idx == 1:
        df = pd.DataFrame({'densities': densities, 'times': times})
        df["timeout"] = df['times'] == 2000000000.0
        df['times'] = df['times'].replace([2000000000.0], 1010000000.0)
        scatters = axs['B'].scatter(densities, df['times'], label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        timeout_line_handle = axs['B'].axhline(y=1000000000.0, color='red', linestyle='--')
        df = df.groupby(densities).sum()
        df['densities_uniq'] = np.unique(densities)
        print(df)
        w = 60
        bars = axs['B_2'].bar(df['densities_uniq']+w*(counter-idx*2)-w/2, df['timeout'], label=next(labels), width = w)
        axs['B_2'].bar_label(bars, fontsize=bar_font)
        axs['B_2'].margins(y=0.25)
        axs['B_2'].set_xlabel(r'Label Density ($e / \sigma$)', labelpad=18, fontsize=axis_fontsize)
        axs['B'].set_title(r'Fix $n = 4000$, $e = 20000$', pad = top_padding, fontsize=axis_fontsize)
    elif idx == 2:
        e_min = min(es)
        es_ratio = np.array(es)/e_min
        print(es_ratio)

        # print(times)
        df = pd.DataFrame({'es_ratio': es_ratio, 'times': times})
        df["timeout"] = df['times'] == 2000000000.0
        df['times'] = df['times'].replace([2000000000.0], 1010000000.0)
        scatters = axs['C'].scatter(es_ratio, df['times'], label=next(labels), marker=markers[counter - 2*idx], alpha=0.6)
        axs['C'].axhline(y=1000000000.0, color='red', linestyle='--')
        df = df.groupby(es_ratio).sum()
        df['es_ratio_uniq'] = np.unique(es_ratio)
        print(df)
        w = 0.45
        bars = axs['C_2'].bar(df['es_ratio_uniq']+w*(counter-idx*2)-w/2, df['timeout'], label=next(labels), width = w)

        axs['C_2'].bar_label(bars, fontsize=bar_font)
        axs['C_2'].margins(y=0.25)
        axs['C_2'].set_xlabel(r'$\sigma / \sigma_{min} ratio$', labelpad=18, fontsize=axis_fontsize)
        axs['C'].set_title(r'Fix $n = 2000$, $e / \sigma = 2000$', pad = top_padding, fontsize=axis_fontsize)

    counter += 1

# plt.setp(axs[:, 0], ylabel='y axis label')

handles, labels = axs['A'].get_legend_handles_labels()
print("handles: ", handles)
handles.append(timeout_line_handle)
fig.legend(handles, ["Wheelie-SMT", "Wheelie-Pr", "Timeout line"], loc='center right', bbox_to_anchor=(0.995,0.7), ncol=1)
# fig.text(0.5, 0.04, 'common xlabel', ha='center', va='center')
plt.savefig(os.path.join("Figure_5.pdf"), format="PDF")


# python plot_exp_all.py ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/smt/results/parsed_all_controlled_RD_exp1_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/permutation/results/parsed_all_controlled_RD_exp1_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/smt/results/parsed_all_controlled_RD_exp2_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/permutation/results/parsed_all_controlled_RD_exp2_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/smt/results/parsed_all_controlled_RD_exp3_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_e_n_l__merged/permutation/results/parsed_all_controlled_RD_exp3_out.txt
