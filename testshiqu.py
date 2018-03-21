# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 22:15:03 2018

@author: Administrator
"""

import os,sys
#os.chdir(path=r'C:\Users\Administrator.ZX-201609072125\Desktop\cryptocurrency')
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


api=BitfinexAPI()
res=api.klines('tBTCUSD','6h',start='20180320')
if not res is None:
    res['time']=[str(time.mktime(t.timetuple())) for t in res.index]
