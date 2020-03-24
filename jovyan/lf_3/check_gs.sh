#!/bin/bash

cd /home/ajar/work/lf_3
/home/ajar/.conda/envs/tf/bin/python ./dnld_team_status.py  >> auto_pilot.log
/home/ajar/.conda/envs/tf/bin/python ./data_analyser.py  >> auto_pilot.log
/home/ajar/.conda/envs/tf/bin/python ./inventory_check.py  >> auto_pilot.log
/home/ajar/.conda/envs/tf/bin/python ./performance_check.py  >> perp_pilot.log
#/home/ajar/.conda/envs/tf/bin/python ./diff_analyzer.py  >> perf_pilot.log
