#!/usr/bin/env python3

import pyshark
import glob
import argparse
import configparser
import subprocess


class ExportPCAPData:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        parser.add_argument('-f', "--file", type=str, help="single pcap file to include (with path")
        parser.add_argument('-m', "--mergefiles", nargs='+', default=[], help="multiple pcap files to include (w/o path)")
        parser.add_argument('-d', "--mergedir", type=str, help="directory containing pcap files to merge")
        self.args = parser.parse_args()

        self.pcap_file = None
        self.pcap_multiple = self.args.mergefiles
        self.pcap_dir = self.config['NETWORK']['pcap_dir']

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
        fixed_param = ['frame.number', '_ws.col.Time', 'ip.src', 'ip.dst']  # Lo tengo qui, ma non serve...
        str_protocols = "-Y '"
        str_protocols += ' || '.join(map(str, protocols)).lower()
        str_protocols += "'"

        str_columns = ''
        for p in protocols:
            for field in self.config['NETWORK']['ws_' + p.lower() + '_fields'].split(','):
                str_columns += f'-e {field} '

        # ud -> UTC date
        # ad -> absolute date (orario locale)
        output = subprocess.check_output(f'tshark -r {self.pcap_file} -t ud -T fields -e frame.number '
                                         f'-e _ws.col.Time -e ip.src -e ip.dst {str_protocols} '
                                         f'-e _ws.col.Protocol {str_columns} '
                                         f'-E header=y -E separator=, -E aggregator=/s', shell=True).decode('utf-8')

        output = output.split('\n')

        output_csv = output[0] + '\n'

        for r in output[1:]:
            r = r.split(',')
            r = r[:2] + r[3:]
            output_csv += ','.join(map(str, r))
            output_csv += '\n'

        print("Saving CSV export ... ")
        with open(f'{self.config["NETWORK"]["csv_output"]}', 'w') as f:
            f.write(output_csv)

        print(f'CSV file {self.config["NETWORK"]["csv_output"]} saved. Exiting')


def main():
    epd = ExportPCAPData()
    epd.check_args()
    epd.merge_pcap()
    prot = epd.find_protocols()
    epd.export_data(prot)


if __name__ == '__main__':
    main()
