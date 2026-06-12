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
BILI_COOKIE = "buvid3=4E34D04A-B8A7-11B8-41B9-4882772EDAA804187infoc; buvid4=FB3F71D3-5B19-03D6-014E-147DD7955F8205858-026060413-d6KEpP6GSI8PoxwPM1r0fWP1WrabMS0FFsxjT4boXPdTlrN6Q549BmTm1l/IyZW/; SESSDATA=68ac72a2%2C1796104822%2C12ce6%2A61CjC1im6DizDyiRgT4nNtoadrvUiNB4mKYO4OJvRDvCrM7_ixQ8G-EZ_CBdP-ZimKeY8SVjdra0JhVGc5LU5VOVVIc2g4Z2pZX1ZLRTBqb1FVb2l0Z24wTW5qTTNtRXlkT1JCeEswZEtsSWtjTS1JNUNJRXBoTUdVRVh4bW9Hd1FMVlRoUVJnbzl3IIEC"

BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
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
						"vod_year": item.get("vod_year", ""),
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
				"vod_year": item.get("vod_year", ""),
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
# 本地测试
if __name__ == "__main__":
    spider = Spider()
    spider.init()
    
    # 测试详情页解析
    detail_result = spider.detailContent(["1001"])
    if detail_result['list']:
        detail = detail_result['list'][0]
        print(f"视频名称: {detail.get('vod_name', '未知')}")
    
    # 测试搜索功能
    search_result = spider.searchContent("仙逆", False, 1)
    print(f"搜索结果数量: {len(search_result['list'])}")
    
    # 测试播放功能
    play_result = spider.playerContent("", "BV1Y64y1B7QC+759583821+380829295", {})
    print(f"播放URL: {play_result.get('url', '')}")