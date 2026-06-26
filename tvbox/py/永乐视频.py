#!/usr/bin/env python3
# coding=utf-8

import re
import requests
from bs4 import BeautifulSoup

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from base.spider import Spider


class Spider(Spider):
  _RE_VOD_DETAIL = re.compile(r'<a href="/voddetail/(\d+)/"[^>]*title="([^"]+)"[^>]*>'
    r'.*?<div class="module-item-note">([^<]+)</div>'
    r'.*?(?:data-original|src)="([^"]+)"', re.S | re.I)
  _RE_SEARCH_ID = re.compile(r'/voddetail/(\d+)/')
  _RE_PLAYER_URL = re.compile(r'var player_aaaa=.*?"url":"([^"]+\.m3u8)"', re.S | re.I)
  _RE_TITLE = re.compile(r'<meta property="og:title" content="([^"]+)-[^-]+"', re.S | re.I)
  _RE_PIC = re.compile(r'<meta property="og:image" content="([^"]+)"', re.S | re.I)
  _RE_DESC = re.compile(r'<meta property="og:description" content="([^"]+)"', re.S | re.I)
  _RE_YEAR = re.compile(r'<a title="(\d+)" href="/vodshow/\d+-----------\1/">', re.S | re.I)
  _RE_AREA = re.compile(r'<a title="([^"]+)" href="/vodshow/\d+-[^"]+/">', re.S | re.I)
  _RE_TYPE = re.compile(r'vod_class":"([^"]+)"', re.S | re.I)
  _RE_TAB_ITEM = re.compile(
    r'<(?:div|a)[^>]*class="[^"]*module-tab-item[^"]*"[^>]*>'
    r'\s*<span>([^<]+)</span>\s*<small(?:\s+class="no")?>(\d+)</small>'
    r'</(?:div|a)>', re.S | re.I)
  _LINE_ID_MAP = {
    "全球3线": "3", "大陆0线": "1", "大陆3线": "4",
    "大陆5线": "2", "大陆6线": "3",
  }

  def getName(self):
    return "永乐视频"

  _headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
  }
  host = "https://www.ylys.tv/"

  def init(self, extend=""):
    self._session = requests.Session()
    import threading
    threading.Thread(target=self.fetch, args=(self.host,), daemon=True).start()

  def fetch(self, url, timeout=30):
    try:
      response = self._session.get(url, headers=self._headers, timeout=timeout, verify=False)
      response.encoding = 'UTF-8'
      return response
    except:
      return None

  def homeContent(self, filter):
    result = {
      "class": [
        {'type_id': str(i), 'type_name': t}
        for i, t in enumerate(['电影', '剧集', '综艺', '动漫'], 1)
      ],
      "filters": self._get_filters(),
      "list": [],
    }
    rsp = self.fetch(self.host)
    if rsp and rsp.status_code == 200:
      result['list'] = self._extract_videos(rsp.text, 20)
    return result

  def homeVideoContent(self):
    rsp = self.fetch(self.host)
    if rsp and rsp.status_code == 200:
      return {"list": self._extract_videos(rsp.text, 40)}
    return {"list": []}

  def categoryContent(self, tid, pg, filter, extend):
    result = {"list": [], "page": pg, "pagecount": 99, "limit": 20, "total": 1980}
    rsp = self.fetch(f"{self.host}/vodshow/{tid}--------{pg}---/")
    if rsp and rsp.status_code == 200:
      result['list'] = self._extract_videos(rsp.text)
    return result

  def searchContent(self, key, quick, pg=1):
    result = {"list": []}
    search_key = requests.utils.quote(key)
    if int(pg) > 1:
      url = f"{self.host}/vodsearch/{search_key}-------------/page/{pg}/"
    else:
      url = f"{self.host}/vodsearch/{search_key}-------------/"
    rsp = self.fetch(url)
    if rsp and rsp.status_code == 200:
      result['list'] = self._extract_search_results(rsp.text)
    return result

  def detailContent(self, ids):
    vid = ids[0]
    rsp = self.fetch(f"{self.host}/voddetail/{vid}/")
    if not rsp or rsp.status_code != 200:
      return {"list": []}

    html = rsp.text
    play_from, play_url = self._extract_play_info(html, vid)
    if not play_from:
      return {"list": []}

    return {
      "list": [{
        'vod_id': vid,
        'vod_name': self._extract_title(html),
        'vod_pic': self._extract_pic(html),
        'vod_content': self._extract_desc(html),
        'vod_remarks': self._extract_remarks(html),
        'vod_play_from': "$$$".join(play_from),
        'vod_play_url': "$$$".join(play_url),
      }]
    }

  def playerContent(self, flag, id, vipFlags):
    result = {"parse": 1, "playUrl": "", "url": ""}
    if "-" not in id:
      return result
    try:
      rsp = self.fetch(f"{self.host}/play/{id}/")
      if not rsp or rsp.status_code != 200:
        return result
      match = self._RE_PLAYER_URL.search(rsp.text)
      if match:
        real_url = match.group(1).replace(r'\u002F', '/').replace(r'\/', '/')
        result["parse"] = 0
        result["url"] = real_url
      else:
        result["url"] = f"{self.host}/play/{id}/"
    except:
      result["url"] = f"{self.host}/play/{id}/"
    return result

  def _resolve_pic(self, pic):
    if pic:
      pic = pic.strip()
      return self.host + pic if pic.startswith('/') else pic
    return ""

  def _get_filters(self):
    return {
      "1": [{"key": "class", "name": "类型", "value": [
        {"n": "全部", "v": ""}, {"n": "动作片", "v": "6"}, {"n": "喜剧片", "v": "7"},
        {"n": "爱情片", "v": "8"}, {"n": "科幻片", "v": "9"}, {"n": "恐怖片", "v": "11"},
      ]}],
      "2": [{"key": "class", "name": "类型", "value": [
        {"n": "全部", "v": ""}, {"n": "国产剧", "v": "13"}, {"n": "港台剧", "v": "14"},
        {"n": "日剧", "v": "15"}, {"n": "韩剧", "v": "33"}, {"n": "欧美剧", "v": "16"},
      ]}],
      "3": [{"key": "class", "name": "类型", "value": [
        {"n": "全部", "v": ""}, {"n": "内地综艺", "v": "27"}, {"n": "港台综艺", "v": "28"},
        {"n": "日本综艺", "v": "29"}, {"n": "韩国综艺", "v": "36"},
      ]}],
      "4": [{"key": "class", "name": "类型", "value": [
        {"n": "全部", "v": ""}, {"n": "国产动漫", "v": "31"}, {"n": "日本动漫", "v": "32"},
        {"n": "欧美动漫", "v": "42"}, {"n": "其他动漫", "v": "43"},
      ]}],
    }

  def _extract_videos(self, html, limit=0):
    videos = [
      {
        'vod_id': vid.strip(),
        'vod_name': title.strip(),
        'vod_pic': self._resolve_pic(pic),
        'vod_remarks': remark.strip(),
      }
      for vid, title, remark, pic in self._RE_VOD_DETAIL.findall(html)
    ]
    return videos[:limit] if limit else videos

  def _extract_search_results(self, html):
    videos = []
    soup = BeautifulSoup(html, 'html.parser')
    for item in soup.select('.module-card-item'):
      link = item.select_one('a[href^="/voddetail/"]')
      if not link:
        continue
      href = link.get('href', '')
      vid_match = self._RE_SEARCH_ID.search(href)
      if not vid_match:
        continue
      title_elem = item.select_one('.module-card-item-title strong')
      img_elem = item.select_one('img')
      pic = (img_elem.get('data-original') or img_elem.get('src')) if img_elem else ""
      note_elem = item.select_one('.module-item-note')
      videos.append({
        'vod_id': vid_match.group(1),
        'vod_name': title_elem.get_text(strip=True) if title_elem else "",
        'vod_pic': self._resolve_pic(pic),
        'vod_remarks': note_elem.get_text(strip=True) if note_elem else "",
      })
    return videos

  def _extract_play_info(self, html, vid):
    play_from, play_url = [], []
    tab_matches = self._RE_TAB_ITEM.findall(html)
    if not tab_matches:
      return play_from, play_url

    line_ids = re.findall(
      rf'<a[^>]*href="/play/{vid}-(\d+)-1/"[^>]*>.*?<span>([^<]+)</span>', html, re.S | re.I)
    line_map = {name: lid for lid, name in line_ids}

    episodes = re.findall(
      rf'<a class="module-play-list-link" href="/play/{vid}-(\d+)-(\d+)/"[^>]*>.*?<span>([^<]+)</span></a>',
      html, re.S | re.I)
    eps_by_line = {}
    for lid, ep_num, ep_name in episodes:
      eps_by_line.setdefault(lid, []).append(
        f"{ep_name.strip()}${vid}-{lid}-{ep_num.strip()}")

    for match in tab_matches:
      line_name = match[0]
      if line_name in play_from:
        continue
      play_from.append(line_name)
      lid = line_map.get(line_name, self._LINE_ID_MAP.get(line_name, "1"))
      play_url.append("#".join(eps_by_line.get(lid, [])))
    return play_from, play_url

  def _extract_title(self, html):
    match = self._RE_TITLE.search(html)
    return match.group(1).strip() if match else ""

  def _extract_pic(self, html):
    match = self._RE_PIC.search(html)
    return self._resolve_pic(match.group(1) if match else "")

  def _extract_desc(self, html):
    match = self._RE_DESC.search(html)
    return match.group(1).strip() if match else "暂无简介"

  def _extract_remarks(self, html):
    year_match = self._RE_YEAR.search(html)
    year = year_match.group(1) if year_match else "未知年份"
    area_match = self._RE_AREA.search(html)
    area = area_match.group(1) if area_match else "未知产地"
    type_match = self._RE_TYPE.search(html)
    type_str = type_match.group(1).replace(",", "/") if type_match else "未知类型"
    return f"{year} | {area} | {type_str}"

