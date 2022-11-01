#!/usr/bin/env python3

import sys
import pandas as pd 
import glob
import csv
import argparse
import math

parser = argparse.ArgumentParser()
parser.add_argument('-g', "--granularity", type=int, help="choose granularity in seconds")
parser.add_argument('-s', "--skiprows", type=int, help="skip seconds from start")
parser.add_argument('-n', "--nrows", type=int, help="number of seconds to consider")
parser.add_argument('-d', "--directory", type=str, help="directory containing CSV files")
parser.add_argument('-o', "--output", type=str, help="output file")
parser.add_argument('-p', "--plcs", nargs='+', default=[], help="PLCs to include (w/o path)")
args = parser.parse_args()

if args.granularity:
  granularity = args.granularity
else:
  granularity = 30

if args.nrows:
  nrows =  args.nrows
else:
  nrows = 86400

if args.skiprows:
  skiprows = [row for row in range(1, args.skiprows)]
else:
  skiprows = ''

if args.directory != None:
  directory = args.directory
else:
  directory = '../../datasets_SWaT'

if args.output != None:
  if args.output.split('.')[-1] != 'csv':
    print('Invalid file format (must be .csv). Aborting')
    exit(1)
  output_file = args.output
else:
  output_file = 'PLC_SWaT_Dataset.csv'

if args.plcs != None:
  plcs = [p for p in args.plcs]
else:
  plcs = []

#CSV files converted from JSON PLCs readings (convertoCSV.py)
#filenames = glob.glob("PLC_CSV/*.csv")
if plcs != []:
  filenames = [f'{directory}/' + p for p in plcs ]
else:
  filenames = glob.glob(f"{directory}/*.csv")

def cleanNull(filenames):
  for f in filenames :
    with open(f, newline='') as f_input:
        csv_input = csv.reader(f_input)
        header = next(csv_input)   # read header
        columns = zip(*list(csv_input))   # read rows and transpose to columns
        data = [(h, c) for h, c in zip(header, columns) if set(c) != set('0')]
        
    with open(f, 'w', newline='') as f_output:
        csv_output = csv.writer(f_output)
        csv_output.writerow(h for h, c in data)   # write the new header
        csv_output.writerows(zip(*[c for h, c in data]))
    print(f + 'done')

# Enrich the dataset with a partial bounded history of registers
# Add previous values of registers
def enrich_df(data_set):
  #Set registers names that holds measurements and actuations
  val_cols = data_set.columns[data_set.columns.str.contains(pat = 'LIT|mv[0-9]{3}|p[0-9]{3}', case=False, regex=True)]
  val_cols_slopes = data_set.columns[data_set.columns.str.contains(pat = 'LIT', case=False, regex=True)]

  for col in val_cols:
    prev_val = list()
    prev_val.append(0)
    slope = list()
    mean_slope=list()
    max_val=list()
    min_val=list()
    #data_var = inv_datasets[col]
    data_var = data_set[col]

    for i in range(len(data_var)-1) : 
      prev_val.append(data_var[i])

    for i in range(len(data_var)):
      if col in val_cols_slopes:
        slope.append(data_var[i] - prev_val[i])

    if col in val_cols_slopes:
      # Valore massimo della colonna selezionata
      max_lev = math.floor(data_set[col].max())
      # Valore minimo della colonna selezionata
      min_lev = math.ceil(data_set[col].min())
      # Valore medio della colonna selezionata (secondo me non serve...)
      #avg_lev = round(data_set[col].mean())

      sum_slope=0
      for i in range(len(data_var)):
        if i%granularity != 0:
          sum_slope += slope[i]
          mean_slope.append(0)
        else:
          if sum_slope/granularity > 0:
            mean_slope.append(1)
          else:
            mean_slope.append(-1)
          if i > 0:
            for j in range(i-1, (i-granularity), -1):
              if sum_slope/granularity > 0:
                mean_slope[j] = 1
              else:
                mean_slope[j] = -1
          sum_slope=0

        max_val.append(max_lev)
        min_val.append(min_lev)

    data_set.insert(len(data_set.columns),'prev_'+col, prev_val)

    if col in val_cols_slopes:
      data_set.insert(len(data_set.columns),'slope_'+col, mean_slope)
      data_set.insert(len(data_set.columns),'max_'+col, max_val)
      data_set.insert(len(data_set.columns),'min_'+col, min_val)


# Removing empty registers (the registers with values equal to 0 are not used in the control of the CPS)
cleanNull(filenames)

df_list_mining = list()
df_list_daikon = list()

for f in filenames:
  #Read Dataset files
  #datasetPLC = pd.read_csv(f)

  #nrows indica il numero di righe da considerare. Se si vuole partire da una certa riga,
  # usare skiprows=<int>, che skippa n righe da inizio file
  #datasetPLC = pd.read_csv(f, nrows=20000)
  datasetPLC = pd.read_csv(f, skiprows=skiprows, nrows=nrows)
  datasetPLC_d = datasetPLC.copy() # Altrimenti non mi differenzia le liste, vai a capire perchè...
  
  # Concatenate the single PLCs datasets for process mining
  df_list_mining.append(datasetPLC)

  # Add previous values, slopes and limits to dataframe
  enrich_df(datasetPLC_d)
  # Concatenate the single PLCs datasets for Daikon
  df_list_daikon.append(datasetPLC_d)


mining_datasets = pd.concat(df_list_mining, axis=1).reset_index(drop=True)
daikon_datasets = pd.concat(df_list_daikon, axis=1).reset_index(drop=True)

# Save dataset with the timestamp for the process mining.
mining_datasets.to_csv(r'../process-mining/data/PLC_SWaT_Dataset_TS.csv', index=False)

print(mining_datasets)

print('************************************************************************************')
print ('************* DATASET FOR PROCESS MINING GENERATED SUCCESSFULLY *******************')
print('************************************************************************************')


# drop timestamps is NOT needed in Daikon
#inv_datasets = mining_datasets.drop(['TimeStamp'], axis=1, errors='ignore')
inv_datasets = daikon_datasets.drop(['Timestamp'], axis=1, errors='ignore')

# Add state transient/stable on PLC1_InputRegisters_IW0 
#PLC1_state = list()
#for x in datasetPLC1["PLC1_InputRegisters_IW0"] :
# if (x in [52,53,54,78,79,80]):
#   PLC1_state.append("stable")
# else:
#   PLC1_state.append("transient")  
#datasetPLC1.insert(len(datasetPLC1.columns),'PLC1_state', PLC1_state)


# Drop first rows (Daikon does not process missing values)
# Taglio anche le ultime righe, che hanno lo slope = 0
inv_datasets = inv_datasets.iloc[1:-granularity , :]

print(inv_datasets)

# Daikon can NOT process a csv of more that 64801 lines
#inv_datasets.iloc[0:64800].to_csv(r'PLC_Dataset.csv', index=False)


inv_datasets.to_csv(r'../daikon/Daikon_Invariants/PLC_SWaT_Dataset.csv', index=False)

print('****************************************************************************************')
print ('************* DATASET FOR INVARIANT ANALYSIS GENERATED SUCCESSFULLY *******************')
print('****************************************************************************************')
