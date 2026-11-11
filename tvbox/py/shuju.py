# coding=utf-8
#!/usr/bin/python
from base.spider import Spider
import json
import re

# B站 Cookie，在此填写
BILI_COOKIE = "buvid3=69EF021A-E6AF-074A-CDD0-3F16F212A02166196infoc; b_nut=1794356863; buvid4=B1320198-0465-EE64-24DD-D2C510FB76FG66196-026111108-d6KEpP6GSI8PoxwPM1r0fZy%2F%2BrpZo87G%2FndnwDRnxiPvPqKILr%2BIPQnxIC8AImDi; buvid_fp=cfde7dd03a07bd9a45a390cb40e87cfb; _uuid=F9543FE8-A2DA-7B48-C8CE-7197A16109F1C66806infoc; home_feed_column=5; user_site=CN; SESSDATA=f659e431%2C1809915641%2C51483%2Ab1CjCziUuQcrlBT-BhlLg1gqAxDHq0YuyCdrPCNT6vsfvdRu6zWbTIqRZONvZEPGurS3ISVm5XUU9RS0RPeV9qTGRxQXRNNnY4WHMxU2gyUzUyMVlwZkNURE1SeVB4Q1RZclBkaTRpWEpvaUkzSnJaeURfRHc3aU9oRjM2MG95bXpPSlR0TENrR1V3IIEC; bili_jct=3a40ba68ca92b5af6448121bfef78ff4; DedeUserID=406729104; DedeUserID__ckMd5=fbc1bebe77240e2c; default_sites=%5B%22CN%22%2C%22OVERSEAS%22%5D; CURRENT_QUALITY=0; rpdid=0zbfVJIp1a|4ZMHIxqy|CCA|3w1XqXXA; CURRENT_FNVAL=2000; theme-tip-show=SHOWED; bp_t_offset_406729104=1269277683393495040; hit-dyn-v2=1; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3OTQ2Mjc0NDgsImlhdCI6MTc5NDM2ODE4OCwicGx0IjotMX0.48jkDoI_IJbhNAA1PmKQk481c4oG3nl5Tr-050pMPH0; bili_ticket_expires=1794627388; browser_resolution=1912-922"


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
        return {"list": self.homeContent(False)["list"]}

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
            apiUrl = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=80&fnval=0&platform=html5&high_quality=1"
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
                apiUrl = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=80&fnval=0&platform=html5&high_quality=1"
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