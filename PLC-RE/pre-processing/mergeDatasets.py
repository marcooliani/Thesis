#!/usr/bin/env python3

import numpy as np
import pandas as pd
import glob
import csv
import argparse
import configparser
import math

from statsmodels.tsa.seasonal import seasonal_decompose, STL


class MergeDatasets:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-g', "--granularity", type=int, help="choose granularity in seconds (for slopes)")
        parser.add_argument('-s', "--skiprows", type=int, help="skip seconds from start")
        parser.add_argument('-n', "--nrows", type=int, help="number of seconds to consider")
        parser.add_argument('-d', "--directory", type=str, help="directory containing CSV files")
        parser.add_argument('-o', "--output", type=str, help="output file")
        parser.add_argument('-p', "--plcs", nargs='+', default=[], help="PLCs to include (w/o path)")
        self.args = parser.parse_args()

        #self.granularity = int(self.config['DEFAULTS']['granularity'])
        self.granularity = None
        self.nrows = int(self.config['DEFAULTS']['number_of_rows'])
        self.skiprows = [row for row in range(1, self.args.skiprows)]
        self.directory = self.config['PATHS']['input_dataset_directory']
        self.output_file = self.config['DEFAULTS']['dataset_file']
        self.plcs = []

    def check_args(self):
        if self.args.granularity:
            self.granularity = self.args.granularity
        else:
            self.granularity = int(self.config['DEFAULTS']['granularity'])

        if self.args.nrows:
            self.nrows = self.args.nrows

        if self.args.skiprows:
            # Skip di tutte le prime row righe tranne l'header
            self.skiprows = [row for row in range(1, self.args.skiprows)]

        if self.args.directory is not None:
            self.directory = self.args.directory

        if self.args.output is not None:
            if self.args.output.split('.')[-1] != 'csv':
                print('Invalid file format (must be .csv). Aborting')
                exit(1)
            self.output_file = self.args.output

        if self.args.plcs is not None:
            self.plcs = [p for p in self.args.plcs]

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

    # Enrich the dataset with a partial bounded history of registers
    # Add previous values of registers
    def enrich_df(self, data_set, filename):
        print(f'Enriching {filename.split("/")[-1]}. This may take a while ...')
        # Set registers names that holds measurements and actuations
        val_cols_prevs = data_set.columns[
            data_set.columns.str.contains(pat=self.config['DATASET']['prev_cols_list'], case=False, regex=True)]
        val_cols_slopes = data_set.columns[
            data_set.columns.str.contains(pat=self.config['DATASET']['slope_cols_list'], case=False, regex=True)]
        val_cols_trends = data_set.columns[
            data_set.columns.str.contains(pat=self.config['DATASET']['trend_cols_list'], case=False, regex=True)]
        val_cols_max_min = data_set.columns[
            data_set.columns.str.contains(pat=self.config['DATASET']['max_min_cols_list'], case=False, regex=True)]

        for col in val_cols_max_min:
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

        for col in val_cols_trends:
            # decomposition = seasonal_decompose(np.array(data_set[col]), model='additive', period=120)
            stl = STL(data_set[col], period=int(self.config['DATASET']['trend_period']), robust=True)
            decomposition = stl.fit()
            col_trend = [x for x in decomposition.trend]

            data_set.insert(len(data_set.columns), self.config['DATASET']['trend_cols_prefix'] + col, col_trend)

        # Genero e aggiungo le colonne slope_
        for col in val_cols_slopes:
            data_var = data_set[self.config['DATASET']['trend_cols_prefix'] + col]

            mean_slope = [0 for _ in range(len(data_var))]

            for i in range(len(data_var)):
                if i % self.granularity == 0 and i + self.granularity <= len(data_var)-1:
                    for j in range(i, (i + self.granularity)):
                        # mean_slope[j] = round((data_var[i + self.granularity] - data_var[i]) / self.granularity, 2)
                        if round((data_var[i + self.granularity] - data_var[i]) / self.granularity, 2) > 0:
                            # mean_slope[j] = math.ceil(round((data_var[i + self.granularity] - data_var[i]) / self.granularity, 2))
                            mean_slope[j] = 1
                        elif round((data_var[i + self.granularity] - data_var[i]) / self.granularity, 2) < 0:
                            # mean_slope[j] = math.floor(round((data_var[i + self.granularity] - data_var[i]) / self.granularity, 2))
                            mean_slope[j] = -1
                        else:
                            mean_slope[j] = 0

            data_set.insert(len(data_set.columns), self.config['DATASET']['slope_cols_prefix'] + col, mean_slope)

        # Genero e aggiungo le colonne prev_
        for col in val_cols_prevs:
            prev_val = list()
            prev_val.append(0)
            data_var = data_set[col]

            for i in range(len(data_var) - 1):
                prev_val.append(data_var[i])

            data_set.insert(len(data_set.columns), self.config['DATASET']['prev_cols_prefix'] + col, prev_val)

    @staticmethod
    def concat_datasets(datasets_list):
        df = pd.concat(datasets_list, axis=1).reset_index(drop=True)
        return df

    @staticmethod
    def add_zeros_column(dataframe):
        print(f'Add zeros column to dataframe')
        zero_col = [0 for _ in range(dataframe.shape[0])]
        dataframe.insert(len(dataframe.columns), "zero_col", zero_col)


