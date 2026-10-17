# -*- coding: utf-8 -*-
from urllib.parse import quote

from base.spider import Spider

XF_API_HOST = "https://xifan-api-cn.youlishipin.com"
XF_QUERY = "version=2001001&androidVersionCode=28&appId=drama"
XF_PAGE_SIZE = 30
XF_CATEGORIES = [
    ("", "推荐"),
    ("都市", "都市"),
    ("青春", "青春"),
    ("现代言情", "现代言情"),
    ("豪门", "豪门"),
    ("大女主", "大女主"),
    ("逆袭", "逆袭"),
    ("打脸虐渣", "打脸虐渣"),
    ("穿越", "穿越"),
]


class Spider(Spider):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36",
            "appId": "drama",
        }

    def getName(self):
        return "西饭短剧"

    def init(self, extend=""):
        return

    def homeContent(self, filter):
        return {"class": [{"type_id": tid, "type_name": name} for tid, name in XF_CATEGORIES]}

    def homeVideoContent(self):
        return {"list": self._listing("", 1)["list"]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1
        return self._listing(tid, page)

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        url = (f"{XF_API_HOST}/xifan/search/getSearchList?reqType=search"
               f"&offset={(page - 1) * XF_PAGE_SIZE}&keyword={quote(key)}&{XF_QUERY}")
        return {"list": self._extract_cards(self._request(url)), "pagecount": 1}

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        duanjuId, _, source = str(ids[0]).partition("#")
        url = f"{XF_API_HOST}/xifan/drama/getDuanjuInfo?duanjuId={duanjuId}&source={source}&{XF_QUERY}"
        data = self._request(url)
        if not data:
            return {"list": []}
        episodes = []
        for index, item in enumerate(data.get("episodeList") or [], start=1):
            playUrl = item.get("playUrl")
            if not playUrl:
                continue
            episodes.append(f"第{item.get('index', index)}集${playUrl}")
        vod = {
            "vod_id": f"{duanjuId}#{source}",
            "vod_name": data.get("title", ""),
            "vod_pic": data.get("coverImageUrl", ""),
            "vod_remarks": f"共{data.get('total', '')}集",
            "vod_content": data.get("desc", ""),
            "vod_play_from": "西饭短剧",
            "vod_play_url": "#".join(episodes),
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": self._resolve_url(id), "header": {"User-Agent": self.headers["User-Agent"]}}

    def isVideoFormat(self, url):
        return any(ext in str(url).lower() for ext in (".m3u8", ".mp4", ".ts"))

    def manualVideoCheck(self):
        return False

    def _listing(self, tid, page):
        offset = (page - 1) * XF_PAGE_SIZE
        url = f"{XF_API_HOST}/xifan/drama/portalPage?reqType=aggregationPage&offset={offset}"
        if tid:
            url += f"&categoryNames={quote(tid)}"
        url += f"&pageID=page_theater&{XF_QUERY}"
        data = self._request(url)
        hasMore = bool((data or {}).get("hasMore"))
        return {
            "list": self._extract_cards(data),
            "page": page,
            "pagecount": page + 1 if hasMore else page,
            "limit": XF_PAGE_SIZE,
        }

    def _extract_cards(self, data):
        cards = []
        for element in (data or {}).get("elements") or []:
            for content in element.get("contents") or []:
                vo = content.get("duanjuVo")
                if not vo:
                    continue
                duanjuId = vo.get("duanjuId")
                if not duanjuId:
                    continue
                cards.append({
                    "vod_id": f"{duanjuId}#{vo.get('source', '')}",
                    "vod_name": vo.get("title", ""),
                    "vod_pic": vo.get("coverImageUrl", ""),
                    "vod_remarks": f"共{vo.get('total', '')}集",
                })
        return cards

    def _request(self, url):
        try:
            rsp = self.fetch(url, headers=self.headers, timeout=10)
        except Exception as e:
            print(f"西饭请求异常: {url} {e}")
            return None
        if rsp.status_code != 200:
            print(f"西饭响应异常: {rsp.status_code} {url}")
            return None
        try:
            body = rsp.json()
        except Exception:
            return None
        if body.get("ret"):
            print(f"西饭接口错误: ret={body.get('ret')} {url}")
            return None
        return body.get("result")

    def _resolve_url(self, url):
        if not str(url).startswith("http"):
            return url
        try:
            rsp = self.fetch(url, headers=self.headers, timeout=10, stream=True)
            final = rsp.url
            rsp.close()
            return final
        except Exception as e:
            print(f"西饭解析跳转异常: {e}")
            return url
