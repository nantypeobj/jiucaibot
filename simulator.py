# -*- coding: utf-8 -*-
"""
Created on Mon Mar  5 18:23:09 2018

@author: Administrator
"""

# -*- coding: utf-8 -*-
"""
Created on Mon Feb 26 12:06:17 2018

@author: Administrator
"""

# -*- coding: utf-8 -*-
"""
Created on Mon Feb 19 15:05:47 2018

@author: Administrator
"""

import os,sys
#os.chdir(path=r'C:\Users\Administrator.ZX-201609072125\Desktop\cryptocurrency\trading_simulator')
from APIS.BitfinexAPI import BitfinexAPI
from web.Connection import Connection 
from apscheduler.schedulers.blocking import BlockingScheduler
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
import common.base as base
from multiprocessing.pool import ThreadPool
from sklearn import preprocessing
from dateutil.relativedelta import relativedelta
from database.DatabaseInterface import DatabaseInterface
import datetime
import time
import seaborn as sns
import simu_config as conf
sns.set_style('white')

#====交易系统初始化============
def getkline(timeframe,start,end=None):
    api=BitfinexAPI()
    res=api.klines(conf.pair,timeframe,start=start,end=end)
    if not res is None:
        res['time']=[str(base.datetime_toTimestamp(t)) for t in res.index]
    return res

def getticker(pair):
    api=BitfinexAPI()
    return api.ticker(pair,return_url=False)


def getbalance(symbol):
    db=DatabaseInterface(conf.usedb)
    return db.db_findone('WALLET',filter_dic={'symbol':symbol},sel_fields=['balance'])

def getposition(pair):
    db=DatabaseInterface(conf.usedb)
    return db.db_findone('POSITION',filter_dic={'pair':pair},sel_fields=['balance','cost'])


def getclose(closetype=0):
    ticker=getticker(conf.pair)
    t=datetime.datetime.now()
    if closetype==0:
        close=(ticker['ask']+ticker['bid'])/2.0
    else:
        close=ticker['ask'] if closetype==1 else ticker['bid']
    return close,ticker['volume'],t


def savekline_db(kline,dropdb=False):
    kline['time']=[str(base.datetime_toTimestamp(t)) for t in kline.index]
    db=DatabaseInterface(conf.usedb)
    if dropdb:
        db.db_drop('KLINE_CURRENT')
    db.db_insertdataframe(kline,'KLINE_CURRENT')

def getkline_db():
    db=DatabaseInterface(conf.usedb)
    kline=db.db_find([],'KLINE_CURRENT',filter_dic={},sort=[("time", 1)])
    kline.set_index('time',inplace=True)
    kline.index=[base.timestamp_toDatetime(float(var)) for var in kline.index]
    return kline
    
def compresskline(data,field,timeframe,pcttype='ma3',k=0.7,cbkline=True,rmnoise=True):
    dt=data.copy()
    if rmnoise:
        db=DatabaseInterface(conf.usedb)
        statrange=db.db_find(['r0','r1'],'STATPARAS',filter_dic={'timeframe':timeframe,'pcttype':pcttype,'k':k},sort=[("time", -1)],limit=1)
        r0,r1=statrange['r0'].loc[0],statrange['r1'].loc[0]
        rm_mask=((dt[field]>r0) & (dt[field]<r1)).shift(-1)
        rm_mask.iloc[-1]=False
        dt=dt.where(rm_mask ==False).dropna()     
        dt.loc[data.index[-1]]=data.iloc[-1,:]
    if cbkline:
        dt[field]=dt[field.split('_')[0]].pct_change()*100
        dt=dt[dt[field]*dt[field].shift(-1)<0]
        dt.loc[data.index[-1]]=data.iloc[-1,:]

    return dt.sort_index()

def set_order(side,price=None,volume=None,note=None):
    db=DatabaseInterface(conf.usedb)

    if not price:
        price=getclose(closetype=1 if side=='buy' else 2)[0]
    if not volume:
        volume=100.0/price
    position,cost=getposition(conf.pair)
    k=-1 if  side in ('sell','sell_clear')  else 1
    
    position=position+k*volume
    cost=cost+k*volume*price
    
    print ('执行交易订单：')
    orderdict={'price':price,'volume':volume,'time':datetime.datetime.now(),'side':side,'position':position,'note':note}
    print (orderdict)
    db.db_updateone(filter_dic={'pair':conf.pair},update_dic={'balance':position,'cost':cost},collnam='POSITION')
    db.db_insertone(orderdict,'ORDERS')

    return price

