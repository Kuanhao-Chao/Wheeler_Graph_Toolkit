import sys
from matplotlib import pyplot as plt
import itertools
import os
import re

marker = itertools.cycle(('+', 'o', '*'))
all_times = []

for file in sys.argv[1:]:
    with open(file, 'r') as f:
        lines = f.readlines()
        times = [float(line.split()[2]) for line in lines]

    sorted_times = sorted(times)

    agg_times = [ sorted_times[0] ]
    for i in range(1, len(sorted_times)):
        agg_times.append(agg_times[i-1] + sorted_times[i])

    all_times.append((agg_times, file))

gtype = "smt__p_converged"
# os.path.basename(os.path.dirname(sys.argv[1]))

# p = re.compile(sys.argv[1])
result = re.search("test_grp[0-9]*", sys.argv[1])
test_case = result.group()
print(test_case)
plt.figure(figsize=(12, 6), dpi=300)

plt.xlabel('# of instances')
plt.ylabel('time (msec)')
for agg_times, label in all_times:
    plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
plt.legend()
# plt.show()
plt.savefig(os.path.join(gtype, test_case+"_cactus_plot.png"), format="PNG")
