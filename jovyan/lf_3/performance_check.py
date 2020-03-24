import io
import sys
import os
import json
import math
import numpy as np
import pandas as pd
import shelve
import math
import matplotlib.pyplot as plt
from pylab import rcParams
import numpy as np
rcParams['figure.figsize'] = 16, 10
rcParams['lines.linewidth'] = 1


#############################
###
DATA_DIR = "."
###
#############################

class StatusManager:
    DATA_FILE_CSV = '%s/pred.csv' % DATA_DIR
    PLANT_SETTINGS = "%s/plant_settings.json"%DATA_DIR
    PLANT_CAPACITY_SETTINGS = "%s/plant.capacity.json"%DATA_DIR
    def __init__(self):
        self.load_data()
    def load_data(self):
        self.df = df = pd.read_csv(self.DATA_FILE_CSV)
        df.fillna(0,inplace=True)
        self.plant_settings = json.load( open( self.PLANT_SETTINGS, "r" ))
        self.plant_capability  = json.load( open(self.PLANT_CAPACITY_SETTINGS, "r" ))
    @property
    def current_day(self):
        return int(self.df.query('JOBIN > 0')['day'].max())

    def check_inventory_low(self,current_day=None,expected_daily_demand=None):
        df = self.df
        current_day = self.current_day
        current_inventory = df.iloc[current_day-1]['INV']
        print ("###")
        print ("###\t Current Day:\t",current_day)
        print ("###\t Average Demand\t:",df.iloc[:current_day-1]['JOBIN'].mean(),"\t INVENTORY AT HAND \t:",current_inventory)
        print ("###\t Inventory Order status : KITS\t",self.plant_settings['inventory']['outstanding_kits'],
               "\tDays:\t",self.plant_settings['inventory']['outstanding_kits_eta'])
        print ("###")
        # print("current_day,mean_demand = ",current_day,df.iloc[:current_day-1]['JOBIN'].mean())
        expected_daily_demand = expected_daily_demand or df.iloc[:current_day-1]['JOBIN'].mean()
        supply_lead_time = 15
        minimum_stock15 = supply_lead_time * expected_daily_demand
        minimum_stock20 = (supply_lead_time + 5)* expected_daily_demand
        print("### PLEASE MAKE SURE YOU PASS IN EXPECTED DEMAND ####")
        # print ("minimum_stock20,minimum_stock15 = ",minimum_stock20,minimum_stock15)
        print("Days remaining ", (current_inventory - minimum_stock15 )/expected_daily_demand)
        warning = current_inventory < minimum_stock20

        return  warning,current_inventory,minimum_stock15,minimum_stock20

    def check_station_performance(self):
        df = self.df
        current_day = self.current_day
        '''
        plant_settings
             "order": {
              "quoted_lead_time": 1.0,
              "wip_limit": 999,
              "contract_type": 1,
              "max_lead_time": 3.0,
              "kits_per_order": 60,
              "lot_size": 60
             }

             "inventory": {
              "lead_time": 4.0,
              "reoder_point": 4200,
              "order_cost": 1000.0,
              "order_quantity": 7200,
              "unit_cost": 10.0
             }
        '''

        df20 = df.iloc[current_day-20:current_day].copy()# last 20 day data
        def s1LastZero():
            station_name = 'station_1'
            machine_count = self.plant_settings[station_name]['machine_count']
            station_capacity = self.plant_capability[station_name]['machine_capacity_daily_kits'] *\
                               self.plant_settings['order']['kits_per_order']
            workkey = 'S1WORK'
            df20[workkey] = station_capacity * df20['S1UTIL']
            checkpoint = np.max( df20['day'] * ( df20[workkey]   > df20['JOBIN'] ) )
            return checkpoint

        d1zero  = s1LastZero()
        days_working = min (1,(current_day - d1zero) + 1)
        working_df =  df20.tail(days_working).copy()

        jobs_in = working_df['JOBIN'].sum()
        jobs_out = working_df['JOBOUT'].sum()

        sinfos = {}
        jobs_done_per_station  = {}
        kits_per_order = self.plant_settings['order']['kits_per_order']
        for ix in [1,3,2]:
            station_name ="station_{0}".format(ix)
            machine_count = self.plant_settings[station_name]['machine_count']
            station_capacity = machine_count * self.plant_capability[station_name]['machine_capacity_daily_kits'] / kits_per_order
            jobs_completed = station_capacity * (working_df['S{0}UTIL'.format(ix)].sum())
            jobs_done_per_station[station_name] = jobs_completed
            # print(station_name,jobs_in,jobs_out,jobs_completed)
            if ix == 1:
                pending = max(0, jobs_in - jobs_completed )
            elif ix == 3:
                pending = max(0, jobs_done_per_station['station_1'] - jobs_completed )
            else :
                # pending = max(0, jobs_done_per_station['station_3'] - jobs_completed )
                pending = max(0,
                              (jobs_done_per_station['station_1'] + jobs_done_per_station['station_3'] )/2 - jobs_completed ,
                              jobs_done_per_station['station_1'] -jobs_out )

            average_util = working_df['S{0}UTIL'.format(ix)].mean()
            warning = pending > (station_capacity * .20) or average_util > .9
            sinfos[station_name] = [station_name,machine_count,station_capacity,average_util,pending,warning]

        sdf = pd.DataFrame([sinfos[sname] for sname in ['station_1','station_2','station_3']])
        sdf.columns = "station_name,machine_count,station_capacity,average_util,pending,warning".split(',')

        wdf_recent = df20.tail(5).copy()

        warning = sdf['warning'].sum() > 0

        return sdf,wdf_recent,warning



