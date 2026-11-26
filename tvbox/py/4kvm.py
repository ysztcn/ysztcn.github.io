import base64
import hashlib
import hmac
import json
import re
import time
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote

import requests
from pyquery import PyQuery as pq

from base.spider import Spider


class Spider(Spider):
  siteKey = "4kvm"
  baseUrl = "https://www.4kvms.org"

  _headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0",
    "Referer": "https://www.4kvms.org/",
  }

  _session = None

  def _get_session(self):
    if self._session is None:
      self._session = requests.Session()
      self._session.headers.update(self._headers)
    return self._session

  categories = {
    "1": ("/movie", "电影"),
    "2": ("/tv", "电视剧"),
    "3": ("/anime", "动漫"),
  }

  _areaOptions = [
    {"n": "--", "v": ""},
    {"n": "美国", "v": "5"},
    {"n": "法国", "v": "6"},
    {"n": "中国", "v": "7"},
    {"n": "日本", "v": "11"},
    {"n": "韩国", "v": "12"},
    {"n": "中国香港", "v": "14"},
    {"n": "俄罗斯", "v": "16"},
    {"n": "波兰", "v": "17"},
    {"n": "德国", "v": "18"},
    {"n": "意大利", "v": "19"},
    {"n": "中国台湾", "v": "21"},
    {"n": "澳大利亚", "v": "22"},
    {"n": "西班牙", "v": "24"},
    {"n": "英国", "v": "30"},
    {"n": "加拿大", "v": "32"},
    {"n": "泰国", "v": "33"},
    {"n": "印度", "v": "34"},
    {"n": "丹麦", "v": "41"},
    {"n": "中国大陆", "v": "52"},
    {"n": "马来西亚", "v": "65"},
    {"n": "菲律宾", "v": "74"},
    {"n": "瑞典", "v": "79"},
    {"n": "挪威", "v": "80"},
    {"n": "阿根廷", "v": "81"},
    {"n": "冰岛", "v": "82"},
    {"n": "保加利亚", "v": "83"},
    {"n": "爱尔兰", "v": "84"},
    {"n": "墨西哥", "v": "86"},
  ]

  _typeOptions = [
    {"n": "--", "v": ""},
    {"n": "剧情", "v": "1"},
    {"n": "悬疑", "v": "2"},
    {"n": "恐怖", "v": "3"},
    {"n": "惊悚", "v": "4"},
    {"n": "喜剧", "v": "5"},
    {"n": "爱情", "v": "6"},
    {"n": "犯罪", "v": "9"},
    {"n": "动作", "v": "10"},
    {"n": "动画", "v": "11"},
    {"n": "奇幻", "v": "12"},
    {"n": "音乐", "v": "13"},
    {"n": "科幻", "v": "14"},
    {"n": "历史", "v": "15"},
    {"n": "战争", "v": "16"},
    {"n": "冒险", "v": "18"},
    {"n": "家庭", "v": "19"},
    {"n": "纪录", "v": "20"},
    {"n": "西部", "v": "23"},
    {"n": "电视电影", "v": "24"},
    {"n": "情色", "v": "25"},
    {"n": "真人秀", "v": "26"},
    {"n": "古装", "v": "27"},
    {"n": "传记", "v": "28"},
    {"n": "同性", "v": "29"},
    {"n": "运动", "v": "30"},
    {"n": "武侠", "v": "31"},
    {"n": "歌舞", "v": "32"},
    {"n": "纪录片", "v": "33"},
    {"n": "灾难", "v": "34"},
    {"n": "短片", "v": "35"},
  ]

  _tagOptions = [
    {"n": "--", "v": ""},
    {"n": "4k", "v": "1"},
    {"n": "院线", "v": "36"},
  ]

  _sortOptions = [
    {"key": "sort", "name": "排序", "value": [
      {"n": "最新上映", "v": "latest"},
      {"n": "最受欢迎", "v": "hottest"},
      {"n": "评分最高", "v": "rating"},
    ]},
  ]

  _sortMap = {
    "latest": "sort_by=update_time&order=desc",
    "hottest": "sort_by=hits&order=desc",
    "rating": "sort_by=score&order=desc",
  }

  def init(self, extend: str = "") -> None:
    self._filterYears = None
    self._serverOffsetMs = None
    self._session = None
    if extend:
      try:
        data = json.loads(extend)
      except json.JSONDecodeError as e:
        self.log(f"4kvm ext 不是合法 JSON，忽略: {e}")
      else:
        self.baseUrl = data.get("baseUrl", self.baseUrl)
    self.baseUrl = self.baseUrl.rstrip("/")
    self._headers = dict(self._headers, Referer=f"{self.baseUrl}/")

  def _get(self, url: str, params: Optional[dict] = None) -> requests.Response:
    ses = self._get_session()
    return ses.get(url, params=params, timeout=15)

  def _parse_list(self, html: str) -> list:
    doc = pq(html)
    result = []
    for card in doc(".movie-card").items():
      vodId = card.attr("data-vod-id")
      if not vodId:
        continue
      title = card("a h3, h3").eq(0).text().strip()
      img = card("img.lazy")
      pic = img.attr("data-src") or img.attr("src") or ""
      remark = ""
      epSpan = card("span.absolute.bottom-0, .aspect-\\[2\\/3\\] > span")
      if epSpan:
        epText = epSpan.text().strip()
        if epText and ("集" in epText or "更新" in epText):
          remark = epText
      result.append({
        "vod_id": vodId,
        "vod_name": title,
        "vod_pic": pic,
        "vod_remarks": remark,
      })
    return result

  def _extract_episodes(self, doc, userlink: str = "") -> list:
    episodes = []
    seenIds = set()
    # 剧集链接带 dataid（worker 的 play_id）；页面其他位置的 /play/ 链接是相关推荐，
    # 没有 dataid，混入选集会导致点开取不到播放地址
    links = doc("a.episode-link").items()
    if not doc("a.episode-link"):
      links = doc("a[href^='/play/'][dataid]").items()
    for epLink in links:
      href = epLink.attr("href")
      dataid = epLink.attr("dataid") or ""
      if not href or not dataid:
        continue
      epVodId = href.split("/play/")[-1].split("?")[0]
      if not epVodId or epVodId in seenIds:
        continue
      seenIds.add(epVodId)
      epName = epLink.text().strip()
      if not epName or len(epName) > 5:
        epName = f"第{len(episodes)+1}集"
      episodes.append(f"{epName}$4kvm://{dataid}|{userlink}{href}")
    return episodes

  def _scrapeFilterOptions(self) -> list:
    if self._filterYears is not None:
      return self._filterYears
    html = self._get(f"{self.baseUrl}/filter?classify=1").text
    doc = pq(html)
    result = [{"n": "--", "v": ""}]
    for a in doc("a[href*='years=']").items():
      href = a.attr("href")
      text = a.text().strip()
      if not href or not text.isdigit():
        continue
      m = re.search(r"years=(\d+)", href)
      if m:
        result.append({"n": text, "v": m.group(1)})
    self._filterYears = result
    return self._filterYears

  def homeContent(self, filter: bool) -> dict:
    classes = []
    for tid, (path, name) in self.categories.items():
      classes.append({
        "type_id": tid,
        "type_name": name,
      })
    result = {"class": classes}
    if filter:
      result["filters"] = self._get_filters()
    return result

  def _get_filters(self) -> dict:
    filters = {}
    yearOptions = self._scrapeFilterOptions()
    for tid in self.categories:
      filters[tid] = [
        {"key": "areas", "name": "地区", "value": self._areaOptions},
        {"key": "types", "name": "类型", "value": self._typeOptions},
        {"key": "years", "name": "年份", "value": yearOptions},
        {"key": "tags", "name": "标签", "value": self._tagOptions},
        self._sortOptions[0],
      ]
    return filters

  def homeVideoContent(self) -> dict:
    html = self._get(self.baseUrl).text
    result = self._parse_list(html)
    return {"list": result}

  def categoryContent(self, tid: str, pg: str, filter: bool, extend: dict) -> dict:
    if tid not in self.categories:
      return {"list": [], "pagecount": 0}
    query = {"classify": tid}
    for key in ("areas", "types", "years", "tags"):
      val = extend.get(key, "")
      if val:
        query[key] = val
    sortVal = extend.get("sort", "")
    if sortVal and sortVal in self._sortMap:
      for part in self._sortMap[sortVal].split("&"):
        k, v = part.split("=", 1)
        query[k] = v
    if pg and pg != "1":
      query["page"] = pg
    resp = self._get(f"{self.baseUrl}/filter", params=query)
    if not resp.text.strip():
      self.log(f"4kvm 分类页返回空内容: {resp.url}")
    html = resp.text
    result = self._parse_list(html)
    return {"list": result, "pagecount": self._parse_pagecount(html)}

  @staticmethod
  def _parse_pagecount(html: str) -> int:
    # 分页控件里带 page=N 的链接，最大 N 即总页数
    pages = [int(p) for p in re.findall(r"page=(\d+)", html)]
    return max(pages) if pages else 1

  def detailContent(self, ids: list) -> dict:
    if not ids:
      return {"list": []}
    vodId = ids[0]
    url = f"{self.baseUrl}/play/{vodId}"
    html = self._get(url).text
    doc = pq(html)

    title = ""
    h1 = doc("h1").eq(0)
    if h1:
      title = h1.text().strip()

    pic = doc(".video-player").attr("data-poster") or ""
    if not pic:
      pic = doc('meta[property="og:image"]').attr("content") or ""

    desc = doc('meta[property="og:description"]').attr("content") or ""
    keywords = doc('meta[name="keywords"]').attr("content") or ""
    kws = [k.strip() for k in keywords.split(",")] if keywords else []

    year = ""
    score = ""

    for kw in kws:
      if re.match(r"^\d{4}$", kw):
        year = kw

    for item in doc("span.text-primary-400, span.bg-primary-500\\/20, span.text-yellow-400").items():
      text = item.text().strip()
      if re.match(r"^\d+\.?\d*$", text):
        score = text
        break

    # 详情信息是「标签 div + 值 div」成对的网格，用相邻节点取值
    infoMap = {}
    for labelNode in doc("div.text-gray-500").items():
      label = labelNode.text().strip()
      if label in ("导演", "主演", "类型", "地区"):
        valueNode = labelNode.next(".text-gray-300")
        if valueNode:
          infoMap[label] = valueNode.text().strip()

    director = infoMap.get("导演", "")
    actor = infoMap.get("主演", "")
    typeNames = infoMap.get("类型", "")
    area = infoMap.get("地区", "")

    userlink = ""
    mUl = re.search(r"userlink:\s*'([^']+)'", html)
    if mUl:
      userlink = mUl.group(1)

    episodes = self._extract_episodes(doc, userlink)

    vod = {
      "vod_id": vodId,
      "vod_name": title,
      "vod_pic": pic,
      "vod_content": desc,
      "vod_year": year,
      "vod_score": score,
      "vod_area": area,
      "vod_actor": actor,
      "vod_director": director,
      "vod_class": typeNames,
    }
    if episodes:
      vod["vod_play_from"] = "4kvm"
      vod["vod_play_url"] = "#".join(episodes)
    return {"list": [vod]}

  def searchContent(self, key: str, quick: bool, pg: str = "1") -> dict:
    # 站点搜索不分页，一次返回全部结果
    html = self._get(f"{self.baseUrl}/search?q={quote(key)}").text
    result = self._parse_search(html)
    return {"list": result, "pagecount": 1}

  def _parse_search(self, html: str) -> list:
    doc = pq(html)
    result = []
    for card in doc("div.group.relative").items():
      link = card("a[href^='/play/']")
      href = link.attr("href")
      if not href:
        continue
      vodId = href.split("/play/")[-1].split("?")[0]
      if not vodId:
        continue
      title = card("h3").eq(0).text().strip()
      img = card("img.lazy")
      pic = img.attr("data-src") or img.attr("src") or ""
      year = card("div.absolute.top-2.left-2").text().strip()
      result.append({
        "vod_id": vodId,
        "vod_name": title,
        "vod_pic": pic,
        "vod_year": year,
      })
    return result

  # 站点 WASM 内的 XOR 密钥，算法见 README「4kvm 爬虫特殊说明」
  _signKey = b"nbmovie2024secretkey"

  def _server_time_ms(self) -> int:
    # /video/play 的 t 只允许与服务端时间相差约 30 秒，用响应头 Date 校正设备时钟
    if self._serverOffsetMs is None:
      offset = 0
      try:
        date = self._get(self.baseUrl).headers.get("Date")
        if date:
          offset = int(parsedate_to_datetime(date).timestamp() * 1000 - time.time() * 1000)
        else:
          self.log("4kvm 响应头缺少 Date，按本地时间签名")
      except Exception as e:
        self.log(f"4kvm 获取服务器时间失败，按本地时间签名: {e}")
      self._serverOffsetMs = offset
    return int(time.time() * 1000) + self._serverOffsetMs

  def _build_play_url(self, dataid: str, vod: str, userlink: str, quality: str = "1080") -> str:
    ts = self._server_time_ms()
    sign = hmac.new(vod.encode(), f"{dataid}:{ts}:{vod}".encode(), hashlib.sha256).hexdigest()[:32]
    key = bytes(b ^ self._signKey[i % len(self._signKey)] for i, b in enumerate(userlink.encode()))
    k = base64.urlsafe_b64encode(key).decode()
    return f"{self.baseUrl}/video/play?p={dataid}&v={vod}&q={quality}&s={sign}&t={ts}&k={k}"

  def playerContent(self, flag: str, id: str, vipFlags: list) -> dict:
    if not id:
      return {"parse": 0, "url": ""}
    # 兼容 TVBox 可能传入完整的 "剧集名$4kvm://..." 格式，使用 search 而非 match
    m = re.search(r"4kvm://([^|]*)\|(.*?)(/play/.*)", id)
    if not m:
      # 不是 4kvm 格式，按普通播放链接处理
      vid = id[len("/play/"):] if id.startswith("/play/") else id
      return {"parse": 1, "url": f"{self.baseUrl}/play/{vid}", "header": self._headers}
    dataid, userlink, path = m.group(1), m.group(2), m.group(3)
    vod = path.split("/play/")[-1].split("?")[0]
    if dataid:
      # 播放接口按请求方 IP 签发地址，必须在设备本地签名，Worker 出口 IP 不同会 403
      try:
        resp = self._get(self._build_play_url(dataid, vod, userlink))
        if resp.status_code == 200:
          data = resp.json().get("data") or {}
          urls = [
            q for q in (data.get("quality_urls") or [])
            if not q.get("locked") and str(q.get("url", "")).startswith("http")
          ]
          if urls:
            best = max(urls, key=lambda q: q.get("bitrate", 0))
            # 播放请求不带 Referer：blbtgg 系 CDN 带 Referer 直接 403
            return {"parse": 0, "url": best["url"], "header": {"User-Agent": self._headers["User-Agent"]}}
          self.log(f"4kvm 播放接口无可用地址: {resp.text[:200]}")
        else:
          self.log(f"4kvm 播放接口 {resp.status_code}: {resp.text[:200]}")
      except Exception as e:
        self.log(f"4kvm 播放接口请求失败: {e}")
    # 签名失败时退回壳内 WebView，由页面 JS 自行签名播放
    return {"parse": 1, "url": f"{self.baseUrl}{path}", "header": self._headers}