def clear_position(note=None):
    balance=getposition(conf.pair)[0]
    if balance>0:
        return set_order('sell',note='clear' if note is None else note)

    elif balance<0:
        return set_order('buy',note='clear' if note is None else note)

    else:
        return None

def analyzetrend(data,field='ma',wave_threshold=0.6):
    trends=[]
    for i in range(1,len(data[field])+1):
        trends.append(checkwave(data[field].iloc[:i],wave_threshold=wave_threshold))
    data['trend']=trends
    return data



def getpctrange(statdata,field='ma_pct_change',k=0.5):
    data=statdata[field] #if statend else traindata['ma_pct_change'].loc[:statend] 
    return data.mean()-(data.std()*k),data.mean()+data.std()*k

#pcttype='ma3','close'
def updatepctrange(timeframe,pcttype='ma3',statdata_length=1500):
    db=DatabaseInterface(conf.usedb)
    statdata=db.db_find(['time','close','pct_change'],'KLINE'+timeframe,filter_dic={},sort=[("time", -1)],limit=statdata_length)
    if pcttype[:2]=='ma':
        statdata['ma']=pd.ewma(statdata['close'],span=int(pcttype[2:]))
        statdata['ma_pct_change']=statdata['ma'].pct_change()*100
        field='ma_pct_change'
    else:
        field='pct_change'
    
    for k in conf.noise_threshold_k:
        r0,r1=getpctrange(statdata,field=field,k=k)
        t=datetime.datetime.now()
        db.db_insertone({'time':t,'r0':r0,'r1':r1,'timeframe':timeframe,'pcttype':pcttype,'k':k},'STATPARAS')
#    db.db_updateone(filter_dic={},update_dic={'time':t,'r0':r0,'r1':r1},collnam='STATPARAS')

def inithistdata(timeframe='15m'):
    db=DatabaseInterface(conf.usedb)
    lastrow=db.db_findone('KLINE'+timeframe,filter_dic={},sel_fields=[],sort=[("time", -1)])#['time']/1000
    lasttime=base.timestamp_toStr(float(lastrow['time'])/1000.0+1,dateformat="%Y%m%d %H:%M:%S")
    df=getkline(timeframe,lasttime,end=None)

    if not df is None:
        df['pct_change'].iloc[0]=(df['close'].iloc[0]-lastrow['close'])*100/lastrow['close']
        db.db_insertdataframe(df,'KLINE'+timeframe)
        return True
    else:
        return False
    
def updatehistdata(timeframe='15m'):
    for i in range(3):
        if inithistdata(timeframe)==True:
            return True
        else:
            time.sleep(5)
            continue
    raise Exception('尝试获取新数据失败')

def gettrend(data,timeframe,ma_units=3,inittrenddb=False):
    
    kline=compresskline(data,'ma_pct_change',timeframe,pcttype='ma3',k=0.7,cbkline=True,rmnoise=True)
    kline=analyzetrend(kline)
    plt.plot(data.index,data['close'])
    plt.plot(kline.index,kline['ma'])

    for x in kline.index[kline['trend']==1]:
        plt.axvline(x=x,color='red',lw=0.5)
    for x in kline.index[kline['trend']==-1]:
            plt.axvline(x=x,color='green',lw=0.5)
    for x in kline.index[kline['trend']==0]:
            plt.axvline(x=x,color='yellow',lw=0.5)
    try:
        data=data.drop(['_id','trend'],axis=1)
    except ValueError:
        pass
    data=pd.concat([data,kline['trend']],axis=1)
    return data

