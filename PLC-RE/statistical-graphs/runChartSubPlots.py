#!/usr/bin/env python3

from array import array
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import argparse

from matplotlib import gridspec

parser = argparse.ArgumentParser()
parser.add_argument('-f', "--filename", type=str, help="CSV file to analyze")
parser.add_argument('-r', "--registers", nargs='+', default=[], help="registers to include")
args = parser.parse_args()

if args.filename != None:
  filename = args.filename
else:
  filename = 'PLC_SWaT_Dataset.csv'

registers = [r for r in args.registers]

colors=["blue", "red", "limegreen", "orange", "cyan", "magenta", "black"]
ax={}
line={}

fig = plt.figure()
gs = gridspec.GridSpec(len(registers), 1)

df = pd.read_csv(f'../daikon/Daikon_Invariants/{filename}')

for x in range(0,len(registers)):
  if x > 1:
    ax[x] = plt.subplot(gs[x], sharex=ax[x-1])
  else:
    ax[x] = plt.subplot(gs[x])

  line[x], = ax[x].plot(pd.DataFrame(df,columns=[str(registers[x])]), label=str(registers[x]), color=colors[(x) % (len(colors))])
  plt.grid()

  ax[x].legend(loc='lower left')

plt.subplots_adjust(hspace=.0)
plt.xlabel("Time")
plt.show()
