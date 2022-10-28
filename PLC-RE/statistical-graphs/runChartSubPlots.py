#!/usr/bin/env python3

from array import array
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys

from matplotlib import gridspec

colors=["blue", "red", "limegreen", "orange", "cyan", "magenta", "black"]
ax={}
line={}

fig = plt.figure()
gs = gridspec.GridSpec(len(sys.argv)-1, 1)

df = pd.read_csv('../daikon/Daikon_Invariants/PLC_SWaT_Dataset.csv')

for x in range(1,len(sys.argv)):
  if x > 1:
    ax[x-1] = plt.subplot(gs[x-1], sharex=ax[x-2])
  else:
    ax[x-1] = plt.subplot(gs[x-1])

  line[x-1], = ax[x-1].plot(pd.DataFrame(df,columns=[str(sys.argv[x])]), label=str(sys.argv[x]), color=colors[(x-1) % (len(colors))])
  plt.grid()

  ax[x-1].legend(loc='lower left')

plt.subplots_adjust(hspace=.0)
plt.xlabel("Time")
plt.show()
