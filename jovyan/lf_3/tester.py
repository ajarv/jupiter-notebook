import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pylab import rcParams

rcParams['figure.figsize'] = 15, 6
rcParams['lines.linewidth'] = 1

# for ix in range(1,len(multiplier)):
#     m = multiplier[ix]
#     m = np.abs(m) * ( 1 if multiplier[ix-1] < 0  else -1)
#     multiplier[ix] = m
# print (multiplier)

# df = pd.DataFrame(data={'day':np.arange(1,390,1)})
#
# df['demand'] = 0
# starting_demand = 50
# m = None
# for ix in df.index:
#     period_ix = int(ix/5)
#     period_begin = period_ix*5
#     if ix % 5 == 0:
#         m = multiplier[period_ix]
#         ending_demand = starting_demand * (1+m)
#         print("Multiplier",1+m)
#         if ix > 0 :
#             starting_demand = df.iloc[ix-1]['demand']
#     print (starting_demand,ending_demand, (ix - period_begin),period_begin)
#     demand = int(starting_demand + (ix - period_begin) * (ending_demand-starting_demand)/5 )
#     demand = min(100,demand)
#     demand = max(10,demand)
#     # print(int(demand))
#     df.set_value(ix,'demand',demand)

def xshow_demand(mean_demand = 10):
    mu, sigma = 0, .09 # mean and standard deviation
    intervals = int(390/5)
    multiplier = np.random.normal(mu, sigma, intervals)

    df = df = pd.DataFrame(data={'day':np.arange(0,len(multiplier),1)})
    d0 = mean_demand
    df['demand'] = 0
    for ix in df.index:
        m = multiplier[ix] + 1
        dn = d0 * m
        d0 = dn
        df.set_value(ix,'demand',dn)

    plt.plot(df['day'],df['demand'])
    plt.ylim(0,mean_demand*3)
    plt.xlabel("day")
    plt.ylabel("orders/day")
    plt.title("Demand Curve")
    plt.grid(True)

    plt.show()


def get_random_df(mean_demand = 10,sigma=.09):
    DAY_COUNT = 390
    mu, sigma = 0, .09 # mean and standard deviation
    intervals = int(DAY_COUNT/5)
    multiplier = np.random.normal(mu, sigma, intervals)

    df = df = pd.DataFrame(data={'day':np.arange(0,DAY_COUNT,1)})
    d0 = mean_demand
    df['demand'] = 0
    for ix in df.index:
        period_ix = int(ix/5)
        m = multiplier[period_ix] + 1
        de = d0 * m
        demand = d0 + (ix- period_ix*5)*(de-d0)/5
        df.set_value(ix,'demand',demand)
        if( (ix+1)%5 == 0 ):
            d0 = de

    scale = mean_demand / df['demand'].mean()
    df['demand'] *= scale
    return df

def plot_max_min(sigma):
    mx,mn,av  =[],[],[]
    for ix in range(0,200):
        df = get_random_df(mean_demand=1000,sigma=sigma)
        mx.append(df['demand'].max())
        mn.append(df['demand'].min())
        mn.append(df['demand'].mean())
    plt.figure()
    plt.subplot(131)
    plt.hist(mx, 20, normed=1, facecolor='green', alpha=0.75)
    plt.title("MAX")
    plt.subplot(132)
    plt.hist(mn, 20, normed=1, facecolor='green', alpha=0.75)
    plt.title("MIN")
    plt.subplot(133)
    plt.hist(mn, 20, normed=1, facecolor='green', alpha=0.75)
    plt.title("AVG")
    plt.show()

def show_demand(mean_demand = 10):
    df = get_random_df(mean_demand=mean_demand)
    plt.plot(df['day'],df['demand'])
    plt.ylim(0,mean_demand*3)
    plt.xlabel("day")
    plt.ylabel("orders/day")
    plt.title("Demand Curve")
    plt.grid(True)

    plt.show()

# show_demand(15)
import sys
plot_max_min(float(sys.argv[1]))