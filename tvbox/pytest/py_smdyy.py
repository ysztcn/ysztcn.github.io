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
    host = "https://www.smdyy.cc"

    header = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Referer": host,
    }

    filterConfig = {}

    # filterConfig={
    #     "1":[{"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"喜剧","v":"喜剧"},{"n":"爱情","v":"爱情"},{"n":"恐怖","v":"恐怖"},{"n":"动作","v":"动作"},{"n":"科幻","v":"科幻"},{"n":"剧情","v":"剧情"},{"n":"战争","v":"战争"},{"n":"警匪","v":"警匪"},{"n":"犯罪","v":"犯罪"},{"n":"动画","v":"动画"},{"n":"奇幻","v":"奇幻"},{"n":"武侠","v":"武侠"},{"n":"冒险","v":"冒险"},{"n":"枪战","v":"枪战"},{"n":"恐怖","v":"恐怖"},{"n":"悬疑","v":"悬疑"},{"n":"惊悚","v":"惊悚"},{"n":"经典","v":"经典"},{"n":"青春","v":"青春"},{"n":"文艺","v":"文艺"},{"n":"微电影","v":"微电影"},{"n":"古装","v":"古装"},{"n":"历史","v":"历史"},{"n":"运动","v":"运动"},{"n":"农村","v":"农村"},{"n":"儿童","v":"儿童"},{"n":"网络电影","v":"网络电影"}]},{"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"大陆","v":"大陆"},{"n":"香港","v":"香港"},{"n":"台湾","v":"台湾"},{"n":"美国","v":"美国"},{"n":"法国","v":"法国"},{"n":"英国","v":"英国"},{"n":"日本","v":"日本"},{"n":"韩国","v":"韩国"},{"n":"德国","v":"德国"},{"n":"泰国","v":"泰国"},{"n":"印度","v":"印度"},{"n":"意大利","v":"意大利"},{"n":"西班牙","v":"西班牙"},{"n":"加拿大","v":"加拿大"},{"n":"其他","v":"其他"}]},{"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"}]},{"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits"},{"n":"评分","v":"score"}]}],
    #     "2":[{"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"古装","v":"古装"},{"n":"战争","v":"战争"},{"n":"青春偶像","v":"青春偶像"},{"n":"喜剧","v":"喜剧"},{"n":"家庭","v":"家庭"},{"n":"犯罪","v":"犯罪"},{"n":"动作","v":"动作"},{"n":"奇幻","v":"奇幻"},{"n":"剧情","v":"剧情"},{"n":"历史","v":"历史"},{"n":"经典","v":"经典"},{"n":"乡村","v":"乡村"},{"n":"情景","v":"情景"},{"n":"商战","v":"商战"},{"n":"网剧","v":"网剧"},{"n":"其他","v":"其他"}]},{"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"内地","v":"内地"},{"n":"韩国","v":"韩国"},{"n":"香港","v":"香港"},{"n":"台湾","v":"台湾"},{"n":"日本","v":"日本"},{"n":"美国","v":"美国"},{"n":"泰国","v":"泰国"},{"n":"英国","v":"英国"},{"n":"新加坡","v":"新加坡"},{"n":"其他","v":"其他"}]},{"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"},{"n":"2009","v":"2009"},{"n":"2008","v":"2008"},{"n":"2006","v":"2006"},{"n":"2005","v":"2005"},{"n":"2004","v":"2004"}]},{"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits"},{"n":"评分","v":"score"}]}],
    #     "3":[{"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"选秀","v":"选秀"},{"n":"情感","v":"情感"},{"n":"访谈","v":"访谈"},{"n":"播报","v":"播报"},{"n":"旅游","v":"旅游"},{"n":"音乐","v":"音乐"},{"n":"美食","v":"美食"},{"n":"纪实","v":"纪实"},{"n":"曲艺","v":"曲艺"},{"n":"生活","v":"生活"},{"n":"游戏互动","v":"游戏互动"},{"n":"财经","v":"财经"},{"n":"求职","v":"求职"}]},{"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"内地","v":"内地"},{"n":"港台","v":"港台"},{"n":"日韩","v":"日韩"},{"n":"欧美","v":"欧美"}]},{"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"},{"n":"2009","v":"2009"},{"n":"2008","v":"2008"},{"n":"2007","v":"2007"},{"n":"2006","v":"2006"},{"n":"2005","v":"2005"},{"n":"2004","v":"2004"}]},{"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits"},{"n":"评分","v":"score"}]}],
    #     "4":[{"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"情感","v":"情感"},{"n":"科幻","v":"科幻"},{"n":"热血","v":"热血"},{"n":"推理","v":"推理"},{"n":"搞笑","v":"搞笑"},{"n":"冒险","v":"冒险"},{"n":"萝莉","v":"萝莉"},{"n":"校园","v":"校园"},{"n":"动作","v":"动作"},{"n":"机战","v":"机战"},{"n":"运动","v":"运动"},{"n":"战争","v":"战争"},{"n":"少年","v":"少年"},{"n":"少女","v":"少女"},{"n":"社会","v":"社会"},{"n":"原创","v":"原创"},{"n":"亲子","v":"亲子"},{"n":"益智","v":"益智"},{"n":"励志","v":"励志"},{"n":"其他","v":"其他"}]},{"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"国产","v":"国产"},{"n":"日本","v":"日本"},{"n":"欧美","v":"欧美"},{"n":"其他","v":"其他"}]},{"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"},{"n":"2009","v":"2009"},{"n":"2008","v":"2008"},{"n":"2007","v":"2007"},{"n":"2006","v":"2006"},{"n":"2005","v":"2005"},{"n":"2004","v":"2004"}]},{"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits"},{"n":"评分","v":"score"}]}]
    # }

    def getName(self):
        return "smdyy"

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
        cateManual = {"电影": "1", "电视剧": "2", "综艺": "3", "动漫": "4", "日韩剧": "15", "欧美剧": "16"}
        classes = []
        for k in cateManual:
            classes.append({"type_name": k, "type_id": cateManual[k]})

        result["class"] = classes
        result["filters"] = self.filterConfig

        rsp = self.fetch(self.host, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("ul.stui-vodlist:not(:last-child) a.stui-vodlist__thumb")
        videos = []
        for vod in vodList:
            name = vod["title"]
            pic = vod["data-original"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.select("span.pic-text")[0].text
            sid = vod["href"]
            sid = self.regStr(sid, "/kan/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
            result["list"] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        if "id" not in extend.keys():
            extend["id"] = tid
        extend["page"] = pg
        filterParams = ["id", "area", "by", "class", "", "", "", "", "page", "", "", "year"]
        params = ["", "", "", "", "", "", "", "", "", "", "", ""]
        for idx in range(len(filterParams)):
            fp = filterParams[idx]
            if fp in extend.keys():
                params[idx] = extend[fp]
        suffix = "-".join(params)
        url = self.host + "/show/{0}.html".format(suffix)
        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        vodList = root.select("ul.stui-vodlist a.stui-vodlist__thumb")
        videos = []
        for vod in vodList:
            name = vod["title"]
            pic = vod["data-original"]
            pic = self.regStr(pic, "\\S*(http\\S+)")
            mark = vod.select("span.pic-text")[0].text
            sid = vod["href"]
            sid = self.regStr(sid, "/kan/(\\S+).html")
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        return {"list": videos}

    def detailContent(self, array):
        tid = array[0]
        url = self.host + "/kan/{0}.html".format(tid)
        rsp = self.fetch(url, headers=self.header)
        root = BeautifulSoup(rsp.text, "lxml")
        title = root.select("h1.title")[0].text
        pic = root.select("div.stui-content__thumb img")[0]["data-original"]
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
        for e in root.select("p.data"):
            txt = e.text
            if self.regStr(txt, "类型：([\s\S]*)") != "":
                vod["type_name"] = self.regStr(txt, "类型：([\s\S]*)").split("/")[0]
            if self.regStr(txt, "年份：([\s\S]*)") != "":
                vod["vod_year"] = self.regStr(txt, "年份：([\s\S]*)").split("/")[0]
            if self.regStr(txt, "地区：([\s\S]*)") != "":
                vod["vod_area"] = self.regStr(txt, "地区：([\s\S]*)").split("/")[0]
            if self.regStr(txt, "主演：([\s\S]*)") != "":
                vod["vod_actor"] = self.regStr(txt, "主演：([\s\S]*)").split("/")[0]
            if self.regStr(txt, "导演：([\s\S]*)") != "":
                vod["vod_director"] = self.regStr(txt, "导演：([\s\S]*)").split("/")[0]

        vod["vod_content"] = root.select("span.detail-content")[0].text
        playFrom = []
        vodHeader = root.select("div.stui-pannel h3")
        for v in vodHeader:
            playFrom.append(v.text.strip())
        vod_play_from = "$$$".join(playFrom)

        playList = []
        vodList = root.select("div.stui-pannel ul")
        for vl in vodList:
            vodItems = []
            for tA in vl.select("a"):
                href = tA["href"]
                name = tA.text
                tId = self.regStr(href, "/play/(\\S+).html")
                vodItems.append(name + "$" + tId)
            joinStr = "#".join(vodItems)
            playList.append(joinStr)
        vod_play_url = "$$$".join(playList)

        vod["vod_play_from"] = vod_play_from
        vod["vod_play_url"] = vod_play_url

        result = {"list": [vod]}
        return result

    def searchContent(self, key, quick):
        url = self.host + "/index.php/ajax/suggest?mid=1&wd={0}".format(key)
        rsp = self.fetch(url, headers=self.header)
        jo = json.loads(rsp.text)
        vodList = jo["list"]
        videos = []
        for vod in vodList:
            name = vod["name"]
            pic = vod["pic"]
            mark = ""
            sid = vod["id"]
            videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
        result = {"list": videos}
        return result

    def playerContent(self, flag, id, vipFlags):
        # https://meijuchong.cc/static/js/playerconfig.js
        result = {}
        url = self.host + "/play/{0}.html".format(id)
        result["parse"] = "1"
        targetUrl = url

        try:
            rsp = self.fetch(url, headers=self.header)
            mJson = json.loads(self.regStr(rsp.text, "player_.*=(\{.+?\})<"))
            rsp = self.fetch(
                self.host
                + "/static/js/playerconfig.js?smdyy={0}".format(
                    datetime.date.today().strftime("%y%M%d")
                )
            )
            pcJson = json.loads(self.regStr(rsp.text, "player_list*=(\{.+?\}),MacPlayerConfig"))
            targetUrl = pcJson[mJson["from"]]["parse"] + mJson["url"]

            rsp = self.fetch(targetUrl, headers=self.header)
            params = {
                "url": self.regStr(rsp.text, '"url":.*"(.*?)"'),
                "vkey": self.regStr(rsp.text, '"vkey":.*"(.*?)"'),
                "token": self.regStr(rsp.text, '"token":.*"(.*?)"'),
                "sign": "smdyycc",
            }
            nheader = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
                "Orgin": pcJson[mJson["from"]]["parse"].split("/player/")[0],
            }
            rsp = self.post(
                pcJson[mJson["from"]]["parse"][0 : pcJson[mJson["from"]]["parse"].rfind("/")]
                + "/xinapi.php",
                params,
                headers=nheader,
            )
            targetUrl = json.loads(rsp.text)["url"]
            targetUrl = str(base64.b64decode(targetUrl[8:])[8:-8], encoding="utf8")
            result["parse"] = "0"
        except:
            pass

        result["playUrl"] = ""
        result["url"] = targetUrl
        result["header"] = ""

        return result

    def localProxy(self, param):
        action = []
        return [200, "video/MP2T", action, ""]
