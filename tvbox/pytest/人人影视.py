# coding = utf-8
# !/usr/bin/python

"""

作者 丢丢喵 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from bs4 import BeautifulSoup
from base64 import b64decode
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

xurl = "http://59.153.164.124:6655"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

headerz = {
    'User-Agent': 'okhttp/3.14.9'
          }

headers = {
    'User-Agent': '8899',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Host': '59.153.164.124:1000',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip, deflate',
    'Content-Length': '0'
          }

headers1 = {
    'User-Agent': 'Mozilla/6.0 (Linux; Android 10; Mi 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko)',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Host': '59.153.164.124:2000',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip, deflate',
    'Content-Length': '0'
           }

pm = ''

class Spider(Spider):
    global xurl
    global headerx
    global headers
    global headers1
    global headerz

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
                            output += f"#{'📽️丢丢👉' + match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{'📽️丢丢👉' + match[1]}${number}{match[0]}"
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
                new_list = [f'✨丢丢👉{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "1", "type_name": "丢丢电影🌠"},
                            {"type_id": "2", "type_name": "丢丢剧集🌠"},
                            {"type_id": "3", "type_name": "丢丢动漫🌠"}]
                  }

        return result

    def decrypt(self,encrypted_data, key, iv):
        key_bytes = base64.b64decode(key)
        iv_bytes = base64.b64decode(iv)
        encrypted_bytes = base64.b64decode(encrypted_data)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        decrypted_bytes = unpad(decrypted_padded_bytes, AES.block_size)
        return decrypted_bytes.decode('utf-8')

    def homeVideoContent(self):
        videos = []
        payload = {}

        response = requests.post(xurl+"/jj.php/getappapi.index/initV119", headers=headerx, json=payload, verify=False)
        if response.status_code == 200:
            response_data = response.json()

            data = response_data.get('data')
            encrypted_data = data
            key = "RjUxRjVENTJEMjNDQkYyNw=="
            iv = "RjUxRjVENTJEMjNDQkYyNw=="
            detail = self.decrypt(encrypted_data, key, iv)
            detail = json.loads(detail)

            duoxuan = ['1', '2', '3']
            for duo in duoxuan:
                js = detail['type_list'][int(duo)]['recommend_list']
                for vod in js:
                    name = vod['vod_name']

                    id = vod['vod_id']

                    pic = vod['vod_pic']

                    remark = vod['vod_remarks']

                    video = {
                        "vod_id": id,
                        "vod_name": '丢丢📽️' + name,
                        "vod_pic": pic,
                        "vod_remarks": '丢丢▶️' + remark
                             }
                    videos.append(video)

        result = {'list': videos}
        return result

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        if pg:
            page = int(pg)
        else:
            page = 1

        payload = {
            "area": "全部",
            "year": "全部",
            "type_id": cid,
            "page": str(page),
            "sort": "最新",
            "lang": "全部",
            "class": "全部"
                  }

        response = requests.post(xurl + "/jj.php/getappapi.index/typeFilterVodList", headers=headerx, json=payload, verify=False)
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data')
            encrypted_data = data
            key = "RjUxRjVENTJEMjNDQkYyNw=="
            iv = "RjUxRjVENTJEMjNDQkYyNw=="
            detail = self.decrypt(encrypted_data, key, iv)
            detail = json.loads(detail)

            js = detail['recommend_list']
            for vod in js:
                name = vod['vod_name']

                id = vod['vod_id']

                pic = vod['vod_pic']

                remark = vod['vod_remarks']

                video = {
                    "vod_id": id,
                    "vod_name": '丢丢📽️' + name,
                    "vod_pic": pic,
                    "vod_remarks": '丢丢▶️' + remark
                        }
                videos.append(video)

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

        payload = {
            "vod_id": did
                  }

        response = requests.post(xurl + "/jj.php/getappapi.index/vodDetail", headers=headerz, json=payload, verify=False)
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data')
            encrypted_data = data
            key = "RjUxRjVENTJEMjNDQkYyNw=="
            iv = "RjUxRjVENTJEMjNDQkYyNw=="
            detail = self.decrypt(encrypted_data, key, iv)
            detail = json.loads(detail)

            content = detail['vod']['vod_blurb']

            soup = detail['vod_play_list']

            xianlu = ''

            for vods in soup:

                xian = "✨丢丢👉" + vods['player_info']['show']

                xianlu = xianlu + xian + '$$$'

            xianlu = xianlu[:-3]

            purl = ''

            for voda in soup:

                soups = voda['urls']

                for vod in soups:

                    name = vod['name']

                    url = vod['url']

                    token = "token=" +vod['token']

                    parse = vod['parse_api_url']

                    fenge = parse.split("?")

                    purl = purl + name + '$' + fenge[0] + "?" + token + "&" + fenge[1] + '#'

                purl = purl[:-1] + '$$$'

            purl = purl[:-3]

        videos.append({
            "vod_id": did,
            "vod_actor": '😸皮皮 😸灰灰',
            "vod_director": '😸丢丢',
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": purl
                     })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):

        id = id
        payload = {}
        if 'parse.php' in id:
            response = requests.post(id, headers=headers1, json=payload,verify=False)
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get('url')

        else:
            response = requests.post(id, headers=headers, json=payload, verify=False)
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get('url')

        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = data
        result["header"] = headerx
        return result


    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []

        if not page:
            page = '1'

        payload = {
            "keywords": key,
            "type_id": "0",
            "page": str(page),
                  }

        response = requests.post(xurl + "/jj.php/getappapi.index/searchList", headers=headerx, json=payload, verify=False)
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data')
            encrypted_data = data
            key = "RjUxRjVENTJEMjNDQkYyNw=="
            iv = "RjUxRjVENTJEMjNDQkYyNw=="
            detail = self.decrypt(encrypted_data, key, iv)
            detail = json.loads(detail)
            
            js = detail['search_list']
            for vod in js:
                name = vod['vod_name']

                id = vod['vod_id']

                pic = vod['vod_pic']

                remark = vod['vod_remarks']

                video = {
                    "vod_id": id,
                    "vod_name": '丢丢📽️' + name,
                    "vod_pic": pic,
                    "vod_remarks": '丢丢▶️' + remark
                        }
                videos.append(video)

        result = {'list': videos}
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


