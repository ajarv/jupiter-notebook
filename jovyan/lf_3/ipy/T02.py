import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import locale
from scipy import stats


from pylab import rcParams
rcParams['figure.figsize'] = 15, 10




locale.setlocale(locale.LC_NUMERIC, '')
df = pd.read_csv(r'E:\DataScience\data\little\pred.csv')



def make_future_predictions(df):

    days_elapsed = (df['CUM_EARN'] > 0).sum()
    print("days_elapsed",days_elapsed)
    current_day = days_elapsed

    #----------
    numrows = current_day
    train_size = int(current_day * .85)
    print ("Training Data ",0,'-',train_size)
    print ("Rolling Data  ",train_size,'-',current_day)
    train_df = df.head(train_size)

    slope, intercept, r_value, p_value, std_err = stats.linregress(train_df['day'],train_df['JOBIN'])
    print ("Slope,intercept",slope,intercept)

    pred_size = numrows - train_size
    pred_df = df.iloc[train_size:current_day].copy()
    pred_df['JOBIN_P1'] = intercept + pred_df['day'] * slope
    jobs_expected = pred_df['JOBIN_P1'].sum()
    jobs_actual = pred_df['JOBIN'].sum()
    jobs_diff = jobs_expected - jobs_actual

    print(pred_df[['day','JOBIN','JOBIN_P1']])

    demand_stdv = np.std(df.iloc[0:numrows]['JOBIN'])

    _days = []
    for ix in range(0,4):
        _nextday = current_day + ix +1
        _nextday_p_demand  = intercept + _nextday * slope
        _mean = _nextday_p_demand + [.4,.2,.1,.05][ix] * jobs_diff
        _range = [_mean - 2*demand_stdv ,_mean ,_mean + 2*demand_stdv]
        _day = [_nextday,_nextday_p_demand] +_range
        _days.append(_day)

    _next4days = pd.DataFrame(_days)
    _next4days.columns =['day','p0','predmin','predmed','predmax']
    _next4days.set_index('day')
    print('--'*30)
    print (_next4days)
    print('--'*30)
    return _next4days
#-----------



def add_pred(df ,halflife,colname,train_days=60):
    numrows,numcols = df.shape
    train_setsize = train_days
    train_df = df.head(int(train_setsize))
    slope, intercept, r_value, p_value, std_err = stats.linregress(train_df['day'],pd.ewma(train_df.JOBIN,halflife=halflife))
    print ("Slope,intercept",slope, intercept, r_value, p_value, std_err )

    known_demand = train_df.JOBIN.values
    increasing_demand = intercept + np.arange(len(known_demand)+1,150+1,1) * slope
    stable_demand = np.zeros(numrows-150)  + increasing_demand[-1]
    pdx = np.concatenate( [known_demand,increasing_demand,stable_demand])
    print (pdx.size)
    df[colname] = pdx

    return slope, intercept


df['JOBIN_AV']= pd.ewma(df.JOBIN,halflife=1)
df['JOBIN_STD']= pd.ewmstd(df.JOBIN,halflife=4)



# df.to_csv(r"E:\DataScience\data\little\px01.csv",index=False)

# df = pd.read_csv('/home/ajar/work/ipy/pred.csv')


def plotx(n,df,colns,ylims,title):
    if not colns:
        colns = df.columns
    days = df['day']
    plt.figure(n)
    plt.subplot(211)

    handles =[]
    for coln in colns:
        h, = plt.plot(days,df[coln],label=coln)
        handles.append(h)
    plt.legend(handles=handles)
    plt.ylim(*ylims)
    plt.title(title)
    plt.tick_params(axis='y', which='both', labelleft='off', labelright='on')
    plt.grid(True)

# ------------------------------------------------------------
# day, jobs_actual,    jobs_expected,  jobs_diff
# 63 68.0 84.46042858362503 16.46042858362503
# ------------------------------------------------------------




# add_pred(df,1,'P1',train_days=55)
# add_pred(df,2,'P2',train_days=55)
# add_pred(df,4,'P4',train_days=55)
# add_pred(df,8,'P8',train_days=55)
# plotx(2,['P1','P2','P4','P8'],(0,30),"JOB PREDS")


add_pred(df,2,'P45',train_days=45)
add_pred(df,2,'P50',train_days=50)
add_pred(df,2,'P55',train_days=55)
add_pred(df,2,'P60',train_days=60)

next4days = make_future_predictions(df)


df = df.iloc[:110]


plotx(1,df,['JOBIN','JOBIN_PRED','JOBOUT'],(0,30),"JOBS")
plotx(2,df,['P45','P50','P55','P60'],(0,30),"JOB Predictions based upon varying time windows")
plotx(3,next4days,None,(0,30),"Next Four Days")


plt.show()