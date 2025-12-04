# coding=utf-8
#!/usr/bin/python
import sys

sys.path.append("..")
from base.spider import Spider
import base64
import re
from Crypto.Cipher import AES
from bs4 import BeautifulSoup


class Spider(Spider):  # 元类 默认的元类 type
    host = "https://www.bttwo.net"

    header = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Referer": host,
    }

    def getName(self):
        return "Subaibai"

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
            "电影": "new-movie",
            "国产剧": "zgjun",
            "美剧": "meiju",
            "日韩剧": "jpsrtv",
        }
        classes = []
        for k in cateManual:
            classes.append({"type_name": k, "type_id": cateManual[k]})

        result["class"] = classes
        result["filters"] = {}

        rsp = self.fetch(self.host, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("div.mi_ne_kd li")
        videos = []
        for vod in vodList:
            name = vod.select("h3>a")[0].text
            pic = vod.select("a > img")[0]["data-original"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = ""
            if vod.select("div.jidi>span") != []:
                mark = vod.select("div.jidi>span")[0].text
            if mark == "" and vod.select("div.hdinfo>span") != []:
                mark = vod.select("div.hdinfo>span")[0].text
            sid = vod.select("a")[0]["href"]
            sid = self.regStr(sid, "/movie/(\\S+).html")
            videos.append(
                {"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark}
            )
            result["list"] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        url = self.host + "/{0}/page/{1}".format(tid, pg)
        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("div.mi_ne_kd li")
        videos = []
        for vod in vodList:
            name = vod.select("h3>a")[0].text
            pic = vod.select("a > img")[0]["data-original"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = ""
            if vod.select("div.jidi>span") != []:
                mark = vod.select("div.jidi>span")[0].text
            if mark == "" and vod.select("div.hdinfo>span") != []:
                mark = vod.select("div.hdinfo>span")[0].text
            sid = vod.select("a")[0]["href"]
            sid = self.regStr(sid, "/movie/(\\S+).html")
            videos.append(
                {"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark}
            )
        return {"list": videos}

    def detailContent(self, array):
        tid = array[0]
        url = self.host + "/movie/{0}.html".format(tid)
        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        title = root.select("div.moviedteail_tt h1")[0].text
        pic = root.select("div.dyimg>img")[0]["src"]
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
        for e in root.select("ul.moviedteail_list>li"):
            txt = ",".join(e.strings)
            if txt[0:3] == "类型：":
                vod["type_name"] = txt[4:]
            elif txt[0:3] == "年份：":
                vod["vod_year"] = txt[4:]
            elif txt[0:3] == "地区：":
                vod["vod_area"] = txt[4:]
            elif txt[0:3] == "主演：":
                vod["vod_actor"] = txt[4:]
            elif txt[0:3] == "导演：":
                vod["vod_director"] = txt[4:]

        vod["vod_content"] = root.select("div.yp_context>p")[0].text.strip()

        playFrom = []

        vodHeader = root.select("div.mi_paly_box>div>div.ypxingq_t")
        for v in vodHeader:
            playFrom.append(v.contents[0])
        vod_play_from = "$$$".join(playFrom)

        playList = []
        vodList = root.select("div.mi_paly_box div.paly_list_btn")
        for vl in vodList:
            vodItems = []
            for tA in vl.select("a"):
                href = tA["href"]
                name = tA.text
                tId = self.regStr(href, "/v_play/(\\S+).html")
                vodItems.append(name + "$" + tId)
            joinStr = "#".join(vodItems)
            playList.append(joinStr)
        vod_play_url = "$$$".join(playList)

        vod["vod_play_from"] = vod_play_from
        vod["vod_play_url"] = vod_play_url

        result = {"list": [vod]}
        return result

    def searchContent(self, key, quick):
        url = self.host + "/xssearch?q={0}".format(key)

        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("div.search_list ul li")
        videos = []
        for vod in vodList:
            name = vod.select("h3>a")[0].text
            if name.find(key) < 0:
                continue

            pic = vod.select("a > img")[0]["data-original"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = ""
            if vod.select("div.jidi>span") != []:
                mark = vod.select("div.jidi>span")[0].text

            sid = vod.select("a")[0]["href"]
            sid = self.regStr(sid, "/movie/(\\S+).html")
            videos.append(
                {"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark}
            )
        result = {"list": videos}
        return result

    def playerContent(self, flag, id, vipFlags):
        # https://meijuchong.cc/static/js/playerconfig.js
        result = {}
        url = self.host + "/v_play/{0}.html".format(id)
        rsp = self.fetch(url, headers=self.header)
        m = re.search(
            'var.*="(\\S+)?";.*parse\\("(\\S+)"\\).*parse\\((\\S+)\\)', rsp.text
        )
        if m:
            enstr = m.group(1)
            key = m.group(2)
            iv = m.group(3)
        root = self.AES_Decrypt(enstr, key, iv)

        targetUrl = self.regStr(root, 'url: "(\\S+?)"')

        result["parse"] = 0
        result["playUrl"] = ""
        result["url"] = targetUrl
        result["header"] = ""

        return result

    def AES_Decrypt(self, ciphertext, key, iv):
        try:
            cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
            ct = base64.b64decode(
                ciphertext.encode()
            )  # base64解码之后输出：b'x\x15\xc5\x0b\xae\xe9\x16\x06\xe2q\xab\xc5\xdd\xdf\xa1\x93'
            pt = cipher.decrypt(
                ct
            )  # 解密之后输出：b'China\xe4\xb8\xad\xe5\x9b\xbd\x05\x05\x05\x05\x05'
            pt = pt.decode(
                "UTF-8"
            )  # 解码之后输出：China中国。注意：此时虽然看到的是“China中国”，其实后面还有填充字符，只不过看不见而已！！！
            # ord函数就是把unicode字符转化为对应的ASCII码，比如'a' -> 97, 'A' -> 65
            pt = pt[0 : -ord(pt[-1])]  # 删除填充之后输出：China中国
            return pt
        except (ValueError, KeyError):
            return ""

    def localProxy(self, param):
        return [200, "video/MP2T", action, ""]