def viewkline():
    kline=getkline_db()
    kline_cmp=compresskline(kline,'ma_pct_change',conf.timeframe)
    plt.plot(kline.index,kline['close'])
    plt.plot(kline_cmp.index,kline_cmp['ma'])
    for x in kline.index[kline['trend']==1]:
        plt.axvline(x=x,color='red',lw=0.5)
    for x in kline.index[kline['trend']==-1]:
            plt.axvline(x=x,color='green',lw=0.5)
    for x in kline.index[kline['trend']==0]:
            plt.axvline(x=x,color='yellow',lw=0.5)



    

def inittradepara(pair,symbol,cash,bal1,bal2,bal3):
    db=DatabaseInterface(conf.usedb)
    db.db_drop('WALLET')
    db.db_drop('POSITION')
    #db.db_updateone(filter_dic={'pair':pair},update_dic={'balance':balance},collnam='WALLET',opr='$set',upserts=True)
    db.db_insertone({'balance':bal1,'symbol':symbol},'WALLET')
    db.db_insertone({'balance':bal2,'symbol':cash},'WALLET')
    db.db_insertone({'balance':bal3,'pair':pair,'cost':0},'POSITION')

def inittrend(ma_units=3,pretrend_length=56):    
    db=DatabaseInterface(conf.usedb)
#    db.db_drop('KLINE_CURRENT')
    data=db.db_find(['time','close','pct_change'],'KLINE'+conf.timeframe,filter_dic={},sort=[("time", -1)],limit=pretrend_length)
#    lasttime=db.db_findone('KLINE'+timeframe,filter_dic={},sel_fields=[],sort=[("time", -1)])['time']/1000
#    starttime=(lasttime-pretrend_length*conf.timeframe_as_minute*60)*1000
#    data=db.db_find(['time','close','pct_change'],'KLINE'+timeframe,filter_dic={"time": {"$gt": starttime}})
    data.set_index('time',inplace=True)
    data.index=[base.timestamp_toDatetime(float(var)) for var in data.index]
    data.sort_index(inplace=True)
    data['ma']=pd.ewma(data['close'],span=ma_units)
    data['ma_pct_change']=data['ma'].pct_change()*100
    savekline_db(gettrend(data,conf.timeframe,ma_units=ma_units),
                 dropdb=True)
    


def get_tradingsignal(kline):
    trends=kline['trend']
    
    if pd.isnull(trends[-1]) or pd.isnull(trends[-2]):
        return None
    
    if trends[-1]!=trends[-2]:
        if trends[-1]!=0:
            if  (trends[-2]!=0) or (trends[-2]==0 and trends[-3]==0) or (trends[-2]==0 and trends[-3]!=trends[-1]):
                return 'buy' if trends[-1]>0 else 'sell'
        else:
            if (trends[-2]!=0) and (trends[-3]==0):
                return ['clear']
    else:
        if trends[-1]==0 and trends[-3]!=0:
            return 'clear'
        
    return None

def handle_tradingsignal(sig):
    if sig=='clear':
        clear_position()
    else:
        set_order(sig,price=None,volume=None)
    
    
def trading(ma_units=3):
    #---获取当前趋势计算k线
    kline=getkline_db()
    #--更新数据
    print ('更新历史数据....')
    updatehistdata(conf.timeframe)
    #更新趋势
    #---暂时使用简单的办法
    
    db=DatabaseInterface(conf.usedb)
#    db.db_drop('KLINE_CURRENT')
    ndata=db.db_find(['time','close','pct_change'],'KLINE'+conf.timeframe,filter_dic={},sort=[("time", -1)],limit=1)
#    lasttime=db.db_findone('KLINE'+timeframe,filter_dic={},sel_fields=[],sort=[("time", -1)])['time']/1000
#    starttime=(lasttime-pretrend_length*conf.timeframe_as_minute*60)*1000
#    data=db.db_find(['time','close','pct_change'],'KLINE'+timeframe,filter_dic={"time": {"$gt": starttime}})
    ndata.set_index('time',inplace=True)
    ndata.index=[base.timestamp_toDatetime(float(var)) for var in ndata.index]
    nkline=pd.concat([kline,ndata])
    nkline['ma']=pd.ewma(nkline['close'],span=ma_units)
    nkline['ma_pct_change']=nkline['ma'].pct_change()*100
    print ('计算最新趋势....')
    trendkline=gettrend(nkline,conf.timeframe,ma_units=3)
    ntrendrow=pd.DataFrame(trendkline.loc[trendkline.index[-1]]).T
    savekline_db(ntrendrow,
                 dropdb=False)
    print ('计算信号....')
    sig=get_tradingsignal(pd.concat([kline,ntrendrow]))
    if sig:
        print ('当前信号'+sig+'进行交易操作.....')
        handle_tradingsignal(sig)
    print ('持仓不变....')

