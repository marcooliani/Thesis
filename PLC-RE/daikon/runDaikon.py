#!/usr/bin/env python3

import os
import re
import subprocess
import networkx as nx
import argparse
import configparser


class RunDaikon:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--filename", type=str, help="name of the input dataset file (CSV format)")
        parser.add_argument('-c', "--conditions", nargs='+', default=[], help="Daikon invariants conditions")
        self.args = parser.parse_args()

        self.dataset = self.config['DEFAULTS']['dataset_file']
        self.conditions = None

    def check_args(self):
        if self.args.filename is not None:
            if self.args.filename.split('.')[-1] != "csv":
                print("Invalid file format (must be .csv). Aborting")
                exit(1)
            self.dataset = self.args.filename

        if self.args.conditions is not None:
            self.conditions = [c for c in self.args.conditions]

    def call_daikon(self):
        dataset_name = self.dataset.split('/')[-1].split('.')[0]

        print(f"Generating {dataset_name}.decls and {dataset_name}.dtrace files ...")
        if subprocess.call(f'perl $DAIKONDIR/scripts/convertcsv.pl {self.dataset}', shell=True):
            print("Error generating invariants. Aborting.")
            exit(1)

        if self.conditions is not None:
            inv_conditions_file = self.config['DAIKON']['inv_conditions_file']

            print("Generating invariants with conditions ...")
            with open(inv_conditions_file, 'w') as f:
                f.write('PPT_NAME aprogram.point:::POINT\n')
                for c in self.conditions:
                    f.write(c + '\n')
            self.conditions.insert(0, f'General')

            output = subprocess.check_output(
                f'java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy {dataset_name}.decls {dataset_name}.dtrace '
                f'{inv_conditions_file}', shell=True)
        else:
            print("Generating invariants with no conditions ...")
            output = subprocess.check_output(
                f'java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy {dataset_name}.decls {dataset_name}.dtrace ',
                shell=True)

        return output

    @staticmethod
    def split_daikon(output):
        # Visto che l'output è codificato in qualche maniera, riportiamolo allo stato "originario"
        # come stringa
        output = output.decode("utf-8")

        output = re.sub('[=]{6,}', 'SPLIT_HERE', output)
        # sections = [sec.split('\n')[1:] for sec in output.split('SPLIT_HERE\n')][1:-1]
        sections = [output.split('SPLIT_HERE\n')[1].split('\n')[1:]] + [sec.split('\n')[1:] for sec in
                                                                        output.split('SPLIT_HERE\n')][2::2]
        return sections

    def parse_daikon(self, section, section_output):
        not_equal = dict()
        edges = dict()
        edges_gt = list()
        edges_ge = list()
        edges_lt = list()
        edges_le = list()
        edges_eq = list()

        for invariant in section:
            # find() trova l'indice della stringa cercata: se non la trova,
            # allora -1
            if invariant.find('<==>') != -1 or invariant.find(' ==>') != -1:
                invariant = invariant.replace('(', '').replace(')', '')
                section_output.append(invariant)
            elif invariant.find('one of') != -1:
                section_output.append(invariant)
            elif invariant.find('!=') != -1 and invariant.find('prev') == -1:
                a, b = invariant.split(' != ')
                if a not in not_equal:
                    not_equal[a] = []
                if a in not_equal:
                    not_equal[a].append(b)
                if b in not_equal:
                    not_equal[b].append(a)

            elif invariant.find('%') != -1 or \
                    invariant.find('prev') != -1 or \
                    invariant == '' or invariant.find('Exiting') != -1:
                continue
            else:
                a, rel, b = invariant.split(' ')[:3]

                if b.find(self.config['DATASET']['prev_cols_prefix']) != -1 or \
                        a.find(self.config['DATASET']['prev_cols_prefix']) != -1:
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

        for k, l in not_equal.items():
            section_output.append(f'{k} != {", ".join(map(str, l))}')

        # Archi del grafo divisi per segno della relazione
        edges['=='] = edges_eq
        edges['>'] = edges_gt
        edges['>='] = edges_ge
        edges['<'] = edges_lt
        edges['<='] = edges_le

        return edges

    @staticmethod
    def make_graph(edge_list):
        G = nx.MultiDiGraph()
        G.add_edges_from(edge_list)

        for g in list(G.nodes())[:]:
            if G.degree(g) == 0:
                G.remove_node(g)

        return G

    def make_dfs(self, G, key):
        section_output = list()
        invariant_list = list()
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
                    invariant_list.append(temp)

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
                if node.find(self.config['DATASET']['max_prefix']) != -1 or \
                        node.find(self.config['DATASET']['min_prefix']) != -1:
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
                invariant_list.append(p)

        for val in invariant_list:
            if key == '==':
                section_output.append(f' {key} '.join(map(str, reversed(sorted(val)))))
            elif key == '>' or key == '>=':
                section_output.append(f' {key} '.join(map(str, val)))
            elif key == '<' or key == '<=':
                section_output.append(f' {">" if key == "<" else ">="} '.join(map(str, reversed(val))))

        return section_output

    def write_invariants_to_file(self, invariants):
        # Scrivo il risultato finale sui file
        print(f'Writing output file daikon_results_{self.conditions[1].replace(" ", "_")}.txt ...')
        with open(
                f'{self.config["DAIKON"]["daikon_results_dir"]}/daikon_results_{self.conditions[1].replace(" ", "_")}.txt',
                'w') as of:
            i = 0
            for inv in invariants:
                of.write('===========================\n')
                of.write(self.conditions[i] + '\n')
                of.write('===========================\n')
                of.write('\n'.join(map(str, inv)))
                of.write('\n\n')
                i += 1


def main():
    rd = RunDaikon()

    rd.check_args()
    start_dir = os.getcwd()
    print("Process start")
    if os.chdir('Daikon_Invariants/'):
        print("Error generating invariants. Aborting.")
        exit(1)

    # TODO: per ogni condizione richiamare Daikon! Altrimenti non riesco a generare tutti i file con le condizioni!
    output_daikon = rd.call_daikon()
    sections = rd.split_daikon(output_daikon)

    invariants_full = list()

    for section in sections:
        section_output = list()
        edges = rd.parse_daikon(section, section_output)
        for key, edge_list in edges.items():
            G = rd.make_graph(edge_list)
            section_output.append('\n'.join(map(str, rd.make_dfs(G, key))))
        invariants_full.append(section_output)

    rd.write_invariants_to_file(invariants_full)

    print("Invariants generated successfully")
    os.chdir(start_dir)


if __name__ == '__main__':
    main()
