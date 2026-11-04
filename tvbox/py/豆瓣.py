import re
from urllib.parse import quote

from base.spider import Spider as BaseSpider

SITE_URL = "https://frodo.douban.com/api/v2"
HOT_URL = "http://api.douban.com/api/v2/subject_collection/subject_real_time_hotest/items"
APIKEY = "?apikey=0ac44ae016490db2204ce0a042db2916"
HEADERS = {
    "Host": "frodo.douban.com",
    "Connection": "Keep-Alive",
    "Referer": "https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat",
}
TYPE_IDS = ["hot_gaia", "tv_hot", "show_hot", "movie", "tv", "rank_list_movie", "rank_list_tv"]
TYPE_NAMES = ["热门电影", "热播剧集", "热播综艺", "电影筛选", "电视筛选", "电影榜单", "电视剧榜单"]
AREAS = ["全部", "中国大陆", "美国", "日本", "韩国", "中国香港", "中国台湾"]
HOT_SORTS = {"recommend": "recommend", "time": "time", "rank": "rank"}
REC_SORTS = {"T": "T", "L": "L", "R": "R", "C": "C"}


def _option(n, v=None):
    return {"n": n, "v": v if v is not None else n}


class Spider(BaseSpider):

    def getName(self):
        return "豆瓣"

    def init(self, extend=""):
        self.extend = extend or ""
        return self

    def _get_json(self, url):
        return self.fetch(url, headers=HEADERS, timeout=10).json()

    @staticmethod
    def _pic(item):
        pic = (item.get("pic") or {}).get("normal")
        if not pic:
            pic = item.get("cover_url") or ""
            # 搜索接口返回签名临时域名，带时效参数，替换为稳定图床域名
            pic = pic.replace("qnmob3-sign.doubanio.com", "img3.doubanio.com")
        return pic

    @staticmethod
    def _rating(item):
        value = (item.get("rating") or {}).get("value")
        return "评分：" + str(value) if value is not None else ""

    @staticmethod
    def _to_vod(item):
        return {
            "vod_id": "msearch:" + str(item.get("id", "")),
            "vod_name": item.get("title") or "",
            "vod_pic": Spider._pic(item),
            "vod_year": str(item.get("year") or ""),
            "vod_remarks": Spider._rating(item),
        }

    @staticmethod
    def _parse_vod_list(items):
        return [Spider._to_vod(item) for item in items or []]

    def _load_filters(self):
        if self.extend.startswith("http"):
            try:
                return self._get_json(self.extend)
            except Exception:
                return None
        movie_sorts = [_option("recommend", "默认推荐"), _option("time", "最新上映"), _option("rank", "实时热度")]
        rec_sorts = [_option("T", "默认"), _option("L", "最新"), _option("R", "热门"), _option("C", "高分")]
        return {
            "热门电影": [
                {"key": "sort", "name": "排序", "value": movie_sorts},
                {"key": "area", "name": "地区", "value": [_option(x) for x in AREAS]},
            ],
            "热播剧集": [
                {"key": "type", "name": "榜单", "value": [_option("tv_hot", "电视剧"), _option("show_hot", "综艺")]},
            ],
            "热播综艺": [
                {"key": "type", "name": "榜单", "value": [_option("show_hot", "综艺"), _option("tv_hot", "电视剧")]},
            ],
            "电影筛选": [{"key": "sort", "name": "排序", "value": rec_sorts}],
            "电视筛选": [{"key": "sort", "name": "排序", "value": rec_sorts}],
            "电影榜单": [{"key": "榜单", "name": "榜单", "value": [_option("movie_real_time_hotest", "实时热门"), _option("movie_top250", "Top250")]}],
            "电视剧榜单": [{"key": "榜单", "name": "榜单", "value": [_option("tv_real_time_hotest", "实时热门")]}],
        }

    @staticmethod
    def _tags(extend):
        tags = ",".join(str(extend[key]) for key in sorted(extend) if key != "sort" and extend.get(key))
        return quote(tags)

    def homeContent(self, filter):
        resp = self._get_json(HOT_URL + APIKEY)
        classes = [
            {"type_id": x, "type_name": y}
            for x, y in zip(TYPE_IDS, TYPE_NAMES)
        ]
        result = {"class": classes}
        if filter:
            result["filters"] = self._load_filters()
        result["list"] = self._parse_vod_list(resp.get("subject_collection_items"))
        return result

    def homeVideoContent(self):
        resp = self._get_json(HOT_URL + APIKEY)
        return {"list": self._parse_vod_list(resp.get("subject_collection_items"))}

    def categoryContent(self, tid, pg, filter, extend):
        start = (int(pg or 1) - 1) * 20
        item_key = "items"
        if tid == "hot_gaia":
            url = "{}&start={}&count=50".format(SITE_URL + "/movie/hot_gaia" + APIKEY, start)
            sort = extend.get("sort")
            if sort in HOT_SORTS:
                url += "&sort=" + HOT_SORTS[sort]
            area = extend.get("area")
            if area and area != "全部":
                url += "&area=" + quote(area)
        elif tid in ("tv_hot", "show_hot"):
            item_key = "subject_collection_items"
            url = "{}&start={}&count=50".format(
                SITE_URL + "/subject_collection/" + (extend.get("type") or tid) + "/items" + APIKEY, start)
        elif tid == "tv":
            url = "{}&sort={}&tags={}&start={}&count=50".format(
                SITE_URL + "/tv/recommend" + APIKEY, extend.get("sort") or "T", self._tags(extend), start)
        elif tid in ("rank_list_movie", "rank_list_tv"):
            item_key = "subject_collection_items"
            rank = extend.get("榜单") or ("movie_real_time_hotest" if tid == "rank_list_movie" else "tv_real_time_hotest")
            url = "{}&start={}&count=50".format(SITE_URL + "/subject_collection/" + rank + "/items" + APIKEY, start)
        else:
            url = "{}&sort={}&tags={}&start={}&count=50".format(
                SITE_URL + "/movie/recommend" + APIKEY, extend.get("sort") or "T", self._tags(extend), start)

        resp = self._get_json(url)
        return {"list": self._parse_vod_list(resp.get(item_key)), "page": int(pg or 1)}

    @staticmethod
    def _names(people):
        result = []
        for p in people or []:
            if isinstance(p, dict):
                name = p.get("name")
                if name:
                    result.append(name)
            elif p:
                result.append(str(p))
        return result

    def detailContent(self, ids):
        vid = str(ids[0] if ids else "")
        match = re.fullmatch(r"msearch:(\d+)", vid)
        if not match:
            return {"list": []}
        resp = self._get_json(SITE_URL + "/movie/" + match.group(1) + APIKEY)
        vod = {
            "vod_id": vid,
            "vod_name": resp.get("title") or resp.get("title_alt") or "",
            "vod_pic": self._pic(resp),
            "vod_year": str(resp.get("year") or ""),
            "vod_area": "、".join(resp.get("areas") or []),
            "vod_content": (resp.get("intro") or "").strip(),
            "vod_remarks": self._rating(resp),
            "vod_actor": "、".join(self._names(resp.get("actors"))),
            "vod_director": "、".join(self._names(resp.get("directors"))),
        }
        # 豆瓣不提供播放地址，vod_play_url 留空；TVBox 对 msearch: 前缀或空剧集
        # 会按片名转搜索其他可换源站点，命中后自动切源播放
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        start = (int(pg or 1) - 1) * 20
        url = "{}&q={}&start={}&count=20&recommend_type=all&aggregated_to=subject&channel=all".format(
            SITE_URL + "/search/movie" + APIKEY, quote(str(key)), start)
        resp = self._get_json(url)
        items = []
        for it in resp.get("items") or []:
            target = it.get("target")
            if target:
                items.append(self._to_vod(target))
        return {"list": items, "page": int(pg or 1)}
