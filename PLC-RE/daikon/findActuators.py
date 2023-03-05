#!/usr/bin/env python3

import os
import re
import subprocess
import networkx as nx
import argparse
import configparser
import pandas as pd
import numpy as np


class FindActuators:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        parser.add_argument('-s', "--simpleanalysis", type=bool, default=False, help="simple daikon analysis on actuators")
        parser.add_argument('-c', "--customanalysis", nargs='+', default=[], help="daikon analysis on actuators based on a condition")
        self.args = parser.parse_args()

        self.dataset = self.config['DEFAULTS']['dataset_file']
        self.actuators = dict()
        self.constants = list()
        self.setpoints = list()

    def check_args(self):
        if self.args.filename is not None:
            if self.args.filename.split('.')[-1] != "csv":
                print("Invalid file format (must be .csv). Aborting")
                exit(1)
            self.dataset = self.args.filename

    def call_daikon(self):
        start_dir = os.getcwd()
        if os.chdir(self.config['DAIKON']['daikon_invariants_dir']):
            print("Error generating invariants. Aborting.")
            exit(1)

        dataset_name = self.dataset.split('/')[-1].split('.')[0]

        # print(f"Generating {dataset_name}.decls and {dataset_name}.dtrace files ...")
        if subprocess.call(f'perl $DAIKONDIR/scripts/convertcsv.pl {self.dataset}', shell=True):
            print("Error generating invariants. Aborting.")
            exit(1)

        # print("Generating invariants with no conditions ...")
        output = subprocess.check_output(
            f'java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy {dataset_name}.decls {dataset_name}.dtrace ',
            shell=True)

        os.chdir(start_dir)

        output = output.decode("utf-8")
        output = re.sub('[=]{6,}', '', output)
        output = output.split('\n')[6:-2]

        return output

    @staticmethod
    def make_dfs(edge_list, output_list):
        G = nx.MultiDiGraph()
        G.add_edges_from(edge_list)

        for g in list(G.nodes())[:]:
            if G.degree(g) == 0:
                G.remove_node(g)

        visited = list()
        for v in list(G.nodes()):
            if v not in visited:
                temp = []
                # DFS
                closure_dfs = list(nx.dfs_edges(G, source=v))

                # "Concateno" di fatto le tuple che fanno parte
                # della DFS
                for a, b in closure_dfs:
                    if a not in visited:
                        temp.append(a.replace('"', ''))
                        visited.append(a)
                    if b not in visited or b.lstrip('-').replace('.', '', 1).isdigit():
                        visited.append(b)
                        temp.append(b.replace('"', ''))

                # Inserisco la lista di nodi nel listone delle invarianti
                output_list.append(temp)

    def find_setpoints(self, daikon_output):
        edge_list = list()
        for invariant in daikon_output:
            if ' == ' in invariant and \
                    self.config['DATASET']['prev_cols_prefix'] not in invariant and \
                    '%' not in invariant and \
                    (self.config['DATASET']['min_prefix'] in invariant or self.config['DATASET']['max_prefix'] in invariant):
                a, b = invariant.split(' == ')
                edge_list.append((a, b))
                edge_list.append((b, a))

        self.make_dfs(edge_list, self.setpoints)

    def find_constants(self, daikon_output):
        edge_list = list()
        for invariant in daikon_output:
            if ' == ' in invariant and \
                    self.config['DATASET']['prev_cols_prefix'] not in invariant and\
                    '%' not in invariant and \
                    self.config['DATASET']['min_prefix'] not in invariant and \
                    self.config['DATASET']['max_prefix'] not in invariant:
                a, b = invariant.split(' == ')
                edge_list.append((a, b))
                edge_list.append((b, a))

        self.make_dfs(edge_list, self.constants)

    def find_other_actuators(self, actuator, daikon_output):
        equals = list()
        for inv in daikon_output:
            if ' == ' in inv and \
                    actuator in inv and \
                    self.config['DATASET']['prev_cols_prefix'] not in inv \
                    and '%' not in inv:
                equals = inv.split(' == ')
                equals.remove(actuator)

        return equals

    def parse_output(self, output):
        for inv in output:
            if 'one of' in inv and self.config['DATASET']['prev_cols_prefix'] not in inv and \
                    self.config['DATASET']['slope_cols_prefix'] not in inv:
                a, b = inv.split(' one of ')
                a.replace('(', '').replace(')', '')
                b = [float(i) for i in b.replace('{ ', '').replace(' }', '').replace(',', '').split(' ')]

                self.actuators[a] = b

                equals = self.find_other_actuators(a, output)
                for act in equals:
                    self.actuators[act] = b

        self.actuators = {key.replace('"', ''): val for key, val in self.actuators.items()}
        self.find_constants(output)
        self.find_setpoints(output)

    def print_info(self):
        print('### Probable Actuators ### ')
        print('---------------------------')
        print('Name\t|  Values')
        print('---------------------------')
        for key, val in self.actuators.items():
            print(f'{key} \t|  {" - ".join(map(str, val))}')
        print('---------------------------')
        print()

        print('### Constants ###')
        print('---------------------------')
        for i in self.constants:
            print(' = '.join(map(str, i)))
        print('---------------------------')
        print()

        print('### Relative Setpoints ###')
        print('---------------------------')
        for i in self.setpoints:
            print(' = '.join(map(str, i)))

    def find_min_max(self, sensor):
        str_max = self.config['DATASET']['max_prefix'] + sensor
        str_min = self.config['DATASET']['min_prefix'] + sensor

        return str_max, str_min

    def make_daikon_simple_analysis(self, str_min, str_max, sensor):
        daikon_condition = ''
        for const in self.setpoints:
            if str_max in const:
                max_v = int(float(const[1]))
                margin = round((max_v / 100) * int(self.config['DAIKON']['max_security_pct_margin']))
                daikon_condition += f'&& {sensor} < {self.config["DATASET"]["max_prefix"]}{sensor} - {margin} '
            if str_min in const:
                min_v = int(float(const[1]))
                margin = round((min_v / 100) * int(self.config['DAIKON']['min_security_pct_margin']))
                daikon_condition += f'&& {sensor} > {self.config["DATASET"]["min_prefix"]}{sensor} + {margin} '

        for key, val in self.actuators.items():
            for v in val:
                subprocess.call(f'./runDaikon.py -c "{key} == {v} {daikon_condition}" -r {key}', shell=True)
                print()

    def make_daikon_custom_analysis(self, str_min, str_max, sensor):
        actuators_list = [key for key, value in self.actuators.items()]
        df = pd.read_csv(os.path.join(self.config['DAIKON']['daikon_invariants_dir'], self.dataset), usecols=actuators_list)

        statuses = df[actuators_list].drop_duplicates().to_numpy()
        sensor_condition = ''

        for const in self.setpoints:
            if str_max in const:
                max_v = int(float(const[1]))
                margin = round((max_v / 100) * int(self.config['DAIKON']['max_security_pct_margin']))
                sensor_condition += f' && {sensor} < {self.config["DATASET"]["max_prefix"]}{sensor} - {margin}'
                # sensor_condition += f' && {sensor} < {self.config["DATASET"]["max_prefix"]}{sensor}'
            if str_min in const:
                min_v = int(float(const[1]))
                margin = round((min_v / 100) * int(self.config['DAIKON']['min_security_pct_margin']))
                sensor_condition += f' && {sensor} > {self.config["DATASET"]["min_prefix"]}{sensor} + {margin}'
                # sensor_condition += f' && {sensor} > {self.config["DATASET"]["min_prefix"]}{sensor}'

        for status in statuses:
            daikon_condition = list()
            for i in range(len(status)):
                tmp = f'{actuators_list[i]} == {status[i]}'
                daikon_condition.append(tmp)
            daikon_condition = ' && '.join(map(str, daikon_condition)) + sensor_condition

            subprocess.call(f'./runDaikon.py -f {self.dataset} -c "{daikon_condition}" -r "Other"', shell=True)
            print()


