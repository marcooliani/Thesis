#!/usr/bin/env python3

import os
import subprocess
import networkx as nx
import matplotlib.pyplot as plt
import argparse
import configparser

parser = argparse.ArgumentParser()
parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
parser.add_argument('-o', "--output", type=str, help="output file (TXT format)")
parser.add_argument('-c', "--conditions", nargs='+', default=[], help="Daikon invariants conditions")
args = parser.parse_args()

config = configparser.ConfigParser()
config.read('../config.ini')

if args.filename is not None:
    if args.filename.split('.')[-1] != "csv":
        print("Invalid file format (must be .csv). Aborting")
        exit(1)
    dataset = args.filename
else:
    dataset = config['DEFAULTS']['dataset_file']

dataset_name = dataset.split('.')[0]

if args.output is not None:
    if args.output.split('.')[-1] != 'txt':
        print("Invalid file format (must be .txt). Aborting")
        exit(1)
    output_file = args.output
else:
    output_file = config['DAIKON']['daikon_output_file']

if args.conditions is not None:
    conditions = [c for c in args.conditions]
else:
    conditions = None

inv_conditions_file = config['DAIKON']['inv_conditions_file']

start_dir = os.getcwd()

print("Process start")

if os.chdir('Daikon_Invariants/'):
    print("Error generating invariants. Aborting.")
    exit(1)

print(f"Generating {dataset_name}.decls and {dataset_name}.dtrace files ...")
if subprocess.call(f'perl $DAIKONDIR/scripts/convertcsv.pl {dataset}', shell=True):
    print("Error generating invariants. Aborting.")
    exit(1)

if conditions is not None:
    with open(inv_conditions_file, 'w') as f:
        f.write('PPT_NAME aprogram.point:::POINT\n')
        for c in conditions:
            f.write(c + '\n')

print("Generating invariants with conditions ...")
output = subprocess.check_output(
    f'java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy {dataset_name}.decls {dataset_name}.dtrace {inv_conditions_file}',
    shell=True)

# Visto che l'output è codificato in qualche maniera, riportiamolo allo stato "originario"
# come stringa
output = output.decode("utf-8")

# taglio le prime righe dell'output di Daikon, che non servono,
# così come l'ultima
output = output.split('\n')[7:-2]

'''
Qui transitive closure!
'''
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
one_of = list()
implications = list()

for inv in invs:
    # 'Sta roba devo cavarla per forza...
    # Ah, find() mi sa che trova l'indice della stringa cercata: se non la trova,
    # allora -1
    if (inv.find('aprogram.point:::POINT') != -1 and inv.find('not') == -1) or \
            inv.find('=========') != -1 or \
            inv.find('!=') != -1 or \
            inv.find('%') != -1 or \
            inv.find('prev') != -1:
        continue
    # Via la condizione negata
    elif inv.find('aprogram.point:::POINT') != -1 and \
            inv.find('not') != -1:
        break
    elif inv.find('<==>') != -1 or inv.find(' ==>') != -1:
        inv = inv.replace('(', '').replace(')', '')
        implications.append(inv)
    elif inv.find('one of') != -1:
        one_of.append(inv)
    else:
        a, rel, b = inv.split(' ')[:3]

        if b.find(config['DATASET']['prev_cols_prefix']) != -1 or \
                a.find(config['DATASET']['prev_cols_prefix']) != -1:
            continue
        # Le condizioni vanno trattate separatamente, altrimenti
        # non riesco a ricostruire correttamente il tutto
        if rel == '>':
            edges_gt.append((a, b))
        elif rel == '>=':
            edges_ge.append((a, b))
        elif rel == '<':
            edges_lt.append((a, b))
        elif rel == '<=':
            edges_le.append((a, b))
        elif rel == '==':
            edges_eq.append((a, b))
            edges_eq.append((b, a))

# Stampo le condizioni "one of" in testa
for imp in implications:
    print(imp)
print('===================')

# Stampo le condizioni "one of" in testa
for of in one_of:
    print(of)
print('===================')

# Archi del grafo divisi per segno della relazione
edges['=='] = edges_eq
edges['>'] = edges_gt
edges['>='] = edges_ge
edges['<'] = edges_lt
edges['<='] = edges_le

