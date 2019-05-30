@setlocal

call xcmd
call activate lotusmoon
echo "Fetching Treasury Rates Data"
python job-fetchdata.py --out-csv ../data/treasury_yield.csv

echo "Creating Charts"
python job-makechart.py --in-csv ../data/treasury_yield.csv --out-png ../notebook/charts/ty_3m_5y_30y.png

