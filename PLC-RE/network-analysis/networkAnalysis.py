#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
import argparse
import configparser
import glob
import graphviz
import pygraphviz as pgv  # apt-get install graphviz graphviz-dev
from PIL import Image


class NetworkAnalysis:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--file", type=str, help="CSV file with network data")
        parser.add_argument('-d', "--directory", type=str, help="CSV files with network data")
        self.args = parser.parse_args()

        self.df = None
        self.file = self.args.file
        if self.args.directory:
            self.directory = self.args.directory
        else:
            self.directory = os.path.join(self.config['PATHS']['project_dir'],
                                          self.config['NETWORK']['split_dir'])

    def merge_datasets(self):
        df_list = list()
        df_files = glob.glob(os.path.join(self.directory, '*.csv'))

        for file in sorted(df_files):
            tmp = pd.read_csv(file)
            df_list.append(tmp)

        df = pd.concat(df_list, axis=0).reset_index(drop=True)
        print(df)
        return df

    def find_communications(self):
        if self.args.directory:
            df = self.merge_datasets()

        else:
            df = pd.read_csv(os.path.join(self.config['PATHS']['project_dir'],
                                          self.config['NETWORK']['data_dir'],
                                          self.file))

        # comm2 = self.df[['src', 'dst']].drop_duplicates().to_numpy()
        comm = df[['src', 'dst', 'protocol', 'service_detail', 'register']].drop_duplicates().values.tolist()
        plc_comm_dir = list()
        for c in comm:
            c = ['missing data' if x is np.nan else x for x in c]
            plc_comm_dir.append(c)

        print("\n".join(map(str, plc_comm_dir)))
        return plc_comm_dir

    @staticmethod
    def draw_network_diagram(plc_comm):
        G = pgv.AGraph(strict=False, directed=True)
        G.graph_attr["label"] = "Communication Network diagram"
        G.graph_attr["fontsize"] = "12"
        G.graph_attr["format"] = "svg"
        # G.graph_attr["size"] = "15,20!"
        # G.graph_attr["ratio"] = "expand"
        G.node_attr["shape"] = "box"
        G.node_attr["color"] = "lightblue2"
        G.node_attr["style"] = "rounded, filled"
        G.node_attr["fontsize"] = "10"
        G.edge_attr["fontfamily"] = "Courier"
        G.edge_attr["fontsize"] = "8"

        for plc in plc_comm:
            src = plc[0]
            dst = plc[1]
            protocol = plc[2]
            service = plc[3]
            register = plc[4]

            arrow_style = "solid"
            color = "black"
            labelfontcolor = "black"

            #if register == "missing data":
            if "missing data" in register:
                arrow_style = "dotted"
                color = "dimgrey"
                labelfontcolor = "dimgrey"

            #if service == "Request":
            if "Request" in service:
                color = "red"

            G.add_node(src, label=src)
            G.add_node(dst, label=dst)
            G.add_edge(src, dst, label=f'{protocol} {service}\n{register}', style=arrow_style, color=color,
                       labelfontcolor=labelfontcolor)

        G.unflatten("-f -l 200")
        G.layout(prog="dot")
        G.draw(f'data/network.svg')
        #G.draw(f'data/network.png')
        #G.draw(f'/tmp/network.png')

        #img = Image.open('/tmp/network.png')
        #img.show()

    @staticmethod
    def draw_network_diagram_OLD(plc_comm):

        dot = graphviz.Digraph(name=f'Network Diagram',
                               node_attr={'color': 'lightblue2', 'style': 'rounded, filled',
                                          'shape': 'box', 'fontsize': '10'},
                               edge_attr={'fontfamily': 'Courier', 'fontsize': '8'},
                               format='svg',
                               engine='dot',
                               directory='graphs')
        dot.attr(rankdir='LR')
        arrow_style = "solid"

        for plc in plc_comm:
            src = plc[0]
            dst = plc[1]
            protocol = plc[2]
            service = plc[3]
            register = plc[4]

            if register == "missing data":
                arrow_style = "dotted"

            dot.node(src, f'{src}')  # Creo nodo
            dot.node(dst, f'{dst}')  # Creo nodo
            dot.edge(src, dst, f'{protocol} {service}\n{register}', style=arrow_style)

        dot.unflatten(stagger=8)
        dot.view()


def main():
    na = NetworkAnalysis()
    comm = na.find_communications()
    na.draw_network_diagram(comm)


if __name__ == '__main__':
    main()
