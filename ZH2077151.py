# coding:utf-8
"""
@Author     :
@Date       :2020/1/11 20:46
@Email      :
@File       :ZH2077151.py
@Description: $2020双低转债轮动(ZH2077151)$的可转债筛选
@Software   :PyCharm
"""
import time
import pandas as pd
from datetime import datetime, timedelta
from pandas.io.json import json_normalize
from util import util


def calc_weight(premium_rt, price):
    premium_rt = float(premium_rt)
    price = float(price)
    if premium_rt <= -2 and 130 <= price <= 150:
        result = 1
    elif premium_rt <= 3:
        if price > 130:
            result = 0
        elif price <= 120:
            result = 3
        else:
            result = 2 if 120 < price <= 125 else 1
    elif 3 < premium_rt <= 5:
        if price > 125:
            result = 0
        else:
            result = 2 if price <= 120 else 1
    elif 5 < premium_rt <= 10:
        result = 1 if price <= 115 else 0
    else:
        result = 0
    return result


def main():
    '''
    # 一档: 溢价率≤3 %，价格≤120，转债标的权重3
    #
    # 二档: 溢价率≤3 %，120<价格≤125;
    # 3 %≤溢价率＜5 %，价格≤120
    # 可转债标的权重为2
    #
    # 三档: 溢价率≤3 %，125＜价格≤130;
    # 3 %<溢价率≤5 %，120<价格≤125;
    # 5 %＜溢价率＜10 %，价格≤110(可放宽115);
    # 折价2个点以上，130＜价格≤150
    # 可转债标的权重为1
    #
    # 可转股10天以内或者已经可以开始转股
    :return:
    '''
    jsl_url = 'https://www.jisilu.cn/data/cbnew/cb_list/'
    # pd.options.display.max_columns = 999
    ts = int(round(time.time() * 1000))
    param = {'___jsl=LST___t': ts}
    data = util.get_json_by_post(jsl_url, param, None)['rows']
    df = json_normalize(data)
    df = df.loc[df['cell.price_tips'].apply(lambda x:x.find('待上市') < 0)].loc[df['cell.bond_nm'].apply(lambda x:x.find('EB') < 0)]
    # print(new_data)
    result = pd.DataFrame({'bond_id': df['cell.bond_id'],
                           'bond_nm': df['cell.bond_nm'],
                           'convert_dt': df['cell.convert_dt'],
                           'premium_rt': df['cell.premium_rt'],
                           'price': df['cell.price'],
                           'convert_value': df['cell.convert_value']})
    result['weight'] = result.apply(lambda row: calc_weight(row['premium_rt'].rstrip('%'), row['price']), axis=1)
    result = result.loc[result['weight'].apply(lambda x: x > 0)].loc[result['convert_dt'].apply(lambda x:((datetime.strptime(x, '%Y-%M-%d')-datetime.today()) < timedelta(days=-10)))]
    result['percentage'] = round(result['weight']/result['weight'].sum(), 4)
    # print(result)
    result.to_excel('D:/cbsd.xlsx')


if __name__ == '__main__':
    main()
