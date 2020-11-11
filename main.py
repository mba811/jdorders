# coding: utf8
import json
import os
import time
import re
import sys
import requests
from lxml import etree
import datetime
import bs4
from selenium import webdriver
from selenium.webdriver import ChromeOptions
import pandas as pd

# 爬取时间范围
TIME_RANGES = range(2015, 2021)
# 每年多少页订单
PAGE_NUM = 10

class JSpider(object):
    def __init__(self, cookie, data_dir="./"):
        self.data_dir = data_dir
        if str(self.data_dir) == "":
            sys.exit(1)
        self.session = requests.session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
        }
        cookie_dict = {}
        list = cookie.split(';')
        for i in list:
            try:
                cookie_dict[i.split('=')[0]] = i.split('=')[1]
            except IndexError:
                cookie_dict[''] = i
        requests.utils.add_dict_to_cookiejar(self.session.cookies, cookie_dict)
    def get_orders(self):
        ret_list = []

        for i in TIME_RANGES:
            for page in range(1, PAGE_NUM):
                url = 'https://order.jd.com/center/list.action?search=0&d={}&s=4096&page={}'.format(i, page)
                print(f"获取订单 {url}")
                json_list = []
                try:
                    resp = self.session.get(url)
                    ele = etree.HTML(resp.content.decode('gbk'))
                    obj_list = ele.xpath('//table[@class="td-void order-tb"]/tbody')[1:]
                    url = 'https://order.jd.com/lazy/getOrderProductInfo.action'
                    data = {
                        'orderWareIds': '{}'.format(
                            re.findall(r"ORDER_CONFIG\['orderWareIds'\]='([\d,]+)'", resp.content.decode('gbk'))[0]),
                        'orderWareTypes': '{}'.format(
                            re.findall(r"ORDER_CONFIG\['orderWareTypes'\]='([\d,]+)'", resp.content.decode('gbk'))[0]),
                        'orderIds': '{}'.format(
                            re.findall(r"ORDER_CONFIG\['orderIds'\]='([\d,]+)'", resp.content.decode('gbk'))[0]),
                        'orderTypes': '{}'.format(
                            re.findall(r"ORDER_CONFIG\['orderTypes'\]='([\d,]+)'", resp.content.decode('gbk'))[0]),
                        'orderSiteIds': '{}'.format(
                            re.findall(r"ORDER_CONFIG\['orderSiteIds'\]='([\d,]+)'", resp.content.decode('gbk'))[0]),
                        'sendPays': '{}'.format(
                            re.findall(r"ORDER_CONFIG\['sendPays'\]='([\d,]+)'", resp.content.decode('gbk'))[0]),
                    }
                    json_list = json.loads(self.session.post(url, data=data).content.decode('gbk'))
                    for obj in obj_list:
                        try:
                            item = json_list[obj_list.index(obj)]
                            test_str = ''.join(obj.xpath('.//div[@class="amount"]//text()')).strip()
                            new_item = {}
                            new_item['img'] = item['imgPath']
                            new_item['id'] = item['productId']
                            new_item['title'] = item.get('name') or item.get('')
                            new_item['amount'] = re.search("\d+(\.\d+)?", test_str)  .group()
                            new_item['datetime'] = ''.join(obj.xpath('.//span[@class="dealtime"]//text()')).strip()
                            ret_list.append(new_item)
                        except Exception as e:
                            print(e)
                except Exception:
                    continue
            print(f'获取{i}年订单，共{len(ret_list)}条')
        if len(ret_list) == 0:
            return
        file_path = os.path.join(self.data_dir, 'jd_orders.json')
        with open(file_path, 'w') as f:
            f.write(json.dumps(ret_list))
        pdObj = pd.read_json('jd_orders.json')
        pdObj.to_csv('jd_orders.csv', index=False, columns=['datetime', 'title', 'amount', 'id', 'img'])
        os.system('rm jd_orders.json')


class JDSpider():
    def Automation(self, url):
        option = ChromeOptions()
        option.add_experimental_option('excludeSwitches', ['enable-automation'])
        option.add_experimental_option('useAutomationExtension', False)
        self.driver = webdriver.Chrome(r"./chromedriver", options=option)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get:()=>undefined})'
        })
        url = str(url)
        self.driver.get(url)
        time.sleep(10)

    def getCookie(self, login):
        cookie_list = self.driver.get_cookies()
        res = ''
        for cookie in cookie_list:
            res += cookie.get('name') + '=' + cookie.get('value').replace('\"', '') + ';'
        return res

    def run(self):
        url = 'https://passport.jd.com/new/login.aspx?ReturnUrl=https%3A%2F%2Fwww.jd.com%2F'
        self.Automation(url)
        login_element = "[class='user_logout']"
        cookie = self.getCookie(login_element)
        if cookie:
            try:
                spider = JSpider(cookie, "./")
                spider.get_orders()
            except Exception as e:
                print(e)
                traceback.print_exc()

if __name__ == '__main__':
    JDSpider().run()
