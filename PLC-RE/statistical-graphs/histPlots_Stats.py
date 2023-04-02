#!/usr/bin/env python3

import pandas as pd
import os
import configparser
import argparse
import matplotlib.pyplot as plt
from scipy.stats import shapiro
from scipy.stats import chisquare


class HistoryPlotStats:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", type=str, default=self.config['DEFAULTS']['dataset_file'],
                            help="name of the input dataset file (CSV format)")
        parser.add_argument('-r', "--register", type=str, required=True, help="register to plot")

        self.args = parser.parse_args()

        self.filename = self.args.filename.split('/')[-1]
        self.register = self.args.register

        self.df = pd.read_csv(os.path.join(self.config['PATHS']['project_dir'],
                                           self.config['DAIKON']['daikon_invariants_dir'],
                                           self.filename))

    def chi_squared_uniformity(self):
        print(f"Chi-squared test for uniformity")

        dataSets = [[x for x in self.df[str(self.register)] if str(x) != 'nan']]
        print(f"{'Distance':^12} {'pvalue':^12} {'Uniform?':^8}")

        for ds in dataSets:
            dist, pvalue = chisquare(ds)
            uni = 'YES' if pvalue > 0.05 else 'NO'
            print(f"{dist:12.3f} {pvalue:12.8f} {uni:^8} ")

        print()

    def shapiro_wilk_normality(self):
        print(f"Shapiro-Wilk test for normality")

        shapiro_test = shapiro([x for x in self.df[str(self.register)] if str(x) != 'nan'])
        norm = ' YES' if shapiro_test.pvalue > 0.05 else 'NO'
        stats = shapiro_test.statistic
        print(f"{'Test statistic':^12} {'pvalue':^12} {'Normal?':^8}")
        print(f"{stats:12.3f} {shapiro_test.pvalue:12.8f} {norm:^8} ")

        print()

    def more_stats(self):
        size = len(self.df)
        data = [x for x in self.df[str(self.register)] if str(x) != 'nan']
 
        mn = sum(data) / size
        sd = (sum(x*x for x in data) / size
              - (sum(data) / size) ** 2) ** 0.5

        print(f"Stats of " + str(self.register))
        print("Sample mean = %g; Stddev = %g; max = %g; min = %g for %i values" % (mn, sd, max(data), min(data), size))
        print()

        return data

    def hist_plot(self, data):
        plt.hist(data, bins='auto', color='blue', alpha=0.7, rwidth=0.85)

        plt.xlabel(str(self.register))
        plt.ylabel('Frequency')
        plt.show()


def main():
    hps = HistoryPlotStats()
    hps.chi_squared_uniformity()
    hps.shapiro_wilk_normality()
    data = hps.more_stats()
    hps.hist_plot(data)


if __name__ == '__main__':
    main()
