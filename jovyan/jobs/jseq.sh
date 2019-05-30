#!/bin/bash
#BASE
BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

echo "Fetching Treasury Rates Data"
python ${BASE}/job-fetchdata.py --out-csv /data/treasury_yield.csv

echo "Creating Charts"
mkdir -p ${BASE}/../notebook/charts
python ${BASE}/job-makechart.py --in-csv /data/treasury_yield.csv --out-png ${BASE}/../charts/ty_3m_5y_30y.png

