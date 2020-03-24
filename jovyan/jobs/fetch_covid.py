import requests
from bs4 import BeautifulSoup
import re
import datetime
import csv
import sys

def get_html(u = 'https://www.worldometers.info/coronavirus/#countries'):
    res = requests.get(u)
    if res.status_code == 200:
        return res.text
    return null

def get_current_stats(html_doc):
    if not html_doc : return None
    soup = BeautifulSoup(html_doc, 'html.parser')
    table = soup.find_all(id='main_table_countries_today')[0]
    output_rows = []

    _tr = table.select_one('thead > tr')
    output_rows.append([item.text for item in _tr.select('th')])

    _trs = table.select('tbody > tr')
    for _tr in _trs:
        output_rows.append([item.text for item in _tr.select('td')])

    return output_rows


def formatted_rows(html_doc):
    rows = get_current_stats(html_doc)
    if not rows : return None
    rows[0] = ['Country', 'TotalCases', 'NewCases', 'TotalDeaths', 'NewDeaths', 'TotalRecovered', 'ActiveCases', 'Serious_Critical', 'Cases_By_Million']
    for row in rows[1:]:
        for ix in range(1,len(row)):
            row[ix] = re.sub("[^0-9.]", "", row[ix])
        #print (row)
    return rows

if __name__ == "__main__":
    html_doc = get_html()
    rows = formatted_rows(html_doc)
    data_dir = sys.argv[1]
    file_name = datetime.datetime.now().strftime('cov-%Y-%m-%d.%H.csv')
    csv_file = f'{data_dir}/{file_name}'
    if rows:
        with open(csv_file, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)
        print ("Wrote CSV File",csv_file)
