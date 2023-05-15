#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
import csv
import argparse
import configparser
import graphviz

import binascii
import struct


class NetworkAnalysis:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--file", type=str, help="CSV file with network data")
        self.args = parser.parse_args()

        self.df = None
        self.file = self.args.file

    def find_communications(self):
        df = pd.read_csv(os.path.join(self.config['PATHS']['project_dir'],
                                      self.config['NETWORK']['data_dir'],
                                      self.file))

        # comm2 = self.df[['src', 'dst']].drop_duplicates().to_numpy()
        comm = df[['src', 'dst']].drop_duplicates().values.tolist()
        req = df[['src', 'dst', 'SCADA_Tag']].drop_duplicates().values.tolist()
        print(req)
        plc_comm_dir = list()
        for i in comm[:]:
            for j in comm[:]:
                if j == i:
                    continue

                if sorted(j) == sorted(i):
                    # print(i, j)
                    plc_comm_dir.append((sorted(j), 'b'))
                    comm.remove(j)
                    comm.remove(i)
                    break
        if len(comm) > 0:
            for x in comm:
                plc_comm_dir.append((x, 'u'))

        print(plc_comm_dir)
        return plc_comm_dir

    def draw_network_diagram(self, plc_comm):
        dot = graphviz.Digraph(name=f'Network Diagram',
                               node_attr={'color': 'lightblue2', 'style': 'rounded, filled',
                                          'shape': 'box', 'fontsize': '10'},
                               edge_attr={'fontfamily': 'Courier', 'fontsize': '8'},
                               format='png',
                               directory='graphs')
        dot.attr(rankdir='LR')


def main():
    na = NetworkAnalysis()
    na.find_communications()


if __name__ == '__main__':
    main()
