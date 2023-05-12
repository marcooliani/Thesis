#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
import glob
import csv
import argparse
import configparser
import subprocess
import math
from rdp import rdp


class MergeDatasets:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-e', "--epsilon", type=int,
                            help="choose granularity in seconds (for slopes)")
        parser.add_argument('-s', "--skiprows", type=int, default=self.config['PREPROC']['skip_rows'],
                            help="skip seconds from start")
        parser.add_argument('-n', "--nrows", type=int, default=self.config['PREPROC']['number_of_rows'],
                            help="number of seconds to consider")
        parser.add_argument('-t', "--timerange", nargs=2,
                            help="time range selection (date format YYYY-MM-DD HH:MM:SS")
        parser.add_argument('-d', "--directory", type=str, default=self.config['PATHS']['input_dataset_directory'],
                            help="directory containing CSV files")
        parser.add_argument('-o', "--output", type=str, default=self.config['PREPROC']['dataset_file'],
                            help="output file")
        parser.add_argument('-p', "--plcs", nargs='+', default=[], help="PLCs to include (w/o path)")
        self.args = parser.parse_args()

        self.epsilon = self.args.epsilon
        self.nrows = self.args.nrows
        # La read_csv() vuole un array con tutte le righe da skippare
        self.skiprows = [row for row in range(1, self.args.skiprows)]
        self.timerange = self.args.timerange
        self.directory = self.args.directory
        self.output_file = self.args.output
        self.plcs = self.args.plcs

    def list_files(self):
        if self.plcs:
            filenames = [f'{self.directory}/{p}' for p in self.plcs]
        else:
            filenames = glob.glob(f'{self.directory}/*.csv')

        return sorted(filenames)

    @staticmethod
    def clean_null(filename):
        print(f'Cleaning null columns from {filename.split("/")[-1]} ...')
        with open(filename, newline='') as f_input:
            csv_input = csv.reader(f_input)
            header = next(csv_input)  # read header
            columns = zip(*list(csv_input))  # read rows and transpose to columns
            data = [(h, c) for h, c in zip(header, columns) if set(c) != set('0')]

        with open(filename, 'w', newline='') as f_output:
            csv_output = csv.writer(f_output)
            csv_output.writerow(h for h, c in data)  # write the new header
            csv_output.writerows(zip(*[c for h, c in data]))

    def __add_setpoints(self, data_set, cols):
        for col in cols:
            data_var = data_set[col]

            # Valore massimo della colonna selezionata
            max_lvl = math.ceil(data_set[col].max())
            # Valore minimo della colonna selezionata
            min_lvl = math.floor(data_set[col].min())
            # Valore medio della colonna selezionata (secondo me non serve...)
            # avg_lvl = round(data_set[col].mean())

            max_val = [max_lvl for _ in range(len(data_var))]
            min_val = [min_lvl for _ in range(len(data_var))]

            data_set.insert(len(data_set.columns), self.config['DATASET']['max_prefix'] + col, max_val)
            data_set.insert(len(data_set.columns), self.config['DATASET']['min_prefix'] + col, min_val)

        return data_set

    @staticmethod
    def truncate_float(num, dec):
        if num > 0:
            return math.floor(num * 10 ** dec) / 10 ** dec
        elif num < 0:
            return math.ceil(num * 10 ** dec) / 10 ** dec

    def __add_slopes(self, data_set, cols):
        # Genero e aggiungo le colonne slope_

        slope = [None for _ in range(len(data_set))]

        for col in cols:
            ind = [i for i in data_set[col].index]
            vals = data_set[col].values.tolist()

            points = np.column_stack([ind, vals])
            points_rdp = rdp(points, epsilon=self.epsilon)

            for i in range(1, len(points_rdp)):
                s = (points_rdp[i][1] - points_rdp[i-1][1]) / (points_rdp[i][0] - points_rdp[i-1][0])
                print(points_rdp[i-1][0], points_rdp[i][0], self.truncate_float(s, 2))
                for j in range(int(points_rdp[i-1][0]), int(points_rdp[i][0])):
                    if self.truncate_floati(s, 2) > 0:
                        slope[j] = 1
                    elif self.truncate_float(s, 2) < 0:
                        slope[j] = -1
                    else:
                        slope[j] = 0

            data_set.insert(len(data_set.columns), self.config['DATASET']['slope_cols_prefix'] + col, slope)

        return data_set

    def __add_prevs(self, data_set, cols):
        # Genero e aggiungo le colonne prev_
        for col in cols:
            prev_val = list()
            prev_val.append(0)
            data_var = data_set[col]

            for i in range(len(data_var) - 1):
                prev_val.append(data_var[i])

            data_set.insert(len(data_set.columns), self.config['DATASET']['prev_cols_prefix'] + col, prev_val)

        return data_set

    # Enrich the dataset with a partial bounded history of registers
    # Add previous values of registers
    def enrich_df(self, dataset, filename):
        print(f'Enriching {filename.split("/")[-1]}. This may take a while ...')

        data_set = None
        val_cols_max_min = None
        val_cols_slopes = None
        val_cols_prevs = None

        if self.config['DATASET']['max_min_cols_list']:
            val_cols_max_min = dataset.columns[
                dataset.columns.str.contains(pat=self.config['DATASET']['max_min_cols_list'], case=False, regex=True)]
        if self.config['DATASET']['slope_cols_list']:
            val_cols_slopes = dataset.columns[
                dataset.columns.str.contains(pat=self.config['DATASET']['slope_cols_list'], case=False, regex=True)]
        if self.config['DATASET']['prev_cols_list']:
            val_cols_prevs = dataset.columns[
                dataset.columns.str.contains(pat=self.config['DATASET']['prev_cols_list'], case=False, regex=True)]

        if self.config['DATASET']['max_min_cols_list']:
            data_set = self.__add_setpoints(dataset, val_cols_max_min)
        if self.config['DATASET']['slope_cols_list']:
            if data_set is not None:
                data_set = self.__add_slopes(data_set, val_cols_slopes)
            else:
                data_set = self.__add_slopes(dataset, val_cols_slopes)
        if self.config['DATASET']['prev_cols_list']:
            if data_set is not None:
                data_set = self.__add_prevs(data_set, val_cols_prevs)
            else:
                data_set = self.__add_prevs(dataset, val_cols_prevs)

        # Se i campi dell'enrichment sono tutti vuoti, anche data_set è vuoto. Quindi ritorno dataset, passato
        # in ingresso
        if data_set is not None:
            return data_set
        else:
            return dataset

    def get_datasets_lists(self):
        filenames = self.list_files()

        df_list_mining = list()
        df_list_daikon = list()

        for file in sorted(filenames):
            # Read Dataset files
            # nrows indica il numero di righe da considerare. Se si vuole partire da una certa riga,
            # usare skiprows=<int>, che skippa n righe da inizio file
            print(f'Reading {file.split("/")[-1]} ...')

            if self.timerange:
                df = pd.read_csv(file)
                df.columns = df.columns.str.replace('.', '_', regex=False)
                df[self.config['DATASET']['timestamp_col']] = \
                    df[self.config['DATASET']['timestamp_col']].apply(lambda x:
                                                                      pd.Timestamp(x).strftime('%Y-%m-%d %H:%M:%S.%f'))
                df = df.loc[df[self.config['DATASET']['timestamp_col']].between(self.timerange[0],
                                                                                self.timerange[1],
                                                                                inclusive="both")]
            else:
                df = pd.read_csv(file, skiprows=self.skiprows, nrows=self.nrows)
                df.columns = df.columns.str.replace('.', '_', regex=False)

                if self.config['DATASET']['timestamp_col'] in df.columns:
                    df[self.config['DATASET']['timestamp_col']] = \
                        df[self.config['DATASET']['timestamp_col']].apply(lambda x: pd.Timestamp(x).strftime(
                            '%Y-%m-%d %H:%M:%S.%f'))

            # I punti nei nomi delle colonne creano parecchi problemi, quindi vanno sostituiti
            # datasetPLC.columns = datasetPLC.columns.str.replace('.', '_', regex=False)
            # print(datasetPLC.isnull().values.any()) # Debug NaN

            # Removing empty registers (the registers with values equal to 0 are not used in the control of the CPS)
            self.clean_null(file)

            datasetPLC_daikon = df.copy()  # Altrimenti non mi differenzia le liste, vai a capire perchè...

            # Concatenate the single PLCs datasets for process mining
            df_list_mining.append(df)

            # Add previous values, slopes and limits to dataframe
            datasetPLC_daikon = self.enrich_df(datasetPLC_daikon, file)
            # Concatenate the single PLCs datasets for Daikon
            df_list_daikon.append(datasetPLC_daikon)

        return df_list_mining, df_list_daikon

    @staticmethod
    def __concat_datasets(datasets_list):
        df = pd.concat(datasets_list, axis=1).reset_index(drop=True)
        df = df.T.drop_duplicates().T  # Drop dup columns in the dataframe (i.e. Timestamps)

        return df

    def save_mining_dataset(self, datasets_list):
        mining_datasets = self.__concat_datasets(datasets_list)
        # Save dataset with the timestamp for the process mining.
        mining_datasets.to_csv(
            f'{os.path.join(self.config["PATHS"]["project_dir"], self.config["MINING"]["data_dir"], self.output_file.split(".")[0])}_TS.csv',
            index=False)
        # print(mining_datasets)  # Debug

    def save_daikon_dataset(self, datasets_list):
        daikon_datasets = self.__concat_datasets(datasets_list)

        # drop timestamps is NOT needed in Daikon
        if self.config['DATASET']['timestamp_col'] in daikon_datasets.columns:
            daikon_datasets = daikon_datasets.drop(self.config['DATASET']['timestamp_col'], axis=1, errors='ignore')

        # Drop first rows (Daikon does not process missing values)
        daikon_datasets = daikon_datasets.iloc[1:-1, :]
        daikon_datasets.to_csv(
            f'{os.path.join(self.config["PATHS"]["project_dir"], self.config["DAIKON"]["daikon_invariants_dir"], self.output_file)}',
            index=False)
        # print(daikon_datasets)  # Debug


def main():
    mg = MergeDatasets()

    # CSV files converted from JSON PLCs readings (convertoCSV.py)
    df_list_mining, df_list_daikon = mg.get_datasets_lists()

    print(f'Generating Process Mining dataset ...')
    mg.save_mining_dataset(df_list_mining)
    print('Process Mining dataset generated successfully')

    print(f'Generating Invariants Analysis dataset ...')
    mg.save_daikon_dataset(df_list_daikon)
    print('Invariants Analysis dataset generated successfully')

    print()

    choice = input("Do you want to perform a brief analysis of the dataset? [y/n]: ")
    while choice != 'Y' or choice != 'y' or choice != 'N' or choice != 'n' or choice != '':
        if choice == 'Y' or choice == 'y':
            subprocess.call(f'./system_info.py -f {mg.output_file}', shell=True)
            break
        elif choice == 'N' or choice == 'n' or choice == '':
            break
        else:
            choice = input("Do you want to perform a brief analysis of the dataset? [y/n]: ")


if __name__ == '__main__':
    main()
