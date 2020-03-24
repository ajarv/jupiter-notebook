import io
import sys
import os
import json
import math
import numpy as np
import pandas as pd
import shelve
import math
import numpy as np
import logging
import httplib2,urllib
from web_util import SimStatus,SimSettings,BeautifulSoup,LittleFieldWebSite
from performance_check import StatusManager

#############################
###
DATA_DIR = "."
###
#############################




class InventoryManager:
    DATA_FILE_CSV = '%s/pred.csv' % DATA_DIR
    PLANT_SETTINGS = "%s/plant_settings.json"%DATA_DIR
    PLANT_CAPACITY_SETTINGS = "%s/plant.capacity.json"%DATA_DIR
    TEAMS_CSV = "%s/team_standings.csv"%DATA_DIR
    def __init__(self):
        self.load_data()
        self.order_settings = None
    def load_data(self):
        self.df = df = pd.read_csv(self.DATA_FILE_CSV)
        df.fillna(0,inplace=True)
        self.plant_settings = json.load( open( self.PLANT_SETTINGS, "r" ))
        self.plant_capability  = json.load( open(self.PLANT_CAPACITY_SETTINGS, "r" ))
        self.inventory_settings = None
    @property
    def current_day(self):
        return int(self.df.query('JOBIN > 0')['day'].max())
    def get_order_settings(self):
        order_settings = self.order_settings  or _SIMSettings.get_order_settings()
        self.order_settings  = order_settings
        return  order_settings
    def get_unreported_JOBOUT(self):
        team_name ='encinitas'
        _teamdf = pd.read_csv(self.TEAMS_CSV,usecols=['day',team_name])
        _teamdf[team_name] = (_teamdf[team_name] > 0)* _teamdf[team_name]
        _teamdf[team_name] -= (_teamdf[team_name] %100) #interest
        _teamdf[team_name] = _teamdf[team_name].diff()
        _day = _teamdf.iloc[-1]['day']
        order_settings = self.get_order_settings()
        _rev_per_order =  order_settings['revenue_per_order']
        _unreported_kits_today = math.ceil( _teamdf.query("day == {0}".format(_day))[team_name].sum()/_rev_per_order)
        print(_day,_rev_per_order,_unreported_kits_today)
        # {'max_lead_time': 2.0, 'revenue_per_order': 1000.0, 'wip_limit': 10, 'lot_size': 1, 'quoted_lead_time': 1.0, 'kits_per_order': 1, 'contract_type': 1}
    def is_inv_available(self):
        current_day = self.current_day
        current_inventory = self.inventory_in_stock 
        mean_demand = self.current_demand 

        if current_inventory > mean_demand:
            return True

        if np.abs(mean_demand -current_inventory) < self.max_wip_allowable/4:
            print("There is still some more inventory to consume till next check")
            return True

        inventory_settings = self.inventory_settings = self.inventory_settings or _SIMSettings.get_inventory_settings()
        outstanding_kits ,outstanding_kits_eta =inventory_settings['outstanding_kits'],\
                                                inventory_settings['outstanding_kits_eta']
        if  outstanding_kits > 0 and  outstanding_kits_eta  < .7:
            print ("### More Inventory will be available shortly \t(outstanding_kits ,outstanding_kits_eta)",
                   outstanding_kits ,outstanding_kits_eta)
            return  True

        return False
    @property
    def current_demand(self):
        df = self.df
        current_day = self.current_day
        mean_demand = df.iloc[current_day-5:current_day-1]['JOBIN'].mean()
        return mean_demand
    @property
    def inventory_in_stock(self):
        df = self.df
        current_day = self.current_day
        current_inventory = df.iloc[current_day-1]['INV']
        return  current_inventory

    @property
    def max_wip_allowable(self):
        status_man = StatusManager()
        sdf,wdf,warning = status_man.check_station_performance()
        min_station_capacity  = sdf['station_capacity'].min()

        # current_inventory = self.inventory_in_stock
        # inventory_settings = self.inventory_settings = self.inventory_settings or _SIMSettings.get_inventory_settings()
        # outstanding_kits ,outstanding_kits_eta =inventory_settings['outstanding_kits'],\
        #                                         inventory_settings['outstanding_kits_eta']
        #
        # mean_inventory_depletion_rate_desired = current_inventory/outstanding_kits_eta if outstanding_kits > 0 \
        #     else min_station_capacity
        #
        # max_allowable_wip = min(mean_inventory_depletion_rate_desired,min_station_capacity)

        max_allowable_wip = min_station_capacity

        return  int(max_allowable_wip)
        pass

    def check_WIP_SETTING(self):
        print("##\tChecking  Suitable WIP")

        available = self.is_inv_available()
        order_settings = self.get_order_settings()
        wip_limit = order_settings['wip_limit']

        if(not available):
            if wip_limit == 0:
                print("##\tWIP is already set to Zero and the Inventory is Empty")
                return False
            _SIMSettings.change_WIP(0)
            return True,"Low Inventory setting WIP %r -> %r"%(wip_limit,0)

        max_wip = int(self.max_wip_allowable)

        if max_wip <  wip_limit:
            print("##\tSuggested max_wip:",max_wip," is lesser than and current WIP ",wip_limit," ...Not changing")
            return False

        if np.abs(max_wip - wip_limit) < 5  :
            print("##\tSuggested max_wip:",max_wip," and current WIP ",wip_limit,"close enough so not changing")
            return False

        print("##\tCURRENT max_wip:",wip_limit,"CORRECTING WIP TO ",max_wip)
        _SIMSettings.change_WIP(max_wip)
        return True,"WIP %r -> %r"%(wip_limit,max_wip)


    # def check_wip_zero(self):
    #     order_settings = self.get_order_settings()
    #     wip_limit = order_settings['wip_limit']
    #     print("## WIP Limit :\t",wip_limit)
    #     if (wip_limit == 0 and self.is_inv_available()):
    #         _SIMSettings.change_WIP(13)
    #         return  True
    #     return False
    def should_make_inv_purchase(self):
        inventory_settings =  _SIMSettings.get_inventory_settings()
        outstanding_kits ,outstanding_kits_eta =inventory_settings['outstanding_kits'],\
                                                inventory_settings['outstanding_kits_eta']
        if outstanding_kits == 0  or outstanding_kits_eta < 1:
            print("PLAN NEXT ORDER")
            return  True
        return  False
        pass

    def get_optimum_order(self):

        status_man = StatusManager()
        sdf,wdf,warning = status_man.check_station_performance()
        max_plant_capacity  = sdf['station_capacity'].min()

        current_inventory = self.inventory_in_stock

        df = self.df
        current_day = self.current_day
        mean_demand = df.iloc[current_day-10:current_day-1]['JOBIN'].mean()
        print("#\tCapacity Check : (mean_demand,max_plant_capacity)",mean_demand,max_plant_capacity)

        # expecting_to_process =  min(mean_demand,max_plant_capacity)
        expecting_to_process =  max_plant_capacity

        expecting_to_process = 21
        shipping_days = 17

        optimum_order_size = int(shipping_days * expecting_to_process)

        # optimum_order_size -= current_inventory

        if optimum_order_size < 0:
            optimum_order_size = 0
        # df = self.df
        # current_day = self.current_day
        # mean_demand = df.iloc[current_day-30:current_day-1]['JOBIN'].mean()
        # optimum_order_size = mean_demand * 15
        # print("OPTIMUM Order :\t 30 day mean demand :",mean_demand," x 15 = ",optimum_order_size)
        print("OPTIMUM Order :\t Max Plant Capacity: \n\t(optimum_order_size,expecting_to_process,current_inventory)",
              optimum_order_size,shipping_days * expecting_to_process,current_inventory)

        return int(optimum_order_size)

    def make_max_inventory_order(self):
        print("##\tChecking Inventory Order Settings ")
        optimum_order_size = self.get_optimum_order()
        inventory_settings =  _SIMSettings.get_inventory_settings()
        current_order_quantity = inventory_settings['order_quantity']
        cash_info = _SIMStatus.fetch_cash_standing()
        cash_balance = cash_info['cash_balance']
        max_possible_order = int((cash_balance -1000)/600)
        print("##\tMax Can Afford",max_possible_order)
        order_size = min(optimum_order_size,max_possible_order)
        print("##\tOptimum Order Size",order_size)
        if order_size == current_order_quantity:
            print ("Order size is as desired,(optimum_order_size,max_possible_order,current_order_quantity)=",optimum_order_size,max_possible_order,current_order_quantity)
            return False
        if self.should_make_inv_purchase():
            print("Set Inventory Order size to ",order_size)
            _SIMSettings.set_inventory_order_size(order_size)
            return  True,"Inventory Order %r -> %r"%(current_order_quantity,order_size)
        return False

    def set_optimum_contract_in_last_inventory_days(self):
        print("##\tChecking Contract in last days of Inventory")

        inventory_settings = self.inventory_settings = self.inventory_settings or _SIMSettings.get_inventory_settings()
        outstanding_kits ,outstanding_kits_eta =inventory_settings['outstanding_kits'],\
                                                inventory_settings['outstanding_kits_eta']

        if not(outstanding_kits > 0  and outstanding_kits_eta < 2):
            print("This check does not apply")
            return False

        # {'max_lead_time': 2.0, 'revenue_per_order': 1000.0, 'wip_limit': 10, 'lot_size': 1,
        # 'quoted_lead_time': 1.0, 'kits_per_order': 1, 'contract_type': 1}
        order_settings = self.get_order_settings()
        wip_limit = order_settings['wip_limit']
        demand = self.current_demand

        c_contract_type = order_settings['contract_type']
        inventory_by_demand_ratio = self.inventory_in_stock/(demand * outstanding_kits_eta )

        r3, r2 = 1.4,.8
        # r3, r2 = 1.3,.8

        if inventory_by_demand_ratio > r3:
            contract_type = 3
        elif inventory_by_demand_ratio < r2:
            contract_type = 1
        else:
            contract_type = 2

        print("##\tCURRENT CONTACT :",c_contract_type,"APPROPRIATE CONTACT :",contract_type,
              "inventory_by_demand_ratio:", inventory_by_demand_ratio)
        if c_contract_type != contract_type:
            _SIMSettings.switch_Contract(contract_type)
            return True,"Contract Type for inventory_by_demand_ratio: %r,  %r -> %r"%(inventory_by_demand_ratio,c_contract_type,contract_type)
        return False

    #
    # def set_optimum_contract_a(self):
    #     EXPECTED_BURN_CSV = "./expected_burn.dat"
    #     if not os.path.exists(EXPECTED_BURN_CSV):
    #         print ("## -Expected Burn file missing .. Aborting the optimum contract check")
    #
    #     expected_burn_df = pd.read_csv(EXPECTED_BURN_CSV)
    #     inventory_now = self.inventory_in_stock
    #     current_day = self.current_day
    #
    #
    #     expected_inventory = expected_burn_df.iloc[current_day-1]['INV']
    #
    #     print("## Inventory expectations : (current_day,inventory_now,expected_inventory):",
    #           current_day,inventory_now,expected_inventory)
    #
    #     order_settings = self.get_order_settings()
    #     wip_limit = order_settings['wip_limit']
    #
    #     boost_factor = (expected_inventory - inventory_now) / wip_limit
    #
    #     print("Boost Factor :",boost_factor)
    #
    #     r3, r2 = 1,-1
    #     if boost_factor > r3:
    #         contract_type = 1
    #     elif boost_factor < r2:
    #         contract_type = 3
    #     else:
    #         contract_type = 2
    #
    #
    #
    #     c_contract_type = order_settings['contract_type']
    #     print("##\tCURRENT CONTACT :",c_contract_type,"APPROPRIATE CONTACT :",contract_type,
    #           "boost_factor:", boost_factor)
    #
    #     if c_contract_type != contract_type:
    #         _SIMSettings.switch_Contract(contract_type)
    #         return True,"Contract Type for boost_factor: %r,  %r -> %r"%(boost_factor,c_contract_type,contract_type)
    #     return False

    # def set_optimum_contract_B(self):
    #     print("##\tChecking Best Contract based upon demand")
    #
    #     inventory_now = self.inventory_in_stock
    #     current_day = self.current_day
    #
    #     inventory_settings = self.inventory_settings = self.inventory_settings or _SIMSettings.get_inventory_settings()
    #     outstanding_kits ,outstanding_kits_eta =inventory_settings['outstanding_kits'],\
    #                                             inventory_settings['outstanding_kits_eta']
    #     if (outstanding_kits > 0  and outstanding_kits_eta < 3):
    #         print("#\This check does not apply in the last few days of inventory")
    #         return False
    #
    #     # current_day = self.current_day
    #     # last_2_day_demand_change = self.df.iloc[current_day-3:current_day-1]['JOBIN'].diff().mean()
    #
    #     mean_demand = self.current_demand
    #
    #     max_capacity = self.max_wip_allowable
    #
    #     boost_factor = (max_capacity- mean_demand  ) / max_capacity
    #
    #     print("Boost Factor :",boost_factor,"(max_capacity, mean_demand  )=",max_capacity, mean_demand )
    #
    #     r3, r2 = 0.1,-0.1
    #     contract_options = []
    #     if boost_factor > r3:
    #         #max capacity is more
    #         contract_type = 3
    #     elif boost_factor < r2:
    #         contract_type = 1
    #     else:
    #         contract_type = 2
    #
    #
    #
    #     order_settings = self.get_order_settings()
    #     c_contract_type = order_settings['contract_type']
    #     print("##\tCURRENT CONTACT :",c_contract_type,"APPROPRIATE CONTACT :",contract_type,
    #           "boost_factor:", boost_factor)
    #
    #     if c_contract_type != contract_type:
    #         _SIMSettings.switch_Contract(contract_type)
    #         return True,"Contract Type for boost_factor: %r,  %r -> %r"%(boost_factor,c_contract_type,contract_type)
    #     return False
    def set_optimum_contract_first_phase(self):
        print("##\tChecking Best Contract first phase")

        inventory_now = self.inventory_in_stock
        current_day = self.current_day

        inventory_settings = self.inventory_settings = self.inventory_settings or _SIMSettings.get_inventory_settings()
        outstanding_kits ,outstanding_kits_eta =inventory_settings['outstanding_kits'],\
                                                inventory_settings['outstanding_kits_eta']
        if (outstanding_kits > 0  and outstanding_kits_eta < 2):
            print("#\This check does not apply in the last few days of inventory")
            return False

        contract_type = 2



        order_settings = self.get_order_settings()
        c_contract_type = order_settings['contract_type']
        print("##\tPhaze 1 CURRENT CONTACT :",c_contract_type,"APPROPRIATE CONTACT :",contract_type)

        if c_contract_type != contract_type:
            _SIMSettings.switch_Contract(contract_type)
            return True,"Phaze 1 Contract Type for  %r -> %r"%(c_contract_type,contract_type)
        return False

