import winsound
import datetime
import requests
import json
import time
import pandas as pd


def get_json_by_post(url, param, header):
    """使用POST方式获取json"""
    response = requests.post(url=url, params=param, headers=header)
    return json.loads(response.text)


def is_trade_time(now, opening, closing):
    if opening < now < closing:
        return True
    else:
        return False


def is_break(now, opening):
    if 7200 < (now-opening).seconds < 12600:
        return True
    else:
        return False


def main():
    jsl_url = 'https://www.jisilu.cn/data/cbnew/cb_list/'
    header = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    now = datetime.datetime.now()
    opening = datetime.datetime(now.year, now.month, now.day, 9, 30)
    closing = datetime.datetime(now.year, now.month, now.day, 15, 0)
    pd.options.display.max_columns = 999
    flag = True
    while flag:
        now = datetime.datetime.now()
        print(now)
        if is_break(now, opening) is False:
            ts = int(round(time.time() * 1000))
            param = {'___jsl=LST___t': ts}
            rows = get_json_by_post(jsl_url, param, header)['rows']
            lst = list()
            for row in rows:
                lst.append(row['cell'])
            df = pd.DataFrame(lst)
            df = df.loc[df['premium_rt'].apply(lambda x:float(x[:-2]) < -0.5)].loc[df['convert_dt'].apply(lambda x:datetime.datetime.strptime(x, '%Y-%m-%d') < now)]
            result = pd.DataFrame({'转债代码': df['bond_id'],
                                   '转债名称': df['bond_nm'],
                                   '转债现价': df['price'],
                                   '股票代码': df['stock_cd'],
                                   '股票名称': df['stock_nm'],
                                   '股票现价': df['sprice'],
                                   '溢价率': df['premium_rt']})
            print(result)
            if len(result.index) > 0:
                winsound.Beep(600, 2000)  # winsound.Beep(f,d)  f:声音频率 d:持续时间
        flag = is_trade_time(now, opening, closing)
        time.sleep(30)


if __name__ == '__main__':
    main()