class TeamManager:
    PRED_CSV = '%s/pred.csv'%(DATA_DIR)
    TEAMS_CSV = "%s/team_standings.csv"%DATA_DIR
    PLANT_SETTINGS = "%s/plant_settings.json"%DATA_DIR
    def __init__(self):
        pass

    def get_damand_info(self):
        groups_df = pd.read_csv(self.TEAMS_CSV,infer_datetime_format=True,
                                   index_col='TS')
        teams = [cn for cn in  groups_df.columns if cn not in ['TS','day']]
        # S800,S900,S1000 = 0,0,0
        for team_name in teams:
            kcash  = team_name
            kdcash = "D_{0}".format(team_name)
            groups_df[kdcash] = groups_df[kcash].diff()
            # S800 += ((groups_df.tail(4)[kdcash] % 800) == 0).sum()
            # S900 += ((groups_df.tail(4)[kdcash] % 900) == 0).sum()
            # S1000 += ((groups_df.tail(4)[kdcash] % 1000) == 0).sum()
            # if cash_sum > 0:
            #     if int(cash_sum) % 800 == 0:
            #         S800 = int(cash_sum/800)
            #     elif int(cash_sum) % 900 == 0:
            #         S900 = int(cash_sum/900)
            #     elif int(cash_sum) % 1000 == 0:
            #         S1000 = int(cash_sum/1000)

        # print("-------Order Rate vs Bid Price--------")
        # print("S800,S900,S1000 = ",S800,S900,S1000)
        # print("---------------------------------------")

        diffdf = groups_df[['day']+["D_{0}".format(team_name) for team_name in teams]]

        earnings = []
        for team_name in teams:
            kdcash = "D_{0}".format(team_name)
            earning = ((groups_df[kdcash] > 0)*groups_df[kdcash] ).sum()
            earnings.append([team_name,earning])
        earnings.sort(key=lambda x:x[1],reverse=True)

        print("-------Top Earning Teams--------")
        top_earnings = earnings[:10]
        top_earners = ['encinitas'] +[k for k,x in top_earnings]

        print(top_earnings)
        for ix in range(0,len(earnings)):
            if earnings[ix][0] =='encinitas':
                print("encinitas Ranking",ix+1, earnings[ix])
        print("---------------------------------------")

        top_d_columns = ["D_{0}".format(team_name)  for team_name in top_earners ]
        top_columns =['day']+ top_d_columns
        # print (top_columns)
        diffdf[top_columns].to_csv("DIFF_EARNINGS.csv",index=False)

    def get_leader_board(self):
        groups_df = pd.read_csv(self.TEAMS_CSV,infer_datetime_format=True,
                                   index_col='TS')
        orders_df = pd.read_csv(self.PRED_CSV)

        def get_top_teams():
            teams = [cn for cn in  groups_df.columns if cn not in ['TS','day']]
            row_dict = groups_df.tail(1)[teams].to_dict()
            #'teamawesome': {13: 205755.0}
            team_cash_map= [(k,list(v.items())[0][1]) for k,v in row_dict.items()]
                # [  (k,v[v.keys()[0]])  for (k,v) in  row_dict.items() ]
            team_cash_map.sort(key=lambda e:e[1],reverse=True)
            team_cash_map= team_cash_map[:6]
            return [team_name for (team_name,cash) in team_cash_map]

        leading_teams = teams = get_top_teams()
        groups_df = groups_df[['day']+leading_teams].copy()

        groups_df['JOBIN'] = groups_df.apply(lambda row: ((orders_df['day']== row['day'])*orders_df['JOBIN']).mean() ,axis=1)
        plant_settings = json.load( open( self.PLANT_SETTINGS, "r" ))
        '''
         "order": {
          "quoted_lead_time": 1.0,
          "wip_limit": 999,
          "contract_type": 1,
          "max_lead_time": 3.0,
          "kits_per_order": 60,
          "lot_size": 60
         }

         "inventory": {
          "lead_time": 4.0,
          "reoder_point": 4200,
          "order_cost": 1000.0,
          "order_quantity": 7200,
          "unit_cost": 10.0
         }
         '''
        shipping_cost,kits_per_order,unit_cost = plant_settings['inventory']['order_cost'],\
                                                 plant_settings['order']['kits_per_order'],\
                                                 plant_settings['inventory']['unit_cost']
        shipping_lead_time = plant_settings['inventory']['lead_time']
        Order_COGS = kits_per_order * unit_cost
        for team_name in teams:
            kcash  = team_name
            kdcash = "D_{0}".format(team_name)
            kinv   = "I_{0}".format(team_name)
            kass   = "A_{0}".format(team_name)
            groups_df[kdcash] = groups_df[kcash].diff()
            groups_df[kinv] = ( (groups_df[kdcash] < 0 ) *(-1)* groups_df[kdcash] - shipping_cost )/Order_COGS

            inv_refresh_day = max(( (groups_df[kdcash] < 0 ) * groups_df['day']).max(),1)
            inv_count = int( (( -groups_df[kdcash].min())-shipping_cost)/kits_per_order) + \
                        shipping_lead_time * orders_df.get_value(inv_refresh_day-1,'JOBIN_PRED')

            groups_df[kinv] = groups_df.apply(lambda  row: (row["day"] > inv_refresh_day)
                            *(inv_count - orders_df.iloc[int(inv_refresh_day):int(row["day"]-1)]['JOBIN'].sum() ), axis=1)
            groups_df[kass] = groups_df[kcash] + (groups_df[kinv]*Order_COGS)
        return  groups_df

    def get_top_10(self):
        groups_df = pd.read_csv(self.TEAMS_CSV,infer_datetime_format=True,
                                   index_col='TS')
        orders_df = pd.read_csv(self.PRED_CSV)

        def get_top_teams():
            teams = [cn for cn in  groups_df.columns if cn not in ['TS','day']]
            row_dict = groups_df.tail(1)[teams].to_dict()
            #'teamawesome': {13: 205755.0}
            team_cash_map= [(k,list(v.items())[0][1]) for k,v in row_dict.items()]
                # [  (k,v[v.keys()[0]])  for (k,v) in  row_dict.items() ]
            team_cash_map.sort(key=lambda e:e[1],reverse=True)
            team_cash_map= team_cash_map[:10]
            return [team_name for (team_name,cash) in team_cash_map]

        leading_teams = teams = get_top_teams()
        groups_df = groups_df[['day']+leading_teams].copy()

        return  groups_df


competition_id,institution,username,password = 'opscom','opscom','encinitas','7rosemary'


if __name__ == "__main__":
    status_man = StatusManager()
    inventory_warning,current_inventory,minimum_stock15,minimum_stock20 = status_man.check_inventory_low()
    print("-------- INVENTORY CHECK: \t",inventory_warning and "WARNING - Inventory" or "A OK" )
    sdf,wdf,warning = status_man.check_station_performance()
    print("-------- UTILIZATION CHECK: \t",warning and "WARNING - Utilization" or "A OK" )
    print("----Stations----")
    print(sdf.to_string(index=False))
    print("----Recent Work----")
    print(wdf[['day','JOBIN','JOBOUT','PENDING','JOBREV','JOBT','INV']].to_string(index=False))
    print("--------")
    # status_man.show_stations(start_day=30,end_day=50)
    # status_man.show_orders()
    team_man = TeamManager()
    team_man.get_damand_info()
    # print("--- Leader Board----")
    # print(team_man.get_top_10().tail(1).to_string(index=False))
    # team_man.show_team_standings()
    # plt.show()
