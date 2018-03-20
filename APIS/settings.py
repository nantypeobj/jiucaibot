# -*- coding: utf-8 -*-
"""
Created on Tue Sep 19 16:29:41 2017

@author: Administrator
"""
#网络配置
TIMEOUT = 5.0
RETRY_TIMES=3
RETRY_DELAYS=2000   #每次重试之间间隔2s



SERVERS={
        'BITFINEX':'https://api.bitfinex.com'
        }

bitfinex_path_dict={
        'SYMBOL':'symbols',
        'CANDELS':'candles/trade:%s:%s/%s'
        }

PATH={
        'BITFINEX':bitfinex_path_dict
        }


