"""

作者 凯悦推荐 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================kaiyuebinguan====================

"""

from Crypto.Util.Padding import unpad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from base.spider import Spider
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://xhaoer.com"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
}

# headerx = {
#     'User-Agent': 'Linux; Android 12; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.101 Mobile Safari/537.36'
#           }

pm = ''


class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def extract_middle_text(self, text, start_str, end_str, pl, start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{'📽️集多👉' + match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{'📽️集多👉' + match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'✨集多👉{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {}
        result = {"class": [
                            {"type_id": "29", "type_name": "集多短剧🌠"}],

                  "list": [],
                  "filters": {
                              "29": [{"key": "年代",
                                     "name": "年代",
                                     "value": [{"n": "全部", "v": ""},
                                               {"n": "2024", "v": "2024"},
                                               {"n": "2023", "v": "2023"},
                                               {"n": "2022", "v": "2022"},
                                               {"n": "2021", "v": "2021"},
                                               {"n": "2020", "v": "2020"},
                                               {"n": "2019", "v": "2019"},
                                               {"n": "2018", "v": "2018"}]}]}}

        return result

    def homeVideoContent(self):
        videos = []

        try:

            detail = requests.get(url=xurl + '/k/29.html', headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text

            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('ul', class_="fed-list-info")

            for soup in soups:
                vods = soup.find_all('li')

                for vod in vods:
                    names = vod.find('a', class_="fed-list-title")
                    name = names.text.strip()

                    ids = vod.find('a', class_="fed-list-title")
                    id = ids['href']

                    pics = vod.find('a', class_="fed-list-pics")
                    pic = pics['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('span', class_="fed-list-remarks")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '集多推荐▶️' + remark
                             }
                    videos.append(video)

            result = {'list': videos}
            return result
        except:
            pass

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        if pg:
            page = int(pg)
        else:
            page = 1

        if '年代' in ext.keys():
            NdType = ext['年代']
        else:
            NdType = ''

        if page == '1':
            url = f'{xurl}/search.php?searchtype=5&tid={cid}'

        else:
            url = f'{xurl}/search.php?page={str(page)}&searchtype=5&tid={cid}&year={NdType}'

        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('ul', class_="fed-list-info")

            for soup in soups:
                vods = soup.find_all('li')

                for vod in vods:
                    names = vod.find('a', class_="fed-list-title")
                    name = names.text.strip()

                    ids = vod.find('a', class_="fed-list-title")
                    id = ids['href']

                    pics = vod.find('a', class_="fed-list-pics")
                    pic = pics['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('span', class_="fed-list-remarks")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '集多推荐▶️' + remark
                    }
                    videos.append(video)

        except:
            pass
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        global pm
        did = ids[0]
        result = {}
        videos = []

        if 'http' not in did:
            did = xurl + did

        res1 = requests.get(url=did, headers=headerx)
        res1.encoding = "utf-8"
        res = res1.text

        tiaozhuan = '1'
        if tiaozhuan == '1':
            did = self.extract_middle_text(res, '<dd class="fed-deta-button fed-col-xs7', '</dd>', 1, 'href="(.*?)">')
            if 'http' not in did:
                did = xurl + did
                res1 = requests.get(url=did, headers=headerx)
                res1.encoding = "utf-8"
                res = res1.text

        url = 'https://fs-im-kefu.7moor-fs1.com/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1732707176882/jiduo.txt'
        response = requests.get(url)
        response.encoding = 'utf-8'
        code = response.text
        name = self.extract_middle_text(code, "s1='", "'", 0)
        Jumps = self.extract_middle_text(code, "s2='", "'", 0)

        content = '集多🎉为您介绍剧情📢本资源来源于网络🚓侵权请联系删除👉' + self.extract_middle_text(res,'name="description" content="','>', 0)

        if name not in content:
            bofang = Jumps
        else:
            bofang = self.extract_middle_text(res, '<ul class="stui-content__playlist  sort-list column8 clearfix">', '</ul>', 3, 'href="(.*?)" target=".*?">(.*?)</a>')

        xianlu = self.extract_middle_text(res, '<ul class="fed-list-head fed-part-rows fed-padding">','剧情介绍',2, 'class="fed-tabs-btns fed-part-curs fed-font-xvi fed-mart-v fed-text-green">(.*?)</li>')

        videos.append({
            "vod_id": did,
            "vod_actor": '集多和他的朋友们',
            "vod_director": '集多',
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": bofang
                     })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        parts = id.split("http")

        xiutan = 0

        if xiutan == 0:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]

            if '/tp/jd.m3u8' in after_https:
                url = after_https
            else:
                res = requests.get(url=after_https, headers=headerx)
                res = res.text

                url = self.extract_middle_text(res, 'var now="', '"', 0).replace('\\', '')

            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = headerx
            return result

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []

        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/search.php?searchword={key}'

        else:
            url = f'{xurl}/search.php?page={str(page)}&searchword={key}&searchtype='

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('ul', class_="fed-list-info")

        for soup in soups:
            vods = soup.find_all('li')

            for vod in vods:
                names = vod.find('a', class_="fed-list-title")
                name = names.text.strip()

                ids = vod.find('a', class_="fed-list-title")
                id = ids['href']

                pics = vod.find('a', class_="fed-list-pics")
                pic = pics['data-original']

                if 'http' not in pic:
                    pic = xurl + pic

                remarks = vod.find('span', class_="fed-list-remarks")
                remark = remarks.text.strip()

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": '集多推荐▶️' + remark
                }
                videos.append(video)

        result['list'] = videos
        result['page'] = page
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None


"""

   =======================================

   换行 \n   零个或者多个空格 \s+   数字型 int   文本型 str   分页{} '年代':'2021'       

   性能要求高"lxml"   处理不规范的HTML"html5lib"   简单应用"html.parser"   解析XML"xml"

   =======================================

   /rss/index.xml?wd=爱情&page=1                                搜索有验证

   /index.php/ajax/suggest?mid=1&wd=爱情&page=1&limit=30        搜索有验证

   /index.php/ajax/data?mid=1&tid={cateId}&class={class}&area={area}&page={catePg}&limit=30   分类有验证

   /index.php/vod/type/class/{cid}/id/41/page/{str(page)}/year/{NdType}.html        隐藏分类

   /{cateId}-{area}-{by}-{class}-{lang}-{letter}---{catePg}---{year}.html

   短剧 穿越 古装 仙侠 女频 恋爱 反转 现代 都市 剧情 玄幻 脑洞 悬疑  

   =======================================

   aaa = self.extract_middle_text(res, 'bbb', 'ccc', 0)
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （不循环)   截取项  （不循环)   长用于直链  二次截取                0号子程序

   aaa =self.extract_middle_text(res, 'bbb', 'ccc',1,'html">(.*?)<')
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （不循环)   截取项  （循环)     长用于详情  和2号区别没有$$$        1号子程序

   aaa = self.extract_middle_text(res, 'bbb','ccc', 2,'<span class=".*?" id=".*?">(.*?)</span>')
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （不循环)   截取项  （循环)     只能用于线路数组  里面包含$$$       2号子程序

   aaa = self.extract_middle_text(res, 'bbb', 'ccc', 3,'href="(.*?)" class=".*?">(.*?)</a>')
   aaa = aaa.replace('aaa', '').replace('bbb', '') 替换多余
   取头 取尾  （循环)     截取项  （循环)    长用于播放数组                     3号子程序

   =======================================

"""

if __name__ == '__main__':
    spider_instance = Spider()

    # res=spider_instance.homeContent('filter')  #  分类🚨

    # res = spider_instance.homeVideoContent()  # 首页🚨

    # res=spider_instance.categoryContent('29', 2, 'filter', {})  #  分页🚨

    # res = spider_instance.detailContent(['https://xhaoer.com/a/153636.html'])  #  详情页🚨

    # res = spider_instance.playerContent('1', '0https://xhaoer.com/y/153636-0-0.html', 'vipFlags')  #  播放页🚨

    res = spider_instance.searchContentPage('爱情', 'quick', '2')  # 搜索页🚨

    print(res)



