#!/usr/bin/env python3

import pandas as pd
import glob
import csv
import argparse
import configparser
import math

parser = argparse.ArgumentParser()
parser.add_argument('-g', "--granularity", type=int, help="choose granularity in seconds")
parser.add_argument('-s', "--skiprows", type=int, help="skip seconds from start")
parser.add_argument('-n', "--nrows", type=int, help="number of seconds to consider")
parser.add_argument('-d', "--directory", type=str, help="directory containing CSV files")
parser.add_argument('-o', "--output", type=str, help="output file")
parser.add_argument('-p', "--plcs", nargs='+', default=[], help="PLCs to include (w/o path)")
args = parser.parse_args()

config = configparser.ConfigParser()
config.read('../config.ini')

if args.granularity:
    granularity = args.granularity
else:
    granularity = int(config['DEFAULTS']['granularity'])

if args.nrows:
    nrows = args.nrows
else:
    nrows = int(config['DEFAULTS']['number_of_rows'])

if args.skiprows:
    # Skip di tutte le prime row righe tranne l'header
    skiprows = [row for row in range(1, args.skiprows)]
else:
    # skiprows = 0
    skiprows = [row for row in range(1, int(config['DEFAULTS']['skip_rows']))]

if args.directory is not None:
    directory = args.directory
else:
    # Da rivedere...
    directory = config['PATHS']['input_dataset_directory']

if args.output is not None:
    if args.output.split('.')[-1] != 'csv':
        print('Invalid file format (must be .csv). Aborting')
        exit(1)
    output_file = args.output
else:
    output_file = config['DEFAULTS']['dataset_file']

if args.plcs is not None:
    plcs = [p for p in args.plcs]
else:
    plcs = []

# CSV files converted from JSON PLCs readings (convertoCSV.py)
# filenames = glob.glob("PLC_CSV/*.csv")
if plcs:
    filenames = [f'{directory}/' + p for p in plcs]
else:
    filenames = glob.glob(f"{directory}/*.csv")


def cleanNull(filenames):
    for f in filenames:
        with open(f, newline='') as f_input:
            csv_input = csv.reader(f_input)
            header = next(csv_input)  # read header
            columns = zip(*list(csv_input))  # read rows and transpose to columns
            data = [(h, c) for h, c in zip(header, columns) if set(c) != set('0')]

        with open(f, 'w', newline='') as f_output:
            csv_output = csv.writer(f_output)
            csv_output.writerow(h for h, c in data)  # write the new header
            csv_output.writerows(zip(*[c for h, c in data]))
        print(f + 'done')


# Enrich the dataset with a partial bounded history of registers
# Add previous values of registers
def enrich_df(data_set):
    # Set registers names that holds measurements and actuations
    val_cols = data_set.columns[data_set.columns.str.contains(pat=config['DATASET']['prev_cols_list'], case=False, regex=True)]
    val_cols_slopes = data_set.columns[data_set.columns.str.contains(pat=config['DATASET']['slope_cols_list'], case=False, regex=True)]

    # Genero e aggiungo le colonne prev_
    for col in val_cols:
        prev_val = list()
        prev_val.append(0)
        # data_var = inv_datasets[col]
        data_var = data_set[col]

        for i in range(len(data_var) - 1):
            prev_val.append(data_var[i])

        data_set.insert(len(data_set.columns), config['DATASET']['prev_cols_prefix'] + col, prev_val)

    # Genero e aggiungo le colonne slope_
    for col in val_cols_slopes:
        mean_slope = list()
        max_val = list()
        min_val = list()
        data_var = data_set[col]

        # Valore massimo della colonna selezionata
        max_lvl = math.ceil(data_set[col].max())
        # Valore minimo della colonna selezionata
        min_lvl = math.floor(data_set[col].min())
        # Valore medio della colonna selezionata (secondo me non serve...)
        # avg_lvl = round(data_set[col].mean())

        prev_lvl = data_var[0]

        for i in range(len(data_var)):
            if i % granularity != 0:
                mean_slope.append(0)
            else:
                slope = round((data_var[i] - prev_lvl) / granularity, 1)
                # slope = round((data_var[i] - prev_lvl), 1)
                mean_slope.append(slope)
                prev_lvl = data_var[i]

                if i > 0:
                    for j in range(i - 1, (i - granularity), -1):
                        mean_slope[j] = slope

            max_val.append(max_lvl)
            min_val.append(min_lvl)

        data_set.insert(len(data_set.columns), config['DATASET']['slope_cols_prefix'] + col, mean_slope)
        data_set.insert(len(data_set.columns), config['DATASET']['max_prefix'] + col, max_val)
        data_set.insert(len(data_set.columns), config['DATASET']['min_prefix'] + col, min_val)


# Removing empty registers (the registers with values equal to 0 are not used in the control of the CPS)
cleanNull(filenames)

df_list_mining = list()
df_list_daikon = list()

for f in sorted(filenames):
    # Read Dataset files
    # nrows indica il numero di righe da considerare. Se si vuole partire da una certa riga,
    # usare skiprows=<int>, che skippa n righe da inizio file
    datasetPLC = pd.read_csv(f, skiprows=skiprows, nrows=nrows)
    datasetPLC_d = datasetPLC.copy()  # Altrimenti non mi differenzia le liste, vai a capire perchè...

    # Concatenate the single PLCs datasets for process mining
    df_list_mining.append(datasetPLC)

    # Add previous values, slopes and limits to dataframe
    enrich_df(datasetPLC_d)
    # Concatenate the single PLCs datasets for Daikon
    df_list_daikon.append(datasetPLC_d)

mining_datasets = pd.concat(df_list_mining, axis=1).reset_index(drop=True)
daikon_datasets = pd.concat(df_list_daikon, axis=1).reset_index(drop=True)

# Save dataset with the timestamp for the process mining.
# mining_datasets.to_csv(r'../process-mining/data/PLC_SWaT_Dataset_TS.csv', index=False)
mining_datasets.to_csv(f'../process-mining/data/{output_file.split(".")[0]}_TS.csv', index=False)

print(mining_datasets)

print('************************************************************************************')
print('************* DATASET FOR PROCESS MINING GENERATED SUCCESSFULLY *******************')
print('************************************************************************************')

# drop timestamps is NOT needed in Daikon
# inv_datasets = daikon_datasets.drop(['Timestamp'], axis=1, errors='ignore')
inv_datasets = daikon_datasets.drop(config['DATASET']['timestamp_col'], axis=1, errors='ignore')

# Drop first rows (Daikon does not process missing values)
# Taglio anche le ultime righe, che hanno lo slope = 0
inv_datasets = inv_datasets.iloc[1:-granularity, :]
print(inv_datasets)

# inv_datasets.to_csv(r'../daikon/Daikon_Invariants/PLC_SWaT_Dataset.csv', index=False)
inv_datasets.to_csv(f'../daikon/Daikon_Invariants/{output_file}', index=False)

print('****************************************************************************************')
print('************* DATASET FOR INVARIANT ANALYSIS GENERATED SUCCESSFULLY *******************')
print('****************************************************************************************')
