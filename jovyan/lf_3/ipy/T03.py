import io
import httplib2
import numpy as np
import pandas as pd
import time
from scipy import stats
import urllib

DATA_FILE_CSV = r'C:\work\GrayHound\l_f_3\pred.csv'


def make_future_predictions(current_day=None):
    df = pd.read_csv(DATA_FILE_CSV)
    days_elapsed = (df['CUM_EARN'] > 0).sum()
    current_day = current_day or days_elapsed

    current_predicted_damand  = df.iloc[current_day]['JOBIN_PRED']
    demand_stdv = df.iloc[current_day-50:current_day]['JOBIN'].std()
    service_level = 2.5
    five_day_range = service_level * (5**.5) *  demand_stdv
    last_four_day_sum = df.iloc[current_day-5:current_day]['JOBIN'].sum()

    # _days = [[current_day+1,
    #           (current_predicted_damand*5 + five_day_range) - last_four_day_sum,current_predicted_damand,
    #           last_four_day_sum - (current_predicted_damand*5 - five_day_range)]]

    _days = [[current_day+1,
              current_predicted_damand- 2.5*demand_stdv,
              current_predicted_damand,
              current_predicted_damand+ 2.5*demand_stdv]]

    _next4days = pd.DataFrame(_days)
    _next4days.columns =['day','p-min','p-med','p-max']
    _next4days.set_index('day')
    return _next4days



def get_data(days_elapsed=None):
    df = pd.read_csv('/home/ajar/work/little/pred.csv')
    days_elapsed =   days_elapsed or (df['CUM_EARN'] > 0).sum()
    return df,int(days_elapsed)


def get_current_assets():

    odf = pd.read_csv("/home/ajar/work/little/pred.csv")
    days_elapsed = (odf['CUM_EARN'] > 0).sum()

    with open ('/home/ajar/work/little/group_stats.csv','r') as f:
        group_df = pd.DataFrame( [line.strip().split() for line in   f.readlines()])
    group_df.columns=['time','day','g1','g2','g3','g4','g5']
    for col in group_df.columns:  group_df[col] = group_df[col].astype(float)
    group_df['time'] = pd.to_datetime(group_df['time'].astype(float).astype(int) -3600*8  ,unit='s')
    group_df.set_index('time')

    odf['JOBIN'] = (odf['day'] <= days_elapsed) * odf['JOBIN'] +(odf['day'] > days_elapsed) * odf['JOBIN_PRED']

    group_df['JOBIN'] = group_df.apply(lambda row: ((odf['day']== row['day'])*odf['JOBIN']).mean()  ,axis=1)

    # group_df.columns=['time','day','g1','g2','g3','g4','g5']
    for i in range(1,6) :
        kcash  = 'g%d'%i
        kdcash = 'g%ddelta'%i
        kinv   = 'g%dinv'%i
        kass   = 'g%dass'%i
        group_df[kdcash] = group_df[kcash].diff()
        group_df[kinv] = ( (group_df[kdcash] < 0 ) *(-1)* group_df[kdcash] -800 )/600
        inv_refresh_day =  ((group_df[kdcash] < 0 ) * group_df['day']).max()
        inv_count = int( (( -group_df[kdcash].min())-800)/600) +70
        group_df[kinv] = group_df.apply(lambda  row: (row["day"] > inv_refresh_day)
                        *(inv_count - odf.iloc[int(inv_refresh_day):int(row["day"]-1)]['JOBIN'].sum() ), axis=1)
        group_df[kass] = group_df[kcash] + (group_df[kinv]*600)

    return  group_df



