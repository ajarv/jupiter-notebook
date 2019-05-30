import matplotlib.pyplot as plt
from pylab import rcParams
import numpy as np
rcParams['figure.figsize'] = 26, 12
rcParams['lines.linewidth'] = 1

def line_plot(plt,title,df,colns=None,colLabs=None,xCol = 'day',xSeries=None,ylims=None,xlab=None,ylab=None,vLines=None,hLines=None):
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
