# -*- coding: utf-8 -*-
from base.spider import Spider

# B站 Cookie，在此填写
BILI_COOKIE = "buvid3=28CF2858-57A1-39EF-4904-B9446403809014396infoc; buvid4=8727877A-29D8-B89B-867E-F8B919844F8116137-025121208-d6KEpP6GSI8PoxwPM1r0fScF/7fVbqf5OSncOOIzA8E/HkvSb3iaU75qiXKpxtS9; SESSDATA=07b2ab5c%2C1791180259%2C713c2%2A41CjC5cvdGdVeJ2ZgrOMnVjg3L4Z0rOlkYV6jDJtcfWUgTo6DO7ZAentnJckXmT14rBlgSVk9rb0xrT0tTZWtFcU5Cejd1VnlJM3NycXYzTjJaRjJLUFpXM29Tb19BLU5JUzVQZS1ETC1uTmd4czJUMDhkcjFDRGc1NFF6T1lDaFNKSUpZTzZUeUN3IIEC; bili_jct=2c6fccd901cc1c2178eeb2202a3d77ed; DedeUserID=406729104; DedeUserID__ckMd5=fbc1bebe77240e2c"

BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}
if BILI_COOKIE:
    BILI_HEADERS["Cookie"] = BILI_COOKIE


class Spider(Spider):
    def getName(self):
        return "本地数据"

    def init(self, extend=""):
        self.dataUrl = "https://www.yszt.dpdns.org/tvbox/shuju/"
		#self.dataUrl = "http://10.1.0.10:8000/tvbox/shuju/"

    def _fetchJson(self, path):
        url = self.dataUrl + path
        rsp = self.fetch(url)
        if rsp.status_code == 200:
            return rsp.json()
        return None

    def _getBiliUrl(self, url):
        bvid = url.split("/video/")[-1].split("/")[0].split("?")[0]
        apiUrl = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        rsp = self.fetch(apiUrl, headers=BILI_HEADERS)
        if rsp.status_code != 200:
            return ""
        data = rsp.json()
        if data.get("code") != 0:
            return ""
        aid = data["data"]["aid"]
        cid = data["data"]["cid"]
        playUrl = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=80&fnval=0"
        rsp2 = self.fetch(playUrl, headers=BILI_HEADERS)
        playData = rsp2.json()
        if playData.get("code") != 0:
            return ""
        durls = playData["data"].get("durl", [])
        if durls:
            return durls[0]["url"]
        return ""

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
					"vod_des": item.get("vod_des", ""),
                    "vod_actor": item.get("vod_actor", ""),
                    "vod_director": item.get("vod_director", ""),
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

        url = id.split("$")[-1] if "$" in id else id
        isBili = url.startswith("https://www.bilibili.com/video/")

        if isBili:
            realUrl = self._getBiliUrl(url)
            if realUrl:
                return {"url": realUrl, "parse": 0, "header": BILI_HEADERS}
            return {"url": "", "parse": 0}

        if not url.startswith("http"):
            data = self._fetchJson(f"{id}.json")
            if not data:
                return {"url": "", "parse": 0}
            listData = data.get("list", [])
            if not listData:
                return {"url": "", "parse": 0}
            item = listData[0]
            playFrom = item.get("vod_play_from", "")
            playUrl = item.get("vod_play_url", "")
            fromList = playFrom.split("$$$")
            urlList = playUrl.split("$$$")
            targetIndex = 0
            for i, f in enumerate(fromList):
                if f == flag:
                    targetIndex = i
                    break
            if targetIndex < len(urlList):
                urls = urlList[targetIndex].split("#")
                if urls:
                    first = urls[0]
                    url = first.split("$")[1] if "$" in first else first
                    if url.startswith("https://www.bilibili.com/video/"):
                        realUrl = self._getBiliUrl(url)
                        if realUrl:
                            return {"url": realUrl, "parse": 0, "header": BILI_HEADERS}
                        return {"url": "", "parse": 0}
                    return {"url": url, "parse": 0}
            return {"url": "", "parse": 0}

        return {"url": url, "parse": 0}

    def searchContent(self, key, quick, pg="1"):
        return {"list": []}
