# coding=utf-8
#!/usr/bin/python
import sys

sys.path.append("..")
from base.spider import Spider
import base64
import re
from Crypto.Cipher import AES


class Spider(Spider):  # 元类 默认的元类 type
    host = "https://www.subaibaiys.com"

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

    def homeContent(self, filter):
        # https://meijuchong.cc/
        result = {}
        cateManual = {
            "电影": "new-movie",
            "电视剧": "tv-drama",
            "热门电影": "hot-month",
            "高分电影": "high-movie",
            "动漫电影": "cartoon-movie",
            "香港电影": "hongkong-movie",
            "国产剧": "domestic-drama",
            "欧美剧": "american-drama",
            "日韩剧": "korean-drama",
            "动漫剧": "anime-drama",
        }
        classes = []
        for k in cateManual:
            classes.append({"type_name": k, "type_id": cateManual[k]})
        result["class"] = classes
        result["filters"] = {}

        rsp = self.fetch(self.host, headers=self.header)
        root = self.html(rsp.text)
        vodList = root.xpath("//div[contains(@class,'mi_ne_kd leibox')]/ul/li")
        videos = []
        for vod in vodList:
            name = vod.xpath("./h3/a/text()")[0]
            pic = vod.xpath(".//img/@data-original")[0]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.xpath(".//div[contains(@class,'jidi')]/span/text()")

            if mark == []:
                mark = vod.xpath("./div[contains(@class,'hdinfo')]/span/text()")
            if mark == []:
                mark = [""]
            mark = mark[0]
            sid = vod.xpath("./a/@href")[0]
            sid = self.regStr(sid, "/movie/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        result["list"] = videos
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = self.host + "/{0}/page/{1}".format(tid, pg)

        rsp = self.fetch(url, headers=self.header)
        root = self.html(rsp.text)
        vodList = root.xpath("//div[contains(@class,'mi_ne_kd mrb')]/ul/li")
        videos = []
        for vod in vodList:
            name = vod.xpath("./h3/a/text()")[0]
            pic = vod.xpath(".//img/@data-original")[0]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.xpath(".//div[contains(@class,'jidi')]/span/text()")

            if mark == []:
                mark = vod.xpath("./div[contains(@class,'hdinfo')]/span/text()")
            if mark == []:
                mark = [""]
            mark = mark[0]
            sid = vod.xpath("./a/@href")[0]
            sid = self.regStr(sid, "/movie/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        result["list"] = videos
        result["page"] = pg
        result["pagecount"] = 9999
        result["limit"] = 90
        result["total"] = 999999
        return result

    def detailContent(self, array):
        tid = array[0]
        url = self.host + "/movie/{0}.html".format(tid)
        rsp = self.fetch(url, headers=self.header)
        root = self.html(rsp.text)
        node = root.xpath("//body")[0]
        title = node.xpath(".//div[@class='moviedteail_tt']/h1/text()")[0]
        pic = root.xpath(".//div[contains(@class,'dyimg')]/img/@src")[0]
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

        vod["type_name"] = ",".join(
            node.xpath(
                "//ul[contains(@class,'moviedteail_list')]/li[contains(text(),'类型')]//text()"
            )
        ).replace("类型：,", "")
        vod["vod_year"] = ",".join(
            node.xpath(
                "//ul[contains(@class,'moviedteail_list')]/li[contains(text(),'年份')]//text()"
            )
        ).replace("年份：,", "")
        vod["vod_area"] = ",".join(
            node.xpath(
                "//ul[contains(@class,'moviedteail_list')]/li[contains(text(),'地区')]//text()"
            )
        ).replace("地区：,", "")
        vod["vod_actor"] = ",".join(
            node.xpath(
                "//ul[contains(@class,'moviedteail_list')]/li[contains(text(),'主演')]//text()"
            )
        ).replace("主演：,", "")
        vod["vod_director"] = ",".join(
            node.xpath(
                "//ul[contains(@class,'moviedteail_list')]/li[contains(text(),'导演')]//text()"
            )
        ).replace("导演：,", "")

        vod["vod_content"] = (
            node.xpath(".//div[contains(@class,'yp_context')]/p//text()")[0]
            .replace("\n", "")
            .replace("\t", "")
        )

        playFrom = []
        vodHeader = root.xpath(
            ".//div[contains(@class,'mi_paly_box')]/div/div[contains(@class,'ypxingq_t')]/text()"
        )
        for v in vodHeader:
            playFrom.append(v.strip())
        vod_play_from = "$$$".join(playFrom)

        playList = []
        vodList = root.xpath(
            ".//div[contains(@class,'mi_paly_box')]/div/div[contains(@class,'paly_list_btn')]"
        )
        for vl in vodList:
            vodItems = []
            aList = vl.xpath("./a")
            for tA in aList:
                href = tA.xpath("./@href")[0]
                name = tA.xpath("./text()")[0]
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
        url = self.host + "/search?q={0}".format(key)

        rsp = self.fetch(url, headers=self.header)
        root = self.html(rsp.text)
        vodList = root.xpath("//div[contains(@class,'mi_ne_kd')]/ul/li")
        videos = []
        for vod in vodList:
            name = vod.xpath("./h3/a/text()")[0]
            if name.find(key) < 0:
                continue

            pic = vod.xpath(".//img/@data-original")[0]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.xpath(".//div[contains(@class,'jidi')]/span/text()")

            if mark == []:
                mark = vod.xpath("./div[contains(@class,'hdinfo')]/span/text()")
            if mark == []:
                mark = [""]
            mark = mark[0]
            sid = vod.xpath("./a/@href")[0]
            sid = self.regStr(sid, "/movie/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        result = {"list": videos}
        return result

    def playerContent(self, flag, id, vipFlags):
        # https://meijuchong.cc/static/js/playerconfig.js
        result = {}
        url = self.host + "/v_play/{0}.html".format(id)
        rsp = self.fetch(url, headers=self.header)
        m = re.search('var.*="(\\S+)?";.*parse\\("(\\S+)"\\).*parse\\((\\S+)\\)', rsp.text)
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
            pt = cipher.decrypt(ct)  # 解密之后输出：b'China\xe4\xb8\xad\xe5\x9b\xbd\x05\x05\x05\x05\x05'
            pt = pt.decode("UTF-8")  # 解码之后输出：China中国。注意：此时虽然看到的是“China中国”，其实后面还有填充字符，只不过看不见而已！！！
            # ord函数就是把unicode字符转化为对应的ASCII码，比如'a' -> 97, 'A' -> 65
            pt = pt[0 : -ord(pt[-1])]  # 删除填充之后输出：China中国
            return pt
        except (ValueError, KeyError):
            return ""

    def localProxy(self, param):
        return [200, "video/MP2T", action, ""]
