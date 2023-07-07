import sys
from time import time
from matplotlib import pyplot as plt
import itertools
import os
import numpy as np
import math
import matplotlib.transforms as mtransforms

markers = ['+', 'o', '*']
colors = itertools.cycle(('blue', 'green', 'red', 'magenta'))
all_times = []

for file in sys.argv[1:]:
    with open(file, 'r') as f:
        lines = f.readlines()
        nodes = [float(line.split()[1]) for line in lines]
        times = [float(line.split()[2]) for line in lines]

    indices = sorted(range(len(times)), key=lambda k:times[k])

    print(indices)

    sorted_times = [times[idx] for idx in indices]
    # sorted_nodes = [nodes[idx] for idx in indices]

    agg_times = [ sorted_times[0] ]

    for i in range(1, len(sorted_times)):
        agg_times.append(agg_times[i-1] + sorted_times[i])

    all_times.append((agg_times, sorted_times, file))

# os.path.basename(os.path.dirname(sys.argv[1]))

# p = re.compile(sys.argv[1])
# result = re.search("test_grp[0-9]*", sys.argv[1])
# test_case = result.group()
# test_case = "random_graph"
# print(test_case)
# fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(23, 6), dpi=300)

fig, axs = plt.subplot_mosaic([['A', 'B']], constrained_layout=True, figsize=(20, 6), dpi=300)

fig.subplots_adjust(left=0.05, right=0.88) # or whatever

for label, ax in axs.items():
    # label physical distance to the left and up:
    trans = mtransforms.ScaledTranslation(-45/72, 17/72, fig.dpi_scale_trans)
    print(trans)
    ax.text(0.0, 1.0, label, transform=ax.transAxes + trans,
            fontsize=30, va='bottom', fontfamily='serif', fontweight='bold')

# axs['A'].set_xlabel('Label group density')
axs['A'].set_ylabel(r'Accumulated recognition time ($\mu s$)', labelpad=12, fontsize=15)
axs['B'].set_ylabel(r'Accumulated recognition time ($\mu s$)', labelpad=12, fontsize=15)
# ax[1].set_xlabel('Label group density')
# ax[1].set_ylabel(r'Timeout case count', labelpad=18, fontsize=axis_fontsize)
counter = 0
times_pre = None
for agg_times, times, label in all_times:
    idx = counter//2
    nodes = np.array(nodes)
    if idx == 0:
        ax_id = 'A'
        log_agg_times = [math.log10(x) for x in agg_times]

        axs[ax_id].plot(range(len(agg_times)), agg_times, label=label, marker=markers[1])

        # axs[ax_id].bar(range(len(agg_times)), nodes*1000000)
        # , label=label, marker=markers[1])

        axs[ax_id].set_title(r'De Bruijn graph (DNA alignments)', pad=18, fontsize=15)
        axs[ax_id].set_xlabel(r'Number of instances', fontsize=15, labelpad=16)
        # if counter == 1:
        #     ax2 = axs[ax_id].twinx()
        #     times_diff = [(ele1 - ele2) for (ele1, ele2) in zip(times, times_pre)]
        #     ax2.plot(range(len(agg_times)), times_diff, 'b-')
        #     ax2.fill_between(range(len(agg_times)), times_diff, 0, alpha=0.2)
        #     # , label=label, marker=markers[1])
    elif idx == 1:
        ax_id = 'B'
        log_agg_times = [math.log10(x) for x in agg_times]

        axs[ax_id].plot(range(len(agg_times)), agg_times, label=label, marker=markers[1])
        axs[ax_id].set_title(r'Reverse deterministic graph' '\n' r'(DNA alignments)', pad=10, fontsize=15)
        axs[ax_id].set_xlabel(r'Number of instances', fontsize=15, labelpad=16)
        # if counter == 3:
        #     ax2 = axs[ax_id].twinx()
        #     times_diff = [(ele1 - ele2) for (ele1, ele2) in zip(times, times_pre)]
        #     ax2.plot(range(len(agg_times)), times_diff)
        #     # , label=label, marker=markers[1])
    times_pre = times

    counter += 1


handles, labels = axs['A'].get_legend_handles_labels()
print("handles: ", handles)
# handles.append(timeout_line_handle)
fig.legend(handles, ["Wheelie-SMT", "Pure SMT"], loc='center right', prop={'size': 15}, ncol=1)
# , bbox_to_anchor=(0.99,1)
plt.savefig(os.path.join("Figure_6.pdf"), format="PDF")

#python plot_cactus.py ../../unit_test/SMT_vs_RHSMT/Timeout_test/DeBruijnG_AA/results/30_DB_AA_restrict_out.txt ../../unit_test/SMT_vs_RHSMT/Timeout_test/DeBruijnG_AA/results/30_DB_AA_full_out.txt ../../unit_test/SMT_vs_RHSMT/Timeout_test/RevDetG_AA/results/30_RD_AA_restrict_out.txt  ../../unit_test/SMT_vs_RHSMT/Timeout_test/RevDetG_AA/results/30_RD_AA_full_out.txt

#python plot_cactus.py ../../unit_test/SMT_vs_RHSMT/Timeout_test/DeBruijnG_DNA/results/DB_DNA_restrict_out.txt ../../unit_test/SMT_vs_RHSMT/Timeout_test/DeBruijnG_DNA/results/DB_DNA_full_out.txt ../../unit_test/SMT_vs_RHSMT/Timeout_test/RevDetG_DNA/results/RD_DNA_restrict_out.txt  ../../unit_test/SMT_vs_RHSMT/Timeout_test/RevDetG_DNA/results/RD_DNA_full_out.txt