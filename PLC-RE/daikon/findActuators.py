#!/usr/bin/env python3

import os
import re
import subprocess
import networkx as nx
import argparse
import configparser


class FindActuators:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        self.args = parser.parse_args()

        self.dataset = self.config['DEFAULTS']['dataset_file']
        self.actuators = dict()
        self.constants = list()

    def check_args(self):
        if self.args.filename is not None:
            if self.args.filename.split('.')[-1] != "csv":
                print("Invalid file format (must be .csv). Aborting")
                exit(1)
            self.dataset = self.args.filename

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

        return output

    def find_constants(self, daikon_output):
        edge_list = list()
        for invariant in daikon_output:
            if ' == ' in invariant and self.config['DATASET']['prev_cols_prefix'] not in invariant and '%' not in invariant:
                a, b = invariant.split(' == ')
                edge_list.append((a, b))
                edge_list.append((b, a))

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
                        temp.append(a)
                        visited.append(a)
                    if b not in visited or b.lstrip('-').replace('.', '', 1).isdigit():
                        visited.append(b)
                        temp.append(b)

                # Inserisco la lista di nodi nel listone delle invarianti
                self.constants.append(temp)

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
        output = output.decode("utf-8")
        output = re.sub('[=]{6,}', '', output)
        output = output.split('\n')[6:-2]

        for inv in output:
            if 'one of' in inv and self.config['DATASET']['prev_cols_prefix'] not in inv:
                a, b = inv.split(' one of ')
                a.replace('(', '').replace(')', '')
                b = [float(i) for i in b.replace('{ ', '').replace(' }', '').replace(',', '').split(' ')]

                self.actuators[a] = b

                equals = self.find_other_actuators(a, output)
                for act in equals:
                    self.actuators[act] = b

        self.find_constants(output)

        # print(self.actuators)
        # print(self.constants)

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


def main():
    fa = FindActuators()

    fa.check_args()
    start_dir = os.getcwd()
    print("Process start")
    if os.chdir('Daikon_Invariants/'):
        print("Error generating invariants. Aborting.")
        exit(1)

    # Controllo se esiste la directory dove verranno scritti i file con i risultati. Se non esiste la creo
    if not os.path.exists(fa.config["DAIKON"]["daikon_results_dir"]):
        os.makedirs(fa.config["DAIKON"]["daikon_results_dir"])

    daikon_output = fa.call_daikon()
    fa.parse_output(daikon_output)

    fa.print_info()
    os.chdir(start_dir)

    # TODO: occhio che qui non va bene nulla! Intanto devo recuperare in qualche modo qual è la tanica,
    # TODO: (non me la dà in automatico Daikon!) e da lì poi calcolare i margini di min e max (che devo
    # TODO: riotteenere in qualche modo dall'array delle costanti). Il tutto assumendo che magari posso o
    # TODO: non avere la tanica, o avere proprio un'altra cosa di cui però voglio verificare il livello...

    print('\n')
    res = input('Perform Daikon analysis? [y/n] ')
    if res == 'Y' or res == 'y':
        sensor = input('Insert sensor name: ')
        for key, val in fa.actuators.items():
            for v in val:
                subprocess.call(f'./runDaikon.py -c '
                                f'"{key} == {v} && {sensor} < max_{sensor} -20 && {sensor} > min_{sensor} +20" '
                                f'-r {key}',
                                shell=True)
                print()


if __name__ == '__main__':
    main()