def post_email(reason,health,toflag='u'):
    url = "http://calm-scarab-685.appspot.com/za/z" #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    data = {'w': toflag, 'health': health,'reason':reason}
    body = urllib.parse.urlencode(data)
    h = httplib2.Http()
    resp, content = h.request(url, method="POST", body=body, headers=headers)
    print ('------Email Send results---------')
    # print(resp)
    print(content)
    print ('------Email Send results---------')
    if resp['status'] != '200':
        print("FATAL ERROR")
        print(resp)
        print(content)
        return None

competition_id,institution,username,password = 'opscom','opscom','encinitas','7rosemary'
_LFWebSite = LittleFieldWebSite(competition_id,institution,username,password )
_SIMSettings = SimSettings(_LFWebSite,competition_id,institution,username,password )
_SIMStatus = SimStatus(_LFWebSite,competition_id,institution,username,password )



LOG_NAME = "plant-monitor"
logging.basicConfig(format='<%(asctime)s> <%(name)s> <%(levelname)s> <%(message)s>',
                    level=logging.INFO,
                    filename="%s.log"%LOG_NAME)

if __name__ == "__main__":
    inv_man = InventoryManager()

    # print (inv_man.get_optimum_order())

    changes_made = []


    # result = inv_man.make_max_inventory_order()
    # if result:
    #     _,reason = result
    #     changes_made.append(reason)

    result = inv_man.check_WIP_SETTING()
    if result:
        _,reason = result
        changes_made.append(reason)


    # result = inv_man.set_optimum_contract_in_last_inventory_days()
    # if result:
    #     _,reason = result
    #     changes_made.append(reason)
    #
    # result = inv_man.set_optimum_contract_first_phase()
    # if result:
    #     _,reason = result
    #     changes_made.append(reason)

    if changes_made:
        email_body = " ; ".join(changes_made)
        print("##   Not Sending email \t:",email_body)
        # post_email(" ; ".join(changes_made),"Update")

    # inventory_warning,current_inventory,minimum_stock15,minimum_stock20 = status_man.check_inventory_low()
    # print("-------- INVENTORY CHECK")
    # print(inventory_warning and "WARNING - Utilization" or "A OK" )
    # sdf,wdf,warning = status_man.check_station_performance()
    # print("-------- UTILIZATION CHECK")
    # print(warning and "WARNING - Utilization" or "A OK" )
    # print("----Inventory----")
    # print("(current_inventory,minimum_stock15,minimum_stock20)=",current_inventory,minimum_stock15,minimum_stock20)
    # print("----Stations----")
    # print(sdf.to_string(index=False))
    # print("----Recent Work----")
    # print(wdf[['day','JOBIN','JOBOUT','PENDING','JOBREV','JOBT','INV']].to_string(index=False))
    # print("--------")
    # # status_man.show_stations(start_day=30,end_day=50)
    # # status_man.show_orders()
    # team_man = TeamManager()
    # team_man.get_damand_info()
    # # print("--- Leader Board----")
    # # print(team_man.get_top_10().tail(1).to_string(index=False))
    # # team_man.show_team_standings()
    # # plt.show()
