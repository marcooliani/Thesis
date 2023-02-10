#!/usr/bin/env python3
import os

import pandas as pd
import csv
import glob
import argparse
import configparser
import subprocess


class SwatCSVExtractor:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-f', "--file", type=str, help="single pcap file to include (with path")
        group.add_argument('-m', "--mergefiles", nargs='+', default=[], help="multiple pcap files to include (w/o path)")
        group.add_argument('-d', "--mergedir", type=str, help="directory containing pcap files to merge")
        parser.add_argument('-t', "--timerange", nargs=2, default=[], help="time range selection (format YYYY-MM-DD HH:MM:SS")
        self.args = parser.parse_args()

        self.df = None
        self.csv_file = self.args.file
        self.csv_multiple = self.args.mergefiles
        self.csv_dir = None
        self.csv_timerange = self.args.timerange

    def check_args(self):
        if self.args.mergedir:
            self.csv_dir = self.args.mergedir

    def import_csv(self):
        if self.csv_file:
            '''
            self.df = pd.read_csv('~/UniVr/Tesi/datasets_SWaT/Altro/nwscan.csv',
                                  usecols=['date', 'time', 'src', 'dst', 'appi_name', 'Modbus_Function_Description',
                                           'Modbus_Transaction_ID', 'SCADA_Tag', 'Modbus_Value', 'Tag'])
            '''
            self.df = pd.read_csv(self.csv_file,
                                  usecols=['date', 'time', 'src', 'dst', 'appi_name', 'Modbus_Function_Description',
                                           'Modbus_Transaction_ID', 'SCADA_Tag', 'Modbus_Value', 'Tag'])

        if self.csv_multiple:
            self.df = pd.concat(map(lambda file:
                                    pd.read_csv(file,
                                                usecols=['date', 'time', 'src', 'dst', 'appi_name',
                                                         'Modbus_Function_Description', 'Modbus_Transaction_ID',
                                                         'SCADA_Tag', 'Modbus_Value', 'Tag'], header=0),
                                    self.csv_multiple), ignore_index=True)

        if self.csv_dir:
            print(self.csv_dir)
            self.df = pd.concat(map(lambda file:
                                    pd.read_csv(file,
                                                usecols=['date', 'time', 'src', 'dst', 'appi_name',
                                                         'Modbus_Function_Description', 'Modbus_Transaction_ID',
                                                         'SCADA_Tag', 'Modbus_Value', 'Tag'], header=0),
                                    glob.glob(os.path.join(self.csv_dir, '*.csv'))), ignore_index=True)

        self.df[self.config['DATASET']['timestamp_col']] = \
            pd.to_datetime(self.df['date']).dt.strftime('%Y-%m-%d') + " " + \
            pd.to_datetime(self.df['time']).dt.strftime('%H:%M:%S.%f')

        timestamp = self.df.pop(self.config['DATASET']['timestamp_col'])
        self.df.insert(loc=0, column=self.config['DATASET']['timestamp_col'], value=timestamp)
        self.df = self.df.drop('time', axis=1, errors='ignore')
        self.df = self.df.drop('date', axis=1, errors='ignore')
        self.df = self.df.drop(self.df[self.df.appi_name != 'CIP_read_tag_service'].index)
        # self.df = self.df.drop('appi_name', axis=1, errors='ignore')

        cond = self.df['Modbus_Function_Description'].str.contains('Response')
        mp = {'src': 'dst', 'dst': 'src'}
        self.df.update(self.df.loc[cond].rename(mp, axis=1))

        print(self.df)
        sources = self.df['src'].unique()
        print(sources)

        self.df.to_csv(f'test_net2015.csv', index=False)


def main():
    sce = SwatCSVExtractor()
    sce.check_args()
    sce.import_csv()


if __name__ == '__main__':
    main()
