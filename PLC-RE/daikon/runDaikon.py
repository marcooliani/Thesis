#!/usr/bin/env python3

import sys
import os
import subprocess
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
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
output=output.split('\n')[7:-2]

'''
Qui transitive closure, se sapessi come farla!
'''
datasetPLC = pd.read_csv(dataset)
dataset_col = list(datasetPLC.columns)

G = nx.DiGraph()
for n in dataset_col:
  if n.find('prev') != -1:
    continue
  else:
    G.add_node(n)
# G.add_nodes_from(dataset_col)


invs = output.copy()

edges_ab = list()
edges_ba = list()
edges_same = list()

for inv in invs:
  # 'Sta roba devo cavarla per forza...
  if inv.find('aprogram.point:::POINT') != -1 or \
      inv.find('=========') != -1 or \
      inv.find('==>') != -1 or \
      inv.find('one of') != -1 or \
      inv.find('!=') != -1 or \
      inv.find('%') != -1 or \
      inv.find('prev') != -1: 
    continue
  else:
    a,rel,b = inv.split(' ')
    if b.isdigit():
      G.add_node(b)
    elif b.find('prev') != -1:
      continue
    if rel == '>=' or rel == '>':
      pass
      #G.add_edge(a, b)
      #edges_ab.append((a,b))
    elif rel == '<=' or rel == '<':
      pass
      #G.add_edge(b, a)
      #edges_ba.append((b,a))
    elif rel == '==':
      G.add_edge(a, b)
      edges_same.append((a,b))

for g in list(G.nodes()):
  if G.degree(g) == 0:
    G.remove_node(g)

#closure = list(nx.dfs_edges(G, source='P203'))

visited = list()
for v in list(G.nodes()):
  if v not in visited:
    closure = list(nx.dfs_edges(G, source=v))
    print(closure)
    for a,b in closure:
      if a not in visited:
        visited.append(a)
      if b not in visited:
        visited.append(b)
    
## Il plot di fatto non mi serve. Magari lo metto come opzione, giusto per allungare
## il brodo alla tesi...
#pos = nx.spring_layout(G)
#pos = nx.circular_layout(G)
#nx.draw_networkx(G,pos,node_color='#00b4d9',node_size=1000,width=2,with_labels=True)
#nx.draw_networkx(G,pos,node_color='#00b4d9',node_size=1200,edgelist=edges_ab,width=2,with_labels=True)

#nx.draw_networkx_nodes(G,pos,node_color='#00b4d9',node_size=1000,cmap=plt.get_cmap('jet'))
#nx.draw_networkx_labels(G, pos)
#nx.draw_networkx_edges(G, pos, edgelist=edges_ab, edge_color='r')
#nx.draw_networkx_edges(G, pos, edgelist=edges_ba, edge_color='b', arrows=True)
#nx.draw_networkx_edges(G, pos, edgelist=edges_same, arrows=True)

#ax = plt.gca()
#ax.set_title('Graph')
#ax.set_title(rel)
#ax.margins(0.20)
#plt.axis("off")

#plt.show()

'''
fine test grafo
'''

# Scrivo l'output finale su file (bisognerebbe fare la transitive closure, prima)
print(f'Writing output file {output_file} ...')
with open(output_file, 'w') as f:
  f.write("\n".join(map(str,output)))

print("Invariants generated successfully")
os.chdir(start_dir)

