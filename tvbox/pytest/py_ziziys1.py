# coding=utf-8
#!/usr/bin/python
import json
import sys

sys.path.append("..")
from base.spider import Spider
import base64
import re
from Crypto.Cipher import AES
from bs4 import BeautifulSoup
import datetime


class Spider(Spider):  # 元类 默认的元类 type
    host = "https://www.ziziys.com"

    header = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Referer": host,
    }

    def getName(self):
        return "ziziys"

    def init(self, extend=""):
        print("============{0}============".format(extend))
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeVideoContent(self):
        pass

    def homeContent(self, filter):
        # https://meijuchong.cc/
        result = {}
        cateManual = {
            "电影": "1",
            "国产剧": "13",
            "动漫": "3",
            "美剧": "14",
            "日韩剧": "15",
        }
        classes = []
        for k in cateManual:
            classes.append({"type_name": k, "type_id": cateManual[k]})

        result["class"] = classes
        result["filters"] = self.filterConfig

        rsp = self.fetch(self.host, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("div.module.module-wrapper div.module-item")
        videos = []
        for vod in vodList:
            name = vod.select("img")[0]["alt"]
            pic = vod.select("img")[0]["data-src"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.select("div.module-item-text")[0].text
            sid = vod.select("a")[0]["href"]
            sid = self.regStr(sid, "/vdetail/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
            result["list"] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        url = self.host + "/list/{0}-{1}.html".format(tid, pg)
        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("div.module-item")
        videos = []
        for vod in vodList:
            name = vod.select("img")[0]["alt"]
            pic = vod.select("img")[0]["data-src"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.select("div.module-item-text")[0].text
            sid = vod.select("a")[0]["href"]
            sid = self.regStr(sid, "/vdetail/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        return {"list": videos}

    def detailContent(self, array):
        tid = array[0]
        url = self.host + "/vdetail/{0}.html".format(tid)
        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        title = root.select("h1")[0].text
        pic = root.select("div.video-cover img")[0]["data-src"]
        vod = {
            "vod_id": tid,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
        }

        els = root.select(".tag-link")
        vod["type_name"] = els[1].text
        vod["vod_year"] = els[2].text
        vod["vod_area"] = els[3].text

        for e in root.select("div.video-info-items"):
            txt = "".join(e.stripped_strings)
            if txt[0:3] == "主演：":
                vod["vod_actor"] = txt.replace("主演：", "")
            elif txt[0:3] == "导演：":
                vod["vod_director"] = txt.replace("导演：", "")

        vod["vod_content"] = root.select("div.vod_content span")[0].text

        playFrom = []

        vodHeader = root.select("div.tab-item span")
        for v in vodHeader:
            playFrom.append(v.text)
        vod_play_from = "$$$".join(playFrom)

        playList = []
        vodList = root.select("div.tab-list div.sort-item")
        for vl in vodList:
            vodItems = []
            for tA in vl.select("a"):
                href = tA["href"]
                name = tA.text
                tId = self.regStr(href, "/video/(\\S+).html")
                vodItems.append(name + "$" + tId)
            joinStr = "#".join(vodItems)
            playList.append(joinStr)
        vod_play_url = "$$$".join(playList)

        vod["vod_play_from"] = vod_play_from
        vod["vod_play_url"] = vod_play_url

        result = {"list": [vod]}
        return result

    def searchContent(self, key, quick):
        url = self.host + "/vsearch/{0}--.html".format(key)

        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("div.module-search-item")
        videos = []
        for vod in vodList:
            name = vod.select("img")[0]["alt"]
            if name.find(key) < 0:
                continue

            pic = vod.select("img")[0]["data-src"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.select("a.video-serial")[0].text
            sid = vod.select("div.video-info-header>a")[0]["href"]
            sid = self.regStr(sid, "/vdetail/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        result = {"list": videos}
        return result

    def playerContent(self, flag, id, vipFlags):
        # https://meijuchong.cc/static/js/playerconfig.js
        result = {}
        url = self.host + "/video/{0}.html".format(id)

        rsp = self.fetch(url, headers=self.header)
        mJson = json.loads(self.regStr(rsp.text, "player_.*=(\{.+?\})<"))
        targetUrl = mJson["url"]
        result["parse"] = 0
        result["playUrl"] = ""
        result["url"] = targetUrl
        result["header"] = ""

        return result

    def CBC_Decrypt(self, ciphertext, key, iv):
        try:
            cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
            ct = base64.b64decode(
                ciphertext.encode()
            )  # base64解码之后输出：b'x\x15\xc5\x0b\xae\xe9\x16\x06\xe2q\xab\xc5\xdd\xdf\xa1\x93'
            pt = cipher.decrypt(ct)  # 解密之后输出：b'China\xe4\xb8\xad\xe5\x9b\xbd\x05\x05\x05\x05\x05'
            pt = pt.decode("UTF-8")  # 解码之后输出：China中国。注意：此时虽然看到的是“China中国”，其实后面还有填充字符，只不过看不见而已！！！
            # ord函数就是把unicode字符转化为对应的ASCII码，比如'a' -> 97, 'A' -> 65
            pt = pt[0 : -ord(pt[-1])]  # 删除填充之后输出：China中国
            return pt
        except (ValueError, KeyError):
            return ""

    def localProxy(self, param):
        action = {}
        return [200, "video/MP2T", action, ""]

    filterConfig = {}