for key, edge_list in edges.items():
    invariants = list()

    G = nx.MultiDiGraph()
    G.add_edges_from(edge_list)

    for g in list(G.nodes())[:]:
        if G.degree(g) == 0:
            G.remove_node(g)

    # Ricavo le uguaglianze con una dfs sul grafo.
    # Per come ho scritto il codice, una bfs produce
    # lo stesso identico output...
    if key == '==':
        visited = list()
        for v in list(G.nodes()):
            if v not in visited:
                temp = []
                # DFS
                closure_dfs = list(nx.dfs_edges(G, source=v))

                # "Concateno" di fatto le tuple che fanno parte
                # della DFS
                for a, b in closure_dfs:
                    if a not in visited:
                        temp.append(a)
                        visited.append(a)
                    if b not in visited or b.isdigit():
                        visited.append(b)
                        temp.append(b)

                # Inserisco la lista di nodi nel listone delle invarianti
                invariants.append(temp)

    # Per le disugualianze, la dfs risulta incasinata da trattare poi.
    # Ergo, sfrutto i gradi in entrata e in uscita dai nodi: se
    # in_degree(nodo) = 0 allora ho una radice, se out_degree(g) = 0
    # allora ho una foglia. Tutti gli altri sono nodi intermedi.
    # Da lì ricostruisco i singoli path radice-foglia.
    else:
        path_list = list()  # lista path
        roots = []  # lista radici
        leaves = []  # lista foglie

        for node in G.nodes():
            # tolgo max e min da root e foglie - sarebbe meglio solo da
            # root, forse...
            if node.find(config['DATASET']['max_prefix']) != -1 or \
                    node.find(config['DATASET']['min_prefix']) != -1:
                continue
            else:
                if G.in_degree(node) == 0:  # it's a root
                    roots.append(node)
                elif G.out_degree(node) == 0:  # it's a leaf
                    leaves.append(node)

        # Calcolo i path radice-foglia e li appendo alla lista
        for root in roots:
            for leaf in leaves:
                for path in nx.all_simple_paths(G, root, leaf):
                    path_list.append(path)

        # Ripulisco la lista dei path eliminando quelli che sono
        # inclusi in un altro path
        for i in path_list[:]:
            for j in path_list[:]:
                if j != i:
                    if all(item in i for item in j):
                        path_list.remove(j)

        for p in path_list:
            invariants.append(p)

    # Stampo le invarianti
    for val in invariants:
        if key == '==':
            print(f' {key} '.join(map(str, reversed(sorted(val)))))
        else:
            print(f' {key} '.join(map(str, val)))

    print('===================')

# Il plot di fatto non mi serve. Magari lo metto come opzione, giusto per allungare
# il brodo alla tesi...
'''
G = nx.MultiDiGraph()  ## Debug
G.add_edges_from(edges_lt)  ## Debug
for g in list(G.nodes())[:]:
    if (g.find('min') != -1 or g.find('max') != -1) and (G.out_degree(g) == 0 or G.in_degree(g) == 0):
        G.remove_node(g)

# pos = nx.spring_layout(G)
# pos = nx.planar_layout(G)
pos = nx.circular_layout(G)
nx.draw_networkx(G, pos, node_color='#00b4d9', node_size=1200, width=2, with_labels=True)

# nx.draw_networkx_nodes(G,pos,node_color='#00b4d9',node_size=1000,cmap=plt.get_cmap('jet'))
# nx.draw_networkx_labels(G, pos)
# nx.draw_networkx_edges(G, pos, edgelist=edges_ab, edge_color='r')
# nx.draw_networkx_edges(G, pos, edgelist=edges_ba, edge_color='b', arrows=True)
# nx.draw_networkx_edges(G, pos, edgelist=edges_eq, arrows=False)

ax = plt.gca()
# ax.set_title('Graph')
ax.set_title(conditions)
# ax.margins(0.20)
# plt.axis("off")
plt.show()
'''
'''
fine test grafo
'''

# Scrivo l'output finale su file (bisognerebbe fare la transitive closure, prima)
print(f'Writing output file {output_file} ...')
with open(output_file, 'w') as f:
    f.write("\n".join(map(str, output)))

print("Invariants generated successfully")
os.chdir(start_dir)
