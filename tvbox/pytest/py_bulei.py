# coding=utf-8
#!/usr/bin/python
import sys

sys.path.append("..")
from base.spider import Spider
import base64
import re
import requests
import json
from Crypto.Cipher import AES
import datetime
from urllib import parse


class Spider(Spider):  # 元类 默认的元类 type
    host = "http://kan.bulei.cc"

    header = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Referer": host,
    }
    cookies = {}

    type_extend = {
        "类型": "class",
        "地区": "area",
        "语言": "lang",
        "年份": "year",
    }

    playerConfig = {
        "HOTV4K": {
            "show": "布蕾4K①",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=HOTV&url=",
        },
        "BL2160P": {
            "show": "布蕾4k②",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=HOTV&url=",
        },
        "HOTVIP": {
            "show": "布蕾蓝光①",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=HOTV&url=",
        },
        "HOTV": {
            "show": "布蕾蓝光②",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=HOTV&url=",
        },
        "BLLG": {
            "show": "布蕾蓝光③",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=HOTV&url=",
        },
        "JHA": {
            "show": "布蕾蓝光④",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=HOTV&url=",
        },
        "ffm3u8": {
            "show": "高清",
            "des": "",
            "ps": "1",
            "parse": "http://vod.bulei.cc/player/ec.php?code=ffzy&from=ffm3u8&url=",
        },
        "qq": {
            "show": "腾讯",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "qiyi": {
            "show": "爱奇艺",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "youku": {
            "show": "优酷",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "mgtv": {
            "show": "芒果TV",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "bilibili": {
            "show": "哔哩哔哩",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "sohu": {
            "show": "搜狐",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "xigua": {
            "show": "西瓜视频",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "pptv": {
            "show": "PPTV",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
        "le": {
            "show": "乐视TV",
            "des": "",
            "ps": "1",
            "parse": "http://bfq.bulei.cc/player/ec.php?code=BLHD&url=",
        },
    }

    def GetHtml(self, url):
        html = self.fetch(url, headers=self.header, cookies=self.cookies)

        if html.text.find("系统安全验证") > 0 or html.text.find("输入验证码") > 0:
            i = 0
            while i < 3:
                imgRsp = self.fetch(
                    self.host + "/index.php/verify/index.html",
                    {},
                    {},
                )
                self.cookies.clear()
                cookies = imgRsp.cookies.items()
                for name, value in cookies:
                    self.cookies[name] = value
                try:
                    print("通过drpy_ocr验证码接口过验证...")
                    code = self.post(
                        "http://drpy.nokia.press:8028/ocr/drpy/text",
                        data={"img": base64.b64encode(imgRsp.content)},
                    )
                    rsp = self.postJson(
                        self.host + "/index.php/ajax/verify_check",
                        {"type": "show", "verify": code.text},
                        self.header,
                        self.cookies,
                    )
                    jrsp = json.loads(rsp.text)
                    if jrsp["msg"] == "ok":
                        html = self.fetch(
                            url, headers=self.header, cookies=self.cookies
                        )
                        return html
                except Exception as e:
                    print("OCR识别验证码发生错误:{0}".format(e))
                i += 1
        return html

    def getName(self):
        return "BuLei"

    def init(self, extend=""):
        print("============{0}============".format(extend))
        pass

    def isVideoFormat(self, url):
        # if self.regStr(url,"(/Cloud/Down/Index)")!="":
        #     return True
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        url = self.host + "/api.php/app/nav"
        rsp = self.fetch(url, headers=self.header)
        jo = json.loads(rsp.text)
        root = jo["list"]

        classes = []
        filters = {}
        for item in root:
            classes.append({"type_name": item["type_name"], "type_id": item["type_id"]})
            filters[item["type_id"]] = []
            for t in self.type_extend:
                aa = {"key": self.type_extend[t], "name": t}
                ls = item["type_extend"][self.type_extend[t]].split(",")
                nv = [{"n": "全部", "v": ""}]
                for sub in ls:
                    nv.append({"n": sub, "v": sub})
                aa["value"] = nv
                filters[item["type_id"]].append(aa)

        result["class"] = classes
        result["filters"] = filters
        return result

    def homeVideoContent(self):
        result = {}
        url = self.host + "/api.php/app/index_video"
        rsp = self.fetch(url, headers=self.header)
        jo = json.loads(rsp.text)
        list = jo["list"]
        videos = []
        for vodList in list:
            for vod in vodList["vlist"]:
                videos.append(
                    {
                        "vod_id": vod["vod_id"],
                        "vod_name": vod["vod_name"],
                        "vod_pic": vod["vod_pic"],
                        "vod_remarks": vod["vod_remarks"],
                    }
                )
        result = {"list": videos}
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = (
            self.host
            + "/api.php/app/video?tid={0}&class=筛选class&area=筛选area&lang=筛选lang&year=筛选year&limit=18&pg={1}".format(
                tid, pg
            )
        )
        for item in extend:
            for t in self.type_extend:
                self.type_extend[t]

        for t in self.type_extend:
            url = url.replace("筛选" + self.type_extend[t], "")

        rsp = self.fetch(url, headers=self.header)
        jo = json.loads(rsp.text)
        vodList = jo["list"]
        videos = []
        for vod in vodList:
            videos.append(
                {
                    "vod_id": vod["vod_id"],
                    "vod_name": vod["vod_name"],
                    "vod_pic": vod["vod_pic"],
                    "vod_remarks": vod["vod_remarks"],
                }
            )
        result = {"list": videos}
        return result

    def detailContent(self, array):
        tid = array[0]
        url = self.host + "/api.php/app/video_detail?id={0}".format(tid)
        rsp = self.fetch(url, headers=self.header)
        jo = json.loads(rsp.text)
        v = jo["data"]
        vod = {
            "vod_id": v["vod_id"],
            "vod_name": v["vod_name"],
            "vod_pic": v["vod_pic"],
            "type_name": v["vod_class"],
            "vod_year": v["vod_year"],
            "vod_area": v["vod_area"],
            "vod_remarks": v["vod_remarks"],
            "vod_actor": v["vod_actor"],
            "vod_director": v["vod_director"],
            "vod_content": v["vod_content"],
            "vod_play_from": v["vod_play_from"],
            "vod_play_url": v["vod_play_url"],
        }

        result = {"list": [vod]}
        return result

    def searchContent(self, key, quick):
        url = self.host + "/api.php/app/search?text={0}".format(key)
        rsp = self.fetch(url, headers=self.header)
        jo = json.loads(rsp.text)
        vodList = jo["list"]
        videos = []
        for vod in vodList:
            videos.append(
                {
                    "vod_id": vod["id"],
                    "vod_name": vod["name"],
                    "vod_pic": vod["pic"],
                    "vod_remarks": "",
                }
            )
        result = {"list": videos}
        return result

    def playerContent(self, flag, id, vipFlags):
        # # https://meijuchong.cc/static/js/playerconfig.js
        result = {}
        # targetUrl = self.playerConfig[flag]["parse"] + id
        # html = self.fetch(targetUrl,self.header)

        # str = self.regStr(html.text,"\"url\":\"(\S+)\",\"id1")

        # base64.b16decode(str)
        header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
            # "referer": targetUrl.replace("ec.php","index.php")
        }
        result["parse"] = "0"
        result["playUrl"] = ""
        # result["url"] = "https://sf9-dycdn-tos.pstatp.com/obj/tos-cn-i-8gu37r9deh/3cf2b1d7cdec474693857b53618b4364?filename=1.mp4"
        result["url"] = "https://aliyun.shpina.top/lzcache/20230511/2433_23f237a7/index.m3u8"
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
        action = []
        return [200, "video/MP2T", action, ""]
