#!/usr/bin/env python3

import os
import re
import subprocess
import networkx as nx
import argparse
import configparser
import pandas as pd


class DaikonAnalysis:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", required=True, type=str,
                            help="name of the input dataset file (CSV format) w/o path")
        parser.add_argument('-s', "--simpleanalysis", type=bool, default=False,
                            help="simple Daikon analysis on single actuators")
        parser.add_argument('-c', "--customanalysis", type=bool, default=False,
                            help="Daikon analysis based on actuators state changes")
        parser.add_argument('-u', "--uppermargin", type=int, default=self.config['DAIKON']['max_security_pct_margin'],
                            help="Upper safety margin (percent)")
        parser.add_argument('-l', "--lowermargin", type=int, default=self.config['DAIKON']['min_security_pct_margin'],
                            help="Lower safety margin (percent)")
        self.args = parser.parse_args()

        if not (self.args.simpleanalysis or self.args.customanalysis):
            parser.error('At least one between -c and -s is required')

        if self.args.filename.split('.')[-1] != "csv":
            print("Invalid file format (must be .csv). Aborting")
            exit(1)
        self.dataset = self.args.filename
        self.actuators = dict()
        self.sensors = list()
        self.constants = list()
        self.setpoints = list()

        self.upper_pct_margin = self.args.uppermargin
        self.lower_pct_margin = self.args.lowermargin

        if os.chdir(os.path.join(self.config['PATHS']['project_dir'], self.config['DAIKON']['daikon_invariants_dir'])):
            print("Error generating invariants. Aborting.")
            exit(1)

    def __call_daikon(self):
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

    def find_actuators(self):
        output = self.__call_daikon()
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

        self.actuators = {key.replace('"', ''): val for key, val in self.actuators.items()}
        # self.__find_constants(output)
        self.__find_setpoints(output)

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

    def __find_setpoints(self, daikon_output):
        edge_list = list()
        for invariant in daikon_output:
            if ' == ' in invariant and \
                    self.config['DATASET']['prev_cols_prefix'] not in invariant and \
                    '%' not in invariant and \
                    (self.config['DATASET']['min_prefix'] in invariant or self.config['DATASET'][
                        'max_prefix'] in invariant):
                a, b = invariant.split(' == ')
                edge_list.append((a, b))
                edge_list.append((b, a))

        self.make_dfs(edge_list, self.setpoints)

    def __find_min_max(self, sensor):
        str_max = self.config['DATASET']['max_prefix'] + sensor
        str_min = self.config['DATASET']['min_prefix'] + sensor

        return str_max, str_min

    def find_sensors(self):
        df = pd.read_csv(self.dataset)
        df_cols = list(df.columns)
        actuators_list = [k for k, v, in self.actuators.items()]

        # Se le colonne hanno un unico valore, abbiamo un attuatore di spare o un setpoint settato
        # nei registri, quindi elimino il registro dalla lista
        for col in df_cols[:]:
            if len(df[col].unique()) == 1:
                df_cols.remove(col)

        # Rimuovo dalla lista gli attuatori trovati in precedenza, ottenendo così i soli sensori
        for col in actuators_list:
            df_cols.remove(col)

        df_cols = [x for x in df_cols if not x.startswith(self.config['DATASET']['max_prefix'])
                   and not x.startswith(self.config['DATASET']['min_prefix'])
                   and not x.startswith(self.config['DATASET']['prev_cols_prefix'])
                   and not x.startswith(self.config['DATASET']['trend_cols_prefix'])
                   and not x.startswith(self.config['DATASET']['slope_cols_prefix'])]

        self.sensors = df_cols.copy()

    def __select_actuators(self):
        actuators_list = [x for x, y in self.actuators.items()]
        input_actuators = input(f'Insert actuators [{" ".join(map(str, actuators_list))}]: ')

        if input_actuators:
            input_actuators = input_actuators.split()

            for a in input_actuators:
                if a not in actuators_list:
                    print(f"Actuator {a} does not exist. Aborting")
                    exit(0)
        else:
            input_actuators = actuators_list

        return input_actuators

    def make_daikon_simple_analysis(self):
        sensor = input(f'Insert sensor name [{" ".join(map(str, self.sensors))}]: ')
        str_max, str_min = self.__find_min_max(sensor)

        daikon_condition = ''
        for const in self.setpoints:
            if str_max in const:
                max_v = int(float(const[1]))
                margin = round((max_v / 100) * self.upper_pct_margin)
                daikon_condition += f'&& {sensor} < {self.config["DATASET"]["max_prefix"]}{sensor} - {margin} '
            if str_min in const:
                min_v = int(float(const[1]))
                margin = round((min_v / 100) * self.lower_pct_margin)
                daikon_condition += f'&& {sensor} > {self.config["DATASET"]["min_prefix"]}{sensor} + {margin} '

        for key, val in self.actuators.items():
            for v in val:
                os.chdir(os.path.join(self.config["PATHS"]["project_dir"], self.config["DAIKON"]["daikon_dir"]))
                subprocess.call(f'{os.path.join(self.config["PATHS"]["project_dir"], self.config["DAIKON"]["daikon_dir"], "runDaikon.py")} '
                                f'-f {self.dataset} -c "{key} == {v} {daikon_condition}" -r {key}', shell=True)
                print()

    def make_daikon_custom_analysis(self):
        sensor = input(f'Insert sensor name [{" ".join(map(str, self.sensors))}]: ')
        str_max, str_min = self.__find_min_max(sensor)

        # actuators_list = [key for key, value in self.actuators.items()]
        actuators_list = self.__select_actuators()

        df = pd.read_csv(os.path.join(self.config['PATHS']['project_dir'],
                                      self.config['DAIKON']['daikon_invariants_dir'],
                                      self.dataset),
                         usecols=actuators_list)

        actuators_states = df[actuators_list].drop_duplicates().to_numpy()
        sensor_condition = ''

        for const in self.setpoints:
            if str_max in const:
                # max_v = int(float(const[1]))
                # margin = round((max_v / 100) * int(self.config['DAIKON']['max_security_pct_margin']))
                # sensor_condition += f' && {sensor} < {self.config["DATASET"]["max_prefix"]}{sensor} - {margin}'
                sensor_condition += f' && {sensor} < {self.config["DATASET"]["max_prefix"]}{sensor}'
            if str_min in const:
                # min_v = int(float(const[1]))
                # margin = round((min_v / 100) * int(self.config['DAIKON']['min_security_pct_margin']))
                # sensor_condition += f' && {sensor} > {self.config["DATASET"]["min_prefix"]}{sensor} + {margin}'
                sensor_condition += f' && {sensor} > {self.config["DATASET"]["min_prefix"]}{sensor}'

        for state in actuators_states:
            daikon_condition = list()
            for i in range(len(state)):
                tmp = f'{actuators_list[i]} == {state[i]}'
                daikon_condition.append(tmp)
            daikon_condition = ' && '.join(map(str, daikon_condition)) + sensor_condition

            os.chdir(os.path.join(self.config["PATHS"]["project_dir"], self.config["DAIKON"]["daikon_dir"]))
            subprocess.call(f'{os.path.join(self.config["PATHS"]["project_dir"], self.config["DAIKON"]["daikon_dir"], "runDaikon.py")}'
                            f' -f {self.dataset} -c "{daikon_condition}" -r "Other"', shell=True)
            print()


def main():
    fa = DaikonAnalysis()

    print("Process start")

    # Controllo se esiste la directory dove verranno scritti i file con i risultati. Se non esiste la creo
    if not os.path.exists(os.path.join(
            fa.config["PATHS"]["project_dir"], fa.config["DAIKON"]["daikon_results_dir"])):
        os.makedirs(os.path.join(
            fa.config["PATHS"]["project_dir"], fa.config["DAIKON"]["daikon_results_dir"]))

    fa.find_actuators()
    fa.find_sensors()

    if fa.args.simpleanalysis:
        fa.make_daikon_simple_analysis()

    if fa.args.customanalysis:
        fa.make_daikon_custom_analysis()

    print('\n')


if __name__ == '__main__':
    main()
