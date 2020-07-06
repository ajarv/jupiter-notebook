#!/bin/bash

# cd /home/ajar/workspace/jupiter-notebook
docker-compose run --rm --entrypoint python beast jobs/fetch_covid.py /data