def get_stations_info(days_elapsed = None):
    df = pd.read_csv('/home/ajar/work/little/pred.csv')

    #--- Machine Capacity Calc
    days_for_mc_performance = 30
    mc_perf_df = df.iloc[0:days_for_mc_performance]
    orders =  (mc_perf_df['JOBIN'].sum() + mc_perf_df['JOBOUT'].sum())/2
    mc_caps = { sname:.5*orders/mc_perf_df["%sUTIL"%sname].sum() for sname in ['S1','S2','S3']}
    #--- Machine Capacity Calc Done

    #-- Current machine counts
    mc_count ={'S1':2,'S2':5,'S3':4}

    df['INV'] = df['INV']/60

    days_elapsed =   days_elapsed or (df['CUM_EARN'] > 0).sum()
    df20 = df.iloc[days_elapsed-20:days_elapsed].copy()# last 20 day data

    def s1LastZero():
        sname ='S1'
        mc = mc_count[sname]
        station_capacity = mc_caps[sname] * mc
        workkey = '%sWORK'%sname
        df20[workkey] = station_capacity* df20['%sUTIL'%sname]
        # print (df20[[workkey,'JOBIN']].to_string())
        checkpoint = np.max( df20['day'] *( df20[workkey]   > df20['JOBIN'] ) )
        return checkpoint

    d1zero , dnow = s1LastZero() , np.max((df20['day']))
    days_working = max (1,(dnow - d1zero) + 1)
    working_df =  df20.tail(days_working).copy()

    # print (working_df)

    jobs_in = working_df['JOBIN'].sum()
    jobs_out = working_df['JOBOUT'].sum()
    # print('-'*30)
    # print( working_df[['JOBIN','JOBOUT','JOBT','S1Q','S2Q','S3Q','S1UTIL','S2UTIL','S3UTIL']].to_string())
    # print('-'*30)

    sinfos = {}
    jobs_done_per_station  = {}
    for sname in ['S1','S3','S2']:
        mc = mc_count[sname]
        station_capacity = mc_caps[sname] * mc
        if sname == 'S1':
            jobs_completed = station_capacity * (working_df['%sUTIL'%sname].sum())
            pending = max(0, jobs_in - jobs_completed )
            jobs_done_per_station[sname] = jobs_completed
        elif sname == 'S3':
            jobs_completed = station_capacity * (working_df['%sUTIL'%sname].sum())
            pending = max(0, jobs_done_per_station['S1'] - jobs_completed )
            jobs_done_per_station[sname] = jobs_completed
        else :
            jobs_completed = station_capacity * (working_df['%sUTIL'%sname].sum())
            pending = max(0,
                          (jobs_done_per_station['S1'] - jobs_done_per_station['S3'] )/2 -jobs_completed ,
                          jobs_done_per_station['S1'] -jobs_out )
            jobs_done_per_station[sname] = jobs_completed

        average_util = working_df['%sUTIL'%sname].mean()
        warning = pending > (station_capacity * .35)
        expected_q = pending*60
        actual_q = working_df['%sQ'%sname].mean()
        sinfos[sname] = [sname,mc,station_capacity,average_util,pending,expected_q,actual_q,warning]

    sdf = pd.DataFrame([sinfos[sname] for sname in ['S1','S2','S3']])
    sdf.columns = "sname,mc,station_capacity,average_util,pending,expected_q,actual_q,warning".split(',')
    return sdf,working_df




def get_cash_data(days_elapsed = None):
    df = pd.read_csv('/home/ajar/work/little/pred.csv')
    eoq, rop = 360,80
    days_elapsed = days_elapsed or (df['CUM_EARN'] > 0).sum()

    av_job_rev = df.iloc[days_elapsed-20:days_elapsed]['JOBREV'].mean()
    av_job_rev_1k = 1000
    av_job_rev_750 = 750

    reorder_day =  217
    df['INV'] = df['INV'] /60
    cash = df.iloc[days_elapsed-1]['CASH']
    pred_ord_4_216plus = df.iloc[reorder_day:]['JOBIN_PRED'].sum()

    df ['CASH_1K']= df['CASH']
    df ['CASH_750']= df['CASH']

    cash_1k = cash
    cash_750 = cash

    for ix in range(days_elapsed,268,1):
        cash = cash + cash*.1/365
        cash_1k = cash_1k  + cash_1k*.1/365
        cash_750= cash_750  + cash_750*.1/365
        jobs = df.iloc[ix-1]['JOBIN_PRED']
        revenue =  jobs * av_job_rev

        
        cash += (revenue/1000)
        cash_1k += (jobs * av_job_rev_1k)/1000
        cash_750 += (jobs * av_job_rev_750)/1000

        inventory = df.iloc[ix-2]['INV'] - df.iloc[ix-1]['JOBIN_PRED']
        if ix == reorder_day:
            eoq = pred_ord_4_216plus - inventory
            rop = inventory + 1
            #print("Order Settings for day ",reorder_day," EOQ:",eoq,"ROP:",rop)
        if ix > reorder_day:
            eoq, rop = 1,0
        if inventory <= rop:
            inventory += eoq
            cash -= ((eoq* 600 +800)/1000)
            cash_1k -= ((eoq* 600 +800)/1000)
            cash_750 -= ((eoq* 600 +800)/1000)

        df.set_value(ix-1,'INV',inventory)
        df.set_value(ix-1,'CASH',cash)
        df.set_value(ix-1,'CASH_1K',cash_1k)
        df.set_value(ix-1,'CASH_750',cash_750)
        df.set_value(ix-1,'EARN',revenue - jobs*600 )
        df.set_value(ix-1,'JOBIN',jobs)
        df.set_value(ix-1,'JOBOUT',jobs)


    df['CUM_EARN'] = df['EARN'].cumsum() /1000
    return df

