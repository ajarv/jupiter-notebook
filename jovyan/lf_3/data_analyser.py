import  pandas as pd
import numpy as np
from scipy import stats
import os
from pprint import pprint
import  json
import math
import time

DATA_DIR = "."
RAW_CSV = "%s/tmp/lf.raw.csv" % DATA_DIR
DATA_CSV = "%s/pred.csv" % DATA_DIR
PLANT_CAPACITY_SETTINGS = "%s/plant.capacity.json"%DATA_DIR
PLANT_SETTINGS = "%s/plant_settings.json"%DATA_DIR

def compute_predicted_demand_(df,orders_schedule=None):
    day_demand_zip = orders_schedule or\
                     list(zip([0,60,120,250,310,370],
                         [0,3,9,9,1,0]))
    (start_ix,_),(end_ix,_) = day_demand_zip[0],day_demand_zip[-1]

    _df_start_ix = df.shape[0]
    for ix in range(_df_start_ix,end_ix):
        df.set_value(ix,'day',ix+1)
    df.fillna(0,inplace=True)
    # print(df.index)
    df['JOBIN_PRED'] = 0
    def fill_demand_between(s, e):
        si,sd = s
        ei,ed = e
        _fragment = df.iloc[si:ei].copy()
        ei = ei-1
        _fragment.set_value(si,'JOBIN', sd if si ==0 else df.get_value(si-1,'JOBIN_PRED'))

        if (_fragment.get_value(ei,'JOBIN') == 0 ) : _fragment.set_value(ei,'JOBIN',ed)
        _fragment = _fragment.query('JOBIN > 0 or day in [{0},{1}]'.format(si+1,ei+1))
        # print (_fragment)
        slope, intercept, r_value, p_value, std_err = stats.linregress(_fragment['day'],_fragment['JOBIN'])
        # print(slope,intercept)
        df.loc[si:ei,('JOBIN_PRED')] = intercept + df.loc[si:ei,('day')]*slope
        df.loc[si:ei,('JOBIN_PRED_NAIVE')] = sd + (df.loc[si:ei,('day')] - 1 - si )*(ed - sd)/(ei-si)

    for ix in range(0,len(day_demand_zip)-1):
        fill_demand_between(day_demand_zip[ix],day_demand_zip[ix+1])

    # current_day = df.query("JOBIN > 0")['day'].max()+1

    return df

def compute_predicted_demand(df,orders_schedule=None):
    _df_start_ix = df.shape[0]
    _average_demand = int(df['JOBIN'].mean())
    current_day = int(df['day'].max())
    for ix in range(_df_start_ix,390):
        current_day += 1
        df.set_value(ix,'day',current_day)
        df.set_value(ix,'JOBIN_PRED',_average_demand)
        # print(df.iloc[ix-1]['day'],_template_demand.iloc[ix]['day'],_template_demand.iloc[ix]['demand'])
    # print(df.shape)
    df.fillna(0,inplace=True)

    return df




