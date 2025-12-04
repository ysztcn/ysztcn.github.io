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

xurl = "http://www.45b7.com"

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
        result = {"class": [{"type_id": "都市", "type_name": "都市🌠"},
                            {"type_id": "赘婿", "type_name": "赘婿🌠"},
                            {"type_id": "战神", "type_name": "战神🌠"},
                            {"type_id": "古代言情", "type_name": "古代言情🌠"},
                            {"type_id": "现代言情", "type_name": "现代言情🌠"},
                            {"type_id": "历史", "type_name": "历史🌠"},
                            {"type_id": "脑洞", "type_name": "脑洞🌠"},
                            {"type_id": "玄幻", "type_name": "玄幻🌠"},
                            {"type_id": "搞笑", "type_name": "搞笑🌠"},
                            {"type_id": "喜剧", "type_name": "喜剧🌠"},
                            {"type_id": "萌宝", "type_name": "萌宝🌠"},
                            {"type_id": "神豪", "type_name": "神豪🌠"},
                            {"type_id": "致富", "type_name": "致富🌠"},
                            {"type_id": "奇幻脑洞", "type_name": "奇幻脑洞🌠"},
                            {"type_id": "超能", "type_name": "超能🌠"},
                            {"type_id": "强者回归", "type_name": "强者回归🌠"},
                            {"type_id": "甜宠", "type_name": "甜宠🌠"},
                            {"type_id": "励志", "type_name": "励志🌠"},
                            {"type_id": "豪门恩怨", "type_name": "豪门恩怨🌠"},
                            {"type_id": "复仇", "type_name": "复仇🌠"},
                            {"type_id": "长生", "type_name": "长生🌠"},
                            {"type_id": "神医", "type_name": "神医🌠"},
                            {"type_id": "马甲", "type_name": "马甲🌠"},
                            {"type_id": "亲情", "type_name": "亲情🌠"},
                            {"type_id": "小人物", "type_name": "小人物🌠"},
                            {"type_id": "奇幻", "type_name": "奇幻🌠"},
                            {"type_id": "无敌", "type_name": "无敌🌠"},
                            {"type_id": "现实", "type_name": "现实🌠"},
                            {"type_id": "重生", "type_name": "重生🌠"},
                            {"type_id": "闪婚", "type_name": "闪婚🌠"},
                            {"type_id": "职场商战", "type_name": "职场商战🌠"},
                            {"type_id": "穿越", "type_name": "穿越🌠"},
                            {"type_id": "年代", "type_name": "年代🌠"},
                            {"type_id": "权谋", "type_name": "权谋🌠"},
                            {"type_id": "高手下山", "type_name": "高手下山🌠"},
                            {"type_id": "悬疑", "type_name": "悬疑🌠"},
                            {"type_id": "家国情仇", "type_name": "家国情仇🌠"},
                            {"type_id": "虐恋", "type_name": "虐恋🌠"},
                            {"type_id": "古装", "type_name": "古装🌠"},
                            {"type_id": "时空之旅", "type_name": "时空之旅🌠"},
                            {"type_id": "玄幻仙侠", "type_name": "玄幻仙侠🌠"},
                            {"type_id": "欢喜冤家", "type_name": "欢喜冤家🌠"},
                            {"type_id": "传承觉醒", "type_name": "传承觉醒🌠"},
                            {"type_id": "情感", "type_name": "情感🌠"},
                            {"type_id": "逆袭", "type_name": "逆袭🌠"},
                            {"type_id": "家庭", "type_name": "家庭🌠"}]

                 }

        return result

    def homeVideoContent(self):
        videos = []

        try:

            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text

            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="SecondList_secondListBox")

            for soup in soups:
                vods = soup.find_all('div', class_="SecondList_secondListItem")

                for vod in vods:
                    names = vod.find('a', class_="image_imageScaleBox")
                    name = names.find('img')['alt']

                    ids = vod.find('a', class_="image_imageScaleBox")
                    id = ids['href']

                    pics = vod.find('a', class_="image_imageScaleBox")
                    pic = pics.find('img')['src']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('a', class_="SecondList_totalChapterNum")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '集多▶️' + remark
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

        if page == '1':
            url = f'{xurl}/vodshow/1---{cid}--------.html'

        else:
            url = f'{xurl}/vodshow/1---{cid}-----{str(page)}---.html'

        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="BrowseList_listBox")

            for soup in soups:
                vods = soup.find_all('div', class_="BrowseList_itemBox")

                for vod in vods:
                    names = vod.find('a', class_="image_imageScaleBox")
                    name = names.find('img')['alt']

                    ids = vod.find('a', class_="image_imageScaleBox")
                    id = ids['href']

                    pics = vod.find('a', class_="image_imageScaleBox")
                    pic = pics.find('img')['src']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('a', class_="BrowseList_totalChapterNum")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '集多▶️' + remark
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

        url = 'https://fs-im-kefu.7moor-fs1.com/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1732707176882/jiduo.txt'
        response = requests.get(url)
        response.encoding = 'utf-8'
        code = response.text
        name = self.extract_middle_text(code, "s1='", "'", 0)
        Jumps = self.extract_middle_text(code, "s2='", "'", 0)

        content = '😸集多🎉为您介绍剧情📢本资源来源于网络🚓侵权请联系删除👉' + self.extract_middle_text(res,'style="">','</div>', 0)
        content = content.replace('\n', '').replace('\r', '').replace(' ', '')

        if name not in content:
            bofang = Jumps
        else:
            bofang = self.extract_middle_text(res, '<div class="pcDrama_catalog">', '</div>', 3, 'href="(.*?)" target=".*?">(.*?)</a>')

        xianlu = self.extract_middle_text(res, '<div class="pcDrama_contentBox">','<div class="pcDrama_catalog">',2, 'class=".*?">(.*?)\s+</h3>')
        xianlu = xianlu.replace('旺旺资源', '集多资源')

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

                url = self.extract_middle_text(res, '},"url":"', '"', 0).replace('\\', '')

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
            url = f'{xurl}/vodsearch/-------------.html?wd={key}'

        else:
            url = f'{xurl}/vodsearch/{key}----------{str(page)}---.html'

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('div', class_="TagBookList_tagBookBox")

        for soup in soups:
            vods = soup.find_all('div', class_="TagBookList_tagItem")

            for vod in vods:
                names = vod.find('a', class_="image_imageScaleBox")
                name = names.find('img')['alt']

                ids = vod.find('a', class_="image_imageScaleBox")
                id = ids['href']

                pics = vod.find('a', class_="image_imageScaleBox")
                pic = pics.find('img')['src']

                if 'http' not in pic:
                    pic = xurl + pic

                remarks = vod.find('a', class_="TagBookList_totalChapterNum")
                remark = remarks.text.strip()

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": '集多▶️' + remark
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






