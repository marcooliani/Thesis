#!/usr/bin/env python3
from io import StringIO

import pyshark
import argparse
import configparser
import subprocess
import pandas as pd


class ExportPCAPData:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-f', "--file", type=str, help="single pcap file to include (with path")
        group.add_argument('-m', "--mergefiles", nargs='+', default=[],
                           help="multiple pcap files to include (w/o path)")
        group.add_argument('-d', "--mergedir", type=str, help="directory containing pcap files to merge")
        parser.add_argument('-t', "--timerange", nargs=2, default=[],
                            help="time range selection (format YYYY-MM-DD HH:MM:SS")
        self.args = parser.parse_args()

        self.pcap_file = None
        self.pcap_multiple = self.args.mergefiles
        self.pcap_dir = None
        self.pcap_timerange = self.args.timerange

    def check_args(self):
        if self.args.file:
            self.pcap_file = self.args.file
        elif self.args.mergedir:
            self.pcap_dir = self.args.mergedir
            self.pcap_file = self.config['NETWORK']['pcap_merge_file']
        elif self.args.mergefiles:
            self.pcap_file = self.config['NETWORK']['pcap_merge_file']
            self.pcap_multiple = self.args.mergefiles

    def merge_pcap(self):
        if not self.pcap_multiple and self.pcap_dir:
            print(f"Merging pcap files from directory {self.pcap_dir} ... ")
            subprocess.check_output(f'mergecap -w {self.pcap_file} {self.pcap_dir}/*.pcap', shell=True)
            print("Done")

        elif self.pcap_multiple:
            print(f"Merging selected files ... ")
            subprocess.check_output(f'mergecap -w {self.pcap_file} '
                                    f'{" ".join(map(str, self.pcap_multiple))}', shell=True)
            print("Done")

    def find_protocols(self):
        print("Detecting protocols ... ")
        cap = pyshark.FileCapture(f'{self.pcap_file}', include_raw=True, use_json=True)

        found_protocols = list()

        protocols = self.config['NETWORK']['protocols'].split(',')

        for proto in protocols:
            pkt_count = 0

            for packet in cap:
                if pkt_count > int(self.config['NETWORK']['packets_limit']):
                    break

                layer = packet.highest_layer

                if proto.upper() in layer:
                    print(f'{proto} protocol found')
                    found_protocols.append(proto)
                    break

                pkt_count += 1

        return found_protocols

    def export_data(self, protocols):
        print("Extracting PCAP data ... ")
        # fixed_param = ['frame.number', '_ws.col.Time', 'ip.src', 'ip.dst']  # Lo tengo qui, ma non serve...
        str_protocols = "-Y '"
        str_protocols += ' || '.join(map(str, protocols)).lower()
        str_protocols += "'"

        str_columns = ''
        for p in protocols:
            for field in self.config['NETWORK']['ws_' + p.lower() + '_fields'].split(','):
                str_columns += f'-e {field} '

        # ud -> UTC date
        # ad -> absolute date (orario locale)
        output = subprocess.check_output(f'tshark -r {self.pcap_file} -t ud -T fields '
                                         f'-e frame.time_epoch -e ip.src -e ip.dst {str_protocols} '
                                         f'-e _ws.col.Protocol {str_columns} -e frame.number -e frame.protocols '
                                         f'-E header=y -E separator=, -E aggregator=/s', shell=True).decode('utf-8')

        df = pd.read_csv(StringIO(output))

        df.rename({'ip.src': 'src'}, axis=1, inplace=True)
        df.rename({'ip.dst': 'dst'}, axis=1, inplace=True)
        df.rename({'_ws.col.Protocol': 'Protocol'}, axis=1, inplace=True)
        df.rename({'frame.time_epoch': self.config['DATASET']['timestamp_col']}, axis=1, inplace=True)
        df[self.config['DATASET']['timestamp_col']] = pd.to_datetime(df[self.config['DATASET']['timestamp_col']],
                                                                     unit='s')

        if self.pcap_timerange:
            df = df.loc[df[self.config['DATASET']['timestamp_col']].between(self.pcap_timerange[0],
                                                                            self.pcap_timerange[1],
                                                                            inclusive="both")]

        print("Saving CSV export ... ")
        df.to_csv(self.config["NETWORK"]["csv_output"], index=False)

        print(f'CSV file {self.config["NETWORK"]["csv_output"]} saved. Exiting')

        sources = sorted(df['src'].unique())
        print(sources)


def main():
    epd = ExportPCAPData()
    epd.check_args()
    epd.merge_pcap()
    prot = epd.find_protocols()
    epd.export_data(prot)


if __name__ == '__main__':
    main()
