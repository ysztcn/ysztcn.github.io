# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import re
import time
from urllib.parse import quote

from base.spider import Spider

# 七猫短剧接口签名常量（App 端写死，接口变更时需同步更新）
QM_KEYS = "d3dGiJc651gSQ8w1"
QM_STORE_HOST = "https://api-store.qmplaylet.com"
QM_READ_HOST = "https://api-read.qmplaylet.com"
QM_SEARCH_TRACK_ID = "ec1280db127955061754851657967"
QM_CHAR_MAP = {
    '+': 'P', '/': 'X', '0': 'M', '1': 'U', '2': 'l', '3': 'E', '4': 'r', '5': 'Y',
    '6': 'W', '7': 'b', '8': 'd', '9': 'J', 'A': '9', 'B': 's', 'C': 'a', 'D': 'I',
    'E': '0', 'F': 'o', 'G': 'y', 'H': '_', 'I': 'H', 'J': 'G', 'K': 'i', 'L': 't',
    'M': 'g', 'N': 'N', 'O': 'A', 'P': '8', 'Q': 'F', 'R': 'k', 'S': '3', 'T': 'h',
    'U': 'f', 'V': 'R', 'W': 'q', 'X': 'C', 'Y': '4', 'Z': 'p', 'a': 'm', 'b': 'B',
    'c': 'O', 'd': 'u', 'e': 'c', 'f': '6', 'g': 'K', 'h': 'x', 'i': '5', 'j': 'T',
    'k': '-', 'l': '2', 'm': 'z', 'n': 'S', 'o': 'Z', 'p': '1', 'q': 'V', 'r': 'v',
    's': 'j', 't': 'Q', 'u': '7', 'v': 'D', 'w': 'w', 'x': 'n', 'y': 'L', 'z': 'e',
}


class Spider(Spider):
    def __init__(self):
        self.qmHeader = None
        self.qmHeaderTime = 0

    def getName(self):
        return "七猫短剧"

    def init(self, extend=""):
        return

    def homeContent(self, filter):
        result = {"class": []}
        data = self._request(self._index_url("0"))
        seen = set()
        for tag in (data or {}).get("tag_items") or []:
            if len(result["class"]) >= 20:
                break
            tagId = str(tag.get("tag_id", ""))
            tagName = tag.get("tag_name", "")
            if not tagId or not tagName or tagId in seen:
                continue
            seen.add(tagId)
            result["class"].append({"type_id": tagId, "type_name": tagName})
        return result

    def homeVideoContent(self):
        return {"list": self._index_list("0")}

    def categoryContent(self, tid, pg, filter, extend):
        return {"list": self._index_list(tid or "0"), "pagecount": 1}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        sign = self._md5(f"extend=page={page}read_preference=0track_id={QM_SEARCH_TRACK_ID}wd={key}{QM_KEYS}")
        url = (f"{QM_STORE_HOST}/api/v1/playlet/search?extend=&page={page}&wd={quote(key)}"
               f"&read_preference=0&track_id={QM_SEARCH_TRACK_ID}&sign={sign}")
        data = self._request(url)
        cards = []
        for item in (data or {}).get("list") or []:
            playletId = str(item.get("playlet_id") or item.get("id") or "")
            if not playletId:
                continue
            cards.append({
                "vod_id": playletId,
                "vod_name": self._stripHtml(item.get("title", "")),
                "vod_pic": item.get("image_link", ""),
                "vod_remarks": item.get("sub_title", "") or item.get("total_num", ""),
            })
        return {"list": cards, "pagecount": 1}

    def detailContent(self, ids):
        playletId = str(ids[0]) if ids else ""
        sign = self._md5(f"playlet_id={playletId}{QM_KEYS}")
        data = self._request(f"{QM_READ_HOST}/player/api/v1/playlet/info?playlet_id={playletId}&sign={sign}")
        if not data:
            return {"list": []}
        episodes = []
        for index, item in enumerate(data.get("play_list") or [], start=1):
            videoUrl = item.get("video_url")
            if not videoUrl:
                continue
            episodes.append(f"第{index}集${videoUrl}")
        vod = {
            "vod_id": playletId,
            "vod_name": data.get("title", ""),
            "vod_pic": data.get("image_link", ""),
            "vod_remarks": f"共{data.get('total_episode_num', '')}集",
            "vod_content": data.get("intro", ""),
            "vod_play_from": "七猫短剧",
            "vod_play_url": "#".join(episodes),
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id, "header": {"User-Agent": "webviewversion/0"}}

    def isVideoFormat(self, url):
        return any(ext in str(url).lower() for ext in (".m3u8", ".mp4", ".ts"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.qmHeader = None

    def _index_url(self, tagId):
        sign = self._md5(f"operation=1playlet_privacy=1tag_id={tagId}{QM_KEYS}")
        return f"{QM_STORE_HOST}/api/v1/playlet/index?tag_id={tagId}&playlet_privacy=1&operation=1&sign={sign}"

    def _index_list(self, tagId):
        data = self._request(self._index_url(tagId))
        cards = []
        for item in (data or {}).get("list") or []:
            playletId = str(item.get("playlet_id", ""))
            if not playletId:
                continue
            cards.append({
                "vod_id": playletId,
                "vod_name": self._stripHtml(item.get("title", "")),
                "vod_pic": item.get("image_link", ""),
                "vod_remarks": f"共{item.get('total_episode_num', '')}集",
            })
        return cards

    def _request(self, url):
        try:
            rsp = self.fetch(url, headers=self._qm_headers(), timeout=10)
        except Exception as e:
            print(f"七猫请求异常: {url} {e}")
            return None
        if rsp.status_code != 200:
            print(f"七猫响应异常: {rsp.status_code} {url}")
            return None
        try:
            body = rsp.json()
        except Exception:
            return None
        return body.get("data")

    def _qm_headers(self):
        now = int(time.time() * 1000)
        if self.qmHeader and now - self.qmHeaderTime < 300000:
            return self.qmHeader
        data = {
            "static_score": "0.8",
            "uuid": "00000000-7fc7-08dc-0000-000000000000",
            "device-id": "20250220125449b9b8cac84c2dd3d035c9052a2572f7dd0122edde3cc42a70",
            "sourceuid": "aa7de295aad621a6",
            "refresh-type": "0",
            "model": "22021211RC",
            "client-id": "aa7de295aad621a6",
            "brand": "Redmi",
            "sys-ver": "12",
            "phone-level": "H",
            "wlb-uid": "aa7de295aad621a6",
            "session-id": str(now),
        }
        encoded = base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()
        qmParams = "".join(QM_CHAR_MAP.get(char, char) for char in encoded)
        signStr = (f"AUTHORIZATION=app-version=10001application-id=com.duoduo.readchannel=unknown"
                   f"is-white=net-env=5platform=androidqm-params={qmParams}reg={QM_KEYS}")
        self.qmHeader = {
            "net-env": "5", "reg": "", "channel": "unknown", "is-white": "",
            "platform": "android", "application-id": "com.duoduo.read", "authorization": "",
            "app-version": "10001", "user-agent": "webviewversion/0",
            "qm-params": qmParams, "sign": self._md5(signStr),
            "content-type": "application/json; charset=utf-8",
        }
        self.qmHeaderTime = now
        return self.qmHeader

    @staticmethod
    def _md5(text):
        return hashlib.md5(text.encode()).hexdigest().lower()

    @staticmethod
    def _stripHtml(text):
        return re.sub(r"<[^>]+>", "", str(text or ""))
