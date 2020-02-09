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
import time
import json
import sqlite3
import requests
import psycopg2
import pymysql
import pymssql
import cx_Oracle
import xlwings as xw
from xlwings.constants import YesNoGuess, ListObjectSourceType, DeleteShiftDirection
import pandas as pd
from PIL import ImageGrab
from datetime import datetime
from win32.win32crypt import CryptUnprotectData


def filldata_screenshot_from_xlsx(data, path, dt):
    app = xw.App(visible=False, add_book=False)
    wb = xw.Book()
    for sheetname, (df, delFlag) in data.items():
        sheet = wb.sheets.add(sheetname)
        sheet.range('A1').value = df
        sheet.range('A1').options(pd.DataFrame, expand='table').value
        # 设置TableStyle 需要Excel WPS会出错
        tbl = sheet.api.ListObjects.Add(SourceType=ListObjectSourceType.xlSrcRange, XlListObjectHasHeaders=YesNoGuess.xlYes)
        tbl.TableStyle = 'TableStyleMedium2'
        tbl.ShowAutoFilterDropDown = False
        sheet.autofit()
        if delFlag:
            sheet.range('A:A').api.Delete(DeleteShiftDirection.xlShiftToLeft)  # 删除DataFrame的index
        if sheet.range('A1').value in ['', '列1', None]:
            sheet.range('A1').value = ' '
        all = sheet.used_range  # 获取有内容的range
        print(all)
        all.api.CopyPicture()  # 复制图片区域
        time.sleep(1)  # 连续截取多张图片的时候会有Bug
        sheet.api.Paste()  # 粘贴
        filename = os.path.join(path, '{0}_{1}.png'.format(sheetname, dt))
        pic = sheet.pictures[0]  # 当前图片
        pic.api.Copy()  # 复制图片
        img = ImageGrab.grabclipboard()  # 获取剪贴板的图片数据
        img.save(filename)  # 保存图片
        pic.delete()  # 删除sheet上的图片
    wb.close()
    app.quit()


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


class SqlConn:
    def __init__(self, dbtype, host, db, user, pwd, port):
        self.dbtype = dbtype
        self.host = host
        self.db = db
        self.user = user
        self.pwd = pwd
        self.port = port
        sql_conn = {'mysql': pymysql,
                    'postgresql': psycopg2,
                    'sqlserver': pymssql,
                    'orcle': cx_Oracle
                    }
        self.conn = sql_conn[self.dbtype].connect(
            database=self.db,
            user=self.user,
            password=self.pwd,
            host=self.host,
            port=self.port)
        self.cursor = self.conn.cursor()

    def try_except(self):
        def wrapper(*args, **kwargs):
            try:
                self(*args, **kwargs)
            except Exception as e:
                print("get error: %s" % e)
        return wrapper

    # @try_except
    def select(self, sqlCode):
        self.cursor.execute(sqlCode)
        return self.cursor.fetchall()

    def insert(self, sqlCode):
        self.common(sqlCode)

    def update(self, sqlCode):
        self.common(sqlCode)

    def delete(self, sqlCode):
        self.common(sqlCode)

    def close(self):
        self.cursor.close()
        self.conn.close()

    def insertAndGetField(self, sql_code, field):
        """
        插入数据，并返回当前 field
        :param sql_code:
        :param field:
        :return:
        """
        try:
            self.cursor.execute(sql_code + " RETURNING " + field)
        except Exception as e:
            print(e)
            self.conn.rollback()
            self.cursor.execute(sql_code + " RETURNING " + field)
        self.conn.commit()

        return self.cursor.fetchone()

    def common(self, sqlCode):
        try:
            self.cursor.execute(sqlCode)
        except Exception as e:
            print(e)
            self.conn.rollback()
            self.cursor.execute(sqlCode)
        self.conn.commit()

    def __del__(self):
        # print("最后一步，关闭数据库")
        self.close()


