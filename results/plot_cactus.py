import sys
from matplotlib import pyplot as plt
import itertools

marker = itertools.cycle(('+', 'o', '*')) 
all_times = []

for file in sys.argv[1:]:
    with open(file, 'r') as f:
        lines = f.readlines()
        times = [float(line.split()[2]) for line in lines]
        print("times: ", times)

    sorted_times = sorted(times)

    agg_times = [ sorted_times[0] ]
    for i in range(1, len(sorted_times)):
        agg_times.append(agg_times[i-1] + sorted_times[i])

    all_times.append((agg_times, file))



plt.xlabel('# of instances')
plt.ylabel('time (msec)')
for agg_times, label in all_times:
    plt.plot(range(len(agg_times)), agg_times, label=label, marker=next(marker))
plt.legend()
plt.show()
