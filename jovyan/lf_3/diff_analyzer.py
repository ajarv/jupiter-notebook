import pandas as pd


def analyze_diff():
    csv_file =  "DIFF_EARNINGS.csv"
    df = pd.read_csv(csv_file)
    df.fillna(0,inplace=True)
    team_ds = [cn for cn in df.columns if cn[:2] =="D_"]
    team_d_df  = df[team_ds]
    interest_df = df[team_ds]%100

    cash_df = team_d_df - interest_df

    earn_df = (cash_df > 0) * cash_df
    purch_df = (cash_df < 0) * cash_df *(-1)
    machine_purch_df =  (purch_df <= 50000   )* purch_df
    inventory_purch_df =  purch_df - machine_purch_df
    machine_purch_df =  (machine_purch_df > 0 ) * 50000

    inventory_purch_df = (inventory_purch_df>0) * (inventory_purch_df-1000)/600

    # earn_df += interest_df

    cearning_df = earn_df.copy()

    earn_df = earn_df/900.0

    earn_df['day'] = df['day']
    purch_df ['day']= df['day']
    machine_purch_df['day']= df['day']
    inventory_purch_df['day']= df['day']
    cearning_df['day']= df['day']


    # earn_df[['day']+team_ds].to_csv("D_REVENUE.csv",index=False)
    # purch_df[['day']+team_ds].to_csv("D_SPENDING.csv",index=False)
    # machine_purch_df[['day']+team_ds].to_csv("D_MACHINE.csv",index=False)

    inventory_purch_df[['day']+team_ds].groupby('day').sum().to_csv("D_INVENTORY.csv")
    earn_df[['day']+team_ds].groupby('day').sum().to_csv("D_REVENUE.csv")
    purch_df[['day']+team_ds].groupby('day').sum().to_csv("D_SPENDING.csv")
    machine_purch_df[['day']+team_ds].groupby('day').sum().to_csv("D_MACHINE.csv")


    cearning_df = cearning_df[['day']+team_ds].groupby('day').sum()
    for cin in cearning_df.columns:
        cearning_df[cin] = cearning_df[cin].cumsum()

    cearning_df.to_csv("D_CUMEAR.csv")


    df = pd.read_csv('D_REVENUE.csv')
    cols = [coln for coln in df.columns if coln !='day']
    df['dmx'] = df[cols].max(axis=1)
    df['dmn'] = df[cols].min(axis=1)
    df['dmm'] = df[cols].mean(axis=1)
    df['rdm5']= pd.rolling_mean(df['dmm'],5)
    df['day','dmm','dmn','dmx','rdm5'].to_csv("demand_indicator.csv")



analyze_diff()
