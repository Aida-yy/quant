# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt  # 引入backtrader框架

import akshare as ak
import numpy as np
import pandas as pd
import talib as ta
from datetime import datetime
 
import os, sys
import argparse

from strategy import MACDStrategyClass,MAStrategyClass
 
def get_data(trader_code="AU0", start_date='2022-01-01', end_date='2023-09-27'):
    """https://akshare.akfamily.xyz/data/futures/futures.html#id54
    """
    # history_df = ak.futures_main_sina(trader_code, start_date=start_date, end_date=end_date).iloc[:, :6]
    history_df = ak.futures_zh_minute_sina(symbol="MA2301", period="5").iloc[:, :6]
    # 处理字段命名，以符合 Backtrader 的要求
    history_df.columns = [
        'date',
        'open',
        'high',
        'low',
        'close',
        'volume',
    ]
    # 把 date 作为日期索引，以符合 Backtrader 的要求
    history_df.index = pd.to_datetime(history_df['date'])
 
    # Create a Data Feed
    data = bt.feeds.PandasData(dataname=history_df,
                                fromdate=pd.to_datetime(start_date),
                                todate=pd.to_datetime(end_date))
 
    return data

def main(StrategyClass):
    cerebro = bt.Cerebro()
    cerebro.adddata(get_data(trader_code="A0"), name='MA')

    # 初始资金 100,000
    start_cash = 100000
    cerebro.broker.setcash(start_cash)  # 设置初始资本为 100000
    cerebro.broker.setcommission(commission=0.1, # 按 0.1% 来收取手续费
                                mult=300, # 合约乘数
                                margin=0.1, # 保证金比例
                                percabs=False, # 表示 commission 以 % 为单位
                                commtype=bt.CommInfoBase.COMM_FIXED,
                                stocklike=False)

    # 加入策略
    cerebro.addstrategy(StrategyClass)
    # 回测时需要添加 PyFolio 分析器
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='pnl') # 返回收益率时序数据
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='_AnnualReturn') # 年化收益率
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='_SharpeRatio') # 夏普比率
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='_DrawDown') # 回撤
    # cerebro.addwriter(bt.WriterFile, csv=True, out='log.csv')

    result = cerebro.run() # 运行回测系统
    # 从返回的 result 中提取回测结果
    strat = result[0]
    # # 返回日度收益率序列
    daily_return = pd.Series(strat.analyzers.pnl.get_analysis())
    # 打印评价指标
    print("--------------- AnnualReturn -----------------")
    print(strat.analyzers._AnnualReturn.get_analysis())
    print("--------------- SharpeRatio -----------------")
    print(strat.analyzers._SharpeRatio.get_analysis())
    print("--------------- DrawDown -----------------")
    print(strat.analyzers._DrawDown.get_analysis())


    port_value = cerebro.broker.getvalue()  # 获取回测结束后的总资金
    pnl = port_value - start_cash  # 盈亏统计

    print(f"初始资金: {start_cash}")
    print(f"总资金: {round(port_value, 2)}")
    print(f"净收益: {round(pnl, 2)}")

    cerebro.plot(style='candlestick')  # 画图


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="backtest")
    parser.add_argument(
        "-s",
        "--strategy",
        help="strategy name",
        default="ma",
    )
    args = parser.parse_args()

    if args.strategy == "macd":
        strategy = MACDStrategyClass
    if args.strategy == "ma":
        strategy = MAStrategyClass
    
    main(StrategyClass=strategy)