def main():
    fa = FindActuators()

    fa.check_args()
    start_dir = os.getcwd()
    print("Process start")

    '''
    if os.chdir(fa.config['DAIKON']['daikon_invariants_dir']):
        print("Error generating invariants. Aborting.")
        exit(1)
    '''

    # Controllo se esiste la directory dove verranno scritti i file con i risultati. Se non esiste la creo
    if not os.path.exists(fa.config["DAIKON"]["daikon_results_dir"]):
        os.makedirs(fa.config["DAIKON"]["daikon_results_dir"])

    daikon_output = fa.call_daikon()
    fa.parse_output(daikon_output)
    fa.print_info()

    # os.chdir(start_dir)

    sensor = input('Insert sensor name: ')
    str_max, str_min = fa.find_min_max(sensor)
    fa.make_daikon_custom_analysis(str_min, str_max, sensor)

    if fa.args.simpleanalysis:
        # res = input('Perform Daikon analysis? [y/n] ')
        # if res == 'Y' or res == 'y':
        sensor = input('Insert sensor name: ')
        str_max, str_min = fa.find_min_max(sensor)
        fa.make_daikon_simple_analysis(str_min, str_max, sensor)

    print('\n')


if __name__ == '__main__':
    main()

# Appunti sparsi
# df[['P1.MV101', 'P1.P101']].drop_duplicates().to_numpy()
