# coding=utf-8
#!/usr/bin/python
from urllib import parse
import datetime
from Crypto.Cipher import AES
import json
import requests
import re
import base64
from base.spider import Spider
import sys

sys.path.append("..")


class Spider(Spider):  # 元类 默认的元类 type
    host = "http://kan.bulei.cc"

    header = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Referer": host,
    }
    cookies = {}

    type_extend = {"类型": "class", "地区": "area", "语言": "lang", "年份": "year"}

    def GetHtml(self, url):
        html = self.fetch(
            url,
            headers=self.header,
            cookies=self.cookies,
        )

        if html.text.find("系统安全验证") > 0 or html.text.find("输入验证码") > 0:
            i = 0
            while i < 3:
                imgRsp = self.fetch(self.host + "/index.php/verify/index.html", {}, {})
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
                        html = self.fetch(url, headers=self.header, cookies=self.cookies)
                        return html
                except Exception as e:
                    print("OCR识别验证码发生错误:{0}".format(e))
                i += 1
        return html

    def getName(self):
        return "Test"

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
        result["class"] = []
        result["filters"] = {}
        videos = []
        videos.append(
            {
                "vod_id": "1",
                "vod_name": "汕头综合",
                "vod_pic": "https://tse4-mm.cn.bing.net/th/id/OIP-C.iFV1kZJAJPpdbfptvXGSVwAAAA?rs=1&pid=ImgDetMain",
                "vod_remarks": "",
            }
        )
        result["list"] = videos
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        # videos.append(
        #     {
        #         "vod_id": "1",
        #         "vod_name": "测试",
        #         "vod_pic": "https://img.ziziys.com/wp-content/uploads/2022/05/281d412e981c73.jpg",
        #         "vod_remarks": "已完结",
        #     }
        # )
        result["list"] = videos
        return result

    def detailContent(self, array):
        result = {}
        vod = {
            "vod_id": "1",
            "vod_name": "汕头综合",
            "vod_pic": "https://tse4-mm.cn.bing.net/th/id/OIP-C.iFV1kZJAJPpdbfptvXGSVwAAAA?rs=1&pid=ImgDetMain",
            "type_name": "电视台",
            "vod_play_from": "CUTV",
            "vod_play_url": "播放$1",
        }

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick):
        result = {}
        videos = []
        result["list"] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        # targetUrl = self.playerConfig[flag]["parse"] + id
        # html = self.fetch(targetUrl,self.header)

        # str = self.regStr(html.text,"\"url\":\"(\S+)\",\"id1")

        # base64.b16decode(str)
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Referer": "http://tv.cutv.com",
            # "JPAUTH": "epawNyWhdt3357Lvkkof/btM3TsGN5yBZuXT2xKFKX41"
            # "referer": targetUrl.replace("ec.php","index.php")
        }
        result["parse"] = "1"
        # result["url"] = "https://sf9-dycdn-tos.pstatp.com/obj/tos-cn-i-8gu37r9deh/3cf2b1d7cdec474693857b53618b4364?filename=1.mp4"
        result["url"] = "http://tv.cutv.com/index.html"
        result["header"] = json.dumps(header)
        # result["header"] = ""
        return result

    def AES_Decrypt(self, ciphertext, key, iv):
        try:
            cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
            ct = base64.b64decode(ciphertext.encode())
            pt = cipher.decrypt(ct)
            pt = pt.decode("UTF-8")
            pt = pt[0 : -ord(pt[-1])]
            return pt
        except:
            return ""

    def isVideoFormat(self, url):
        if url.find(".m3u8") !=-1:
            return True
        else:
            return False
        pass

    def localProxy(self, param):
        action = {}
        return [200, "video/MP2T", action, ""]