def print_summary(days_elapsed=0):
    df = pd.read_csv('/home/ajar/work/little/pred.csv')
    days_elapsed =  days_elapsed  or (df['CUM_EARN'] > 0).sum()
    xdf = df.iloc[days_elapsed-5:days_elapsed].copy()

    health = None
    stinfo ,working_df = get_stations_info(days_elapsed)

    if (stinfo['warning'].sum() > 0 ):
        health = "WARNING"
        print ("-- WARNING  : BAD HEALTH  --")
        # print('--'*30)
        # print (working_df[['JOBIN','JOBOUT','JOBT','S1Q','S2Q','S3Q','S1UTIL','S2UTIL','S3UTIL']].to_string())
        # print('--'*30)


    hstatus = xdf.tail(1)['JOBT'].values[0]
    health = health if health !=None else\
        "FLYING" if (hstatus < .5) else \
        "SAILING"  if (hstatus < .7) else \
        "BIKING UPHILL"  if (hstatus < 1) else \
        "DROWNING help!"

    xdf["INV"] = xdf["INV"]/60
    print ("#"*5,"Time :",time.ctime(),": Today is DAY :",days_elapsed)
    print ("Current Health :",health)
    _mean,_std = df.iloc[150:days_elapsed]['JOBIN'].mean(),df.iloc[150:days_elapsed]['JOBIN'].std() 
    _inventory_needed  = _mean
    print ("# 98% pecentile order range",[df.iloc[days_elapsed]['JOBIN_PRED'] ,int(_mean-2.5*_std),_mean,int(_mean+2.5*_std)+1]," std :",_std)
    print('--'*30)
    print (xdf[['day','JOBIN','JOBQ','JOBOUT','JOBREV','JOBT','INV','CASH']].to_string(index=False))
    print('--'*30)

    print ("#"*5,"Stations")
    print('--'*30)
    print (stinfo.to_string(index=False))
    print('--'*30)

    print ("#"*5,"Continuous work window - days since station 1 has been processing more than it received")
    print('--'*30)
    print (working_df[['day','JOBIN','JOBQ','JOBOUT','JOBREV','JOBT','INV']].to_string())
    print('--'*30)



def plotx(plt,n,df,colns,ylims,title,current_day=None):
    if not colns:
        colns = df.columns
    days = df['day']
    plt.figure(n)
    plt.subplot(211)

    handles =[]
    for coln in colns:
        h, = plt.plot(days,df[coln],label=coln)
        handles.append(h)
    if current_day:
        p = plt.axvspan(current_day, current_day+1, facecolor='red', alpha=0.7)
    
    plt.legend(handles=handles,loc=2)
    plt.ylim(*ylims)
    plt.title(title)
    plt.tick_params(axis='y', which='both', labelleft='off', labelright='on')
    plt.grid(True)

def plottime(plt,n,df,colns,ylims,title):
    if not colns:
        colns = df.columns
    days = df['time']
    plt.figure(n)
    plt.subplot(211)

    handles =[]
    for coln in colns:
        h, = plt.plot(days,df[coln],label=coln)
        handles.append(h)
    
    plt.legend(handles=handles,loc=2)
    plt.ylim(*ylims)
    plt.title(title)
    plt.tick_params(axis='y', which='both', labelleft='off', labelright='on')
    plt.grid(True)


    

def build_status():
    output = io.StringIO()

    health = None
    stinfo ,working_df = get_stations_info()
    if (stinfo['warning'].sum() > 0 ):
        health = "WARNING"

    df = pd.read_csv('/home/ajar/work/little/pred.csv')
    days_elapsed = (df['CUM_EARN'] > 0).sum()
    xdf = df.iloc[days_elapsed-5:days_elapsed].copy()

    print ("##"*20,file=output)
    print ("##"*5,"Time :",time.ctime(),file=output)
    print ("##"*5,"Today is DAY :",days_elapsed,file=output)
    print ("##"*20,file=output)
    print('--'*30,file=output)
    print (xdf[['day','JOBIN','JOBQ','JOBOUT','JOBREV','JOBT','INV']].to_string(),file=output)
    print('--'*30,file=output)

    print ("2 Day Predictions",file=output)
    next4days = make_future_predictions()
    print('--'*30,file=output)
    print (next4days.iloc[0:2].to_string(),file=output)
    print('--'*30,file=output)
    hstatus = xdf.tail(1)['JOBT'].values[0]
    health = health if health !=None else\
        "FLYING" if (hstatus < .47) else \
        "SAILING"  if (hstatus < .55) else \
        "BIKING UPHILL"  if (hstatus < 1) else \
        "DROWNING help!"

    print ("-- Station Status --",file=output)
    print (stinfo.to_string(),file=output)

    reason = output.getvalue()

    output.close()

    return reason,health

http = httplib2.Http()
def send_out_status():
    reason , health = build_status()

    url = "http://calm-scarab-685.appspot.com/za/z" #-H "Cookie: JSESSIONID=%COOKIE%"  --data "download=download&data=JOBIN" -o JOBIN.csv
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    toflag = 'v' if health in ['FLYING'] else 'w'
    data = {'w': toflag, 'health': health,'reason':reason}
    body = urllib.parse.urlencode(data)
    h = httplib2.Http()
    resp, content = h.request(url, method="POST", body=body, headers=headers)
    print ('------Email Send results---------')
    print(resp)
    print(content)
    print ('------Email Send results---------')
    if resp['status'] != '200':
        print("FATAL ERROR")
        print(resp)
        print(content)
        return None

def bktst1():
    for d in range (22,50):
        stinfo ,working_df = get_stations_info(d)
        if (stinfo['warning'].sum() > 0 ):
            print ("-- WARNING--")
            print (stinfo.to_string())
            print('--'*30)
            print (working_df[['JOBIN','JOBOUT','JOBT','S1Q','S2Q','S3Q','S1UTIL','S2UTIL','S3UTIL']].to_string())
            print('--'*30)



if __name__ == "__main__":
	send_out_status()
    # print_summary()
    # bktst1()