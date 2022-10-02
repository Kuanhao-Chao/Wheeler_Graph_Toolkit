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



    f, ax = plt.subplots(figsize=(6, 6), dpi=300)
    labels = ["De Bruijn WGs (DNA)", "De Bruijn WGs (Protein)", "Trie WGs (DNA)", "Trie WGs (Protein)", "Reverse Deterministic Graphs (DNA)", "Reverse Deterministic Graphs (Protein)", "Random WGs"]
    idx = 0
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
        xs_filter = xs[xs < 60000000]
        ys_filter = ys[xs < 60000000]
        log_xs = [math.log10(x) for x in xs_filter]
        log_ys = [math.log10(y) for y in ys_filter]
        print(log_xs)
        print(log_ys)



        ax.set_xlabel(r'G & T recognizer time ($\log_{10} \mu s$)')
        ax.set_ylabel(r'WGT recognizer time ($\log_{10} \mu s$)')
        ax.scatter(log_xs, log_ys, alpha=0.5, label=labels[idx])
        idx += 1

    add_identity(ax, color='r', ls='--')
    # ax.set_aspect('equal', adjustable='box')
    xlim = ax.get_xlim()
    # plt.setp(ax, xlim=xlim, ylim=xlim)
    plt.legend()
    # plt.show()

    # plt.scatter(log_xs, log_ys, alpha=0.5)
    # # for agg_times, label in all_times:
    # #     plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
    # plt.gca().set_aspect('equal', adjustable='box')
    # # ax.set_aspect('equal', adjustable='box')
    # plt.show()
    plt.savefig(os.path.join("Figure_1.png"), format="PNG")

if __name__ == "__main__":
    main()