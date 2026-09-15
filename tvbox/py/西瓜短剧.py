#!/usr/bin/env python3
# coding=utf-8

import json
import time
import urllib.parse

import requests

from base.spider import Spider


class Spider(Spider):
  _apiHost = "https://m.xgshort.com"
  _workerUrl = "https://xgshort-api.yszt.dpdns.org"
  _headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
  }
  _filterKeyMap = {
    "排序": "sort", "题材": "theme", "地区": "area",
    "语言": "lang", "年份": "year", "状态": "status",
  }
  _filterIndex = {"sort": 0, "theme": 1, "area": 2, "lang": 3, "year": 4, "status": 5}

  def getName(self):
    return "西瓜短剧"

  def init(self, extend=""):
    self._token = ""
    self._tokenExp = 0
    if extend:
      try:
        cfg = json.loads(extend)
        if "workerUrl" in cfg:
          self._workerUrl = cfg["workerUrl"]
        if "apiHost" in cfg:
          self._apiHost = cfg["apiHost"]
      except json.JSONDecodeError:
        pass

  def _fetchApi(self, path, method="GET", body=None, needAuth=False):
    # 每个接口约耗1~2次网络请求，token 失效时重试一次
    for attempt in range(2):
      url = f"{self._workerUrl}/api/proxy?url={urllib.parse.quote(self._apiHost + path)}"
      if needAuth:
        url += f"&authtoken={self._getToken()}"
      try:
        if method == "POST":
          resp = requests.post(url, data=body, headers=self._headers, timeout=20)
        else:
          resp = requests.get(url, headers=self._headers, timeout=20)
        resp.encoding = "utf-8"
        outer = resp.json()
      except Exception:
        return None
      data = outer.get("data") if isinstance(outer, dict) else None
      if isinstance(data, str):
        try:
          data = json.loads(data)
        except json.JSONDecodeError:
          pass
      if needAuth and attempt == 0 and self._isUnauthorized(data):
        self._token = ""
        self._tokenExp = 0
        continue
      return data
    return None

  def _isUnauthorized(self, data):
    return isinstance(data, dict) and data.get("statusCode") in (401, 403)

  def _getToken(self):
    if self._token and self._tokenExp > time.time() + 600:
      return self._token
    data = self._fetchApi("/api/auth/guest-login", method="POST", body='{"guestToken":""}', needAuth=False)
    if isinstance(data, dict) and data.get("access_token"):
      self._token = data["access_token"]
      self._tokenExp = int(time.time()) + int(data.get("expires_in", 604800))
    return self._token

  def homeContent(self, filter):
    result = {"class": [], "filters": {}}
    data = self._fetchApi("/api/home/categories")
    if isinstance(data, list):
      for c in data:
        result["class"].append({
          "type_id": str(c.get("id", "")),
          "type_name": c.get("name", ""),
        })
    if filter and result["class"]:
      tags = self._fetchApi("/api/list/getfilterstags")
      filters = self._buildFilters(tags)
      if filters:
        for c in result["class"]:
          result["filters"][c["type_id"]] = filters
    return result

  def homeVideoContent(self):
    result = {"list": []}
    data = self._fetchApi("/api/home/gethomemodules?channeid=1")
    inner = data.get("data") if isinstance(data, dict) else None
    if isinstance(inner, dict):
      for m in inner.get("list", []):
        if m.get("type") == 3:
          for v in m.get("list", []):
            result["list"].append(self._buildVodCard(v))
          break
    return result

  def categoryContent(self, tid, pg, filter, extend):
    result = {"list": [], "page": pg, "pagecount": 999, "limit": 20}
    ids = self._buildFilterIds(extend or {})
    data = self._fetchApi(f"/api/list/getfiltersdata?channeid={tid}&ids={ids}&page={pg}&size=20")
    for v in self._extractList(data):
      result["list"].append(self._buildVodCard(v))
    total = self._extractTotal(data)
    if total:
      result["total"] = total
      result["pagecount"] = (total + 19) // 20
    return result

  def searchContent(self, key, quick, pg="1"):
    result = {"list": [], "page": pg, "pagecount": 1, "limit": 20}
    encoded = urllib.parse.quote(key)
    data = self._fetchApi(f"/api/list/fuzzysearch?keyword={encoded}&page={pg}&size=20&categoryId=1")
    for v in self._extractList(data):
      result["list"].append(self._buildVodCard(v))
    return result

  def detailContent(self, ids):
    if not ids:
      return {"list": []}
    sid = ids[0]
    data = self._fetchApi(f"/api/video/episodes?seriesShortId={sid}&page=1&size=200", needAuth=True)
    inner = data.get("data") if isinstance(data, dict) else None
    if not isinstance(inner, dict) or not inner.get("seriesInfo"):
      return {"list": []}

    info = inner.get("seriesInfo", {})
    play = []
    score = ""
    for e in inner.get("list", []):
      key = e.get("episodeAccessKey")
      if key:
        title = e.get("episodeTitle") or e.get("title", "")
        play.append(f"{title}${key}")
      if not score and e.get("seriesScore"):
        score = str(e["seriesScore"])

    vod = {
      "vod_id": sid,
      "vod_name": info.get("title", ""),
      "vod_pic": info.get("coverUrl", ""),
      "vod_remarks": info.get("updateStatus", ""),
      "vod_score": score,
      "vod_director": info.get("director", ""),
      "vod_actor": info.get("starring", "") or info.get("actor", ""),
      "vod_content": info.get("description", ""),
      "vod_play_from": "西瓜短剧",
      "vod_play_url": "#".join(play),
    }
    if info.get("tags"):
      vod["vod_class"] = ",".join(info["tags"])
    return {"list": [vod]}

  def playerContent(self, flag, id, vipFlags):
    result = {"parse": 0, "playUrl": "", "url": ""}
    try:
      body = json.dumps({"type": "episode", "accessKey": id})
      data = self._fetchApi("/api/video/episode-url/query", method="POST", body=body, needAuth=True)
      inner = data.get("data") if isinstance(data, dict) else None
      if isinstance(inner, dict):
        for u in inner.get("urls", []):
          if u.get("cdnUrl"):
            result["url"] = u["cdnUrl"]
            result["header"] = dict(self._headers)
            break
    except Exception:
      pass
    return result

  def _buildVodCard(self, v):
    remarks = []
    if v.get("upStatus"):
      remarks.append(v["upStatus"])
    if v.get("score"):
      remarks.append(f'{v["score"]}分')
    return {
      "vod_id": v.get("shortId", ""),
      "vod_name": v.get("title", ""),
      "vod_pic": v.get("coverUrl", ""),
      "vod_remarks": " | ".join(remarks),
      "vod_score": v.get("score", ""),
    }

  def _buildFilters(self, data):
    filters = []
    inner = data.get("data") if isinstance(data, dict) else None
    if not isinstance(inner, dict):
      return filters
    for g in inner.get("list", []):
      name = g.get("name", "")
      key = self._filterKeyMap.get(name)
      if not key:
        continue
      filters.append({
        "key": key,
        "name": name,
        "value": [
          {"n": i.get("classifyName", ""), "v": str(i.get("classifyId", ""))}
          for i in g.get("list", [])
        ],
      })
    return filters

  def _buildFilterIds(self, extend):
    ids = ["0"] * 7
    for k, v in extend.items():
      if k in self._filterIndex:
        ids[self._filterIndex[k]] = str(v)
    return ",".join(ids)

  def _extractList(self, data):
    if isinstance(data, list):
      return data
    if isinstance(data, dict):
      inner = data.get("data")
      if isinstance(inner, dict):
        return inner.get("list", [])
      if isinstance(inner, list):
        return inner
    return []

  def _extractTotal(self, data):
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
      return data["data"].get("total", 0)
    return 0