# coding=utf-8
#!/usr/bin/python
import sys
from pathlib import Path
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))  
from base.spider import Spider
import json
import re

# B站 Cookie，在此填写
BILI_COOKIE = "buvid3=28CF2858-57A1-39EF-4904-B9446403809014396infoc; buvid4=8727877A-29D8-B89B-867E-F8B919844F8116137-025121208-d6KEpP6GSI8PoxwPM1r0fScF/7fVbqf5OSncOOIzA8E/HkvSb3iaU75qiXKpxtS9; SESSDATA=66fff173%2C1792201186%2C7a3b3%2A41CjDTlCf_aFK4Y9DKanlLazUz9fGbDuznHwuH45X3q0Z_GhScFLoBG3Z_sHwoxtcOcZUSVndmNXFaYXlxX1ZxaE12cFNvU2ViS0ZObEJtNzFmcVpUckIxZllsX19tc1FlMW5hNDd5QmpQYk44c1IzcVY5T2haV2wxV3hvbW92R2ZHVkZLdnpfX1J3IIEC; DedeUserID=406729104; DedeUserID__ckMd5=fbc1bebe77240e2c"

BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}
if BILI_COOKIE:
    BILI_HEADERS["Cookie"] = BILI_COOKIE


class Spider(Spider):
    def getName(self):
        return "本地数据2"

    def init(self, extend=""):
        self.dataUrl = "https://www.yszt.dpdns.org/tvbox/shuju/"
        #self.dataUrl = "http://10.1.0.10:8000/tvbox/shuju/"	
    

    def _fetchJson(self, path):
        url = self.dataUrl + path
        rsp = self.fetch(url)
        if rsp.status_code == 200:
            return rsp.json()
        return None
            

    def homeContent(self, filter):
        data = self._fetchJson("class.json")
        if not data:
            return {"class": [], "list": []}
        result = {"class": data.get("class", []), "list": []}
        if "list" in data:
            for item in data["list"]:
                result["list"].append(
                    {
                        "vod_id": item.get("vod_id"),
                        "vod_name": item.get("vod_name"),
                        "vod_pic": item.get("vod_pic", ""),
                        "vod_remarks": item.get("vod_remarks", ""),
                        "vod_play_from": item.get("vod_play_from", ""),
                    }
                )
        return result

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        data = self._fetchJson(f"{tid}.json")
        if not data:
            return {"page": 1, "pagecount": 1, "limit": 20, "total": 0, "list": []}
        listData = data.get("list", [])
        vodList = [
            {
                "vod_id": item.get("vod_id"),
                "vod_name": item.get("vod_name"),
                "vod_pic": item.get("vod_pic", ""),
                "vod_remarks": item.get("vod_remarks", ""),
                "vod_score": item.get("vod_score", ""),
            }
            for item in listData
        ]
        return {
            "page": data.get("page", 1),
            "pagecount": data.get("pagecount", 1),
            "limit": data.get("limit", 20),
            "total": data.get("total", len(listData)),
            "list": vodList,
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        data = self._fetchJson(f"{ids[0]}.json")
        if not data:
            return {"list": []}
        listData = data.get("list", [])
        if not listData:
            return {"list": []}
        item = listData[0]
        return {
            "list": [
                {
                    "vod_id": item.get("vod_id"),
                    "vod_name": item.get("vod_name"),
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_director": item.get("vod_director", ""),
                    "vod_actor": item.get("vod_actor", ""),
                    "vod_content": item.get("vod_des", ""),
                    "vod_blurb": item.get("vod_blurb", ""),
                    "vod_remarks": item.get("vod_remarks", ""),
                    "vod_pubdate": item.get("vod_pubdate", ""),
                    "vod_year": item.get("vod_year", ""),
                    "vod_area": item.get("vod_area", ""),
                    "vod_lang": item.get("vod_lang", ""),
                    "vod_play_from": item.get("vod_play_from", ""),
                    "vod_play_url": item.get("vod_play_url", ""),
                }
            ]
        }

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"url": "", "parse": 0}

        if id.startswith("BV"):
            bvid, aid, cid = id.split("+")[:3]
            apiUrl = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=80&fnval=0"
            rsp = self.fetch(apiUrl, headers=BILI_HEADERS)
            if rsp.status_code == 200:
                playData = rsp.json()
                if playData.get("code") == 0:
                    durls = playData["data"].get("durl", [])
                    if durls:
                        return {"url": durls[0]["url"], "parse": 0, "header": BILI_HEADERS}
            return {"url": "", "parse": 0}
        
        
        if id.startswith("https://www.bilibili.com/video/"):
            bvid = id.split("/video/")[-1].split("/")[0].split("?")[0]
            apiUrl = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            rsp = self.fetch(apiUrl, headers=BILI_HEADERS)
            if rsp.status_code == 200:
                playData = rsp.json()
                aid = playData["data"]["aid"]
                cid = playData["data"]["cid"]
                apiUrl = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=80&fnval=0"
                rsp = self.fetch(apiUrl, headers=BILI_HEADERS)
                if rsp.status_code == 200:
                    playData = rsp.json()
                    if playData.get("code") == 0:
                        durls = playData["data"].get("durl", [])
                        if durls:
                            return {"url": durls[0]["url"], "parse": 0, "header": BILI_HEADERS}
            return {"url": "", "parse": 0}
            
        return {"url": "", "parse": 0}
        
    def searchContent(self, key, quick, pg="1"):
        return {"list": []}