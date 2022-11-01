#!/usr/bin/env python3

import sys
import os
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
parser.add_argument('-o', "--output", type=str, help="output file (TXT format)")
parser.add_argument('-c', "--conditions", nargs='+', default=[], help="Daikon invariants conditions")
args = parser.parse_args()

if args.filename != None:
  if args.filename.split('.')[-1] != "csv":
    print("Invalid file format (must be .csv). Aborting")
    exit(1)
  dataset = args.filename
else:
  dataset = 'PLC_SWaT_Dataset.csv'

dataset_name = dataset.split('.')[0]

if args.output != None:
  if args.output.split('.')[-1] != 'txt':
    print("Invalid file format (must be .txt). Aborting")
    exit(1)
  output_file = args.output
else:
  output_file = "daikon_results_cond.txt"

if args.conditions != None:
  conditions = [c for c in args.conditions]

inv_conditions_file = "Inv_conditions.spinfo"

start_dir = os.getcwd()

print("Process start")

if os.chdir('Daikon_Invariants/'):
  print("Error generating invariants. Aborting.")
  exit(1)

print(f"Generating {dataset_name}.decls and {dataset_name}.dtrace files ...")
if subprocess.call(f'perl $DAIKONDIR/scripts/convertcsv.pl {dataset}', shell=True):
  print("Error generating invariants. Aborting.")
  exit(1)

if conditions != None:
  with open(inv_conditions_file, 'w') as f:
    f.write('PPT_NAME aprogram.point:::POINT\n')
    for c in conditions:
      f.write(c + '\n')

print("Generating invariants with conditions ...")
output = subprocess.check_output(f'java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy {dataset_name}.decls {dataset_name}.dtrace {inv_conditions_file}', shell=True)

# Visto che l'output è codificato in qualche maniera, riportiamolo allo stato "originario"
# come stringa
output = output.decode("utf-8") 

# taglio le prime righe dell'output di Daikon, che non servono,
# così come l'ultima
output=output.split('\n')[6:-2]

'''
Qui transitive closure, se sapessi come farla!
'''

# Scrivo l'output finale su file (bisognerebbe fare la transitive closure, prima)
print(f'Writing output file {output_file} ...')
with open(output_file, 'w') as f:
  f.write("\n".join(map(str,output)))

print("Invariants generated successfully")
os.chdir(start_dir)

