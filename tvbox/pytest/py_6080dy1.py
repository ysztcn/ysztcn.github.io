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
    host = "https://www.6080dy4.com"

    header = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Referer": host,
    }

    def getName(self):
        return "6080dy"

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
        cateManual = {"电影": "1", "剧集": "2", "综艺": "3", "动漫": "4"}
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
            sid = self.regStr(sid, "/video/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
            result["list"] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        if "id" not in extend.keys():
            extend["id"] = tid
        extend["page"] = pg
        filterParams = ["id", "area", "by", "class", "lang", "", "", "", "page", "", "", "year"]
        params = ["", "", "", "", "", "", "", "", "", "", "", ""]
        for idx in range(len(filterParams)):
            fp = filterParams[idx]
            if fp in extend.keys():
                params[idx] = extend[fp]
        suffix = "-".join(params)
        url = self.host + "/vodshow/{0}.html".format(suffix)
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
            sid = self.regStr(sid, "/video/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        return {"list": videos}

    def detailContent(self, array):
        tid = array[0]
        url = self.host + "/video/{0}.html".format(tid)
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
                tId = self.regStr(href, "/vplay/(\\S+).html")
                vodItems.append(name + "$" + tId)
            joinStr = "#".join(vodItems)
            playList.append(joinStr)
        vod_play_url = "$$$".join(playList)

        vod["vod_play_from"] = vod_play_from
        vod["vod_play_url"] = vod_play_url

        result = {"list": [vod]}
        return result

    def searchContent(self, key, quick):
        url = self.host + "/vodsearch/-------------.html"

        rsp = self.post(url, {"wd": key}, headers=self.header)
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
            sid = self.regStr(sid, "/video/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        result = {"list": videos}
        return result

    def playerContent(self, flag, id, vipFlags):
        # https://meijuchong.cc/static/js/playerconfig.js
        result = {}
        url = self.host + "/vplay/{0}.html".format(id)

        rsp = self.fetch(url, headers=self.header)
        mJson = json.loads(self.regStr(rsp.text, "player_.*=(\{.+?\})<"))
        if mJson["url"].startswith("http"):
            targetUrl = mJson["url"]
            result["parse"] = 0
        else:
            targetUrl = url
            result["parse"] = 1

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

    filterConfig = {
        "1": [
            {
                "key": "id",
                "name": "类型",
                "value": [
                    {"n": "全部", "v": "1"},
                    {"n": "动作片", "v": "25"},
                    {"n": "喜剧片", "v": "26"},
                    {"n": "爱情片", "v": "27"},
                    {"n": "科幻片", "v": "28"},
                    {"n": "恐怖片", "v": "30"},
                    {"n": "剧情片", "v": "31"},
                    {"n": "战争片", "v": "33"},
                    {"n": "纪录片", "v": "35"},
                    {"n": "悬疑片", "v": "36"},
                    {"n": "犯罪片", "v": "38"},
                    {"n": "冒险片", "v": "40"},
                    {"n": "动画片", "v": "41"},
                    {"n": "惊悚片", "v": "43"},
                    {"n": "奇幻片", "v": "44"},
                    {"n": "理论片", "v": "46"},
                ],
            },
            {
                "key": "class",
                "name": "剧情",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "喜剧", "v": "喜剧"},
                    {"n": "爱情", "v": "爱情"},
                    {"n": "恐怖", "v": "恐怖"},
                    {"n": "动作", "v": "动作"},
                    {"n": "科幻", "v": "科幻"},
                    {"n": "剧情", "v": "剧情"},
                    {"n": "战争", "v": "战争"},
                    {"n": "警匪", "v": "警匪"},
                    {"n": "犯罪", "v": "犯罪"},
                    {"n": "动画", "v": "动画"},
                    {"n": "奇幻", "v": "奇幻"},
                    {"n": "武侠", "v": "武侠"},
                    {"n": "冒险", "v": "冒险"},
                    {"n": "枪战", "v": "枪战"},
                    {"n": "恐怖", "v": "恐怖"},
                    {"n": "悬疑", "v": "悬疑"},
                    {"n": "惊悚", "v": "惊悚"},
                    {"n": "经典", "v": "经典"},
                    {"n": "青春", "v": "青春"},
                    {"n": "文艺", "v": "文艺"},
                    {"n": "微电影", "v": "微电影"},
                    {"n": "古装", "v": "古装"},
                    {"n": "历史", "v": "历史"},
                    {"n": "运动", "v": "运动"},
                    {"n": "农村", "v": "农村"},
                    {"n": "儿童", "v": "儿童"},
                    {"n": "网络电影", "v": "网络电影"},
                ],
            },
            {
                "key": "area",
                "name": "地区",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "大陆", "v": "大陆"},
                    {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"},
                    {"n": "美国", "v": "美国"},
                    {"n": "法国", "v": "法国"},
                    {"n": "英国", "v": "英国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "德国", "v": "德国"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "印度", "v": "印度"},
                    {"n": "意大利", "v": "意大利"},
                    {"n": "西班牙", "v": "西班牙"},
                    {"n": "加拿大", "v": "加拿大"},
                    {"n": "其他", "v": "其他"},
                ],
            },
            {
                "key": "lang",
                "name": "语言",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国语", "v": "国语"},
                    {"n": "英语", "v": "英语"},
                    {"n": "粤语", "v": "粤语"},
                    {"n": "闽南语", "v": "闽南语"},
                    {"n": "韩语", "v": "韩语"},
                    {"n": "日语", "v": "日语"},
                    {"n": "法语", "v": "法语"},
                    {"n": "德语", "v": "德语"},
                    {"n": "其它", "v": "其它"},
                ],
            },
            {
                "key": "year",
                "name": "时间",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"},
                    {"n": "2014", "v": "2014"},
                    {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"},
                ],
            },
        ],
        "2": [
            {
                "key": "id",
                "name": "类型",
                "value": [
                    {"n": "全部", "v": "2"},
                    {"n": "国产剧", "v": "42"},
                    {"n": "欧美剧", "v": "45"},
                    {"n": "日韩剧", "v": "47"},
                    {"n": "港台剧", "v": "49"},
                    {"n": "泰剧", "v": "51"},
                    {"n": "海外剧", "v": "52"},
                ],
            },
            {
                "key": "class",
                "name": "剧情",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "古装", "v": "古装"},
                    {"n": "战争", "v": "战争"},
                    {"n": "青春偶像", "v": "青春偶像"},
                    {"n": "喜剧", "v": "喜剧"},
                    {"n": "家庭", "v": "家庭"},
                    {"n": "犯罪", "v": "犯罪"},
                    {"n": "动作", "v": "动作"},
                    {"n": "奇幻", "v": "奇幻"},
                    {"n": "剧情", "v": "剧情"},
                    {"n": "历史", "v": "历史"},
                    {"n": "经典", "v": "经典"},
                    {"n": "乡村", "v": "乡村"},
                    {"n": "情景", "v": "情景"},
                    {"n": "商战", "v": "商战"},
                    {"n": "网剧", "v": "网剧"},
                    {"n": "其他", "v": "其他"},
                ],
            },
            {
                "key": "area",
                "name": "地区",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "内地", "v": "内地"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"},
                    {"n": "日本", "v": "日本"},
                    {"n": "美国", "v": "美国"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "英国", "v": "英国"},
                    {"n": "新加坡", "v": "新加坡"},
                    {"n": "其他", "v": "其他"},
                ],
            },
            {
                "key": "lang",
                "name": "语言",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国语", "v": "国语"},
                    {"n": "英语", "v": "英语"},
                    {"n": "粤语", "v": "粤语"},
                    {"n": "闽南语", "v": "闽南语"},
                    {"n": "韩语", "v": "韩语"},
                    {"n": "日语", "v": "日语"},
                    {"n": "其它", "v": "其它"},
                ],
            },
            {
                "key": "year",
                "name": "时间",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"},
                    {"n": "2014", "v": "2014"},
                    {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"},
                ],
            },
        ],
        "3": [
            {
                "key": "id",
                "name": "类型",
                "value": [
                    {"n": "全部", "v": "3"},
                    {"n": "大陆综艺", "v": "20"},
                    {"n": "日韩综艺", "v": "21"},
                    {"n": "港台综艺", "v": "22"},
                    {"n": "欧美综艺", "v": "23"},
                ],
            },
            {
                "key": "class",
                "name": "剧情",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "选秀", "v": "选秀"},
                    {"n": "情感", "v": "情感"},
                    {"n": "访谈", "v": "访谈"},
                    {"n": "播报", "v": "播报"},
                    {"n": "旅游", "v": "旅游"},
                    {"n": "音乐", "v": "音乐"},
                    {"n": "美食", "v": "美食"},
                    {"n": "纪实", "v": "纪实"},
                    {"n": "曲艺", "v": "曲艺"},
                    {"n": "生活", "v": "生活"},
                    {"n": "游戏互动", "v": "游戏互动"},
                    {"n": "财经", "v": "财经"},
                    {"n": "求职", "v": "求职"},
                ],
            },
            {
                "key": "area",
                "name": "地区",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "内地", "v": "内地"},
                    {"n": "港台", "v": "港台"},
                    {"n": "日韩", "v": "日韩"},
                    {"n": "欧美", "v": "欧美"},
                ],
            },
            {
                "key": "lang",
                "name": "语言",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国语", "v": "国语"},
                    {"n": "英语", "v": "英语"},
                    {"n": "粤语", "v": "粤语"},
                    {"n": "闽南语", "v": "闽南语"},
                    {"n": "韩语", "v": "韩语"},
                    {"n": "日语", "v": "日语"},
                    {"n": "其它", "v": "其它"},
                ],
            },
            {
                "key": "year",
                "name": "时间",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"},
                    {"n": "2014", "v": "2014"},
                    {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"},
                ],
            },
        ],
        "4": [
            {
                "key": "id",
                "name": "类型",
                "value": [
                    {"n": "全部", "v": "4"},
                    {"n": "国产动漫", "v": "29"},
                    {"n": "日韩动漫", "v": "32"},
                    {"n": "欧美动漫", "v": "34"},
                ],
            },
            {
                "key": "class",
                "name": "剧情",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "情感", "v": "情感"},
                    {"n": "科幻", "v": "科幻"},
                    {"n": "热血", "v": "热血"},
                    {"n": "推理", "v": "推理"},
                    {"n": "搞笑", "v": "搞笑"},
                    {"n": "冒险", "v": "冒险"},
                    {"n": "萝莉", "v": "萝莉"},
                    {"n": "校园", "v": "校园"},
                    {"n": "动作", "v": "动作"},
                    {"n": "机战", "v": "机战"},
                    {"n": "运动", "v": "运动"},
                    {"n": "战争", "v": "战争"},
                    {"n": "少年", "v": "少年"},
                    {"n": "少女", "v": "少女"},
                    {"n": "社会", "v": "社会"},
                    {"n": "原创", "v": "原创"},
                    {"n": "亲子", "v": "亲子"},
                    {"n": "益智", "v": "益智"},
                    {"n": "励志", "v": "励志"},
                    {"n": "其他", "v": "其他"},
                ],
            },
            {
                "key": "area",
                "name": "地区",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国产", "v": "国产"},
                    {"n": "日本", "v": "日本"},
                    {"n": "欧美", "v": "欧美"},
                    {"n": "其他", "v": "其他"},
                ],
            },
            {
                "key": "lang",
                "name": "语言",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国语", "v": "国语"},
                    {"n": "英语", "v": "英语"},
                    {"n": "粤语", "v": "粤语"},
                    {"n": "闽南语", "v": "闽南语"},
                    {"n": "韩语", "v": "韩语"},
                    {"n": "日语", "v": "日语"},
                    {"n": "其它", "v": "其它"},
                ],
            },
            {
                "key": "year",
                "name": "时间",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"},
                    {"n": "2014", "v": "2014"},
                    {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"},
                ],
            },
        ],
    }
