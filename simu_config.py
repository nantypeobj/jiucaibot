# -*- coding: utf-8 -*-
"""
Created on Tue Mar  6 18:39:33 2018

@author: Administrator
"""

#====数据库配置
pair='tBTCUSD'
timeframe='15m'
timeframe_as_minute=15
usedb='bitfinex'
collnam='KLINE'+timeframe
symbol='BTC'
cash='USD'

#===k线分析设置
noise_threshold_k=[0.3,0.5,0.7,1,1.5,2,2.5,3,4,5]


#==交易设置
#---止损
losestoprate=0.03
winstoprate=None