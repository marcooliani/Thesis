#!/usr/bin/env python3

import pandas as pd
import os
import argparse
import configparser
import subprocess
import re


class ActuatorsBehaviour:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        parser.add_argument('-l', "--actuatorslist", default=False, help="print actuators list")
        parser.add_argument('-a', "--actuator", type=str, required=True, help="actuator's name")
        parser.add_argument('-s', "--sensor", type=str, required=True, help="sensor's name")
        self.args = parser.parse_args()

        self.dataset = self.config['DEFAULTS']['dataset_file']
        self.actuators = dict()
        self.setpoints = list()

        self.actuator = None
        self.sensor = None

    def check_args(self):
        if self.args.filename is not None:
            if self.args.filename.split('.')[-1] != "csv":
                print("Invalid file format (must be .csv). Aborting")
                exit(1)
            self.dataset = self.args.filename

        self.actuator = self.args.actuator
        self.sensor = self.args.sensor

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

    def find_single_actuator(self, output):
        for inv in output:
            if 'one of' in inv and self.config['DATASET']['prev_cols_prefix'] not in inv and \
                    self.config['DATASET']['slope_cols_prefix'] not in inv and \
                    self.actuator in inv:
                a, b = inv.split(' one of ')
                a.replace('(', '').replace(')', '')
                b = [float(i) for i in b.replace('{ ', '').replace(' }', '').replace(',', '').split(' ')]

                self.actuators[a] = b

                return

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

    def actuator_status_change(self, file, actuator, sensor):
        df = pd.read_csv(file, usecols=[actuator, self.config["DATASET"]["prev_cols_prefix"] + actuator, sensor])

        for v in self.actuators[actuator]:
            print(df[df.eval(f'{actuator} == {v} and {self.config["DATASET"]["prev_cols_prefix"]}{actuator} != {v}')])
            print()

    def actuator_status_period(self, file, actuator):
        df = pd.read_csv(file, encoding='utf-8', usecols=[actuator])
        vals_act = [x for x in df[actuator]]

        for v in self.actuators[actuator]:
            period = list()
            count_vals = 0
            for i in range(1, len(vals_act)):
                if vals_act[i] == v and vals_act[i-1] != v:
                    count_vals += 1
                elif vals_act[i] == v and vals_act[i-1] == v:
                    count_vals += 1
                elif vals_act[i] != v and vals_act[i-1] == v:
                    count_vals += 1
                    period.append(count_vals)
                    count_vals = 0

            print(f'{actuator} == {v}')
            print('  '.join(map(str, period)))
            print()


def main():
    ab = ActuatorsBehaviour()
    ab.check_args()
    start_dir = os.getcwd()

    if os.chdir('Daikon_Invariants/'):
        print("Error generating invariants. Aborting.")
        exit(1)
    # print(ab.actuators)
    # print(ab.setpoints)
    output = ab.call_daikon()
    ab.find_single_actuator(output)

    ab.actuator_status_change(ab.dataset, ab.actuator, ab.sensor)
    ab.actuator_status_period(ab.dataset, ab.actuator)


if __name__ == '__main__':
    main()
