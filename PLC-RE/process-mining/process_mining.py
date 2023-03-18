#!/usr/bin/env python3

import pandas as pd
import os
import argparse
import configparser
import subprocess
import re
import datetime as dt

import graphviz

from collections import defaultdict
import json


class ProcessMining:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        group = parser.add_argument_group()

        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        group.add_argument('-s', "--sensor", type=str, required=False, help="sensor's name")
        group.add_argument('-t', "--tolerance", type=int, default=0, required=False, help="tolerance")
        group.add_argument('-o', "--offset", type=int, default=0, required=False, help="offset")
        group.add_argument('-g', "--graph", type=bool, default=0, required=False, help="generate state graph")

        self.args = parser.parse_args()

        self.dataset = self.config['DEFAULTS']['dataset_file']
        self.actuators = dict()

        self.actuator = None
        self.sensor = None
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

        self.sensor = self.args.sensor
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
                a, b = inv.split(' one of ')
                a.replace('(', '').replace(')', '')
                b = [float(i) for i in b.replace('{ ', '').replace(' }', '').replace(',', '').split(' ')]

                self.actuators[a] = b

                equals = self.__find_other_actuators(a, output)
                for act in equals:
                    self.actuators[act] = b

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

        # print(starting_value, ending_value, difference_seconds, end=' ')
        slope = (ending_value - starting_value) / difference_seconds
        if difference_value > self.tolerance:
            # print(f"-> ASCENDING ({slope})")
            trend = "ASCENDING"
        elif difference_value < -self.tolerance:
            # print(f"-> DESCENDING ({slope})")
            trend = "DESCENDING"
        else:
            # print(f"-> STABLE ({slope})")
            trend = "STABLE"

        conf = ', '.join(map(str, config))
        # if conf not in self.configurations:
        #   self.configurations[conf] = defaultdict(dict)
        self.configurations[conf]['start_value'].append(starting_value)
        self.configurations[conf]['end_value'].append(ending_value)
        self.configurations[conf]['time'].append(difference_seconds)
        self.configurations[conf]['trend'].append(trend)
        self.configurations[conf]['slope'].append(slope)
        self.configurations[conf]['next_state'].append(', '.join(map(str, next_config)))

    def mining(self):
        prev_values = []
        starting_value = None
        ending_value = None
        starting_time = None
        ending_time = None

        actuators_list = [key for key, val in self.actuators.items()]

        df = pd.read_csv(self.dataset)
        states = df[actuators_list].drop_duplicates().to_numpy()

        for state in states:
            config = list()
            for a, s in zip(actuators_list, state):
                config.append(f'{a} == {s}')

            self.configurations[', '.join(map(str, config))] = defaultdict(list)

        for i in range(len(df)):
            # if df['P1_MV101'].iloc[i] == 1 and df['P1_P101'].iloc[i] == 2:
            values = [df[k].iloc[i] for k in actuators_list]

            if values != prev_values:
                if starting_time:
                    act_conf = list()
                    next_conf = list()

                    for a, pv in zip(actuators_list, prev_values):
                        act_conf.append(f'{a} == {pv}')

                    for a, nv in zip(actuators_list, values):
                        next_conf.append(f'{a} == {nv}')

                    # print(', '.join(map(str, act_conf)))
                    # print(prev_values)
                    self.__compute(act_conf, next_conf, starting_time, ending_time, starting_value, ending_value)
                    # print()

                starting_value = df[self.sensor].iloc[i]
                starting_time = df['Timestamp'].iloc[i]
            else:
                ending_value = df[self.sensor].iloc[i]
                ending_time = df['Timestamp'].iloc[i]
            prev_values = values

        print_json = json.dumps(self.configurations, indent=4)
        # print(print_json)

    def generate_state_graph(self):
        dot = graphviz.Digraph(name='State graph', node_attr={'color': 'lightblue2', 'style': 'filled'}, format='png')
        stati = [k for k, v in self.configurations.items()]
        nodi = [f'Nodo{n+1}' for n in range(len(stati))]

        nodes_labels = list()
        for n, s in zip(nodi, stati):
            nodes_labels.append((n, s))

        next_states = list()
        pend = list()
        for x in nodes_labels:
            ns = list(set(self.configurations[x[1]]['next_state']))
            pend = list(set(self.configurations[x[1]]['trend']))
            if len(pend) > 1:
                pend = pend[1]
            else:
                pend = pend[0]
            for w in nodes_labels:
                if ns[0] in w:
                    next_states.append((x[0], w[0], pend))

        for x in nodes_labels:
            dot.node(f'{x[0]}', f'{x[1]}')
        for w in next_states:
            dot.edge(w[0], w[1], label=w[2])

        # print(dot.source)
        dot.view()


def main():
    pm = ProcessMining()
    pm.check_args()
    start_dir = os.getcwd()
    if os.chdir('data/'):
        print("Error generating invariants. Aborting.")
        exit(1)
    output = pm.call_daikon()
    pm.find_actuators_list(output)
    pm.mining()
    if pm.graph:
        pm.generate_state_graph()
    os.chdir(start_dir)


if __name__ == '__main__':
    main()
