from array import array
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import statistics

#df = pd.read_csv('../daikon/Daikon_Invariants/PLC_Dataset.csv')
df = pd.read_csv('../daikon/Daikon_Invariants/PLC_SWaT_Dataset.csv')

for x in range(1,len(sys.argv)):
  plt.plot(pd.DataFrame(df,columns=[str(sys.argv[x])]), label=str(sys.argv[x]))
  plt.legend(loc='best', bbox_to_anchor = (0.5, 1.1))

plt.grid()
plt.xlabel("Time")
plt.show()
