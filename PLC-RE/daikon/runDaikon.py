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
#datasetPLC = pd.read_csv(dataset)
#dataset_col = list(datasetPLC.columns)

#for n in dataset_col[:]:
#  if n.find('prev') != -1:
#    dataset_col.remove(n)

# Creo il grafo delle invarianti. I nodi sono le colonne
# del dataset
#G = nx.MultiDiGraph()
#G.add_nodes_from(dataset_col)

# Copia dell'output di Daikon
invs = output.copy()

# Dizionario che contiene la lista delle invarianti divise per
# relazione (in questo caso, gli archi del grafo)
edges = dict()
edges_gt = list()
edges_ge = list()
edges_lt = list()
edges_le = list()
edges_eq = list()

for inv in invs:
  # 'Sta roba devo cavarla per forza...
  # Ah, find() mi sa che trova l'indice della stringa cercata: se non la trova,
  # allora -1
  if (inv.find('aprogram.point:::POINT') != -1 and inv.find('not') == -1) or \
      inv.find('=========') != -1 or \
      inv.find('==>') != -1 or \
      inv.find('one of') != -1 or \
      inv.find('!=') != -1 or \
      inv.find('%') != -1 or \
      inv.find('prev') != -1: 
    continue
  # Via la condizione negata
  elif inv.find('aprogram.point:::POINT') != -1 and \
      inv.find('not') != -1:
      break
  else:
    a,rel,b = inv.split(' ')[:3]
    if b.isdigit():
      G.add_node(b)
    elif b.find('prev') != -1 or a.find('prev') != -1:
      continue
    # Le condizioni vanno trattate separatamente, altrimenti
    # non riesco a ricostruire correttamente il tutto
    if rel == '>':
      edges_gt.append((a,b))
    elif rel == '>=':
      edges_ge.append((a,b))
    elif rel == '<':
      edges_lt.append((b,a))
    elif rel == '<=':
      edges_le.append((b,a))
    elif rel == '==':
      edges_eq.append((a,b))
      edges_eq.append((b,a))

edges['=='] = edges_eq
edges['>'] = edges_gt
edges['>='] = edges_ge
edges['<'] = edges_lt
edges['<='] = edges_le

#G.add_edges_from(edges_ge, label='>=')

for key, edge_list in edges.items():
  invariants = list()
  visited = list()

  G = nx.MultiDiGraph()
  G.add_edges_from(edge_list)

  for g in list(G.nodes())[:]:
    if G.degree(g) == 0:
      G.remove_node(g)

  for v in list(G.nodes()):
    if v not in visited:
      temp = []
      # Faccio una DFS per trovare le chiusure transitive
      closure = list(nx.dfs_edges(G, source=v))
      if key == '==':
        for a,b in closure:
          if a not in visited:
            temp.append(a)
            visited.append(a)
          if b not in visited or b.isdigit():
            visited.append(b)
            temp.append(b)
        invariants.append(temp) ## Questo va un tab indietro, alla fine...
      else:
        for a,b in closure:
          if a.find('max') != -1 or b.find('max') != -1 or a.find('min') != -1 or b.find('min') != -1:
            continue
          else:
            invariants.append((a,b))

  for i in invariants:
    if key == '==':
      print(f' {key} '.join(map(str,reversed(sorted(i)))))
    else:
      print(f'{i[0]} {key} {i[1]}')

## Il plot di fatto non mi serve. Magari lo metto come opzione, giusto per allungare
## il brodo alla tesi...
#pos = nx.spring_layout(G)
#pos = nx.planar_layout(G)
#pos = nx.circular_layout(G)
#nx.draw_networkx(G,pos,node_color='#00b4d9',node_size=1200,edgelist=edges_eq,width=2,with_labels=True)

#nx.draw_networkx_nodes(G,pos,node_color='#00b4d9',node_size=1000,cmap=plt.get_cmap('jet'))
#nx.draw_networkx_labels(G, pos)
#nx.draw_networkx_edges(G, pos, edgelist=edges_ab, edge_color='r')
#nx.draw_networkx_edges(G, pos, edgelist=edges_ba, edge_color='b', arrows=True)
#nx.draw_networkx_edges(G, pos, edgelist=edges_eq, arrows=False)

#ax = plt.gca()
#ax.set_title('Graph')
#ax.set_title('')
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

