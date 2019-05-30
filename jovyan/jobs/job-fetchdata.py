import urllib.request
import xml.etree.ElementTree as ET
import os
import pandas as pd
import numpy as np
import logging
import datetime


def get_year_rates(year=2019):
    logging.info("Fetching for year {year}".format(year=year))

    _url = 'http://data.treasury.gov/feed.svc/DailyTreasuryYieldCurveRateData?$filter=year(NEW_DATE)%20eq%20{0}'.format(
        year)
    with urllib.request.urlopen(_url) as response:
        root = ET.parse(response)
    d = {}
    for _entry in root.findall(".//m:properties", namespaces={'m': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'}):
        for a in _entry:
            tg, tx = a.tag.split("}")[1], a.text
            _l = d.get(tg, None) or []
            _l.append(tx)
            d[tg] = _l
#     print(d)
    df = pd.DataFrame(data=d)
    df.sort_values(by=['NEW_DATE'], ascending=[True], inplace=True)
    df.NEW_DATE = pd.to_datetime(df.NEW_DATE)
    df = df.set_index('NEW_DATE')
#     df.drop('NEW_DATE', axis=1, inplace=True)

    for cn in [c for c in df.columns if c[:3] == 'BC_']:
        df[cn] = df[cn].astype('float')
    return df


def load_web_data(csv_file_path):
    logging.info("Using CSV File :{csv_file_path}".format(
        csv_file_path=csv_file_path))
    now = datetime.datetime.now()
    yr = now.year + 1
    if os.path.exists(csv_file_path):
        dfa = [get_year_rates(year) for year in range(yr-1, yr)]
        df = pd.read_csv(csv_file_path)
        df.NEW_DATE = pd.to_datetime(df.NEW_DATE)
        df = df.set_index('NEW_DATE')
        dfa = [df]+dfa
    else:
        dfa = [get_year_rates(year) for year in range(1990, yr)]

    df = pd.concat(dfa)
#     df = df.drop_duplicates(subset='index', keep='last')
#     df.NEW_DATE = pd.to_datetime(df.NEW_DATE)
#     df = df.set_index('NEW_DATE')
    # dfa = [get_year_rates(year) for year in range(2015,2017)]
    df.to_csv(csv_file_path, sep=',')
    return df


def load_local_data(csv_file_path):
    df = pd.read_csv(csv_file_path)
#     TS = df['NEW_DATE'].astype('datetime64')
    df.NEW_DATE = pd.to_datetime(df.NEW_DATE)
    df = df.set_index('NEW_DATE')
    return df


def main():
    LOGFORMAT = '<%(asctime)-15s> %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)
    # base_dir = os.path.abspath(os.path.split(__file__)[0]+'/..')
    # LOCAL_FILE = os.path.join(base_dir, "data","treasury_yield.csv")
    from optparse import OptionParser
    parser = OptionParser(description='Download US Treasury Bond Rates')
    parser.add_option("-f", "--out-csv", dest="filename",
                    help="CSV File Path", metavar="FILE")
    (options, args) = parser.parse_args()
    print(options,args)
    csv_file_path = options.filename

    df = load_web_data(csv_file_path)
    print(df.tail(1))


if __name__ == "__main__":

    main()
    