def create_predictions_csv(in_csv=RAW_CSV,
                           out_csv=DATA_CSV,
                           orders_schedule = None,
                           discount_rate = .1):
    df = pd.read_csv(in_csv)
    current_day = int(df['day'].max())
    compute_predicted_demand(df,orders_schedule=orders_schedule)
    df['day'] = df['day'].astype('int')

    for col in df.columns:
        df[col] =  df[col].apply(lambda x : float(str(x).replace(',','')))

    # Index(['JOBT_075', 'JOBT_100', 'JOBT_125'], dtype='object')
    # sets=3&data=JOBOUT&download=download
    # Index(['JOBOUT_075', 'JOBOUT_100', 'JOBOUT_125'], dtype='object')
    # sets=3&data=JOBREV&download=download
    # Index(['JOBREV_075', 'JOBREV_100', 'JOBREV_125'], dtype='object')
    df['JOBOUT'] = df['JOBOUT_075'] + df['JOBOUT_100'] +df['JOBOUT_125']
    df['JOBT'] = (df['JOBOUT_075']*df['JOBT_075'] + df['JOBOUT_100']*df['JOBT_100']+ df['JOBOUT_125']*df['JOBT_125'])/df['JOBOUT']
    df['JOBREV'] = (df['JOBOUT_075']*df['JOBREV_075'] + df['JOBOUT_100']*df['JOBREV_100']+ df['JOBOUT_125']*df['JOBREV_125'])/df['JOBOUT']

    df['PENDING'] =  df['JOBIN'].cumsum() - df['JOBOUT'].cumsum()

    plant_settings = json.load( open( PLANT_SETTINGS, "r" ))
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
     }'''
    cost_per_kit,kits_per_order ,revenue_per_order= plant_settings['inventory']['unit_cost'] , \
                                                    plant_settings['order']['kits_per_order'],\
                                                    plant_settings['order']['revenue_per_order']

    Order_COGS = cost_per_kit * kits_per_order
    df['EARN'] =   (df['JOBOUT_075']*df['JOBREV_075'] + df['JOBOUT_100']*df['JOBREV_100']+ df['JOBOUT_125']*df['JOBREV_125']) # - df['JOBOUT'] * Order_COGS

    def eoq_for_day(day):
        lead_time = int(plant_settings['inventory']['lead_time'])
        day = int(day)
        if df.iloc[-1]['day'] - day < lead_time:
            return 0,100,0
        R ,S , H=  df.iloc[day+lead_time-1]['JOBIN_PRED'],plant_settings['inventory']['order_cost'], Order_COGS*discount_rate/365
        demand_std,service_level =   df.iloc[day-10:day]['JOBIN'].std(),2.5
        eoq = math.ceil(math.sqrt(  2 *  R * S / H))
        cycle_stock = df.iloc[day:day+lead_time+5]['JOBIN_PRED'].sum()
        safety_stock =   math.ceil ( service_level * (lead_time**.5) * demand_std )
        rop = cycle_stock + safety_stock
        cost = eoq * Order_COGS + S
        return (eoq,rop,cost)

    #--- Inventory
    # print("###-- kits_per_order",kits_per_order)
    df['INV'] = df['INV'] / kits_per_order
    df['EXPENSE'] =  0.0


    print ("-------- Data Analyser \t:",time.ctime())

    if current_day-1 < df.shape[0] :
        # df.loc[current_day-1:,('EARN')] = df.loc[current_day-1:,('JOBIN_PRED')] * ( revenue_per_order-Order_COGS)
        average_demand  = df.iloc[:current_day]['JOBIN'].mean()
        current_inventory = df.iloc[current_day-1]['INV']
        df.loc[current_day-1:,('EARN')] = df.loc[current_day-1:,('JOBIN_PRED')] * ( revenue_per_order)
        supply_lead_time = 15
        minimum_stock15 = supply_lead_time * average_demand
        S = 1000
        for ix in range(current_day,df.shape[0]):
            new_inv = df.iloc[ix-1]['INV'] - df.iloc[ix]['JOBIN_PRED']
            day = df.iloc[ix]['day']
            # eoq,rop,order_cost = eoq_for_day(day)
            rop = eoq = minimum_stock15
            order_cost = eoq * Order_COGS + S
            if new_inv < rop:
                # print ("Inventory Order Settings:",day,new_inv,rop,eoq,order_cost)
                new_inv += eoq
                df.iloc[ix]['EXPENSE'] = order_cost
            df.iloc[ix]['INV'] = new_inv


    # print  (df.loc[current_day-1:,('EARN')] )
    df['CUM_EARN'] = (df['EARN']-df['EXPENSE']).cumsum()



    # df = fill_predicted_demand(df)

    df['PRED_DIFF'] = df['JOBIN_PRED'].cumsum() - df['JOBIN'].cumsum()

    columns = ['day','CASH','CUM_EARN','INV', 'JOBIN', 'JOBQ', 'JOBOUT','JOBT', 'JOBREV','S1IN','S1Q',
               'S1UTIL','S2Q', 'S2UTIL', 'S3Q', 'S3UTIL','PENDING' ,'JOBIN_PRED','JOBOUT_075', 'JOBOUT_100',
               'JOBOUT_125','JOBT_075', 'JOBT_100', 'JOBT_125',
               'JOBREV_075', 'JOBREV_100', 'JOBREV_125','EARN']
    df = df.reindex_axis(columns, axis=1)

    bkpfile = out_csv+".bak"
    csvfile = out_csv
    if os.path.exists(bkpfile):
        os.remove(bkpfile)
    if os.path.exists(csvfile):
        os.rename(csvfile,bkpfile)

    df.to_csv(csvfile,index=False)


def predict_plant_capability(mc_counts):
    '''
    plant_settings = {'inventory': {'lead_time': 4.0,
               'order_cost': 1000.0,
               'order_quantity': 7200,
               'reoder_point': 4200,
               'unit_cost': 10.0},
 'order': {'contract_type': 1,
           'lot_size': 60,
           'max_lead_time': 3.0,
           'quoted_lead_time': 1.0,
           'wip_limit': 999},
 'station_1': {'cost_price': 90000.0,
               'machine_count': 1,
               'salvage_value': 10000.0,
               'sched_policy': 'FIFO',
               'station_id': 1},
 'station_2': {'cost_price': 80000.0,
               'machine_count': 1,
               'salvage_value': 10000.0,
               'sched_policy': 'FIFO',
               'station_id': 2},
 'station_3': {'cost_price': 100000.0,
               'machine_count': 1,
               'salvage_value': 10000.0,
               'sched_policy': 'FIFO',
               'station_id': 3}}

    :return:
    '''
    df = pd.read_csv(DATA_CSV).iloc[:60]
    df['day'] = df['day'].astype('int')

    # print(df[['JOBIN','JOBOUT','PENDING']])
    zero_pending_day = df.query('PENDING == 0 and day > 21')['day'].min()
    if zero_pending_day != zero_pending_day : zero_pending_day = 30
    # zero_pending_day=29
    # print("zero_pending_day",zero_pending_day)
    min_observed_processing_time_per_order = df['JOBT'].min()
    util_calc_df = df[:zero_pending_day]

    orders_processed = util_calc_df['JOBIN'].sum()
    plant_settings = json.load(open(PLANT_SETTINGS,"r"))
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

    lot_size ,kits_per_order = plant_settings['order']['lot_size'] ,plant_settings['order']['kits_per_order']

    lots_per_order = kits_per_order/lot_size #-- For first 50 days
    # kits_per_order = lot_size * lots_per_order
    kits_processed = orders_processed  * kits_per_order


    plant_capability = {}
    station_mc_times_per_order = []
    for ix in [1,2,3]:
        station_name = 'station_{0}'.format(ix)
        station_utilization = util_calc_df['S{0}UTIL'.format(ix)].sum()

        # machine_count = station_setting['machine_count']
        machine_count = mc_counts[station_name]
        station_capacity_daily_orders = orders_processed/station_utilization

        # print(station_name ,machine_count,station_capacity_daily_orders,1/station_capacity_daily_orders)

        machine_capacity_daily_kits = station_capacity_daily_orders*kits_per_order/machine_count

        machine_capacity_daily_lots = machine_capacity_daily_kits / lot_size

        station_machine_time_per_order  = station_machine_time_per_lot = 1/machine_capacity_daily_lots
        # print(station_name,"station_capacity_daily_orders",station_capacity_daily_orders,"machine_capacity_daily_lots",machine_capacity_daily_lots)


        plant_capability[station_name] = station_capability =  {}

        station_capability['machine_time_per_order_60'] = station_machine_time_per_order
        station_capability['machine_capacity_daily_kits'] =\
            machine_capacity_daily_kits = kits_processed/(station_utilization * machine_count)
        station_capability['machine_kit_processing_time'] = 1/machine_capacity_daily_kits

        station_mc_times_per_order.append(station_machine_time_per_order)



    print("station_mc_times_per_order",station_mc_times_per_order)
    plant_mc_time_per_order  = np.sum(station_mc_times_per_order)
    setup_time_per_order = max(0, min_observed_processing_time_per_order - plant_mc_time_per_order)

    plant_capability.update(dict(plant_mc_time_per_order_60=plant_mc_time_per_order,
                            setup_time_per_order=setup_time_per_order,
                            min_observed_processing_time_per_order = min_observed_processing_time_per_order))

    json.dump( plant_capability , open(PLANT_CAPACITY_SETTINGS, "w" ),indent=1)
    pprint(plant_capability)



if __name__ == "__main__":
    orders_schedule = list(zip([0,60,120,250,310,370,390],
                             [0,6,19,19,6,3,0]))
    create_predictions_csv(orders_schedule=orders_schedule)
    if not os.path.exists(PLANT_CAPACITY_SETTINGS):
        plant_settings = json.load(open(PLANT_SETTINGS,"r"))
        mc_counts =  dict(station_1=plant_settings['station_1']['machine_count'],
                          station_2=plant_settings['station_2']['machine_count'],
                          station_3=plant_settings['station_3']['machine_count'])
        predict_plant_capability(mc_counts=mc_counts)
    # predict_plant_capability(mc_counts=dict(station_1=1,station_2=1,station_3=1))
