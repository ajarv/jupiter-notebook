#!/bin/bash
cd /home/ajar/work/lf_3
/home/ajar/.conda/envs/tf/bin/python ./dnld_plant_status.py  >> auto_pilot.log
/home/ajar/.conda/envs/tf/bin/python ./data_analyser.py  >> auto_pilot.log
