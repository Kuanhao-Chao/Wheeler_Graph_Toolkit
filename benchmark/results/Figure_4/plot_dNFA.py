from posixpath import basename
import sys
from turtle import color
from matplotlib import pyplot as plt
import matplotlib 
import itertools
import os
import pandas as pd
import numpy as np
import matplotlib.transforms as mtransforms


marker = itertools.cycle(('+', 'o', '*'))

labels = itertools.cycle(('Wheelie-SMT', 'Wheelie-Pr'))
all_vars = []
colors = ['cornflowerblue', 'orange']

for file in sys.argv[1:]:
    print("file: ", file)
    with open(file, 'r') as f:
        lines = f.read().splitlines() 
        # print(lines)
        ans = np.array([float(line.split("\t")[0]) for line in lines])
        # selector = np.array(ans)== 1.0

        times =  np.array([float(line.split("\t")[2]) for line in lines])
        ns = np.array([float(line.split("\t")[4]) for line in lines])
        es = np.array([float(line.split("\t")[5]) for line in lines])
        ls = np.array([float(line.split("\t")[6]) for line in lines])
        densities = np.array([float(line.split("\t")[7]) for line in lines])
        ds = np.array([float(line.split("\t")[8]) for line in lines])

        print("times: ", times)
        # print("ns: ", ns)
        # print("es: ", es)
        # print("ls: ", ls)
        # print("densities: ", densities)
        all_vars.append((ans, times, ns, es, ls, densities, ds))



font = {'size'   : 13}
matplotlib.rc('font', **font)

fig, axs = plt.subplot_mosaic([['A'],['A_2']], constrained_layout=True, figsize=(12, 6), dpi=300, gridspec_kw={'height_ratios': [4.5, 1]})

ax_counter = 0
# for label, ax in axs.items():
#     # if ax_counter == 3: break
#     # label physical distance to the left and up:
#     trans = mtransforms.ScaledTranslation(-35/72, 17/72, fig.dpi_scale_trans)
#     print(trans)
#     if ax_counter == 0:
#         ax.text(0.0, 1.0, label, transform=ax.transAxes + trans,
#                 fontsize=30, va='bottom', fontfamily='serif', fontweight='bold')
#     ax_counter += 1

axis_fontsize=12
axs['A'].set_ylabel(r'recognition time ($\mu s$)', labelpad=26, fontsize=axis_fontsize)
axs['A_2'].set_ylabel(r'Timeout count', labelpad=28, fontsize=axis_fontsize)
counter = 0
timeout_line_handle = None


for idx, (ans, times, ns, es, ls, densities, ds) in enumerate(all_vars):
    df = pd.DataFrame({'ds': ds, 'times': times})
    df["timeout"] = df['times'] > 1000000000.0

    df['times'] = np.where(df.times > 1000000000.0, 1010000000.0, df.times)
    print(df['times'])
    # = df['times'] .replace([2000000000.0], 1010000000.0)

    axs['A'].scatter(df['ds'], df['times'], label=next(labels), marker=next(marker))

    # color = axs['A'].get_color()

    timeout_line_handle = axs['A'].axhline(y=1000000000.0, color='red', linestyle='--')

    df_sum = df.groupby(ds).sum()
    df_median = df.groupby(ds).median()

    df_sum['ds_uniq'] = np.unique(ds)
    df_median['ds_uniq'] = np.unique(ds)

    axs['A'].plot(df_median['ds_uniq'], df_median['times'], label=next(labels), marker='.')
    # , color=colors[idx])

    # axs['A'].fill_between(df_median['ds_uniq'], df_median['times'], 0, alpha=0.2)
    # , color=colors[idx])



    w = 0.15
    # print(idx)
    # print(df['ds_uniq']+w*(idx)-w/2)
    bars = axs['A_2'].bar(df_sum['ds_uniq']+w*(idx)-w/2, df_sum['timeout'], label=next(labels), width = w)
    # , color=colors[idx])

    axs['A_2'].bar_label(bars, fontsize=9)
    axs['A_2'].margins(y=0.3)
    axs['A_2'].set_xlabel(r'$d$', labelpad=15, fontsize=axis_fontsize)
    # axs['A'].set_title(r'', pad = 50, fontsize=axis_fontsize, loc='left')
    axs['A'].set_title(r'Fix $n = 1000$, $e = 3000, \sigma = 4$', pad = 50, fontsize=axis_fontsize, loc='left')
handles, labels = axs['A'].get_legend_handles_labels()
print("handles: ", handles)
handles.append(timeout_line_handle)
fig.legend(handles, ['Wheelie-SMT', 'Wheelie-SMT median', 'Wheelie-Pr', 'Wheelie-Pr median', '1000-second timeout line'], loc='upper right', bbox_to_anchor=(1, 1.0097), ncol=3)

# plt.show()
plt.savefig(os.path.join("Figure_4.pdf"), format="PDF")
# plt.savefig(os.path.join("per_vs_smt__dNFA.png"), format="PNG")

# python plot_dNFA.py ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_dNFA/results/parsed_RHSMT_out.txt ../../unit_test/RHPer_vs_RHSMT/Timeout_test/RandomG_dNFA/results/parsed_RHPer_out.txt