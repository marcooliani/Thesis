#!/usr/bin/env python3

import pandas as pd
import os
import argparse
import configparser
import subprocess
import re
import datetime as dt
import math
import graphviz

from statistics import mean
from collections import defaultdict
import json


class ProcessMining:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        group = parser.add_argument_group()

        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        group.add_argument('-a', "--actuators", nargs='+', required=False, help="actuators list")
        group.add_argument('-s', "--sensor", type=str, required=True, help="sensor's name")
        group.add_argument('-t', "--tolerance", type=int, default=0, required=False, help="tolerance")
        group.add_argument('-o', "--offset", type=int, default=0, required=False, help="offset")
        group.add_argument('-g', "--graph", type=bool, default=0, required=False, help="generate state graph")

        self.args = parser.parse_args()

        self.dataset = self.config['DEFAULTS']['dataset_file']

        self.actuators = list()
        self.sensors = None
        self.tolerance = None
        self.offset = None
        self.graph = None

        self.configurations = defaultdict(dict)

    def check_args(self):
        if self.args.filename is not None:
            if self.args.filename.split('.')[-1] != "csv":
                print("Invalid file format (must be .csv). Aborting")
                exit(1)
            self.dataset = self.args.filename

        if self.args.actuators:
            self.actuators = self.args.actuators
        else:
            output = self.call_daikon()
            self.find_actuators_list(output)

        self.sensors = self.args.sensor
        self.tolerance = self.args.tolerance
        self.offset = self.args.offset
        self.graph = self.args.graph

    def call_daikon(self):
        dataset_name = self.dataset.split('/')[-1].split('.')[0]

        # print(f"Generating {dataset_name}.decls and {dataset_name}.dtrace files ...")
        if subprocess.call(f'perl $DAIKONDIR/scripts/convertcsv.pl {self.dataset}', shell=True):
            print("Error generating invariants. Aborting.")
            exit(1)

        # print("Generating invariants with no conditions ...")
        output = subprocess.check_output(
            f'java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy {dataset_name}.decls {dataset_name}.dtrace ',
            shell=True)

        output = output.decode("utf-8")
        output = re.sub('[=]{6,}', '', output)
        output = output.split('\n')[6:-2]

        return output

    def find_actuators_list(self, output):
        for inv in output:
            if 'one of' in inv and self.config['DATASET']['prev_cols_prefix'] not in inv and \
                    self.config['DATASET']['slope_cols_prefix'] not in inv:
                a, _ = inv.split(' one of ')
                a.replace('(', '').replace(')', '')

                self.actuators.append(a)

                equals = self.__find_other_actuators(a, output)
                for act in equals:
                    self.actuators.append(act)

    def __find_other_actuators(self, actuator, daikon_output):
        equals = list()
        for inv in daikon_output:
            if ' == ' in inv and \
                    actuator in inv and \
                    self.config['DATASET']['prev_cols_prefix'] not in inv \
                    and '%' not in inv:
                equals = inv.split(' == ')
                equals.remove(actuator)

        return equals

    def __compute(self, config, next_config, starting_time, ending_time, starting_value, ending_value):
        date1 = dt.datetime.strptime(starting_time, '%Y-%m-%d %H:%M:%S.%f')
        date2 = dt.datetime.strptime(ending_time, '%Y-%m-%d %H:%M:%S.%f')
        difference_seconds = 1 + (date2 - date1).seconds  # Conta anche il secondo di partenza!

        difference_value = ending_value - starting_value

        slope = (ending_value - starting_value) / difference_seconds
        if difference_value > self.tolerance:
            trend = "ASCENDING"
        elif difference_value < -self.tolerance:
            trend = "DESCENDING"
        else:
            trend = "STABLE"

        conf = ', '.join(map(str, config))

        self.configurations[conf][f'start_value_{self.sensors}'].append(starting_value)
        self.configurations[conf][f'end_value_{self.sensors}'].append(ending_value)
        self.configurations[conf]['time'].append(difference_seconds)
        self.configurations[conf][f'trend_{self.sensors}'].append(trend)
        self.configurations[conf][f'slope_{self.sensors}'].append(slope)
        self.configurations[conf]['next_state'].append(', '.join(map(str, next_config)))

    def mining(self):
        prev_values = []
        starting_value = None
        ending_value = None
        starting_time = None
        ending_time = None

        df = pd.read_csv(self.dataset)
        states = df[self.actuators].drop_duplicates().to_numpy()

        for state in states:
            config = list()
            for a, s in zip(self.actuators, state):
                config.append(f'{a} == {s}')

            self.configurations[', '.join(map(str, config))] = defaultdict(list)

        for i in range(len(df)):
            # if df['P1_MV101'].iloc[i] == 1 and df['P1_P101'].iloc[i] == 2:
            values = [df[k].iloc[i] for k in self.actuators]

            if values != prev_values:
                if starting_time:
                    act_conf = list()
                    next_conf = list()

                    for a, pv in zip(self.actuators, prev_values):
                        act_conf.append(f'{a} == {pv}')

                    for a, nv in zip(self.actuators, values):
                        next_conf.append(f'{a} == {nv}')

                    self.__compute(act_conf, next_conf, starting_time, ending_time, starting_value, ending_value)

                starting_value = df[self.sensors].iloc[i]
                starting_time = df[self.config['DATASET']['timestamp_col']].iloc[i]
            else:
                ending_value = df[self.sensors].iloc[i]
                ending_time = df[self.config['DATASET']['timestamp_col']].iloc[i]
            prev_values = values

        print_json = json.dumps(self.configurations, indent=4)
        # print(print_json)

        with open('results.json', 'w') as f:
            f.write(print_json)

    def generate_state_graph(self):
        dot = graphviz.Digraph(name=f'State graph {self.sensors}',
                               node_attr={'color': 'lightblue2', 'style': 'rounded, filled',
                                          'shape': 'box', 'fontsize': '10'},
                               edge_attr={'fontfamily': 'Courier', 'fontsize': '8'},
                               format='png')
        dot.attr(rankdir='LR')

        states_list = [k for k, v in self.configurations.items()]

        for state in states_list:
            # Genero i nodi.
            # L'id del nodo è lo stato stesso, mentre la label è composta dallo stato
            # più l'indicazione del trend per quello stato (acendente, discentende, stabile)
            trend_list = list(
                dict.fromkeys(self.configurations[state][f'trend_{self.sensors}']))  # Elimino i duplicati
            if len(trend_list) >= 3:
                trend = ', '.join(map(str, trend_list[1:-1]))  # Elimino primo e ultimo elemento
            elif len(trend_list) == 2:
                trend = trend_list[1:]
            else:
                trend = trend_list[0]

            # Metto come attributo del nodo anche lo slope (arrotondato al secondo decimale)
            slope_list = list(dict.fromkeys(self.configurations[state][f'slope_{self.sensors}']))
            if len(slope_list) >= 3:
                slope = round(mean(slope_list[1:-1]), 2)
            else:
                slope = round(mean(slope_list[1:]), 2)

            state_label = '\n'.join(map(str, state.split(', ')))  # Riformatto lo stato per una label più leggibile
            dot.node(state, f'{state_label}\n\n{trend}\n(slope: {slope})')  # Creo nodo

            # Genero gli archi
            nextstates_list = list(
                dict.fromkeys(self.configurations[state]['next_state']))  # Lista degli stati successivi

            for nextstate in nextstates_list:
                endvals = list()
                timevals = list()
                edge_attr = list()

                indexes = [i for (i, item) in enumerate(self.configurations[state]['next_state']) if item == nextstate]

                for i in indexes:
                    endvals.append(self.configurations[state][f'end_value_{self.sensors}'][i])
                    timevals.append(self.configurations[state][f'time'][i])

                if len(endvals) >= 3:
                    endvals = endvals[1:-1]
                if len(timevals) >= 3:
                    timevals = timevals[1:-1]

                for v, t in zip(endvals, timevals):
                    row = f' Value: {round(v)} | Time: {t}'
                    edge_attr.append(row)

                dot.edge(state, nextstate, label='\n'.join(map(str, edge_attr)))

        # print(dot.source)
        dot.view()


def main():
    pm = ProcessMining()
    start_dir = os.getcwd()
    if os.chdir('data/'):
        print("Error generating invariants. Aborting.")
        exit(1)

    pm.check_args()
    # output = pm.call_daikon()
    # pm.find_actuators_list(output)
    pm.mining()
    if pm.graph:
        pm.generate_state_graph()
    os.chdir(start_dir)


if __name__ == '__main__':
    main()
