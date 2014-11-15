import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import sys

infile = sys.argv[1]
outimg = sys.argv[2]


tab = pd.read_csv(infile, index_col=0)
tab.index
per_hour = len(tab.columns) / 24

plt.figure(figsize=(6, 10))
plt.pcolor(tab.values)
plt.axes()
plt.gca().invert_yaxis()
xticks = np.arange(0, per_hour*24, per_hour)
plt.xticks(xticks, tab.columns[xticks], rotation='vertical')
yticks = np.arange(0, len(tab.index), 2)
plt.yticks(yticks, tab.index[yticks])
plt.savefig(outimg, dpi=300, bbox_inches='tight')
