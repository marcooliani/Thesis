#!/usr/bin/env python3

import os
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import configparser

from matplotlib import gridspec


class RunChartsSubPlots:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", type=str,
                            default=self.config['PREPROC']['dataset_file'], help="CSV file to analyze")
        parser.add_argument('-r', "--registers", nargs='+', help="registers to include", required=False)
        parser.add_argument('-e', "--excluderegisters", nargs='+', help="registers to exclude", required=False)
        parser.add_argument('-a', "--addregisters", nargs='+', help="registers to add", required=False)
        self.args = parser.parse_args()

        self.filename = self.args.filename

        self.df = pd.read_csv(f'{os.path.join(self.config["PATHS"]["project_dir"], self.config["DAIKON"]["daikon_invariants_dir"], self.filename)}')

        if self.args.registers:
            self.registers = [r for r in self.args.registers]
        else:
            df_cols = list(self.df.columns)
            registers = [x for x in df_cols if not x.startswith(self.config['DATASET']['max_prefix'])
                         and not x.startswith(self.config['DATASET']['min_prefix'])
                         and not x.startswith(self.config['DATASET']['prev_cols_prefix'])
                         and not x.startswith(self.config['DATASET']['slope_cols_prefix'])]

            if self.args.excluderegisters:
                for i in self.args.excluderegisters:
                    registers.remove(i)

            if self.args.addregisters:
                for i in self.args.addregisters:
                    registers.append(i)

            self.registers = registers

        self.colors = ["blue", "red", "limegreen", "orange", "cyan", "magenta", "black"]

        self.ax = {}
        self.line = {}

    def make_plot(self, grdspec, registers, index):
        if index > 0:
            self.ax[index] = plt.subplot(grdspec[index], sharex=self.ax[index - 1])
        else:
            self.ax[index] = plt.subplot(grdspec[index])

        self.line[index], = self.ax[index].plot(pd.DataFrame(self.df, columns=[str(registers[index])]),
                                                label=str(registers[index]),
                                                color=self.colors[index % (len(self.colors))])
        plt.grid()

        self.ax[index].legend(loc='lower left')


def main():
    rcsp = RunChartsSubPlots()

    gs = gridspec.GridSpec(len(rcsp.registers), 1)

    for x in range(0, len(rcsp.registers)):
        rcsp.make_plot(gs, rcsp.registers, x)

    plt.subplots_adjust(hspace=.0)
    plt.xlabel("Time (seconds)")
    plt.show()


if __name__ == '__main__':
    main()
