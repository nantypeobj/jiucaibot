# -*- coding: utf-8 -*-
"""
Created on Fri Dec 22 10:41:22 2017

@author: Administrator
"""
from web.Connection import Connection
from bs4 import BeautifulSoup
import pandas as pd

class HTMLAPI(object):
    
    def _init_(self,use_proxy):
        self.use_proxy=use_proxy
    
    #format_type=['text','table']
    def get(self,url,format_type='text',*args,**kwards):
        conn=Connection(self.use_proxy)
        return self._format_result(conn.request_get(url,formattype='text'),
                                   format_type=format_type)

            
    
    def _format_result(self,res,format_type='text',*args,**kwards):
        if format_type=='text':
            return res
        elif format_type=='table':
            return self.parse_tb(res,*args,**kwards)
        else:
            raise Exception('没有这种格式化类型')

        
    def parse_tb(self,text,tbid=None):
        soup = BeautifulSoup(text, 'html.parser')
        table = soup.find('table',id=tbid)
        rows = table.findAll('tr')
        data=[]
        for row in rows[1:]:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            data.append(cols)
        columns=[ele.text.strip() for ele in rows[0].find_all('th')]
        try:
            return pd.DataFrame(data,columns=columns) 
        except AssertionError:
            return pd.DataFrame(columns=columns)
