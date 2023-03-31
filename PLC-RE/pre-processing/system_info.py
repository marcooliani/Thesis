#!/usr/bin/env python3

import pandas as pd
import os
import argparse
import configparser
import subprocess
import re
from collections import defaultdict


class SystemInfo:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        group = parser.add_argument_group()

        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        parser.add_argument('-a', "--actuators", nargs='+', help="name of the input dataset file (CSV format)")
        parser.add_argument('-s', "--sensors", nargs='+', help="name of the input dataset file (CSV format)")

        self.args = parser.parse_args()

        self.dataset = self.args.filename
        self.actuators = defaultdict(list)
        self.sensors = defaultdict(dict)
        self.setpoints = defaultdict(dict)

        os.chdir(os.path.join(self.config['PATHS']['project_dir'], self.config['DAIKON']['daikon_invariants_dir']))

    def __call_daikon(self):
        dataset_name = self.dataset.split('.')[0]

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

    def find_actuators_list(self):
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

        # print(self.actuators)
        print("Actuators: ")
        for k, v in self.actuators.items():
            print(f'{k} {v}')
        print()

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

        for col in df_cols:
            self.sensors[col]['max_lvl'] = round(df[col].max(), 1)
            self.sensors[col]['min_lvl'] = round(df[col].min(), 1)

        # print(self.sensors)
        print("Sensors: ")
        for k, v in self.sensors.items():
            print(f'{k} {v}')
        print()

    def find_setpoints_spares(self):
        df = pd.read_csv(self.dataset)
        df_cols = list(df.columns)

        df_cols = [x for x in df_cols if not x.startswith(self.config['DATASET']['max_prefix'])
                   and not x.startswith(self.config['DATASET']['min_prefix'])
                   and not x.startswith(self.config['DATASET']['prev_cols_prefix'])
                   and not x.startswith(self.config['DATASET']['trend_cols_prefix'])
                   and not x.startswith(self.config['DATASET']['slope_cols_prefix'])]

        for col in df_cols[:]:
            if len(df[col].unique()) == 1:
                self.setpoints[col] = df[col].unique()[0]

        # print(self.setpoints)
        print("Hardcoded setpoints or spare actuators: ")
        for k, v in self.setpoints.items():
            print(f'{k} {v}')
        print()

    def actuator_status_change(self):
        actuators = defaultdict(dict)
        sensors = defaultdict(dict)

        if self.args.actuators:
            for act in self.args.actuators:
                if act in self.actuators:
                    actuators[act] = self.actuators[act]
        else:
            actuators = self.actuators

        if self.args.sensors:
            for sensor in self.args.sensors:
                if sensor in self.sensors:
                    sensors[sensor] = self.sensors[sensor]
        else:
            sensors = self.sensors

        for actuator, _ in actuators.items():
            for sensor, _ in sensors.items():
                df = pd.read_csv(self.dataset,
                                 usecols=[actuator, self.config["DATASET"]["prev_cols_prefix"] + actuator, sensor])

                for v in actuators[actuator]:
                    print(df[df.eval(f'{actuator} == {v} '
                                     f'and {self.config["DATASET"]["prev_cols_prefix"]}{actuator} != {v}')])
                    print()


def main():
    si = SystemInfo()
    si.find_actuators_list()
    si.find_sensors()
    si.find_setpoints_spares()
    # si.actuator_status_change()


if __name__ == '__main__':
    main()
