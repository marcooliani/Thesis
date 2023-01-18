#!/usr/bin/env python3

import pyshark
import csv
import glob
import argparse
import configparser
import subprocess


class ExportPCAPData:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--files", nargs='+', default=[], help="pcap files to include (w/o path)")
        self.args = parser.parse_args()

        self.pcap_files = list()

    def check_args(self):
        self.pcap_files = self.args.files

    def merge_pcap(self):
        pass

    def find_protocols(self, file):
        cap = pyshark.FileCapture(f'{self.config["NETWORK"]["pcap_dir"]}/{file}', include_raw=True, use_json=True)
        print(file)

        found_protocols = list()

        protocols = self.config['NETWORK']['protocols'].split(',')

        for proto in protocols:
            print(proto)
            pkt_count = 0
            for packet in cap:
                if pkt_count > int(self.config['NETWORK']['packets_limit']):
                    break

                layer = packet.highest_layer
                print(layer)

                if proto.upper() in layer:
                    print(f'{proto} protocol found')
                    found_protocols.append(proto)
                    break

                pkt_count += 1

        return found_protocols

    def export_data(self, file, protocols):
        fixed_param = ['frame.number', '_ws.col.Time', 'ip.src', 'ip.dst']
        # str_protocols = "-Y 'modbus || cip' "
        str_protocols = "-Y '"
        str_protocols += ' || '.join(map(str, protocols)).lower()
        str_protocols += "'"
        print(str_protocols)

        str_columns = ''
        for p in protocols:
            for field in self.config['NETWORK']['ws_' + p.lower() + '_fields'].split(','):
                str_columns += f'-e {field} '

        print(str_columns)

        ## ud -> UTC date   ad -> absolute date (orario locale)
        #output = subprocess.check_output(
        #    f'tshark -r {file} -t ud -T fields -e frame.number -e _ws.col.Time -e ip.src -e ip.dst -E header=y -E separator=, -E aggregator=/s')


def main():
    epd = ExportPCAPData()
    epd.check_args()
    prot = epd.find_protocols('Plant1.pcap')
    epd.export_data('bla', prot)


if __name__ == '__main__':
    main()