def risktracking():
    print ('止损/止盈处理.....')
    balance,cost=getposition(conf.pair)
    
    
    if balance>0:
        avg_price=abs(cost)/abs(balance)
        close=getclose(closetype=2)[0]
        #多仓止损,多仓止盈
        print ('当前仓位为多仓，仓位均价='+str(avg_price)+',当前bid价格='+str(close))
        if close<avg_price*(1-conf.losestoprate) or (conf.winstoprate and close>avg_price*(1+conf.winstoprate)):
            print('触发止损线='+str(conf.losestoprate) if close<avg_price else '触发止盈线='+str(conf.winstoprate))
            clear_position(note='stoplose')
    elif balance<0:
        avg_price=abs(cost)/abs(balance)
        close=getclose(closetype=1)[0]
        print ('当前仓位为空仓，仓位均价='+str(avg_price)+',当前ask价格='+str(close))
        if close>avg_price*(1+conf.losestoprate) or (conf.winstoprate and close<avg_price*(1-conf.winstoprate)):
            print('触发止损线='+str(conf.losestoprate) if close>avg_price else '触发止盈线='+str(conf.winstoprate))
            clear_position(note='stopwin')
    else:
        print ('当前未开仓.....')
        return True
    


#    losestoprate
        
    #计算ma

def initsys():
    #---补充数据库数据
    inithistdata(timeframe='3h')
    inithistdata(timeframe='15m')
    #---初始化钱包
    inittradepara(conf.pair,conf.symbol,conf.cash,0,0,0)
    #---初始化统计参数
    updatepctrange(conf.timeframe,statdata_length=1500)


    
def main():
    initsys()
    inittrend()
    scheduler = BlockingScheduler()
    scheduler.add_job(trading, 'interval',minutes=15)
    scheduler.add_job(risktracking, 'interval',minutes=7)
    scheduler.start()






def checkwave(pts,wave_threshold=0.7): 
    #    
    check_line=lambda x,y:int(y>x)+(-1)*int(y<x)
    if len(pts)==1:
        return 0
    
    #pts=issameline(pd.Series(pts)).tolist()
#    pts=pts.tolist()
    
    if len(pts)==2:
        return check_line(pts[-2],pts[-1])
#    
    
    if len(pts)==3:
        a,b,c=pts
        per1,per2=(b-a),(c-b)
    
        if (abs(per2)/abs(per1)<wave_threshold):
                return 1 if per1>0 else -1
        if (abs(per2)/abs(per1)>=wave_threshold) and (abs(per2)/abs(per1)<1):
                return 0
        else:
                return 1 if per2>0 else -1
    
    if len(pts)>=4:
        pts=pts[-4:]
        a,b,c,d=pts
        pretrend=checkwave(pts[:3],wave_threshold=wave_threshold)
        trend=checkwave(pts[-3:],wave_threshold=wave_threshold)
        if pretrend*(d-c)>0:
            return pretrend
        elif pretrend*(d-c)==0:
            return trend if trend*(d-c)>0 else 0
        else:
            return trend
        
#if __name__ == '__main__':
#    #initsys()
#    #inittrend()
#    now=datetime.datetime.now()
#    #15min的情况
#    starttimes= pd.Series([15,30,45,60])
#    if now.minute in starttimes:
#        waittime=0
#    else:
#        waittime=(starttimes[starttimes-now.minute>0].min()-now.minute)*60+1
#        
#    scheduler = BlockingScheduler()
#    scheduler.add_job(trading, 'interval',minutes=15)
#    scheduler.add_job(risktracking, 'interval',minutes=7)
#    print ('waiting for'+str(waittime)+'s to start')
#    time.sleep(waittime)
#    print ('trading start at'+ base.get_currenttime_asstr())
#    scheduler.start()
