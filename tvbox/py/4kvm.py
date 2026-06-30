import json
import re
import sys
from urllib.parse import quote

import requests
from pyquery import PyQuery as pq

from base.spider import Spider


class Spider(Spider):
  siteKey = "4kvm"
  baseUrl = "https://www.4kvm.top"

  _headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0",
    "Referer": "https://www.4kvm.top/",
  }

  _session = None

  def _get_session(self):
    if self._session is None:
      self._session = requests.Session()
      self._session.headers.update(self._headers)
    return self._session

  def _log(self, msg: str):
    print(f"[4kvm-debug] {msg}", flush=True)

  _workerUrl = "https://4kvm-play.yszt.dpdns.org/api/play"

  categories = {
    "1": ("/movie", "电影"),
    "2": ("/tv", "电视剧"),
    "3": ("/anime", "动漫"),
    "4": ("/variety", "综艺"),
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
    if extend:
      try:
        data = json.loads(extend)
        self.baseUrl = data.get("baseUrl", self.baseUrl)
      except json.JSONDecodeError:
        pass

  def _get(self, url: str, params: dict = None) -> requests.Response:
    ses = self._get_session()
    return ses.get(url, params=params, timeout=15)

  def _parse_list(self, html: str) -> list:
    try:
      doc = pq(html.encode('utf-8'))
    except Exception as e:
      self._log(f"parse failed: {e}, html(len={len(html)}) repr={repr(html[:200])}")
      try:
        doc = pq(html)
      except Exception:
        return []
    result = []
    for card in doc(".movie-card").items():
      vodId = card.attr("data-vod-id")
      if not vodId:
        continue
      title = card("a h3, h3").eq(0).text().strip()
      img = card("img.lazy")
      pic = img.attr("data-src") or img.attr("src") or ""
      remark = ""
      ep_span = card("span.absolute.bottom-0, .aspect-\\[2\\/3\\] > span")
      if ep_span:
        ep_text = ep_span.text().strip()
        if ep_text and ("集" in ep_text or "更新" in ep_text):
          remark = ep_text
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
    selectors = ["a.episode-link", "a[href^='/play/']"]
    for sel in selectors:
      for ep_link in doc(sel).items():
        href = ep_link.attr("href")
        if not href:
          continue
        epVodId = href.split("/play/")[-1].split("?")[0]
        if not epVodId or epVodId in seenIds:
          continue
        seenIds.add(epVodId)
        dataid = ep_link.attr("dataid") or ""
        ep_name = ep_link.text().strip()
        if not ep_name or len(ep_name) > 5:
          ep_name = f"第{len(episodes)+1}集"
        episodes.append(f"{ep_name}$4kvm://{dataid}|{userlink}/{href}")
    return episodes

  def _scrapeFilterOptions(self) -> list:
    if hasattr(self, '_filterYears') and self._filterYears is not None:
      return self._filterYears
    try:
      html = self._get(f"{self.baseUrl}/filter?classify=1").text
      doc = pq(html)
      result = []
      for a in doc("a[href*='years=']").items():
        href = a.attr("href")
        text = a.text().strip()
        if not href or not text:
          continue
        m = re.search(r"years=(\d+)", href)
        if m and text.isdigit():
          result.append({"n": text, "v": m.group(1)})
      if result:
        result.insert(0, {"n": "--", "v": ""})
        self._filterYears = result
        return self._filterYears
    except Exception:
      pass
    self._filterYears = [{"n": "--", "v": ""}]
    return self._filterYears

  def homeContent(self, filter: bool) -> str:
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

  def homeVideoContent(self) -> str:
    html = self._get(self.baseUrl).text
    result = self._parse_list(html)
    return {"list": result}

  def categoryContent(self, tid: str, pg: str, filter: bool, extend: dict) -> str:
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
    self._log(f"url={resp.url} status={resp.status_code} len={len(resp.text)} query={query}")
    if not resp.text or not resp.text.strip():
      self._log(f"empty body! headers={dict(resp.headers)}")
    html = resp.text
    result = self._parse_list(html)
    self._log(f"parsed {len(result)} items for pg={pg}")
    return {"list": result, "pagecount": 999}

  def detailContent(self, ids: list) -> str:
    if not ids:
      return {"list": []}
    vodId = ids[0]
    url = f"{self.baseUrl}/play/{vodId}"
    html = self._get(url).text
    try:
      doc = pq(html)
    except Exception:
      return {"list": []}

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
    area = ""
    typeNames = ""
    actor = ""
    director = ""

    for kw in kws:
      if re.match(r"^\d{4}$", kw):
        year = kw

    for item in doc("span.text-primary-400, span.bg-primary-500\\/20, span.text-yellow-400").items():
      text = item.text().strip()
      if re.match(r"^\d+\.?\d*$", text):
        score = text
        break

    info_patterns = [
      ("导演", "director"),
      ("主演", "actor"),
      ("类型", "typeNames"),
      ("地区", "area"),
    ]
    for label, field in info_patterns:
      pattern = re.compile(
        r'<div[^>]*>\s*' + re.escape(label) + r'\s*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>',
        re.IGNORECASE
      )
      m = pattern.search(html)
      if m:
        val = m.group(1).strip()
        if field == "typeNames":
          typeNames = val
        elif field == "area":
          area = val
        elif field == "director":
          director = val
        elif field == "actor":
          actor = val

    userlink = ""
    m_ul = re.search(r"userlink:\s*'([^']+)'", html)
    if m_ul:
      userlink = m_ul.group(1)

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

  def searchContent(self, key: str, quick: bool, pg: str = "1") -> str:
    api_url = f"{self.baseUrl}/api/search?q={quote(key)}&page={pg}"
    try:
      resp = self._get(api_url)
      data = resp.json()
      if data.get("code") == 200:
        result = []
        total = data.get("data", {}).get("total", 0)
        for item in data.get("data", {}).get("list", []):
          result.append({
            "vod_id": str(item.get("id", "")),
            "vod_name": item.get("title", ""),
            "vod_pic": item.get("cover", ""),
            "vod_remarks": f"更新至{item.get('updated_episodes', '?')}集" if item.get("vod_total", 0) > 1 else "",
            "vod_year": str(item.get("year", "")),
            "vod_score": str(item.get("rating", "")),
          })
        pagecount = max(1, (total + 19) // 20)
        return {"list": result, "pagecount": pagecount}
    except Exception:
      pass
    html = self._get(f"{self.baseUrl}/search?q={quote(key)}").text
    result = self._parse_list(html)
    return {"list": result, "pagecount": 1}

  def playerContent(self, flag: str, id: str, vipFlags: list) -> str:
    if not id:
      return {"parse": 0, "url": ""}
    if id.startswith("4kvm://"):
      m = re.match(r"4kvm://(\d+)\|([^/]*)(/.*)", id)
      if not m:
        return {"parse": 0, "url": ""}
      dataid, userlink, path = m.group(1), m.group(2), m.group(3)
      vod = path.split("/play/")[-1].split("?")[0] if "/play/" in path else path
      params = {
        "dataid": dataid,
        "vod": vod,
        "userlink": userlink,
      }
      try:
        resp = requests.get(self._workerUrl, params=params, timeout=15)
        body = resp.json()
        if body.get("code") == 200 and body.get("data", {}).get("quality_urls"):
          self._headers["Referer"] = f"{self.baseUrl}/"
          unlocked = [q for q in body["data"]["quality_urls"] if not q.get("locked")]
          valid = unlocked if unlocked else body["data"]["quality_urls"]
          best = max(valid, key=lambda q: q.get("bitrate", 0))
          return {"parse": 0, "url": best["url"], "header": self._headers}
      except Exception:
        pass
      return {"parse": 1, "url": f"{self.baseUrl}{path}", "header": self._headers}
    vid = id[len("/play/"):] if id.startswith("/play/") else id
    return {"parse": 1, "url": f"{self.baseUrl}/play/{vid}", "header": self._headers}
