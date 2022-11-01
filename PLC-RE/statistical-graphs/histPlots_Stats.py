#!/usr/bin/env python3

import pandas as pd
import sys
import matplotlib.pyplot as plt
from scipy.stats import shapiro
from scipy.stats import chisquare

df = pd.read_csv('../daikon/Daikon_Invariants/PLC_SWaT_Dataset.csv')

print(f"Chi-squared test for uniformity")
if __name__ == '__main__':
    dataSets = [[x for x in df[str(sys.argv[1])] if str(x) != 'nan']]
    print(f"{'Distance':^12} {'pvalue':^12} {'Uniform?':^8}")
    for ds in dataSets:
        dist, pvalue = chisquare(ds)
        uni = 'YES' if pvalue > 0.05 else 'NO'
        print(f"{dist:12.3f} {pvalue:12.8f} {uni:^8} ")

print("\n \n")
print(f"Shapiro-Wilk test for normality")
shapiro_test = shapiro([x for x in df[str(sys.argv[1])] if str(x) != 'nan'])
norm = ' YES' if shapiro_test.pvalue > 0.05 else 'NO'
stats = shapiro_test.statistic
print(f"{'Test statistic':^12} {'pvalue':^12} {'Normal?':^8}")
print(f"{stats:12.3f} {shapiro_test.pvalue:12.8f} {norm:^8} ")

print("\n \n")


size = len(df)
data = [x for x in df[str(sys.argv[1])] if str(x) != 'nan']
 
mn = sum(data) / size
sd = (sum(x*x for x in data) / size 
      - (sum(data) / size) ** 2) ** 0.5
print(f"Stats of " + str(sys.argv[1]))
print("Sample mean = %g; Stddev = %g; max = %g; min = %g for %i values" 
      % (mn, sd, max(data), min(data), size))
 
n, bins, bars = plt.hist(data,bins='auto',color='blue', alpha=0.7, rwidth=0.85)

'''
for i in range(len(bins)-1):
  plt.text(bins[i]+4,n[i]+15,str(int(bins[i])))
'''

plt.xlabel(str(sys.argv[1]))
plt.ylabel('Frequency')
plt.show()
