import findActuators as fA
import pandas as pd
import numpy as np
import os
import configparser
import argparse


class ActuatorsBehaviour:
    def __init__(self):
        fa = fA.FindActuators()

        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        self.args = parser.parse_args()

        self.dataset = self.config['DEFAULTS']['dataset_file']

        self.start_dir = os.getcwd()

        if os.chdir('Daikon_Invariants/'):
            print("Error generating invariants. Aborting.")
            exit(1)

        out = fa.call_daikon()
        fa.parse_output(out)
        fa.find_setpoints(out)

        self.actuators = fa.actuators
        self.setpoints = fa.setpoints

    @staticmethod
    def open_dataframe(file, actuator, sensor):
        df = pd.read_csv(file, usecols=[actuator, 'prev_' + actuator, sensor])
        # print(df.keys())
        # print(df[(df[actuator] == 2) & (df['prev_'+actuator] != 2)].count())
        print(df[df.eval(f'{actuator} == 0 and prev_{actuator} != 0')])


def main():
    ab = ActuatorsBehaviour()
    # print(ab.actuators)
    # print(ab.setpoints)

    ab.open_dataframe(ab.dataset, 'MV201', 'LIT301')


if __name__ == '__main__':
    main()
