# coding:utf-8
"""
@Author     :
@Date       :2019/7/19 22:02
@Email      :
@File       :util.py
@Description:
@Software   :PyCharm
"""
import os
import json
import sqlite3
import requests
from win32.win32crypt import CryptUnprotectData

def get_cookie_from_chrome(host):
    """从Chrome中获取cookie"""
    cookiepath = os.environ['LOCALAPPDATA'] + r"\Google\Chrome\User Data\Default\Cookies"
    sql = "select host_key,name,encrypted_value from cookies where host_key='%s'" % host
    with sqlite3.connect(cookiepath) as conn:
        cu = conn.cursor()
        lst = cu.execute(sql).fetchall()
        cookies = {name: CryptUnprotectData(encrypted_value)[1].decode() for host_key, name, encrypted_value in lst}
        # print(cookies)
        return cookies


def get_json_by_post(url, param, header):
    """使用POST方式获取json"""
    response = requests.post(url=url, params=param, headers=header)
    return json.loads(response.text)


def get_json_by_get(url, param, header, cookie):
    """使用GET方式获取json"""
    response = requests.get(url=url, params=param, headers=header, cookies=cookie)
    return json.loads(response.text)

