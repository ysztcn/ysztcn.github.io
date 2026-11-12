# coding=utf-8

import os
import re
import json
import time
import tempfile

import requests
from concurrent.futures import ThreadPoolExecutor

from base.spider import Spider


class Spider(Spider):
  siteKey = "bilibili"

  _apiHost = "https://api.bilibili.com"
  _headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
  }
  _chanTtl = 21600  # 栏目树缓存时长(秒)
  _kvAppKey = "333.1339"
  _hisPs = 20  # 历史每页项数(接口上限30)
  _favPs = 20  # 收藏每页项数(接口上限20)
  # 登录 Cookie 常量, ext 配置里的 cookie 优先级更高
  _savedCookie = "buvid3=69EF021A-E6AF-074A-CDD0-3F16F212A02166196infoc; b_nut=1794356863; buvid4=B1320198-0465-EE64-24DD-D2C510FB76FG66196-026111108-d6KEpP6GSI8PoxwPM1r0fZy%2F%2BrpZo87G%2FndnwDRnxiPvPqKILr%2BIPQnxIC8AImDi; buvid_fp=cfde7dd03a07bd9a45a390cb40e87cfb; _uuid=F9543FE8-A2DA-7B48-C8CE-7197A16109F1C66806infoc; home_feed_column=5; user_site=CN; SESSDATA=f659e431%2C1809915641%2C51483%2Ab1CjCziUuQcrlBT-BhlLg1gqAxDHq0YuyCdrPCNT6vsfvdRu6zWbTIqRZONvZEPGurS3ISVm5XUU9RS0RPeV9qTGRxQXRNNnY4WHMxU2gyUzUyMVlwZkNURE1SeVB4Q1RZclBkaTRpWEpvaUkzSnJaeURfRHc3aU9oRjM2MG95bXpPSlR0TENrR1V3IIEC; bili_jct=3a40ba68ca92b5af6448121bfef78ff4; DedeUserID=406729104; DedeUserID__ckMd5=fbc1bebe77240e2c; default_sites=%5B%22CN%22%2C%22OVERSEAS%22%5D; CURRENT_QUALITY=0; rpdid=0zbfVJIp1a|4ZMHIxqy|CCA|3w1XqXXA; CURRENT_FNVAL=2000; theme-tip-show=SHOWED; bp_t_offset_406729104=1269277683393495040; hit-dyn-v2=1; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3OTQ2Mjc0NDgsImlhdCI6MTc5NDM2ODE4OCwicGx0IjotMX0.48jkDoI_IJbhNAA1PmKQk481c4oG3nl5Tr-050pMPH0; bili_ticket_expires=1794627388; browser_resolution=1912-922"

  def getName(self):
    return "bilibili"

  def init(self, extend=""):
    self._cookie = self._savedCookie
    self._buvid3 = ""
    self._chan = []
    self._chanAt = 0
    self._mid = ""
    self._hist = {}
    self._fav = []
    self._favAt = 0
    self._favAll = []
    self._favAllAt = 0
    self._seasonEntryCache = {}
    # 栏目树+探测结果的磁盘缓存路径, 设备端落在应用缓存目录
    self._cachePath = os.path.join(tempfile.gettempdir(), "tvbox_bili_channels.json")
    if extend:
      try:
        cfg = json.loads(extend)
        extCookie = (cfg.get("cookie") or "").strip()
        if extCookie:
          self._cookie = extCookie
      except (json.JSONDecodeError, TypeError):
        pass

  def homeContent(self, filter):
    classes = [
      {"type_id": "history", "type_name": "我的历史"},
      {"type_id": "fav", "type_name": "我的收藏"},
      {"type_id": "seasons", "type_name": "我追的合集"},
      {"type_id": "hot", "type_name": "全站热榜"},
    ]
    filters = {}
    # 收藏夹 / 栏目树+探测 / 热榜三组请求互不依赖, 并行拉取
    with ThreadPoolExecutor(3) as pool:
      fFolders = pool.submit(self._favFolders)
      fChannels = pool.submit(self._loadChannels)
      fPopular = pool.submit(self._popular, 1)
      folders = fFolders.result()
      channels = fChannels.result()
      popularJ = fPopular.result()
    if folders:
      filters["fav"] = [{"key": "folder", "name": "收藏夹", "value":
                         [{"n": "全部收藏", "v": "all"}] +
                         [{"n": f["title"], "v": str(f["id"])} for f in folders]}]
    for ch in channels:
      tid = str(ch["tid"])
      classes.append({"type_id": tid, "type_name": ch["name"]})
      groups = []
      modes = [{"n": "推荐", "v": "rcmd"}]
      if ch["new_ok"]:
        modes.append({"n": "最新", "v": "new"})
      if ch["old_tid"]:
        modes.append({"n": "排行榜", "v": "rank"})
      groups.append({"key": "mode", "name": "排序方式", "value": modes})
      if ch["subs"]:
        groups.append({"key": "sub", "name": "子分区", "value":
                       [{"n": "全部", "v": "0"}] +
                       [{"n": s["name"], "v": str(s["tid"])} for s in ch["subs"]]})
      filters[tid] = groups
    classes.append({"type_id": "global_rank", "type_name": "全站排行"})
    return {
      "class": classes,
      "filters": filters,
      "list": self._listCards(self._archivesOf(popularJ))[:10],
    }

  def homeVideoContent(self):
    return {"list": self._listCards(self._archivesOf(self._popular(1)))}

  def categoryContent(self, tid, pg, filter, extend):
    page = int(pg or 1)
    extend = extend or {}
    if tid == "history":
      return self._historyContent(page)
    if tid == "fav":
      return self._favContent(page, extend)
    if tid == "seasons":
      return self._seasonsContent(page)
    if tid == "hot":
      j = self._popular(page)
      archives = self._archivesOf(j)
      # 热榜 pn 真翻页, 翻过实际深度出现空页时把 pagecount 收敛到已到达的页
      pagecount = 999 if archives else max(page - 1, 1)
      return self._paged(j, self._listCards(archives), str(page), pagecount, 20, len(archives))
    if tid == "global_rank":
      j = self._ranking(0)
      return self._slicePaged(j, self._archivesOf(j), page)
    ch = self._channelByTid(tid)
    if not ch:
      return {"list": [], "page": str(page), "pagecount": 1, "limit": "20", "total": 0}
    sub = str(extend.get("sub") or "0")
    if sub != "0":
      # B站匿名端没有二级分区列表接口(网页端独立二级页已下线),
      # 选中子分区时以子分区名为关键词检索相关视频
      for s in ch["subs"]:
        if str(s["tid"]) == sub:
          result = self.searchContent(s["name"], "0", str(page))
          result["page"] = str(page)
          result["limit"] = "20"
          return result
    mode = extend.get("mode")
    if mode == "rank" and ch["old_tid"]:
      j = self._ranking(ch["old_tid"])
      return self._slicePaged(j, self._archivesOf(j), page)
    if mode == "new" and ch["new_ok"]:
      # newlist 的 pn 参数不生效, 固定返回最新 50 条, 切片成 20 条/页翻看
      j = self._newlist(ch["old_tid"], 1)
      return self._slicePaged(j, self._archivesOf(j, "archives"), page)
    j = self._regionFeed(ch["tid"], page)
    archives = self._archivesOf(j, "archives")
    pagecount = 100 if archives else max(page - 1, 1)
    return self._paged(j, self._listCards(archives), str(page), pagecount, 20, len(archives))

  def _slicePaged(self, j, archives, pg, limit=20):
    # 单次拉全量的列表(排行/最新)按页切片返回, 让端上能翻页
    total = len(archives)
    pagecount = (total + limit - 1) // limit if total else 1
    chunk = archives[(pg - 1) * limit:pg * limit] if pg <= pagecount else []
    return self._paged(j, self._listCards(chunk), str(pg), pagecount, limit, total)

  def _paged(self, j, cards, page, pagecount, limit, total):
    # 列表页统一返回结构, 接口失败时把原因放进 msg 透出给面板/TVBox
    result = {"list": cards, "page": str(page), "pagecount": pagecount,
              "limit": str(limit), "total": total}
    if j.get("code") != 0:
      result["msg"] = self._msgOf(j)
    return result

  def _msgOf(self, j):
    return j.get("msg") or j.get("message") or "接口失败"

  def _archivesOf(self, j, key="list"):
    return (j.get("data") or {}).get(key) or []

  def _loadChannels(self):
    now = time.time()
    if self._chan and now - self._chanAt < self._chanTtl:
      return self._chan
    cached = self._readChanCache()
    if cached and now - cached.get("ts", 0) < self._chanTtl:
      self._chan, self._chanAt = cached["channels"], now
      return self._chan
    channels = self._fetchChannels()
    if channels:
      self._chan, self._chanAt = channels, now
      self._writeChanCache(channels)
    return self._chan

  def _readChanCache(self):
    # 栏目树+探测结果磁盘缓存, 读取失败时退回内存缓存
    try:
      with open(self._cachePath, "r", encoding="utf-8") as f:
        return json.load(f)
    except (OSError, ValueError):
      return None

  def _writeChanCache(self, channels):
    try:
      with open(self._cachePath, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), "channels": channels}, f, ensure_ascii=False)
    except OSError:
      pass  # 只读介质或权限不足时放弃落盘, 进程内缓存仍有效

  def _fetchChannels(self):
    with ThreadPoolExecutor(2) as pool:
      fNew = pool.submit(self._chanTree, "10")
      fOld = pool.submit(self._chanTree, "2")
      newTree, oldTree = fNew.result(), fOld.result()
    channels = []
    probeTids = []
    for route, c in newTree.items():
      tid = int(c.get("tid") or 0)
      if tid < 1000:  # 番剧/影视等 PGC 频道与专题页无 UGC 列表接口, 不纳入
        continue
      subs = [{"tid": int(s.get("tid") or 0), "name": (s.get("name") or "").strip()}
              for s in c.get("sub") or [] if int(s.get("tid") or 0) >= 2000]
      old_tid = int((oldTree.get(route) or {}).get("tid") or 0)
      channels.append({
        "tid": tid,
        "name": (c.get("name") or route).strip(),
        "subs": subs,
        "old_tid": old_tid,
        "new_ok": False,
      })
      if old_tid:
        probeTids.append(len(channels) - 1)
    if probeTids:
      # newlist 探测逐频道并行(8 线程), 保序写回
      with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(
            self._probeNewlist, [channels[i]["old_tid"] for i in probeTids]))
      for i, newOk in zip(probeTids, results):
        channels[i]["new_ok"] = newOk
    return channels

  def _probeNewlist(self, rid):
    # 轻量试拉一条, 判断该旧分区在 newlist 是否真有投稿流(运动/汽车/动物等无)
    j = self._api("/x/web-interface/newlist", {"rid": rid, "ps": 1, "pn": 1})
    return bool((j.get("data") or {}).get("archives"))

  def _chanTree(self, nscode):
    # kv-frontend 命名空间接口: nscode=10 新版栏目树, nscode=2 旧分区(排行榜 rid 用)
    j = self._api("/x/kv-frontend/namespace/data", {"appKey": self._kvAppKey, "nscode": nscode})
    data = ((j.get("data") or {}).get("data")) or {}
    rawSort = data.get("channel_list.sort")
    if not rawSort:
      return {}
    tree = {}
    for route in json.loads(rawSort):
      raw = data.get("channel_list." + route)
      if not raw:
        continue
      try:
        tree[route] = json.loads(raw)
      except ValueError:
        continue
    return tree

  def _channelByTid(self, tid):
    for ch in self._loadChannels():
      if str(ch["tid"]) == str(tid):
        return ch
    return None

  def _historyContent(self, pg):
    pageData = self._histPage(pg)
    cards = []
    for it in pageData["items"]:
      his = it.get("history") or {}
      bvid = his.get("bvid") or ""
      if his.get("business") != "archive" or not bvid:
        continue  # 剧集/直播/专栏条目无稿件 bvid, 本爬虫不支持播放
      progress = int(it.get("progress") or 0)
      duration = int(it.get("duration") or 0)
      remarks = self._fmtDuration(duration)
      if 0 < progress < duration:
        remarks = f"看到{self._fmtDuration(progress)}/{self._fmtDuration(duration)}"
      cards.append({
        "vod_id": bvid,
        "vod_name": self._cleanTitle(it.get("title", "")),
        "vod_pic": self._httpsPic(it.get("cover")),
        "vod_remarks": remarks,
      })
    # 游标链: 还有下一页给 999, 当前是最后一页收敛到本页, 越过末尾收敛到前一页
    if pageData["items"] and pageData["next"]:
      pagecount = 999
    elif pageData["items"]:
      pagecount = pg
    else:
      pagecount = max(pg - 1, 1)
    return self._paged(pageData, cards, str(pg), pagecount, self._hisPs, len(cards))

  def _histPage(self, pg):
    # history/cursor 用游标翻页, 没有页号, 按页序把游标链补齐到第 pg 页
    while str(pg) not in self._hist:
      p = str(len(self._hist) + 1)
      prev = self._hist.get(str(int(p) - 1))
      if prev is not None and not prev["next"]:
        self._hist[p] = {"items": [], "next": {}, "code": 0, "message": ""}
        continue
      params = {"ps": self._hisPs, "type": "all", "max": 0, "business": "", "view_at": 0}
      if prev:
        params.update({"max": prev["next"].get("max", 0),
                       "business": prev["next"].get("business", ""),
                       "view_at": prev["next"].get("view_at", 0)})
      j = self._api("/x/web-interface/history/cursor", params)
      d = j.get("data") or {}
      items = d.get("list") or []
      self._hist[p] = {"items": items, "next": (d.get("cursor") or {}) if items else {},
                       "code": j.get("code"), "message": self._msgOf(j) if j.get("code") != 0 else ""}
    return self._hist[str(pg)]

  def _favContent(self, pg, extend):
    folder = str(extend.get("folder") or "all")
    if folder == "all":
      items = self._favAllList()
      if not items and not self._cookie:
        return self._paged({"code": -1, "message": "未登录或 Cookie 失效"},
                           [], str(pg), 1, self._favPs, 0)
      start = (pg - 1) * self._favPs
      chunk = self._favCards(items[start:start + self._favPs])
      total = len(items)
      pagecount = (total + self._favPs - 1) // self._favPs if total else 1
      return self._paged({"code": 0}, chunk, str(pg), pagecount, self._favPs, total)
    folders = self._favFolders()
    if not folders:
      msg = "未登录或 Cookie 失效" if not self._cookie else "获取收藏夹失败"
      return self._paged({"code": -1, "message": msg}, [], str(pg), 1, self._favPs, 0)
    media_id = folder if folder.isdigit() else str(self._defaultFolder(folders))
    j = self._api("/x/v3/fav/resource/list", {
      "media_id": media_id, "pn": pg, "ps": self._favPs,
      "type": 0, "order": "mtime", "platform": "web",
    })
    cards = self._favCards(self._archivesOf(j, "medias"))
    info = (j.get("data") or {}).get("info") or {}
    total = int(info.get("media_count") or 0) if j.get("code") == 0 else 0
    pagecount = (total + self._favPs - 1) // self._favPs if total else 1
    return self._paged(j, cards, str(pg), pagecount, self._favPs, total)

  def _favAllList(self):
    # 接口端"全部收藏夹"模式(type=1)已下线(11010), 按收藏夹顺序自己聚合;
    # 各文件夹并行拉取, 聚合层只按 bvid 去重, 失效过滤统一在 _favCards 展示层做
    if self._favAll and time.time() - self._favAllAt < self._chanTtl:
      return self._favAll
    folders = self._favFolders()
    if folders:
      with ThreadPoolExecutor(8) as pool:
        folderPages = list(pool.map(self._favFolderPages, folders))
    else:
      folderPages = []
    medias = []
    seen = set()
    for pages in folderPages:
      for m in pages:
        bvid = m.get("bvid") or ""
        if not bvid or bvid in seen:
          continue  # 同一视频可能收藏在多个文件夹, 去重
        seen.add(bvid)
        medias.append(m)
    self._favAll, self._favAllAt = medias, time.time()
    return medias

  def _favFolderPages(self, folder):
    # 单个收藏夹按 has_more 翻完, 返回原始 media 列表(不过滤)
    pages = []
    pn = 1
    while True:
      j = self._api("/x/v3/fav/resource/list", {
        "media_id": str(folder["id"]), "pn": pn, "ps": self._favPs,
        "type": 0, "order": "mtime", "platform": "web",
      })
      page = self._archivesOf(j, "medias")
      if page:
        pages.extend(page)
      if not page or not (j.get("data") or {}).get("has_more"):
        break
      pn += 1
    return pages

  def _favCards(self, medias):
    cards = []
    for m in medias:
      if int(m.get("type") or 0) != 2 or int(m.get("attr") or 0) != 0:
        continue  # 只保留未失效的视频稿件
      cnt = m.get("cnt_info") or {}
      pubtime = int(m.get("pubtime") or 0)
      cards.append({
        "vod_id": m.get("bvid", ""),
        "vod_name": self._cleanTitle(m.get("title", "")),
        "vod_pic": self._httpsPic(m.get("cover")),
        "vod_remarks": f"{self._fmtCount(cnt.get('play', 0))}播放",
        "vod_year": time.strftime("%Y", time.localtime(pubtime)) if pubtime else "",
      })
    return cards

  def _seasonsContent(self, pg):
    # "我追的合集": collected/list 返回订阅的合集与收藏的收藏夹混排, fid=0 的是合集
    mid = self._myMid()
    if not mid:
      msg = "未登录或 Cookie 失效" if not self._cookie else "获取账号信息失败"
      return self._paged({"code": -1, "message": msg}, [], str(pg), 1, self._favPs, 0)
    j = self._api("/x/v3/fav/folder/collected/list", {
      "up_mid": mid, "pn": pg, "ps": self._favPs, "platform": "web",
    })
    d = j.get("data") or {}
    cards = []
    for it in d.get("list") or []:
      fid = it.get("fid")
      if fid is None or int(fid) != 0:
        continue  # 收藏的收藏夹(fid 不为 0)不是合集
      sid = int(it.get("id") or 0)
      entry = self._seasonEntry(sid)
      if not entry:
        continue  # 合集无成员视频时无法进入详情
      mediaCount = int(it.get("media_count") or 0)
      mtime = int(it.get("mtime") or 0)
      cards.append({
        "vod_id": entry,
        "vod_name": self._cleanTitle(it.get("title", "")),
        "vod_pic": self._httpsPic(it.get("cover")),
        "vod_remarks": f"{mediaCount}集",
        "vod_year": time.strftime("%Y", time.localtime(mtime)) if mtime else "",
      })
    total = int(d.get("count") or 0) if j.get("code") == 0 else 0
    pagecount = (total + self._favPs - 1) // self._favPs if total else 1
    return self._paged(j, cards, str(pg), pagecount, self._favPs, total)

  def _seasonEntry(self, sid):
    # 合集首集的 bvid, 用作详情入口, 进程内缓存
    if sid not in self._seasonEntryCache:
      j = self._api("/x/space/fav/season/list", {"season_id": sid, "pn": 1, "ps": 1})
      medias = (j.get("data") or {}).get("medias") or []
      self._seasonEntryCache[sid] = (medias[0].get("bvid") or "") if medias else ""
    return self._seasonEntryCache[sid]

  def _favFolders(self):
    # 收藏夹列表与历史都要登录 Cookie, 未登录时接口返回 -101, 此处得到空列表
    if self._fav and time.time() - self._favAt < self._chanTtl:
      return self._fav
    mid = self._myMid()
    folders = []
    if mid:
      j = self._api("/x/v3/fav/folder/created/list-all", {"up_mid": mid, "tid": 0})
      for f in (j.get("data") or {}).get("list") or []:
        if f.get("id"):
          folders.append({"id": int(f["id"]), "title": (f.get("title") or "").strip(),
                          "is_default": int(f.get("attr") or 0) & 2 == 0})
    if folders:
      self._fav, self._favAt = folders, time.time()
    return folders

  def _defaultFolder(self, folders):
    for f in folders:
      if f["is_default"]:
        return f["id"]
    return folders[0]["id"]

  def _myMid(self):
    if not self._mid:
      j = self._api("/x/web-interface/nav", {})
      d = j.get("data") or {}
      if d.get("isLogin"):
        self._mid = str(d.get("mid") or "")
    return self._mid

  def _regionFeed(self, region, pg):
    return self._api("/x/web-interface/region/feed/rcmd", {
      "display_id": pg, "request_cnt": 20, "from_region": region,
      "device": "web", "plat": 30,
    })

  def _newlist(self, rid, pg):
    return self._api("/x/web-interface/newlist", {"rid": rid, "ps": 50, "pn": pg})

  def searchContent(self, key, quick, pg="1"):
    j = self._api("/x/web-interface/search/all/v2", {
      "keyword": key, "page": str(pg), "pagesize": "50",
    })
    result = {"list": [], "page": str(pg), "pagecount": 1}
    for group in self._archivesOf(j, "result"):
      if group.get("result_type") != "video":
        continue
      videos = []
      for v in group.get("data") or []:
        videos.append({
          "vod_id": v.get("bvid", ""),
          "vod_name": self._cleanTitle(v.get("title", "")),
          "vod_pic": self._httpsPic(v.get("pic")),
          "vod_remarks": self._fmtDuration(v.get("duration", "")),
        })
      result["list"] = videos
      result["pagecount"] = int(((j.get("data") or {}).get("numPages", 1)) or 1)
      break
    if j.get("code") != 0:
      result["msg"] = self._msgOf(j)
    return result

  def detailContent(self, ids):
    bvid = ids[0]
    j = self._api("/x/web-interface/view", {"bvid": bvid})
    if j.get("code") != 0:
      return {"list": [], "msg": self._msgOf(j)}
    d = j["data"]
    season = d.get("ugc_season") or {}
    sections = season.get("sections") or []
    if sections:
      play_from, play_url = self._buildSeasonLines(sections)
      vod_name = (season.get("title") or d.get("title", "")).strip()
      pic = self._httpsPic(season.get("cover") or d.get("pic"))
      desc = season.get("intro") or d.get("desc", "")
    else:
      episodes = []
      for p in d.get("pages") or []:
        name = (p.get("part") or "").strip() or f"P{p.get('page', len(episodes) + 1)}"
        episodes.append(f"{self._safeName(name)}${bvid}|{p.get('cid')}|{p.get('page', 1)}")
      play_from = ["哔哩哔哩"]
      play_url = ["#".join(episodes)]
      vod_name = d.get("title", "")
      pic = self._httpsPic(d.get("pic"))
      desc = d.get("desc", "")

    stat = d.get("stat") or {}
    vod = {
      "vod_id": bvid,
      "vod_name": vod_name,
      "vod_pic": pic,
      "vod_class": d.get("tname", "") or d.get("typename", ""),
      "vod_year": time.strftime("%Y", time.localtime(d.get("pubdate", 0))) if d.get("pubdate") else "",
      "vod_director": (d.get("owner") or {}).get("name", ""),
      "vod_content": self._cleanDesc(desc),
      "vod_remarks": f"{self._fmtCount(stat.get('view', 0))}播放",
      "vod_play_from": "$$$".join(play_from),
      "vod_play_url": "$$$".join(play_url),
    }
    return {"list": [vod]}

  def _buildSeasonLines(self, sections):
    play_from, play_url = [], []
    used = {}
    for sec in sections:
      episodes = []
      for ep in sec.get("episodes") or []:
        e_bvid = ep.get("bvid", "")
        pages = ep.get("pages") or []
        if len(pages) > 1:
          for p in pages:
            name = f"{ep.get('title', '')}-P{p.get('page', 1)}"
            episodes.append(f"{self._safeName(name)}${e_bvid}|{p.get('cid')}|{p.get('page', 1)}")
        else:
          cid = pages[0].get("cid") if pages else ep.get("cid")
          episodes.append(f"{self._safeName(ep.get('title', ''))}${e_bvid}|{cid}|1")
      title = self._safeName((sec.get("title") or "").strip()) or "合集"
      used[title] = used.get(title, 0) + 1
      if used[title] > 1:
        title += str(used[title])
      play_from.append(title)
      play_url.append("#".join(episodes))
    return play_from, play_url

  def playerContent(self, flag, id, vipFlags):
    parts = str(id).split("|")
    bvid = parts[0]
    cid = parts[1] if len(parts) >= 2 else ""
    if not cid:
      j = self._api("/x/web-interface/view", {"bvid": bvid})
      d = j.get("data") or {}
      cid = d.get("cid", "")
      aid = d.get("aid", "")
    else:
      # 已有 cid，获取 aid
      j = self._api("/x/web-interface/view", {"bvid": bvid})
      aid = (j.get("data") or {}).get("aid", "")
    
    # 采用 shuju 方式：fnval=0 + high_quality=1，获取源文件清晰度列表，取最高清晰度
    # 优先用 aid+cid，fnval=0 不强制合流，可获取 1080P+ 源文件
    params = {"cid": cid, "qn": 112, "fnval": 0, "platform": "html5", "high_quality": 1}
    if aid:
      params["avid"] = aid
    else:
      params["bvid"] = bvid
    
    j = self._api("/x/player/playurl", params)
    durls = ((j.get("data") or {}).get("durl")) or []
    if not durls:
      return {"parse": 0, "url": "", "msg": f"播放地址获取失败: {self._msgOf(j)}"}
    
    # durl 数组按清晰度降序，第一个为最高画质
    url = durls[0].get("url", "")
    return {
      "parse": 0,
      "url": url,
      "header": {"User-Agent": self._headers["User-Agent"], "Referer": "https://www.bilibili.com/", "Cookie": self._cookie},
    }

  def _dashVideoUrl(self, d, qn):
    # DASH 音视频分离, 只取视频流: 选不高于目标 qn 的最高档, 编码优先 AVC(兼容性), 其次 HEVC
    videos = (d.get("dash") or {}).get("video") or []
    pool = []
    for v in videos:
      vid = int(v.get("id") or 0)
      if vid > qn:
        continue
      codec = (v.get("codecs") or "").lower()
      if codec.startswith("avc1"):
        rank = 2
      elif codec.startswith(("hev1", "hvc1")):
        rank = 1
      else:
        rank = 0  # av01 等新编码播放器兼容差, 仅在无可播编码时兜底
      pool.append((vid, rank, v))
    if not pool:
      return ""
    best = max(pool, key=lambda it: (it[0], it[1]))
    return best[2].get("baseUrl") or best[2].get("base_url") or ""

  def _api(self, path, params=None):
    headers = dict(self._headers)
    cookie = self._cookie or self._getBuvid3()
    if cookie:
      headers["Cookie"] = cookie
    url = self._apiHost + path
    lastErr = "请求失败"
    for _ in range(2):  # 网络异常与 HTTP 5xx 各重试一次, 其余失败不重试
      try:
        rsp = self.fetch(url, params=params or {}, headers=headers, timeout=15)
      except requests.RequestException as e:
        lastErr = f"网络异常: {type(e).__name__}"
        continue
      if rsp.status_code >= 500:
        lastErr = f"HTTP {rsp.status_code}"
        continue
      try:
        return rsp.json()
      except ValueError:
        return {"code": -1, "msg": f"非JSON响应 http {rsp.status_code}"}
    return {"code": -1, "msg": lastErr}

  def _getBuvid3(self):
    if not self._buvid3:
      try:
        rsp = self.fetch(self._apiHost + "/x/frontend/finger/spi", headers=self._headers, timeout=10)
        self._buvid3 = "buvid3=" + rsp.json()["data"]["b_3"]
      except (requests.RequestException, ValueError, KeyError):
        return ""
    return self._buvid3

  def _popular(self, pg):
    return self._api("/x/web-interface/popular", {"ps": 20, "pn": pg})

  def _ranking(self, rid):
    return self._api("/x/web-interface/ranking/v2", {"rid": rid, "type": "all"})

  def _listCards(self, archives):
    videos = []
    for a in archives:
      stat = a.get("stat") or {}
      videos.append({
        "vod_id": a.get("bvid", ""),
        "vod_name": self._cleanTitle(a.get("title", "")),
        "vod_pic": self._httpsPic(a.get("pic") or a.get("cover")),
        "vod_remarks": f"{self._fmtCount(stat.get('view', a.get('play', 0)))}播放",
        "vod_year": time.strftime("%Y", time.localtime(a["pubdate"])) if a.get("pubdate") else "",
      })
    return videos

  def _cleanTitle(self, title):
    return re.sub(r"<[^>]+>", "", title or "")

  def _cleanDesc(self, desc):
    return re.sub(r"\s+", " ", (desc or "").replace("\n", " ")).strip()[:200]

  def _httpsPic(self, pic):
    if not pic:
      return ""
    if pic.startswith("//"):
      return "https:" + pic
    return pic.replace("http://", "https://", 1) if pic.startswith("http://") else pic

  def _fmtDuration(self, duration):
    text = str(duration).strip()
    if ":" in text:
      return text
    seconds = int(text) if text.isdigit() else 0
    h, m, sec = seconds // 3600, seconds % 3600 // 60, seconds % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

  def _fmtCount(self, n):
    n = int(n or 0)
    if n >= 100000000:
      return f"{n / 100000000:.1f}亿"
    if n >= 10000:
      return f"{n / 10000:.1f}万"
    return str(n)

  def _safeName(self, name):
    return name.replace("$", "＄").replace("#", "＃")
