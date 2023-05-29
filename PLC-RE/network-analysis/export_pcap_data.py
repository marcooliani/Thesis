#!/usr/bin/env python3
import os
from io import StringIO
from textwrap import wrap

import numpy as np
import pyshark
import argparse
import configparser
import subprocess
import pandas as pd
import service_codes as sc


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
        group.add_argument('-s', "--singledir", type=str, help="directory containing pcap files for single analysis")
        parser.add_argument('-t', "--timerange", nargs=2, default=[],
                            help="time range selection (format YYYY-MM-DD HH:MM:SS")
        self.args = parser.parse_args()

        self.pcap_dir = self.config['NETWORK']['pcap_dir']
        if self.args.file:
            self.pcap_file = self.args.file
        else:
            self.pcap_file = self.config['NETWORK']['pcap_merge_file']

        self.pcap_multiple = self.args.mergefiles
        if self.args.mergedir:
            self.pcap_dir = self.args.mergedir
        elif self.args.singledir:
            self.pcap_dir = self.args.singledir
        self.pcap_timerange = self.args.timerange

    def merge_pcap(self, pcap_file):
        # if not self.pcap_multiple and self.pcap_dir:
        if self.args.mergedir:
            print(f"Merging pcap files from directory {self.pcap_dir} ... ")
            subprocess.check_output(f'mergecap -w {pcap_file} {self.pcap_dir}/*.pcap', shell=True)
            print("Done")

        elif self.pcap_multiple:
            print(f"Merging selected files ... ")
            subprocess.check_output(f'mergecap -w {pcap_file} '
                                    f'{" ".join(map(str, self.pcap_multiple))}', shell=True)
            print("Done")

        else:
            return pcap_file

        return pcap_file

    def __find_protocols(self, pcap_file):
        print("Detecting protocols ... ")
        cap = pyshark.FileCapture(f'{pcap_file}', include_raw=True, use_json=True)

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

    def extract_data(self, pcap_file):
        protocols = self.__find_protocols(pcap_file)

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
        output = subprocess.check_output(f'tshark -r {pcap_file} -t ud -T fields '
                                         f'-e frame.time_epoch -e ip.src -e ip.dst {str_protocols} '
                                         f'-e _ws.col.Protocol {str_columns} -e frame.number -e frame.protocols '
                                         f'-E header=y -E separator=, -E aggregator=/s', shell=True).decode('utf-8')

        df = pd.read_csv(StringIO(output))

        df.rename({'ip.src': 'src'}, axis=1, inplace=True)
        df.rename({'ip.dst': 'dst'}, axis=1, inplace=True)
        df.rename({'_ws.col.Protocol': 'protocol'}, axis=1, inplace=True)
        df.rename({'cip.symbol': 'register'}, axis=1, inplace=True)
        df.rename({'cip.data': 'data'}, axis=1, inplace=True)
        df.rename({'cip.service': 'service_detail'}, axis=1, inplace=True)
        df.rename({'cip.rr': 'service'}, axis=1, inplace=True)
        df.rename({'frame.time_epoch': self.config['DATASET']['timestamp_col']}, axis=1, inplace=True)
        df[self.config['DATASET']['timestamp_col']] = pd.to_datetime(df[self.config['DATASET']['timestamp_col']], unit='s')

        if self.pcap_timerange:
            df = df.loc[df[self.config['DATASET']['timestamp_col']].between(self.pcap_timerange[0],
                                                                            self.pcap_timerange[1],
                                                                            inclusive="both")]

        print("Sostituzioni")
        df["service"] = np.where(df["service"].str.contains("0x01"), "Response", df['service'])
        df["service"] = np.where(df["service"].str.contains("0x00"), "Request", df['service'])
        df["service_detail"] = np.where(df["service_detail"].str.fullmatch("0x4c", case=False), "Read Tag Request",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.fullmatch("0xcc", case=False), "Read Tag Response",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.fullmatch("0x4d", case=False), "Write Tag Request",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.fullmatch("0xcd", case=False), "Write Tag Response",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.match("0x0a", case=False),
                                        "Multiple Service Packet Request",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.match("0x8a", case=False),
                                        "Multiple Service Packet Response",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.match("0x01"), "Get Attribute All Request",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.match("0x81"), "Get Attribute All Response",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.match("0x0e"), "Get Attribute Single Request",
                                        df['service_detail'])
        df["service_detail"] = np.where(df["service_detail"].str.match("0x8e"), "Get Attribute Single Response",
                                        df['service_detail'])
        df = df[df['protocol'] != "CIP CM"]

        ## Da qui
        #df['cip.rr'] = df['cip.rr'].apply(wrap(df['cip.rr'], 8))
        ## A qui

        sources = sorted(df['src'].unique())
        destinations = sorted(df['dst'].unique())
        # print(sources, destinations)
        ips = list(set(sources).intersection(destinations))
        print(ips)

        return df

    def save_to_csv(self, dataframe, split=False, filename=''):
        if not split:
            data_dir = os.path.join(self.config["PATHS"]["project_dir"], self.config["NETWORK"]["data_dir"])
        else:
            data_dir = os.path.join(self.config["PATHS"]["project_dir"], self.config["NETWORK"]["split_dir"])

        if not filename:
            filename = self.config["NETWORK"]["pcap_export_output"]

        print("Saving CSV export ... ")
        dataframe.to_csv(
            f'{os.path.join(data_dir, filename)}',
            index=False)
        print(f'CSV file {self.config["NETWORK"]["pcap_export_output"]} saved. Exiting')


def main():
    epd = ExportPCAPData()

    if not epd.args.singledir:
        pcap_file = epd.merge_pcap(epd.pcap_file)
        df = epd.extract_data(pcap_file)
        epd.save_to_csv(df)
    else:
        for f in sorted(os.listdir(epd.args.singledir)):
            if f.split('.')[-1] == 'pcap':
                df = epd.extract_data(os.path.join(epd.pcap_dir, f))
                epd.save_to_csv(df, split=True, filename=f'{f}.csv')


if __name__ == '__main__':
    main()
