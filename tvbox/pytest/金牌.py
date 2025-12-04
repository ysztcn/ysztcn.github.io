"""

作者 丢丢喵 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

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

xurl = "https://www.cfkj86.com"

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
        result = {"class": [{"type_id": "1", "type_name": "集多电影🌠"},
                            {"type_id": "2", "type_name": "集多剧集🌠"},
                            {"type_id": "4", "type_name": "集多动漫🌠"},
                            {"type_id": "3", "type_name": "集多综艺🌠"}],
                 }

        return result

    def homeVideoContent(self):
        videos = []

        try:

            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            res = self.extract_middle_text(res, '[\\"$\\",\\"main\\",null,', ']\\n"])', 0)

            jso = json.loads(res)

            duoxuan = ['homeNewMoviePageData', 'homeBroadcastPageData', 'homeManagerPageData', 'newestTvPageData',
                       'newestVarietyPageData','newestCartoonPageData']

            for duo in duoxuan:

                if duo in jso.get('children', [{}])[3].get('data', {}).get('data', {}):

                    for vod in jso['children'][3]['data']['data'][duo]['list']:

                        name = vod['vodName']

                        id = vod['vodId']
                        id = f"https://www.cfkj86.com/detail/{vod['vodId']}"

                        pic = vod['vodPic']
                        pic = f"{vod['vodPic']}?x-image-process=image/resize,w_356,h_498/quality,q_65/format,webp"

                        remar1 = vod['vodVersion']
                        remar2 = vod['vodArea']
                        remark = remar2 + remar1

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

        if page == '1':
            url = f'{xurl}/vod/show/id/{cid}'

        else:
            url = f'{xurl}/vod/show/id/{cid}/page/{str(page)}'

        if '1' in {cid}:
            try:
                detail = requests.get(url=url, headers=headerx)
                detail.encoding = "utf-8"
                res = detail.text
                res = self.extract_middle_text(res, '[\\"$\\",\\"$L2a\\",null,', ']\\n"])', 0)

                res = res.replace('a "', 'a \\"').replace('Christmas Story', 'Christmas Story\\').replace('""An Almost', '"\\"An Almost')

                jso = json.loads(res)

                for vod in jso['videoList']['data']['list']:

                    name = vod['vodName']

                    id = vod['vodId']
                    id = f"https://www.cfkj86.com/detail/{vod['vodId']}"

                    pic = vod['vodPic']
                    pic = f"{vod['vodPic']}?x-image-process=image/resize,w_356,h_498/quality,q_65/format,webp"

                    remar1 = vod['vodVersion']
                    remar2 = vod['vodArea']
                    remark = remar2 + remar1

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": '集多推荐▶️' + remark
                            }
                    videos.append(video)

            except:
                pass
        else:
            try:
                detail = requests.get(url=url, headers=headerx)
                detail.encoding = "utf-8"
                res = detail.text
                res = self.extract_middle_text(res, '[\\"$\\",\\"$L2a\\",null,', ']\\n"])', 0)

                jso = json.loads(res)

                for vod in jso['videoList']['data']['list']:
                    name = vod['vodName']

                    id = vod['vodId']
                    id = f"https://www.cfkj86.com/detail/{vod['vodId']}"

                    pic = vod['vodPic']
                    pic = f"{vod['vodPic']}?x-image-process=image/resize,w_356,h_498/quality,q_65/format,webp"

                    remar1 = vod['vodVersion']
                    remar2 = vod['vodArea']
                    remark = remar2 + remar1

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

        url = 'https://fs-im-kefu.7moor-fs1.com/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1732707176882/jiduo.txt'
        response = requests.get(url)
        response.encoding = 'utf-8'
        code = response.text
        name = self.extract_middle_text(code, "s1='", "'", 0)
        Jumps = self.extract_middle_text(code, "s2='", "'", 0)

        content = '集多🎉为您介绍剧情📢本资源来源于网络🚓侵权请联系删除👉' + self.extract_middle_text(res,'<div class="jiantou"></div>','</div>', 0)
        content = content.replace('</label>', '')

        if name not in content:
            bofang = Jumps
        else:
            bofang = self.extract_middle_text(res, '<div type="', '<div class="panel', 3, 'href="(.*?)">(.*?)</a>')

        videos.append({
            "vod_id": did,
            "vod_actor": '集多和他的朋友们',
            "vod_director": '集多',
            "vod_content": content,
            "vod_play_from": '集多专线',
            "vod_play_url": bofang
                     })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        parts = id.split("http")

        xiutan = 1

        if xiutan == 1:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]
            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = after_https
            result["header"] = headerx
            return result

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []

        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/vod/search/{key}'

        else:
            url = f'{xurl}/vod/search/{key}'

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        res = self.extract_middle_text(res, '\\"$\\",\\"$L2b\\",null,', ']\\n"])', 0)

        jso = json.loads(res)

        for vod in jso['data']['data']['result']['list']:

            name = vod['vodName']

            id = vod['vodId']
            id = f"https://www.cfkj86.com/detail/{vod['vodId']}"

            pic = vod['vodPic']
            pic = f"{vod['vodPic']}?x-image-process=image/resize,w_356,h_498/quality,q_65/format,webp"

            remar1 = vod['vodVersion']
            remar2 = vod['vodArea']
            remark = remar2 + remar1

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






