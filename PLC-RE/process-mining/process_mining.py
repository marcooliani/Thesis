#!/usr/bin/env python3
import numpy as np
import pandas as pd
import os
import argparse
import configparser
import subprocess
import re
import datetime as dt
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

        parser.add_argument('-f', "--filename", type=str, help="name of the input physical dataset file (CSV format)")
        # parser.add_argument('-n', "--network", type=str, help="name of the input network dataset file (CSV format)")
        parser.add_argument('-a', "--actuators", nargs='+', required=False, help="actuators list")
        parser.add_argument('-s', "--sensors", nargs='+', required=False, help="sensors list")
        parser.add_argument('-t', "--tolerance", type=float, default=self.config['MINING']['tolerance'],
                            required=False, help="tolerance")
        group.add_argument('-o', "--offset", type=int, default=0, required=False, help="offset")
        group.add_argument('-g', "--graph", type=bool, default=False, required=False, help="generate state graph")

        self.args = parser.parse_args()

        self.dataset = self.config['PREPROC']['dataset_file']

        self.tolerance = self.args.tolerance
        self.offset = self.args.offset
        self.graph = self.args.graph

        self.configurations = defaultdict(dict)

        if self.args.filename is not None:
            if self.args.filename.split('.')[-1] != "csv":
                print("Invalid file format (must be .csv). Aborting")
                exit(1)
            self.dataset = self.args.filename

        # Vado nella dir col dataset
        if os.chdir(os.path.join(self.config['PATHS']['project_dir'], self.config['MINING']['data_dir'])):
            print(f"Directory {os.path.join(self.config['PATHS']['project_dir'], self.config['MINING']['data_dir'])} "
                  f"not found. Aborting.")
            exit(1)

        self.df = pd.read_csv(self.dataset)

        # Recupero la lista completa di attuatori e sensori (mi servono poi)
        output = self.call_daikon()
        self.full_actuators = self.find_actuators_list(output)
        self.full_sensors = self.find_sensors()

        if self.args.actuators:
            self.actuators = self.args.actuators
        else:
            self.actuators = self.full_actuators

        if self.args.sensors:
            self.sensors = self.args.sensors
        else:
            self.sensors = self.find_sensors()

    def call_daikon(self):
        dataset_name = self.dataset.split('.')[0].split('/')[-1]

        if subprocess.call(f'perl $DAIKONDIR/scripts/convertcsv.pl {self.dataset}', shell=True):
            print("Error generating invariants. Aborting.")
            exit(1)

        output = subprocess.check_output(
            f'java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy {dataset_name}.decls {dataset_name}.dtrace ',
            shell=True)

        output = output.decode("utf-8")
        output = re.sub('[=]{6,}', '', output)
        output = output.split('\n')[6:-2]

        return output

    def find_actuators_list(self, output):
        actuators = list()
        for inv in output:
            if 'one of' in inv and self.config['DATASET']['prev_cols_prefix'] not in inv and \
                    self.config['DATASET']['slope_cols_prefix'] not in inv:
                a, _ = inv.split(' one of ')
                a.replace('(', '').replace(')', '')

                actuators.append(a)

                equals = self.__find_other_actuators(a, output)
                for act in equals:
                    actuators.append(act)

        return actuators

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

    def find_sensors(self):
        df_cols = list(self.df.columns)

        # Se le colonne hanno un unico valore, abbiamo un attuatore di spare o un setpoint settato
        # nei registri, quindi elimino il registro dalla lista
        for col in df_cols[:]:
            if len(self.df[col].unique()) == 1:
                df_cols.remove(col)

        # Rimuovo il timestamp
        df_cols.remove(self.config['DATASET']['timestamp_col'])

        # Rimuovo dalla lista gli attuatori trovati in precedenza, ottenendo così i soli sensori
        for col in self.full_actuators:
            df_cols.remove(col)

        return df_cols

    def __compute(self, config, next_config, starting_time, ending_time, starting_value, ending_value):
        conf = ', '.join(map(str, config))

        date1 = dt.datetime.strptime(starting_time, '%Y-%m-%d %H:%M:%S.%f')
        date2 = dt.datetime.strptime(ending_time, '%Y-%m-%d %H:%M:%S.%f')
        difference_seconds = 1 + abs((date2 - date1)).seconds  # Conta anche il secondo di partenza!

        for (sensor, end_val), (sensor, start_val) in zip(ending_value.items(), starting_value.items()):
            self.configurations[conf][f'start_value_{sensor}'].append(start_val)
            self.configurations[conf][f'end_value_{sensor}'].append(end_val)

            # Con l'arrotondamento al terzo decimale sono un po' più preciso...
            slope = round((end_val - start_val)/difference_seconds, 3)

            if -self.tolerance < slope < self.tolerance:
                trend = 'STBL'
                slope = 0
            elif slope >= self.tolerance:
                trend = 'ASC'
            else:
                trend = 'DESC'

            self.configurations[conf][f'slope_{sensor}'].append(slope)
            self.configurations[conf][f'trend_{sensor}'].append(trend)

        self.configurations[conf]['time'].append(difference_seconds)
        self.configurations[conf]['next_state'].append(', '.join(map(str, next_config)))

    def mining(self):
        prev_values = []
        starting_value = defaultdict(list)
        ending_value = defaultdict(list)
        starting_time = None
        ending_time = None

        states = self.df[self.actuators].drop_duplicates().to_numpy()

        for state in states:
            config = list()
            for a, s in zip(self.actuators, state):
                config.append(f'{a} == {s}')

            self.configurations[', '.join(map(str, config))] = defaultdict(list)

        for i in range(len(self.df)):
            values = [self.df[k].iloc[i] for k in self.actuators]

            if values != prev_values:
                if starting_time:
                    # Se lo stato dura un secondo, l'ending time non fa in tempo ad aggiornarsi
                    # e resta quello precedente (minore dello starting time): quindi lo forzo ad essere uguale
                    # allo starting time. Il resto è corretto!
                    if ending_time < starting_time:
                        ending_time = starting_time

                    act_conf = list()
                    next_conf = list()

                    for a, pv in zip(self.actuators, prev_values):
                        act_conf.append(f'{a} == {pv}')

                    for a, nv in zip(self.actuators, values):
                        next_conf.append(f'{a} == {nv}')

                    self.__compute(act_conf, next_conf, starting_time, ending_time, starting_value, ending_value)

                for sensor in self.full_sensors:
                    starting_value[sensor] = self.df[sensor].iloc[i]
                starting_time = self.df[self.config['DATASET']['timestamp_col']].iloc[i]
            else:
                for sensor in self.full_sensors:
                    ending_value[sensor] = self.df[sensor].iloc[i]
                ending_time = self.df[self.config['DATASET']['timestamp_col']].iloc[i]
            prev_values = values

        # Converto i dict in json per poi salvare tutto su file
        print_json = json.dumps(self.configurations, indent=4)

        with open('results.json', 'w') as f:
            f.write(print_json)

    def generate_state_graph(self):
        dot = graphviz.Digraph(name=f'State graph {self.sensors}',
                               node_attr={'color': 'lightblue2', 'style': 'rounded, filled',
                                          'shape': 'box', 'fontsize': '10'},
                               edge_attr={'fontfamily': 'Courier', 'fontsize': '8'},
                               format='png',
                               directory='graphs')
        dot.attr(rankdir='LR')

        states_list = [k for k, v in self.configurations.items()]

        for state in states_list:
            slope_state = defaultdict(list)

            for sensor in self.sensors:
                trend_list = list(dict.fromkeys(self.configurations[state][f'trend_{sensor}'][1:-1]))
                slope_list = list(self.configurations[state][f'slope_{sensor}'][1:-1])

                slope_vals = defaultdict(list)
                for tl in trend_list:
                    indexes = [i for (i, item) in enumerate(self.configurations[state][f'trend_{sensor}'][1:-1])
                               if item == tl]

                    for i in indexes:
                        slope_vals[tl].append(slope_list[i])

                for trend, slopes in slope_vals.items():
                    slope_state[sensor].append((trend, round(mean(slopes), 2)))

                trend_slope_label = ''

                for sens, vals in slope_state.items():
                    trend_slope_label += f'{sens}: '

                    for v in vals:
                        trend_slope_label += str(v[0]) + ' (slope: ' + str(v[1]) + ') '
                    trend_slope_label += '\n'

            state_label = '\n'.join(map(str, state.split(', ')))  # Riformatto lo stato per una label più leggibile
            dot.node(state, f'{state_label}\n\n{trend_slope_label}')  # Creo nodo

            # Genero gli archi
            nextstates_list = list(
                dict.fromkeys(self.configurations[state]['next_state']))  # Lista degli stati successivi

            for nextstate in nextstates_list:
                startvals = defaultdict(list)
                endvals = defaultdict(list)
                endval_mean = defaultdict(list)
                startval_mean = defaultdict(list)
                endval_std_dev = defaultdict(list)
                startval_std_dev = defaultdict(list)

                timevals = list()

                indexes = [i for (i, item) in enumerate(self.configurations[state]['next_state']) if item == nextstate]

                for i in indexes:
                    for sensor in self.full_sensors:
                        endvals[sensor].append(self.configurations[state][f'end_value_{sensor}'][i])
                        startvals[sensor].append(self.configurations[state][f'start_value_{sensor}'][i])
                    timevals.append(self.configurations[state][f'time'][i])

                if len(timevals) >= 3:
                    timevals = timevals[1:-1]

                time_mean = mean(timevals)
                time_std_dev = np.std(timevals)

                for sensor in self.full_sensors:
                    if len(endvals[sensor]) >= 3:
                        endvals[sensor] = endvals[sensor][1:-1]
                    if len(startvals[sensor]) >= 3:
                        startvals[sensor] = startvals[sensor][1:-1]

                    endval_mean[sensor] = mean(endvals[sensor])
                    endval_std_dev[sensor] = np.std(list(endvals[sensor]))

                edge_label = ''
                for sensor in self.full_sensors:
                    edge_label += f'{sensor} lvl: {round(endval_mean[sensor], 1)} ' \
                                  f'(Std dev: {round(endval_std_dev[sensor])})\n'
                edge_label += f'Time: {round(time_mean)} (Std dev: {round(float(time_std_dev))})'

                dot.edge(state, nextstate, label=edge_label)

        # print(dot.source)
        dot.view()


def main():
    start_dir = os.getcwd()
    pm = ProcessMining()
    # pm.find_sensors()

    pm.mining()
    if pm.graph:
        pm.generate_state_graph()

    os.chdir(start_dir)


if __name__ == '__main__':
    main()
