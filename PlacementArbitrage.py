# coding:utf-8
"""
@Author     :
@Date       :2019/12/27 20:23
@Email      :
@File       :PlacementArbitrage.py
@Description:
@Software   :PyCharm
"""

from util import util
import pandas as pd
import numpy as np
import time
from datetime import datetime, date, timedelta
from pandas.io.json import json_normalize
from tiingo import TiingoClient
import tushare as ts


def get_jsl_data(convert_dt):
    '''
    从集思录获取开始转股日期在指定日期之后的沪市可转债
    :param convert_dt: 开始转股日期
    :return:
    '''
    url = 'https://www.jisilu.cn/data/cbnew/cb_list/'
    # pd.options.display.max_columns = 999
    t = int(round(time.time() * 1000))
    param = {'___jsl=LST___t': t}
    result = util.get_json_by_post(url, param, None)
    new_result = filter(
        lambda x: datetime.strptime(x['cell']['convert_dt'], '%Y-%m-%d') > datetime.strptime(convert_dt, '%Y-%m-%d')
        and x['cell']['stock_id'].startswith('sh') and x['cell']['bond_nm'].find('EB') < 0, result['rows'])
    df = json_normalize(list(new_result))
    df['wps'] = round(df['cell.orig_iss_amt'].astype(float) * 100000000 / df['cell.total_shares'].astype(float), 3)  # 每股含权
    df['shares_to_buy'] = (np.ceil(500 / df['wps'] / 100) * 100).astype(int)  # 需要买入的正股数量
    new_df = pd.DataFrame({'bond_id': df['cell.bond_id'],  # 转债代码
                           'bond_nm': df['cell.bond_nm'],  # 转债名称
                           'stock_cd': df['cell.stock_cd'],  # 正股代码
                           'stock_nm': df['cell.stock_nm'],  # 正股名称
                           'rating_cd': df['cell.rating_cd'],  # 债项评级
                           'issuer_rating_cd': df['cell.issuer_rating_cd'],  # 主体评级
                           'wps': df['wps'],  # 每股含权
                           'shares_to_buy': df['shares_to_buy']})  # 需要买入的正股数量
    return new_df


def get_cninfo_announcement(mkt, keywords, startdate):
    '''
    从巨潮获取相关公告
    :param mkt: 市场
    :param keywords: 查询关键字 以;分割
    :param startdate: 查询开始日期
    :return:
    '''
    url = 'http://www.cninfo.com.cn/new/hisAnnouncement/query'
    # pd.options.display.max_columns = 999
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'}
    enddate = datetime.strftime(date.today(),'%Y-%m-%d')
    pageNum = 1
    pageSize =30
    param = {'pageNum': pageNum,  # 页数
             'pageSize': pageSize,  # 页面容量
             'plate': mkt,  # 市场版块
             'tabName': 'fulltext',
             'column': 'sse',  # 市场
             'stock': '',  # 股票代码
             'searchkey': keywords,  # 关键字以;分割
             'seDate': startdate+'~'+enddate,  # 查询日期 YYYY-mm-dd 以~分割
             'secId': '',
             'category': '',
             'trade': '',
             'sortName': 'time',  # 排序字段
             'sortType': 'asc',  # 排序方式
             'isHLtitle': 'false'}  # 是否高亮查询关键字
    flag = True
    df = pd.DataFrame()
    while flag:
        result = (util.get_json_by_post(url, param, header))
        if pageNum == 1:
            df = json_normalize(list(result['announcements']))
        else:
            df = pd.concat([df, json_normalize(list(result['announcements']))], axis=0)
        if pageNum <= (int(result['totalAnnouncement'])/pageSize + 1):
            pageNum += 1
            param['pageNum'] = pageNum
        else:
            flag = False
    new_df = pd.DataFrame({'secCode': df.secCode,
                           'secName': df.secName,
                           'title': df.announcementTitle,
                           'time': pd.to_datetime(df.announcementTime.values, unit='ms',
                                                  utc=True).tz_convert('Asia/Shanghai').to_period('D')
                          .strftime('%Y-%m-%d')})
    return new_df


def adjBDate(dtstr, direction, interval=1, isForced=False):
    '''
    调整交易日期
    :param dtstr: 日期
    :param direction: 方向 previous:向前  next:向后
    :param interval: 间隔 单位 天
    :param isForced: 是否强制调整 True:无论当前是否交易日都调整  False:当前不是交易日才调整
    :return:
    '''
    holiday_dates = [pd.datetime(2019, 6, 7), pd.datetime(2019, 9, 13)]  # 节日
    dt = date.today() if pd.isnull(dtstr) else datetime.strptime(str(dtstr), '%Y-%m-%d')
    flag = bool(len(pd.bdate_range(dt, dt, freq='C', holidays=holiday_dates)))
    if isForced:
        dt = dt + timedelta(days=interval) if direction.lower() == 'next' else dt - timedelta(days=interval)
        flag = bool(len(pd.bdate_range(dt, dt, freq='C', holidays=holiday_dates)))
    while not flag:
        dt = dt + timedelta(days=interval) if direction.lower() == 'next' else dt - timedelta(days=interval)
        flag = bool(len(pd.bdate_range(dt, dt, freq='C', holidays=holiday_dates)))
    return datetime.strftime(dt, '%Y-%m-%d')


