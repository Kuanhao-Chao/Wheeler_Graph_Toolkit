import sys
from matplotlib import pyplot as plt
import itertools
import os
import re
import math
import numpy as np

def add_identity(ax=None, ls='--', *args, **kwargs):
    # see: https://stackoverflow.com/q/22104256/3986320
    ax = ax or plt.gca()
    identity, = ax.plot([], [], ls=ls, *args, **kwargs)
    def callback(axes):
        low_x, high_x = ax.get_xlim()
        low_y, high_y = ax.get_ylim()
        low = min(low_x, low_y)
        high = max(high_x, high_y)
        print("low: ", low)
        print("high: ", high)
        identity.set_data([low, high], [low, high])
    callback(ax)
    ax.callbacks.connect('xlim_changed', callback)
    ax.callbacks.connect('ylim_changed', callback)
    return ax

def main():
    marker = itertools.cycle(('+', 'o', '*'))
    all_times = []


    f, ax = plt.subplots(figsize=(6, 6), dpi=300, constrained_layout=True)
    labels = [u"Random Wheeler graphs", u"De Bruijn graphs (DNA)", u"De Bruijn graphs (Protein)", u"Tries (DNA)", u"Tries (Protein)", u"Pseudo-De Bruijn graphs (DNA)", u"Pseudo-De Bruijn graphs (Protein)", u"Reverse deterministic graphs (DNA)", u"Reverse deterministic graphs (Protein)"]
    idx = 0
    timeout_padding = 4000000
    timeout = 30000000
    for arg in sys.argv[1:]:
        xs = []
        ys = []
        with open(arg+"/GT_out.txt", 'r') as f:
            lines = f.readlines()
            xs = np.array([float(line.split()[2]) for line in lines])

        with open(arg+"/WGT_out.txt", 'r') as f:
            lines = f.readlines()
            ys = np.array([float(line.split()[2]) for line in lines])

        print(xs)
        xs[xs == 60000000] = timeout + timeout_padding
        ys[ys == 60000000] = timeout + timeout_padding

        # xs_filter = xs[xs < 60000000]
        # ys_filter = ys[xs < 60000000]

        # xs_filter = xs
        # ys_filter = ys
        
        timeout_line_handle = ax.axvline(x=math.log10(timeout), color='red', linestyle='--')
        ax.axhline(y=math.log10(timeout), color='red', linestyle='--')


        log_xs = [math.log10(x) for x in xs]
        log_ys = [math.log10(y) for y in ys]
        print(log_xs)
        print(log_ys)



        ax.set_xlabel(r'G & T algorithm recognition time ($\log_{10} \mu s$)')
        ax.set_ylabel(r'Wheelie-Pr exhaustive search recognition time ($\log_{10} \mu s$)')
        ax.scatter(log_xs, log_ys, alpha=0.5, label=labels[idx])
        # ax.scatter(xs_filter, ys_filter, alpha=0.5, label=labels[idx])
        idx += 1

    add_identity(ax, color='gray', ls='--')
    ax.set_aspect('equal', adjustable='box')
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()


    plt.setp(ax, xlim=ylim, ylim=ylim)


    handles, labels = ax.get_legend_handles_labels()
    print("handles: ", handles)
    handles.append(timeout_line_handle)
    labels.append("30-second timeout line")
    ax.legend(handles, labels, loc='upper right', bbox_to_anchor=[0.56, 0.93],prop={'size': 9})

    # plt.legend()
    # plt.show()

    # plt.scatter(log_xs, log_ys, alpha=0.5)
    # # for agg_times, label in all_times:
    # #     plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
    # plt.gca().set_aspect('equal', adjustable='box')
    # # ax.set_aspect('equal', adjustable='box')
    # plt.show()
    plt.savefig(os.path.join("Figure_1.pdf"), format="PDF")

if __name__ == "__main__":
    main()

# python plot_solvers.py ../../unit_test/GT_vs_WGT/Timeout_test/RandomG/results/ ../../unit_test/GT_vs_WGT/Timeout_test/DeBruijnG_DNA/results/ ../../unit_test/GT_vs_WGT/Timeout_test/DeBruijnG_AA/results/ ../../unit_test/GT_vs_WGT/Timeout_test/Trie_DNA/results/ ../../unit_test/GT_vs_WGT/Timeout_test/Trie_AA/results/ ../../unit_test/GT_vs_WGT/Timeout_test/DeBruijnGNC_DNA/results ../../unit_test/GT_vs_WGT/Timeout_test/DeBruijnGNC_AA/results ../../unit_test/GT_vs_WGT/Timeout_test/RevDetG_DNA/results/ ../../unit_test/GT_vs_WGT/Timeout_test/RevDetG_AA/results/