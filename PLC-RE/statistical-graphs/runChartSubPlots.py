#!/usr/bin/env python3

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
        parser.add_argument('-f', "--filename", type=str, help="CSV file to analyze")
        parser.add_argument('-r', "--registers", nargs='+', default=[], help="registers to include", required=True)
        self.args = parser.parse_args()

        self.filename = self.config['DEFAULTS']['dataset_file']
        self.registers = [r for r in self.args.registers]

        self.colors = ["blue", "red", "limegreen", "orange", "cyan", "magenta", "black"]

        self.ax = {}
        self.line = {}

    def check_args(self):
        if self.args.filename is not None:
            self.filename = self.args.filename

    def make_plot(self, dataframe, grdspec, registers, index):
        if index > 0:
            self.ax[index] = plt.subplot(grdspec[index], sharex=self.ax[index - 1])
        else:
            self.ax[index] = plt.subplot(grdspec[index])

        self.line[index], = self.ax[index].plot(pd.DataFrame(dataframe, columns=[str(registers[index])]),
                                                label=str(registers[index]),
                                                color=self.colors[index % (len(self.colors))])
        plt.grid()

        self.ax[index].legend(loc='lower left')


def main():
    rcsp = RunChartsSubPlots()
    rcsp.check_args()

    df = pd.read_csv(f'../daikon/Daikon_Invariants/{rcsp.filename}')

    fig = plt.figure()
    gs = gridspec.GridSpec(len(rcsp.registers), 1)

    for x in range(0, len(rcsp.registers)):
        rcsp.make_plot(df, gs, rcsp.registers, x)

    plt.subplots_adjust(hspace=.0)
    plt.xlabel("Time")
    plt.show()


if __name__ == '__main__':
    main()
