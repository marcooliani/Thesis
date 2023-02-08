#!/usr/bin/env python3

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
        self.args = parser.parse_args()

        self.df = None

    def check_args(self):
        pass

    def import_csv(self, file):
        self.df = pd.read_csv('~/UniVr/Tesi/datasets_SWaT/Altro/nwscan.csv',
                              usecols=['date', 'time', 'src', 'dst', 'appi_name', 'Modbus_Function_Description',
                                       'Modbus_Transaction_ID', 'SCADA_Tag', 'Modbus_Value', 'Tag'])

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
    sce.import_csv('bla')


if __name__ == '__main__':
    main()
