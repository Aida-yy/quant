# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt  # 引入backtrader框架

import os, sys

import akshare as ak
import numpy as np
import pandas as pd
import talib as ta
from datetime import datetime
 
from ._base import BaseStrategyClass
 
""" MACD 经典策略
macd_dif > macd_ema, 金叉买入, 做多
macd_dif < macd_emd, 死叉卖出, 做空
TR止损
"""
 
class MACDStrategyClass(BaseStrategyClass):
    '''#平滑异同移动平均线MACD
        DIF(蓝线): 计算12天平均和26天平均的差，公式：EMA(C,12)-EMA(c,26)
       Signal(DEM或DEA或MACD) (红线): 计算macd9天均值，公式：Signal(DEM或DEA或MACD)：EMA(MACD,9)
        Histogram (柱): 计算macd与signal的差值，公式：Histogram：MACD-Signal
        period_me1=12
        period_me2=26
        period_signal=9
        macd = ema(data, me1_period) - ema(data, me2_period)
        signal = ema(macd, signal_period)
        histo = macd - signal
    '''
 
    def __init__(self):
        # sma源码位于indicators\macd.py
        # 指标必须要定义在策略类中的初始化函数中
        self.close = self.datas[0].close
        self.open = self.datas[0].open
        self.high = self.datas[0].high
        self.low = self.datas[0].low

        macd = bt.ind.MACD(self.close,
            period_me1=20,
            period_me2=40,
            period_signal=15
        )
        self.macd = macd.macd
        self.signal = macd.signal
        self.histo = bt.ind.MACDHisto()

        self.TR = bt.ind.Max((self.high(0)-self.low(0)), # 当日最高价-当日最低价
                                    abs(self.high(0)-self.close(-1)), # abs(当日最高价−前一日收盘价)
                                    abs(self.low(0)-self.close(-1))) # abs(当日最低价-前一日收盘价)
        self.ATR = bt.ind.SimpleMovingAverage(self.TR, period=10, subplot=False)
        self.adx = bt.talib.ADX(self.high, self.low, self.close, timeperiod=14)
 
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.max_cash = 0
        self.hard_loss = 0.1
        self.atr_rate = 1
 
    def next(self):
 
        if self.order: # 检查是否有指令等待执行,
            return
 
        self.last_price = self.position.price
        self.max_cash = max(self.broker.getvalue(), self.max_cash)

        # 如果当前持有多单
        if self.position.size > 0 :
            self.log("last_price {} close {} max_cash {} atr {} cash {}"
                .format(self.last_price, self.close[0], self.max_cash, self.ATR[0], self.broker.getvalue())
            )
            # self.order = self.sell(size=abs(self.position.size))
            # 多单止损
            if (self.close[0] - self.last_price) < -1*self.ATR[0]:
                self.log("多单止损")
                self.order = self.sell(size=abs(self.position.size))
                self.buy_count = 0
                self.max_cash = self.broker.getvalue()
            # 多单止盈
            elif 1-self.broker.getvalue()/self.max_cash > self.hard_loss:
                self.log("多单止盈")
                self.order = self.sell(size=abs(self.position.size))
                self.buy_count = 0
                self.max_cash = self.broker.getvalue()
            elif (self.close[0] - self.close[-1]) < -self.atr_rate*self.ATR[0]:
                self.log("多单止盈")
                self.order = self.sell(size=abs(self.position.size))
                self.buy_count = 0
                self.max_cash = self.broker.getvalue()
                
        # 如果当前持有空单
        elif self.position.size < 0 :  
            self.log("last_price {} close {} max_cash {} atr {}"
                .format(self.last_price, self.close[0], self.max_cash, self.ATR[0])
            )
            # self.order = self.buy(size=abs(self.position.size))
            # 空单止损：当价格上涨至ATR时止损平仓
            if (self.close[0] - self.last_price) > 1*self.ATR[0]:
                self.log("空单止损")
                self.order = self.buy(size=abs(self.position.size))
                self.buy_count = 0
                self.max_cash = self.broker.getvalue()
            # 空单止盈：当价格突破20日最高点时止盈平仓
            elif 1-self.broker.getvalue()/self.max_cash > self.hard_loss:
                self.log("空单止盈")
                self.order = self.buy(size=abs(self.position.size))
                self.buy_count = 0
                self.max_cash = self.broker.getvalue()

            elif (self.close[0] - self.close[-1]) > self.atr_rate*self.ATR[0]:
                self.log("空单止盈")
                self.order = self.buy(size=abs(self.position.size))
                self.buy_count = 0
                self.max_cash = self.broker.getvalue()
            
        # 如果没有持仓，等待入场时机
        else:
            # Simply log the closing price of the series from the reference
            self.log('Close, %.2f' % self.close[0])
            # Check if we are in the market
    
            # self.data.close是表示收盘价
            # 收盘价大于histo，做多
            
            self.log("{} {} {} {}".format(self.macd,self.signal,self.histo,self.histo[-1]))

            if self.macd > self.signal and self.histo > self.histo[-1]and self.adx>=25:
                self.log('BUY CREATE,{}'.format(self.close[0]))
                self.log('BUY Price,{}'.format(self.position.price))
                self.log("做多")
                self.order = self.buy(self.datas[0],size=1)


            # 收盘价小于等于histo，做空
            if self.macd < self.signal and self.histo < self.histo[-1] and self.adx>=25:
                self.log('BUY CREATE,{}'.format(self.close[0]))
                self.log('Pos size %s' % self.position.size)
                self.log("做空")
                self.order = self.sell(self.datas[0],size=1)
