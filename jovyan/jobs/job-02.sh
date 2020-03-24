#!/bin/bash

#BASE
BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
WORK_DIR=/home/jovyan

echo "Fetching Covid Data"
python ${BASE}/fetch_covid.py 


