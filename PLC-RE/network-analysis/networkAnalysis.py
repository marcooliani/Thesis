#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
import argparse
import configparser
import glob
import ipaddress
import graphviz
import pygraphviz as pgv  # apt-get install graphviz graphviz-dev
from PIL import Image


class NetworkAnalysis:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-f', "--file", type=str, help="CSV file with network data")
        group.add_argument('-D', "--directory", type=str, help="CSV files with network data")
        parser.add_argument('-s', "--srcaddr", type=str, default=None, help="Source IP address")
        parser.add_argument('-d', "--dstaddr", type=str, default=None, help="Destination IP address")
        self.args = parser.parse_args()

        self.df = None
        self.file = self.args.file
        if self.args.directory:
            self.directory = self.args.directory
        else:
            self.directory = os.path.join(self.config['PATHS']['project_dir'],
                                          self.config['NETWORK']['split_dir'])
        self.src_addr = self.args.srcaddr
        self.dst_addr = self.args.dstaddr

    def merge_datasets(self):
        df_list = list()
        df_files = glob.glob(os.path.join(self.directory, '*.csv'))

        for file in sorted(df_files):
            tmp = pd.read_csv(file)
            df_list.append(tmp)

        df = pd.concat(df_list, axis=0).reset_index(drop=True)
        df.drop_duplicates(inplace=True)

        return df

    def find_communications(self):
        if self.args.directory:
            df = self.merge_datasets()

        else:
            df = pd.read_csv(os.path.join(self.config['PATHS']['project_dir'],
                                          self.config['NETWORK']['data_dir'],
                                          self.file))

        df = df[['src', 'dst', 'protocol', 'service_detail', 'register']]
        df['register'] = df['register'].fillna(value='missing data')
        # df_nodup = df[['src', 'dst', 'protocol', 'service_detail', 'register']].drop_duplicates().reset_index(drop=True)
        # df_nodup['register'] = df_nodup['register'].fillna(value='missing data')

        # Trovo, ordino e stampo gli ip
        sources = sorted(df['src'].unique(), key=ipaddress.IPv4Address)
        destinations = sorted(df['dst'].unique(), key=ipaddress.IPv4Address)
        ips = sorted(list(set(sources + destinations)), key=ipaddress.IPv4Address)
        print(f'IP adrresses found: ')
        print(' | '.join(map(str, ips)))
        print()

        if self.src_addr:
            # df_nodup = df_nodup[df_nodup["src"] == self.src_addr].reset_index(drop=True)
            df = df[df["src"] == self.src_addr].reset_index(drop=True)
        if self.dst_addr:
            # df_nodup = df_nodup[df_nodup["dst"] == self.dst_addr].reset_index(drop=True)
            df = df[df["dst"] == self.dst_addr].reset_index(drop=True)

        df_print = df.groupby(['src', 'dst']).value_counts()
        print(df_print.to_string())

        df = df.groupby(['src', 'dst'], as_index=False).value_counts()

        return df

    def save_to_csv(self, dataframe):
        print("Saving CSV export ... ")
        dataframe.to_csv(
            f'{os.path.join(self.config["PATHS"]["project_dir"], self.config["NETWORK"]["data_dir"], "network.csv")}',
            index=False)
        print(f'CSV file {self.config["NETWORK"]["networks_output"]} saved. Exiting')

    @staticmethod
    def draw_network_diagram(df):
        plc_comm = df.values.tolist()

        G = pgv.AGraph(strict=False, directed=True, rankdir='TD')
        # G.graph_attr["label"] = "Communication Network diagram"
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

            if "missing data" in register:
                arrow_style = "dotted"
                color = "dimgrey"
                labelfontcolor = "dimgrey"

            if "Request" in service or "Write" in service:
                color = "red"

            G.add_node(src, label=src)
            G.add_node(dst, label=dst)
            # G.add_edge(src, dst, style=arrow_style, color=color)
            G.add_edge(src, dst, label=f'{protocol} {service}\n{register}', style=arrow_style, color=color,
                       labelfontcolor=labelfontcolor)

        G.unflatten("-f -l 200")
        G.layout(prog="dot")
        G.draw(f'data/network.svg')
        G.draw(f'data/network.png')
        #G.draw(f'/tmp/network.png')

        #img = Image.open('/tmp/network.png')
        #img.show()

    @staticmethod
    def draw_network_diagram_OLD(df):

        dot = graphviz.Digraph(name=f'Network Diagram',
                               node_attr={'color': 'lightblue2', 'style': 'rounded, filled',
                                          'shape': 'box', 'fontsize': '10'},
                               edge_attr={'fontfamily': 'Courier', 'fontsize': '8'},
                               format='svg',
                               engine='dot',
                               directory='graphs')
        dot.attr(rankdir='LR')
        arrow_style = "solid"

        plc_comm = df.values.tolist()
        #print(plc_comm)
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
    na.save_to_csv(comm)
    na.draw_network_diagram(comm)


if __name__ == '__main__':
    main()
