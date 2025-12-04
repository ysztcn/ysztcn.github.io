# coding = utf-8
# !/usr/bin/python

"""

作者 丢丢喵 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
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

xurl = "https://www.ppxys.cc"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

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

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "1", "type_name": "丢丢电影🌠"},
                            {"type_id": "2", "type_name": "丢丢剧集🌠"},
                            {"type_id": "3", "type_name": "丢丢综艺🌠"},
                            {"type_id": "4", "type_name": "丢丢动漫🌠"}]
                  }

        return result

    def decrypt(self, encrypted_data):
        key = "UVdFMTIzQVNERjEyM1pYQw=="
        iv = "UVdFMTIzQVNERjEyM1pYQw=="
        key_bytes = base64.b64decode(key)
        iv_bytes = base64.b64decode(iv)
        encrypted_bytes = base64.b64decode(encrypted_data)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        decrypted_bytes = unpad(decrypted_padded_bytes, AES.block_size)
        return decrypted_bytes.decode('utf-8')

    def decrypt_wb(self, encrypted_data):
        key_base64 = "UVdFMTIzQVNERjEyM1pYQw=="
        key_bytes = base64.b64decode(key_base64)
        iv_base64 = "UVdFMTIzQVNERjEyM1pYQw=="
        iv_bytes = base64.b64decode(iv_base64)
        plaintext = encrypted_data
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        ciphertext_bytes = cipher.encrypt(pad(plaintext.encode('utf-8'), AES.block_size))
        ciphertext_base64 = base64.b64encode(ciphertext_bytes).decode('utf-8')
        return ciphertext_base64

    def homeVideoContent(self):
        videos = []
        payload = {}

        response = requests.post(xurl + "/api.php/getappapi.index/initV119", headers=headerx, json=payload, verify=True)
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data')

            encrypted_data = data
            detail = self.decrypt(encrypted_data)
            detail = json.loads(detail)

            duoxuan = ['1', '2', '3','4']
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

        response = requests.post(xurl + "/api.php/getappapi.index/typeFilterVodList", headers=headerx, json=payload, verify=True)
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data')
            encrypted_data = data
            detail = self.decrypt(encrypted_data)
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

        response = requests.post(xurl + "/api.php/getappapi.index/vodDetail", headers=headerx, json=payload, verify=True)
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data')
            encrypted_data = data
            detail = self.decrypt(encrypted_data)
            detail = json.loads(detail)

            content = detail['vod']['vod_blurb']

            soup = detail['vod_play_list']
            xianlu = ''
            purl = ''

            gl = ['官方']

            for vod in soup:

                xian = "✨丢丢👉" + vod['player_info']['show']

                if any(item in xian for item in gl):
                    continue

                xianlu = xianlu + xian + '$$$'

                soups = vod['urls']

                for vods in soups:
                    name = vods['name']

                    parse = vods['parse_api_url']

                    purl = purl + name + '$' + parse + '#'

                purl = purl[:-1] + '$$$'

            xianlu = xianlu[:-3]

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

        if 'NBY' in id:
            fenge = id.split("NBY")
            parse_api = fenge[0]
            url1 = "NBY" + fenge[1]
            id2 = self.decrypt_wb(url1)

            payload = {
                "parse_api": parse_api,
                "url": id2,
                "token": ""
                      }

            response = requests.post(xurl+"/api.php/getappapi.index/vodParse", headers=headerx, json=payload, verify=True)

            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get('data')
                encrypted_data = data
                detail = self.decrypt(encrypted_data)
                detail = json.loads(detail)
                detail_json = json.loads(detail.get('json'))
                url = detail_json.get('url')

        elif 'url=' in id and 'm3u8' in id:
            fenge = id.split("url=")
            url = fenge[1]

        elif 'm3u8' in id:
            fenge = id.split("https:")
            url = "https:" + fenge[1]

        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = url
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

        response = requests.post(xurl + "/api.php/getappapi.index/searchList", headers=headerx, json=payload, verify=True)

        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data')
            encrypted_data = data
            detail = self.decrypt(encrypted_data)
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






