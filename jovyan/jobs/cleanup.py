import os
import sys
import csv
import datetime

hdrs = ['Time','Country', 'TotalCases', 'NewCases', 'TotalDeaths',\
         'NewDeaths', 'TotalRecovered', 'ActiveCases', 'Serious_Critical', 'Cases_per_mill','Deaths_per_mill']

def clean_file(file_path):
    _d,_f = os.path.split(file_path)
    ts = datetime.datetime.strptime(_f,'cov-%Y-%m-%d.%H.csv').isoformat()
    with open(file_path) as f: 
        rdr = csv.reader(f)
        rows = list(rdr)
    if rows[0][0] == 'Time':
        print(f"File {file_path} is latest not doing anything")
        return
    rows[0] = hdrs
    for ix in range(1,len(rows)):
        rows[ix] = [ts] + rows[ix]
    
    with open(file_path,'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

if __name__ == "__main__":
    p,f = os.path.split(sys.argv[1])
    _ff = [_f for _f in os.listdir(p) if _f.startswith(f)]
    for _f in _ff:
        print (_f)
        clean_file(f"{p}/{_f}")