def get_df_from_tiingo(symbol, start, end):
    '''
    从Tiingo获取行情数据
    :param symbol: 代码 600000
    :param start: 开始日期 yyyy-mm-dd
    :param end: 结束日期 yyyy-mm-dd
    :return:
    '''
    df = pd.DataFrame(client.get_ticker_price(symbol,
                      startDate=start,
                      endDate=end,
                      frequency='daily'))
    df.set_index('date', inplace=True)
    df.index = pd.to_datetime(df.index)
    del df.index.name
    return df


def get_df_from_ts(symbol, start, end):
    '''
    从Tushare获取行情数据
    :param symbol: 代码  600000.SH
    :param start: 开始日期  yyyymmdd
    :param end: 结束日期  yyyymmdd
    :return:
    '''
    df = pro.daily(ts_code=symbol, start_date=start, end_date=end)
    df.set_index('trade_date', inplace=True)
    df.index = pd.to_datetime(df.index)
    del df.index.name
    return df

def main():
    # pd.options.display.max_rows=999
    # pd.options.display.max_columns=999
    # Tiingo
    config = {}
    config['session'] = True
    config['api_key'] = "请填写自己的 Tiingo api_key"
    global client
    client = TiingoClient(config)
    # Tushare
    ts.set_token('请填写自己的 Tushare 的token')
    global pro
    pro = ts.pro_api()
    # print(get_df_from_ts('603806.SH','20190913','20191118'))
    # return

    base_df = get_jsl_data('2019-06-30')
    keyDict = {'Approval': ['可转换公司债券申请获得证监会核准', '可转换公司债券申请获中国证监会核准',
                            '可转换公司债券申请获中国证券监督管理委员会核准', '可转换公司债券获得中国证监会核准',
                            '可转换公司债券申请获得中国证券监督管理委员会核准', '可转换公司债券申请获得中国证监会核准',
                            '可转债申请获得中国证监会核准'],
               'PlacingResult': ['可转换公司债券网上发行中签率及网下发行配售结果', '可转换公司债券网上中签率及优先配售结果']}
    df_app = get_cninfo_announcement('sh', ';'.join(keyDict['Approval']), '2018-07-01')
    df_app = df_app.loc[df_app.title.apply(lambda x:x.find('公开发行') >= 0)]
    df_app.rename(columns={'time': 'approval_date'}, inplace=True)
    df_result = get_cninfo_announcement('sh', ';'.join(keyDict['PlacingResult']),'2019-01-01')
    df_result.rename(columns={'time': 'apply_date'}, inplace=True)
    df = pd.merge(base_df, df_app, how='left', left_on='stock_cd', right_on='secCode')
    df = pd.merge(df, df_result, how='left', left_on='stock_cd', right_on='secCode')
    df.drop(['secCode_x', 'secName_x', 'title_x', 'secCode_y', 'secName_y', 'title_y'], axis=1, inplace=True)
    df['approval_date'] = df['approval_date'].apply(adjBDate, args=('next', 1, False))
    df['apply_date'] = df['apply_date'].apply(adjBDate, args=('previous', 1, True))
    buy = list()
    high_dt = list()
    high = list()
    sell = list()
    low = list()
    low_dt =list()
    for index, row in df.iterrows():
        # temp = get_df_from_tiingo(row['stock_cd'],row['approval_date'],row['apply_date'])
        temp = get_df_from_ts(row['stock_cd']+'.SH', row['approval_date'].replace('-', ''), row['apply_date'].replace('-', ''))
        buy.append(temp.at[row['approval_date'], 'close'])
        hp = max(temp.high)
        lp = min(temp.low)
        high.append(hp)
        high_dt.append(temp[temp.high == hp].index.tolist()[0])
        low.append(lp)
        low_dt.append(temp[temp.low == lp].index.tolist()[0])
        sell.append(temp.at[row['apply_date'], 'open'])
    df['buy_price'] = pd.Series(buy).fillna(0).astype(str).str.strip('[]').astype(float)
    df['cost'] = df['shares_to_buy']*df['buy_price']
    df['high_date'] = pd.Series(high_dt)
    df['high_price'] = pd.Series(high).fillna(0).astype(str).str.strip('[]').astype(float)
    df['max_earning'] = (df['high_price']-df['buy_price'])*df['shares_to_buy']
    # df['max_return'] = round((df['high_price']/df['buy_price']-1),4)
    df['high_interval'] = pd.to_datetime(df['high_date'])-pd.to_datetime(df['approval_date'])
    df['low_date'] = pd.Series(low_dt)
    df['low_price'] = pd.Series(low).fillna(0).astype(str).str.strip('[]').astype(float)
    df['sell_price'] = pd.Series(sell).fillna(0).astype(str).str.strip('[]').astype(float)
    df['last_earning'] = (df['sell_price']-df['buy_price'])*df['shares_to_buy']
    # df['last_return'] = round((df['sell_price']/df['buy_price']-1),4)
    df['last_interval'] = pd.to_datetime(df['apply_date'])-pd.to_datetime(df['approval_date'])
    df.to_excel('D:/cbarb.xlsx')


if __name__ == '__main__':
    main()
