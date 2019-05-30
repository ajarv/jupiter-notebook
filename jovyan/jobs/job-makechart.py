import os 
import pandas as pd
import numpy as np

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

from pylab import rcParams
import logging

rcParams['figure.figsize'] = 26, 12
rcParams['lines.linewidth'] = 3
rcParams['font.size'] = 24

def line_plot(plt,title,df,colns=None,colLabs=None,xCol = 'day',xSeries=None,ylims=None,xlab=None,ylab=None,vLines=None,hLines=None,fig_path=None):
    # figure = plt.figure()
    if not colns: colns = df.columns
    colns =[c for c in colns if c != xCol]
    handles =[]
    X = df[xCol] if xSeries is None else xSeries
    cn_cl = zip(colns, colLabs or colns)
    for coln,colL in cn_cl:
        Y = df[coln]
        h, = plt.plot(X,Y,label=colL)
        handles.append(h)
    if vLines:
        for line in vLines:
            start, end, color = line
            p = plt.axvspan(start, end,color= color, alpha=0.7)
    if hLines:
        for line in hLines:
            start, end, color = line
            p = plt.axhspan(start, end, color=color, alpha=0.7)
    plt.legend(handles=handles,loc='best')
    if ylims:
        plt.ylim(*ylims)
    xlab and plt.xlabel(xlab)
    ylab and plt.ylabel(ylab)
    plt.title(title)
    plt.tick_params(axis='y', which='both', labelleft=False, labelright=True)
    plt.grid(True)
    if fig_path:
        plt.savefig(fig_path)

def get_df(csv_path):
    df = pd.read_csv(csv_path)
    df.NEW_DATE = pd.to_datetime(df.NEW_DATE)
    df = df.set_index('NEW_DATE')
    return df


def main():
    LOGFORMAT = '<%(asctime)-15s> %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)


    from optparse import OptionParser
    parser = OptionParser(description='Download US Treasury Bond Rates')
    parser.add_option("--in-csv", dest="csvfile",
                    help="Input CSV File Path")
    parser.add_option("--out-png", dest="chartfile",
                    help="Output Chart PNG File Path")
    (options, args) = parser.parse_args()
    print(options,args)

    csv_file_path = options.csvfile
    fig_path = options.chartfile
    # fig_path = os.path.join(base_dir, "charts", "ty_3m_5y_30y.png")


    # base_dir = os.path.abspath( os.path.split(__file__)[0]+'/..')
    # logging.info("Running in base Dir {}".format(base_dir))

    df = get_df(csv_file_path)
    _df = df.resample('7D', convention='end').mean()
    _df = _df.tail(52*7)

    # print(df['FC_3'])

    # line_plot(plt,'',_df,colns=['BC_3MONTH','BC_1YEAR','BC_5YEAR','BC_10YEAR','BC_20YEAR','BC_30YEAR'],xSeries=_df.index)
    line_plot(plt,
            '% US Treasury Yield',
            _df,
            colns=['BC_3MONTH', 'BC_5YEAR', 'BC_30YEAR'],
            colLabs=['@3 months', '@5 Years', '@30 Years'],
            #           colns=['BC_3MONTH','BC_1YEAR','BC_5YEAR','BC_10YEAR','BC_20YEAR','BC_30YEAR'],
            #           colLabs=['@3 month','@1 Y','@5 Y','@10 Y','@20 Y','@30 Y'],
            xSeries=_df.index,
              fig_path= fig_path)
    logging.info("wrote {}".format(fig_path))

if __name__ == "__main__":
    main()