def main():
    mg = MergeDatasets()

    mg.check_args()

    # CSV files converted from JSON PLCs readings (convertoCSV.py)
    if mg.plcs:
        filenames = [f'{mg.directory}/' + p for p in mg.plcs]
    else:
        filenames = glob.glob(f'{mg.directory}/*.csv')

    df_list_mining = list()
    df_list_daikon = list()

    for file in sorted(filenames):
        # Read Dataset files
        # nrows indica il numero di righe da considerare. Se si vuole partire da una certa riga,
        # usare skiprows=<int>, che skippa n righe da inizio file
        print(f'Reading {file.split("/")[-1]} ...')
        datasetPLC = pd.read_csv(file, skiprows=mg.skiprows, nrows=mg.nrows)
        datasetPLC[mg.config['DATASET']['timestamp_col']] = \
            datasetPLC[mg.config['DATASET']['timestamp_col']].apply(lambda x:
                                                                    pd.Timestamp(x).strftime('%Y-%m-%d %H:%M:%S.%f'))
        # print(datasetPLC.isnull().values.any()) # Debug NaN

        # Removing empty registers (the registers with values equal to 0 are not used in the control of the CPS)
        mg.clean_null(file)

        datasetPLC_daikon = datasetPLC.copy()  # Altrimenti non mi differenzia le liste, vai a capire perchè...

        # Concatenate the single PLCs datasets for process mining
        df_list_mining.append(datasetPLC)

        # Add previous values, slopes and limits to dataframe
        mg.enrich_df(datasetPLC_daikon, file)
        # Concatenate the single PLCs datasets for Daikon
        df_list_daikon.append(datasetPLC_daikon)

    print(f'Generating Process Mining dataset ...')
    mining_datasets = mg.concat_datasets(df_list_mining)
    # Save dataset with the timestamp for the process mining.
    mining_datasets.to_csv(f'../process-mining/data/{mg.output_file.split(".")[0]}_TS.csv', index=False)
    # print(mining_datasets)  # Debug
    print('Process Mining dataset generated successfully')

    print(f'Generating Invariants Analysis dataset ...')
    daikon_datasets = mg.concat_datasets(df_list_daikon)
    # mg.add_zeros_column(daikon_datasets)  # Maybe not necessary

    # drop timestamps is NOT needed in Daikon
    daikon_datasets = daikon_datasets.drop(mg.config['DATASET']['timestamp_col'], axis=1, errors='ignore')

    # Drop first rows (Daikon does not process missing values)
    # Taglio anche le ultime righe, che hanno lo slope = 0
    # daikon_datasets = daikon_datasets.iloc[::mg.granularity, :] # Prendo solo le n-granularities righe
    daikon_datasets = daikon_datasets.iloc[1:-mg.granularity, :]
    daikon_datasets.to_csv(f'../daikon/Daikon_Invariants/{mg.output_file}', index=False)
    # print(daikon_datasets)  # Debug
    print('Invariants Analysis dataset generated successfully')


if __name__ == '__main__':
    main()
