# 皮皮驴 (pipilv.top) — TVBox/CatVod Spider
# 苹果CMS二开 + mxtheme模板 + 验证码防护
#
# 路由:
#   首页: /
#   分类: /list/<tid>-----------.html  (分类来自首页导航 /type/<tid>.html)
#   筛选: 各分类列表页的筛选区(剧情/地区/语言/年份/字母/排序)
#   详情: /v/<vod_id>.html
#   播放: /play/<vod_id>-<sid>-<nid>.html  (player_aaaa)
#   搜索: /search/<keyword>-------------.html
#   验证: POST /captcha.php type=verify&check=<code>
#
# 验证机制 (2026-10-20 复测):
#   * UA分层: 桌面UA->404; 蜘蛛UA(百度/谷歌/bing)->403; 只有移动UA能进,
#     随后全站被 mxone "系统安全验证" 页拦截
#   * 免验证接口不存在: /api.php/provide/vod 返回 closed, /rss.php 404,
#     ajax/suggest 也在验证页之后 -> 唯一入口是验证票
#   * 过码必须带上会话PHPSESSID; 过码(POST /captcha.php type=verify&check=码)后下发
#     captcha_login_sign = <md5>-<sha256>-<过期时间戳>, 不绑会话/UA/IP,
#     单独带这一枚Cookie即可通行全站
#   * 有效期12小时; 票面ts即过期时刻, 故判过期用: ts > time.time() 视为未过期
#   * 票统一由远程 Worker(tools/pipilv-worker)识别验证码后下发
#
# 特点:
#   1. 票统一从 Worker 取, 失效自动重新取票
#   2. 移动端UA (桌面端404)
#   3. 图片用 data-original (懒加载, 豆瓣图床)
#   4. player_aaaa 用花括号计数精确提取JSON
import sys
import re
import json
import time
import base64
import hashlib
import urllib.parse

import requests
from requests.adapters import HTTPAdapter

sys.path.append('..')
from base.spider import Spider


# ============================================================
# 剧集库 /list/ 路由的筛选维度与各分类可选项
# URL 约定(共12段, 以 "-" 连接, 末尾拼 .html):
#   /list/{tid}-{地区}-{排序}-{剧情}-{语言}-{字母}---{页码}---{年份}.html
#   段下标: [0]分类 [1]地区 [2]排序 [3]剧情(类型) [4]语言 [5]字母
#           [6][7]空 [8]页码(>1) [9][10]空 [11]年份
# 以上布局是从站点各筛选下拉里的真实链接逆向得到的, 中文段需 URL 编码。
# 筛选选项不写死, 从各分类列表页的筛选区实时解析
FILTER_KEYS = {
  '剧情': ('genre', 3),
  '地区': ('area', 1),
  '语言': ('lang', 4),
  '年份': ('year', 11),
  '字母': ('letter', 5),
  '排序': ('sort', 2),
}

def _buildListUrl(tid, area='', genre='', lang='', year='', page=1, sort='', letter=''):
  """根据筛选值拼出剧集库 /list/ URL(与站点下拉里的真实链接一致)"""
  segments = [''] * 12
  segments[0] = str(tid)
  segments[1] = area
  segments[2] = sort
  segments[3] = genre
  segments[4] = lang
  segments[5] = letter
  if int(page or 1) > 1:
    segments[8] = str(page)
  segments[11] = year
  body = '-'.join(urllib.parse.quote(s, safe='') for s in segments)
  return Spider.HOST + '/list/' + body + '.html'


class Spider(Spider):
  HOST = 'https://www.pipilv.top'
  UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
  TIMEOUT = 12
  s = None
  _cachedSign = ''
  # 远程取票 Worker, 默认地址; ext 里可用 {"worker": "..."} 覆盖
  _WORKER_URL = 'https://pipilv-ticket.yszt.dpdns.org'
  _workerUrl = _WORKER_URL

  @staticmethod
  def _signTs(sign):
    """票面时间戳; 取不到返回0"""
    try:
      return int(str(sign).rsplit('-', 1)[-1])
    except (ValueError, IndexError):
      return 0

  def _validSigns(self):
    """未过期的票(票面ts就是过期时刻, 大于当前时间才算有效)"""
    if self._cachedSign and self._signTs(self._cachedSign) > time.time():
      return [self._cachedSign]
    return []

  def _pickSign(self):
    """取一枚当前可用的票; 没有则空串"""
    signs = self._validSigns()
    return signs[0] if signs else ''

  def _cookieStr(self, sign=None):
    """Cookie头: 会话Cookie(PHPSESSID) + 指定或自动挑选的验证票"""
    if sign is None:
      sign = self._pickSign()
    parts = []
    if self.s:
      parts += ['%s=%s' % (c.name, c.value) for c in self.s.cookies if c.name != 'captcha_login_sign']
    if sign:
      parts.append('captcha_login_sign=' + sign)
    return '; '.join(parts)

  def _needNewSign(self):
    """没有有效票时的明确指引"""
    print('=' * 62)
    print('皮皮驴: 没有可用的验证票, 当前无法取数!')
    print('原因: 本站全站在"系统安全验证"之后, 需要 captcha_login_sign 才能取数。')
    print('处理: 检查 ext 里的 worker 地址是否可访问')
    print('      {"worker": "https://pipilv-ticket.yszt.dpdns.org"}')
    print('=' * 62)

  def init(self, extend=''):
    self._cachedSign = ''
    self._workerUrl = self._WORKER_URL
    if extend:
      text = str(extend).strip()
      if text.startswith('http'):
        self._workerUrl = text
      else:
        worker = (json.loads(text).get('worker') or '').strip()
        if worker:
          self._workerUrl = worker
    self.s = requests.Session()
    self.s.mount('https://', HTTPAdapter(max_retries=1))
    self._pullWorkerTicket()
    if not self._validSigns():
      self._needNewSign()
    return self

  def _pullWorkerTicket(self, force=False):
    """从远程 Worker 取一张票; 未配置或失败返回空"""
    if not self._workerUrl:
      return ''
    url = self._workerUrl.rstrip('/') + '/api/ticket'
    if force:
      url += '?force=1'
    try:
      rsp = self.s.get(url, timeout=60)
      data = rsp.json()
      sign = (data.get('data') or {}).get('sign', '')
    except (requests.RequestException, ValueError) as err:
      print('皮皮驴: Worker 取票失败', err)
      return ''
    if sign and self._signTs(sign) > time.time():
      self._cachedSign = sign
      print('皮皮驴: 已从 Worker 取到票')
      return sign
    print('皮皮驴: Worker 返回的票无效', sign)
    return ''

  def getName(self):
    return '皮皮驴'

  def isVideoFormat(self, url):
    return bool(re.search(r'\.(m3u8|mp4|flv)(\?|$)', str(url), re.I))

  def manualVideoCheck(self):
    return False

  def destroy(self):
    return

  # ======================== HTTP
  def _buildHeaders(self, ref=None, sign=None):
    headers = {'User-Agent': self.UA, 'Accept': '*/*', 'Accept-Language': 'zh-CN,zh;q=0.9',
               'Referer': ref or self.HOST + '/'}
    cookie = self._cookieStr(sign)
    if cookie:
      headers['Cookie'] = cookie
    return headers

  def _httpGet(self, url, headers):
    """单次GET; 404返回空串(与验证页/网络错误区分)"""
    rsp = self.s.get(url, headers=headers, timeout=self.TIMEOUT)
    if rsp.status_code == 404:
      return ''
    return rsp.text

  def fetch(self, url, ref=None):
    """GET请求: 带 Worker 票; 遇到"系统安全验证"页重新取票重试"""
    for sign in self._validSigns():
      text = self._httpGet(url, self._buildHeaders(ref, sign))
      if text == '':
        return ''
      if '系统安全验证' not in text:
        return text
    if self._pullWorkerTicket(force=True):
      text = self._httpGet(url, self._buildHeaders(ref))
      if text and '系统安全验证' not in text:
        return text
    self._needNewSign()
    return ''

  @staticmethod
  def _plainText(value):
    if not value:
      return ''
    value = re.sub(r'<script[\s\S]*?</script>', ' ', value, flags=re.I)
    value = re.sub(r'<style[\s\S]*?</style>', ' ', value, flags=re.I)
    value = re.sub(r'<[^>]+>', ' ', value)
    value = re.sub(r'&(?:nbsp|#160);?', ' ', value)
    value = re.sub(r'&(amp|quot|lt|gt|#39|apos);',
                   lambda m: {'amp': '&', 'quot': '"', 'lt': '<', 'gt': '>', '#39': "'", 'apos': "'"}[m.group(1)], value)
    return re.sub(r'\s+', ' ', value).strip()

  @staticmethod
  def _firstMatch(text, patterns):
    for pattern in patterns:
      match = re.search(pattern, text or '', re.S | re.I)
      if match:
        return Spider._plainText(match.group(1))
    return ''

  @staticmethod
  def _absoluteUrl(url):
    if not url:
      return ''
    url = url.strip()
    if url.startswith('//'):
      return 'https:' + url
    if url.startswith('http'):
      return url
    return Spider.HOST.rstrip('/') + '/' + url.lstrip('/')

  @staticmethod
  def _toInt(value, default=1):
    text = re.sub(r'\D', '', str(value))
    return int(text) if text else default

  @staticmethod
  def _extractJson(html, varName):
    """用花括号计数精确提取JS变量中的JSON对象"""
    index = html.find(varName)
    if index < 0:
      return None
    braceStart = html.find('{', index)
    if braceStart < 0:
      return None
    depth = 0
    inString = False
    escaped = False
    for position in range(braceStart, min(len(html), braceStart + 100000)):
      char = html[position]
      if escaped:
        escaped = False
        continue
      if char == '\\':
        escaped = True
        continue
      if char == '"' and not escaped:
        inString = not inString
        continue
      if inString:
        continue
      if char == '{':
        depth += 1
      elif char == '}':
        depth -= 1
        if depth == 0:
          raw = html[braceStart:position + 1]
          try:
            return json.loads(raw)
          except json.JSONDecodeError:
            return None
    return None

  @staticmethod
  def _extractIntro(html):
    """提取剧情简介(处理div嵌套)"""
    marker = 'module-info-introduction-content'
    index = html.find(marker)
    if index >= 0:
      start = html.find('<p', index)
      if start >= 0:
        end = html.find('</p>', start)
        if end >= 0:
          return html[start:end]
    match = re.search(r'name="description"\s+content="([^"]+)"', html, re.I)
    if match:
      return match.group(1)
    return ''

  # ======================== 卡片解析
  def _parseCards(self, html):
    """解析 mxtheme 卡片(支持 poster-item 和 card-item 两种模板)"""
    if not html:
      return []
    cards, seen = [], set()
    for match in re.finditer(r'<a[^>]*\bhref="(/v/(\d+)\.html)"[^>]*\btitle="([^"]{1,120})"', html, re.I):
      vodId = match.group(2)
      if vodId in seen:
        continue
      seen.add(vodId)
      name = self._plainText(match.group(3))
      if not name:
        continue
      block = html[match.start():min(len(html), match.end() + 600)]
      pic = self._firstMatch(block, [
        r'data-original="([^"]+)"',
        r'data-src="([^"]+)"',
        r'src="((?:https?:)?//[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
      ])
      if pic:
        pic = self._absoluteUrl(pic)
      remarks = self._firstMatch(block, [
        r'class="[^"]*module-item-note[^"]*"[^>]*>([\s\S]{0,40}?)<',
      ])
      cards.append({'vod_id': vodId, 'vod_name': name, 'vod_pic': pic, 'vod_remarks': remarks[:12] if remarks else ''})
      if len(cards) >= 30:
        break

    if len(cards) < 10:
      parts = re.split(r'class="module-card-item module-item"', html)
      for block in parts[1:]:
        block = block[:1500]
        idMatch = re.search(r'href="/v/(\d+)\.html"', block, re.I)
        if not idMatch:
          continue
        vodId = idMatch.group(1)
        if vodId in seen:
          continue
        nameMatch = re.search(r'<strong>([^<]+)</strong>', block, re.I)
        if not nameMatch:
          nameMatch = re.search(r'alt="([^"]+)"', block, re.I)
        if not nameMatch:
          continue
        name = self._plainText(nameMatch.group(1))
        if not name:
          continue
        seen.add(vodId)
        pic = self._firstMatch(block, [
          r'data-original="([^"]+)"',
          r'data-src="([^"]+)"',
          r'src="((?:https?:)?//[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        ])
        if pic:
          pic = self._absoluteUrl(pic)
        remarks = self._firstMatch(block, [
          r'class="[^"]*module-item-note[^"]*"[^>]*>([\s\S]{0,40}?)<',
        ])
        cards.append({'vod_id': vodId, 'vod_name': name, 'vod_pic': pic, 'vod_remarks': remarks[:12] if remarks else ''})
        if len(cards) >= 30:
          break
    return cards

  # ======================== 首页
  def homeContent(self, filter):
    html = self.fetch(self.HOST + '/')
    categories = self._parseCategories(html)
    result = {'class': categories, 'filters': {}}
    if filter:
      for category in categories:
        listHtml = self.fetch(_buildListUrl(category['type_id']))
        result['filters'][category['type_id']] = self._parseFilterGroups(listHtml)
    result['list'] = self._parseCards(html)
    return result

  def _parseCategories(self, html):
    """从首页导航解析分类(/type/<tid>.html)"""
    start = html.find('navbar-items')
    if start < 0:
      return []
    block = html[start:html.find('</ul>', start)]
    categories, seen = [], set()
    for match in re.finditer(r'<a[^>]*href="/type/(\d+)\.html"[^>]*title="([^"]+)"', block):
      typeId = match.group(1)
      if typeId in seen:
        continue
      seen.add(typeId)
      categories.append({'type_id': typeId, 'type_name': self._plainText(match.group(2))})
    return categories

  def _parseFilterGroups(self, html):
    """从列表页 module-class-items 解析筛选分组, 选项值取自选项链接的 URL 段"""
    start = html.find('module-class-items')
    if start < 0:
      return []
    groups = []
    for match in re.finditer(
        r'<div class="module-item-title">([^<]*)<i[^>]*></i></div>\s*'
        r'<div class="module-item-box">([\s\S]*?)</div>', html[start:]):
      title = self._plainText(match.group(1))
      mapping = FILTER_KEYS.get(title)
      if not mapping:
        continue
      key, index = mapping
      values = []
      for link in re.finditer(r'<a[^>]*href="(/list/[^"]+)"[^>]*>([^<]*)</a>', match.group(2)):
        segments = urllib.parse.unquote(link.group(1)).replace('.html', '').split('/')[-1].split('-')
        value = segments[index] if len(segments) > index else ''
        if key == 'sort' and value == 'time':
          continue
        values.append({'n': self._plainText(link.group(2)), 'v': value})
      if key == 'sort':
        values.insert(0, {'n': '时间', 'v': ''})
      groups.append({'key': key, 'name': title, 'value': values})
    return groups

  def homeVideoContent(self):
    html = self.fetch(self.HOST + '/')
    return {'list': self._parseCards(html)}

  # ======================== 分类(剧集库 /list/, 支持 剧情/地区/语言/年份/字母/排序 筛选)
  def categoryContent(self, tid, pg, filter, extend):
    page = max(self._toInt(pg, 1), 1)
    params = extend or {}
    area = (params.get('area', '') or '').strip()
    genre = (params.get('genre', '') or '').strip()
    lang = (params.get('lang', '') or '').strip()
    year = (params.get('year', '') or '').strip()
    letter = (params.get('letter', '') or '').strip()
    sort = (params.get('sort', '') or '').strip()
    url = _buildListUrl(tid, area=area, genre=genre, lang=lang,
                        year=year, page=page, sort=sort, letter=letter)
    html = self.fetch(url)
    cards = self._parseCards(html)
    pageCount = self._parsePageCount(html) or (page if page > 1 else 1)
    if cards:
      pageCount = max(pageCount, page)
    return {'list': cards, 'page': page, 'pagecount': pageCount,
            'limit': 30, 'total': len(cards)}

  def _parsePageCount(self, html):
    """从 mxtheme 列表分页 HTML 提取最大页码(尾页)"""
    if not html:
      return 0
    best = 0
    for match in re.finditer(r'href="(/list/[^"]*?)"\s+class="page-link[^"]*page-next[^"]*"[^>]*title="尾页"', html, re.I):
      href = match.group(1)
      segments = href.split('/')[-1].replace('.html', '').split('-')
      for segment in reversed(segments[:-1]):
        if segment.isdigit():
          best = max(best, int(segment))
          break
    if not best:
      for match in re.finditer(r'class="page-link[^"]*"[^>]*>(\d+)</a>', html):
        if match.group(1).isdigit():
          best = max(best, int(match.group(1)))
    return best

  # ======================== 详情
  def detailContent(self, ids):
    vodId = re.sub(r'\D', '', str(ids[0] if isinstance(ids, list) else ids))
    if not vodId:
      return {'list': []}
    html = self.fetch(f'{self.HOST}/v/{vodId}.html')
    if not html:
      return {'list': []}
    vod = {
      'vod_id': vodId,
      'vod_name': self._firstMatch(html, [r'<h1[^>]*>([^<]+)</h1>',
                                          r'<h2[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h2>',
                                          r'<title>([^<\-]+?)(?:\s*[-_–]|详情|在线)', r'<title>([^<]+)']),
      'vod_pic': self._absoluteUrl(self._firstMatch(html, [r'data-original="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                                                          r'class="[^"]*module-item-pic[^"]*"[^>]*>[\s\S]{0,200}?data-original="([^"]+)"'])),
      'vod_year': '',
      'vod_area': self._pickField(html, '地区'),
      'vod_remarks': (self._pickField(html, '状态') or self._pickField(html, '连载')
                      or self._pickField(html, '备注') or self._pickField(html, '更新')),
      'vod_actor': self._pickField(html, '主演'),
      'vod_director': self._pickField(html, '导演') or self._pickField(html, '编剧'),
      'vod_content': self._extractIntro(html),
      'type_name': self._pickField(html, '类型'),
      'vod_play_from': '', 'vod_play_url': '',
    }
    vod['vod_name'] = re.sub(r'\s*[-_–]\s*.*$', '', vod['vod_name']).strip()
    vod['vod_content'] = re.sub(r'^(?:剧情简介|简介|介绍|剧情)\s*[:：]?\s*', '', self._plainText(vod['vod_content']))[:800]
    titled = re.findall(r'module-info-tag-link"><a[^>]*title="([^"]+)"', html)
    yearMatch = re.search(r'(?:19|20)\d{2}', self._pickField(html, '年份') or self._pickField(html, '上映'))
    vod['vod_year'] = next((text.strip() for text in titled if re.fullmatch(r'(?:19|20)\d{2}', text.strip())),
                           yearMatch.group(0) if yearMatch else '')
    if not vod['vod_area']:
      vod['vod_area'] = next((text for text in titled if text and not re.fullmatch(r'\d{4}', text)), '')
    if not vod['type_name']:
      tags = []
      for match in re.finditer(r'module-info-tag-link">\s*<a[^>]*?(?:title="([^"]*)")?[^>]*>([^<]*)</a>', html):
        tag = match.group(1) or match.group(2)
        if tag:
          tags.append(tag.strip())
      vod['type_name'] = ','.join(tags[2:]) if len(tags) > 2 else (tags[-1] if tags else '')
    playFrom, playUrl = self._parsePlayList(html, vodId)
    vod['vod_play_from'] = playFrom
    vod['vod_play_url'] = playUrl
    return {'list': [vod]} if vod['vod_name'] else {'list': []}

  @staticmethod
  def _pickField(html, label):
    for currentLabel in (label, label.upper()):
      marker = 'module-info-item-title'
      searchPos = 0
      while True:
        index = html.find(marker, searchPos)
        if index < 0:
          break
        tagEnd = html.find('>', index)
        if tagEnd < 0:
          break
        closeEnd = html.find('</', tagEnd)
        if closeEnd < 0:
          break
        labelText = re.sub(r'<[^>]+>', '', html[tagEnd + 1:closeEnd]).strip()
        cleanLabel = re.sub(r'[:：]', '', labelText)
        if cleanLabel == currentLabel or labelText.rstrip('：:') == currentLabel.rstrip('：:'):
          contentStart = html.find('module-info-item-content">', closeEnd)
          if contentStart >= 0:
            contentStart += len('module-info-item-content">')
            depth = 1
            position = contentStart
            while position < len(html) and depth > 0:
              if html.startswith('<div ', position) or html.startswith('<div>', position):
                depth += 1
              elif html.startswith('</div>', position):
                depth -= 1
                if depth == 0:
                  break
              position += 1
            content = html[contentStart:position]
            segment = re.sub(r'<[^>]+>', '', content).replace('&nbsp;', ',').replace('/', ',').strip()
            segment = re.sub(r',+', ',', segment).strip(',')
            if segment:
              return segment
        searchPos = index + len(marker)
      match = re.search(rf'>\s*{re.escape(currentLabel)}\s*[:：]\s*</[^>]+>\s*([^<]+)', html, re.S | re.I)
      if not match:
        match = re.search(rf'{re.escape(currentLabel)}\s*[:：]\s*<[^>]+>\s*([^<]+)', html, re.S | re.I)
      if not match:
        match = re.search(rf'<span[^>]*>\s*{re.escape(currentLabel)}\s*[:：]?</span>\s*<[^>]+>\s*([^<]+)', html, re.S | re.I)
      if match:
        segment = re.sub(r'<[^>]+>', '', match.group(1)).replace('&nbsp;', ',').strip()
        segment = re.sub(r',+', ',', segment).strip(',')
        if segment:
          return segment
    return ''

  def _parsePlayList(self, html, vodId):
    """解析播放源和剧集: /play/ID-SID-NID.html 分组"""
    names = []
    for match in re.finditer(r'class="[^"]*module-tab-item[^"]*tab-item[^"]*"[^>]*data-dropdown-value="([^"]+)"', html, re.I):
      names.append(match.group(1).strip())
    if not names:
      for match in re.finditer(r'class="[^"]*tab-item[^"]*"[^>]*>([\s\S]{0,100}?)</', html, re.I):
        name = self._plainText(match.group(1))
        if name and name not in ('选择播放源', '更多', '展开', '收起', '选集播放'):
          names.append(name)
    if not names:
      for match in re.finditer(r'<a[^>]*class="[^"]*tab-item[^"]*"[^>]*>([\s\S]{0,100}?)</a>', html, re.I):
        name = self._plainText(match.group(1))
        if name and name not in ('选择播放源', '更多', '展开', '收起'):
          names.append(name)
    groups, order = {}, []
    for match in re.finditer(r'href="(/play/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([\s\S]{0,80}?)</a>', html, re.I):
      if match.group(2) != vodId:
        continue
      sourceId, episodeId = int(match.group(3)), int(match.group(4))
      spanMatch = re.search(r'<span[^>]*>([^<]+)</span>', match.group(5), re.I)
      name = self._plainText(spanMatch.group(1)) if spanMatch else self._plainText(match.group(5))
      name = re.sub(r'\s+', '', name) or ('第%02d集' % episodeId)
      if name in ('立即播放', '立刻播放', '播放', '立即观看', '在线播放') or ('播放' in name and len(name) <= 5):
        name = '第%02d集' % episodeId
      if sourceId not in groups:
        groups[sourceId] = {}
        order.append(sourceId)
      if episodeId not in groups[sourceId]:
        groups[sourceId][episodeId] = (name[:40], match.group(1))
    if not groups:
      return '', ''
    playFroms, playUrls = [], []
    for index, sourceId in enumerate(sorted(order)):
      sourceName = names[index] if index < len(names) else '线路%d' % (index + 1)
      episodes = [groups[sourceId][key] for key in sorted(groups[sourceId].keys())]
      playFroms.append(sourceName)
      playUrls.append('#'.join('%s$%s' % (title.strip(), self._absoluteUrl(url)) for title, url in episodes))
    return '$$$'.join(playFroms), '$$$'.join(playUrls)

  # ======================== 搜索
  def searchContent(self, key, quick, pg='1'):
    page = self._toInt(pg, 1)
    keyword = str(key or '').strip()
    if not keyword:
      return {'list': [], 'page': page}
    if page > 1:
      return {'list': [], 'page': page}
    encoded = urllib.parse.quote(keyword, safe='')
    url = f'{self.HOST}/search/{encoded}-------------.html'
    html = self.fetch(url)
    for _ in range(3):
      if html and '请不要频繁操作' in html:
        time.sleep(3.2)
        html = self.fetch(url)
      else:
        break
    cards = self._parseCards(html)
    return {'list': cards, 'page': page}

  # ======================== 播放
  def playerContent(self, flag, id, vipFlags):
    if self.isVideoFormat(id):
      return {'parse': 0, 'url': id, 'header': {'User-Agent': self.UA, 'Referer': self.HOST + '/'}}
    playUrl = str(id)
    if not playUrl.startswith('http'):
      playUrl = self.HOST + '/play/' + re.sub(r'^.*/play/', '', playUrl)
    html = self.fetch(playUrl)
    if not html:
      return {'parse': 1, 'url': playUrl, 'header': self._buildHeaders(playUrl)}
    playerData = self._extractJson(html, 'player_aaaa')
    if playerData:
      raw = playerData.get('url', '').replace('\\/', '/').replace('\\u002F', '/')
      if self.isVideoFormat(raw):
        return {'parse': 0, 'url': raw, 'header': {'User-Agent': self.UA, 'Referer': self.HOST + '/'}}
      encryptMode = playerData.get('encrypt', 0)
      if encryptMode == 1 and raw:
        try:
          decoded = urllib.parse.unquote(raw)
          if self.isVideoFormat(decoded):
            return {'parse': 0, 'url': decoded, 'header': {'User-Agent': self.UA, 'Referer': self.HOST + '/'}}
        except (ValueError, TypeError):
          pass
      if encryptMode == 2 and raw:
        try:
          decoded = urllib.parse.unquote(base64.b64decode(raw).decode('utf-8', 'ignore'))
          if self.isVideoFormat(decoded):
            return {'parse': 0, 'url': decoded, 'header': {'User-Agent': self.UA, 'Referer': self.HOST + '/'}}
        except (ValueError, TypeError):
          pass
      if raw:
        m3u8 = self._resolvePlay(raw, playUrl)
        if m3u8:
          return {'parse': 0, 'url': m3u8, 'header': {'User-Agent': self.UA, 'Referer': self.HOST + '/'}}
        parseUrl = self.HOST + '/lvplayer/index.php?vid=' + raw
        return {
          'parse': 1,
          'url': parseUrl,
          'header': {'User-Agent': self.UA, 'Referer': playUrl, 'Cookie': self._cookieStr()},
          'click': 'document.querySelector("#start").click()',
        }
    for pattern in (r'[?&](?:url|v|m3u8|playurl|src|video)=([^"\'&\s<>]+?\.(?:m3u8|mp4)[^"\'&\s<>]*)',
                    r'(https?:[^"\'\\\s<>]+?\.m3u8[^"\'\\\s<>]*)'):
      urlMatch = re.search(pattern, html, re.I)
      if urlMatch:
        candidate = urllib.parse.unquote(urlMatch.group(1).replace('\\/', '/'))
        if self.isVideoFormat(candidate):
          return {'parse': 0, 'url': candidate, 'header': {'User-Agent': self.UA, 'Referer': self.HOST + '/'}}
    return {'parse': 1, 'url': playUrl, 'header': self._buildHeaders(playUrl)}

  # ======================== 播放解析: 调用api.php + decode2解密
  def _resolvePlay(self, vid, playUrl):
    apiUrl = self.HOST + '/lvplayer/api.php'
    headers = {
      'User-Agent': self.UA,
      'Referer': playUrl,
      'X-Requested-With': 'XMLHttpRequest',
      'Cookie': self._cookieStr(),
    }
    for _ in range(8):
      try:
        rsp = self.s.post(apiUrl, data={'vid': vid}, headers=headers, timeout=10)
        playInfo = rsp.json().get('data', {})
      except (requests.RequestException, ValueError) as err:
        print('皮皮驴: 播放接口请求失败', err)
        continue
      cipher = playInfo.get('url', '')
      urlMode = int(playInfo.get('urlmode', 0) or 0)
      if urlMode == 2:
        url = self._decode2(cipher)
        if url and url.startswith('http'):
          return url
      if urlMode == 1:
        url = self._decode1(cipher)
        if url and url.startswith('http'):
          return url
        url = self._decode2(cipher)
        if url and url.startswith('http'):
          return url
    return ''

  # ======================== 解密辅助
  @staticmethod
  def _fixBase64(value):
    value = re.sub(r'[^A-Za-z0-9+/=]', '', str(value).strip())
    return value + '=' * (-len(value) % 4)

  def _decode1(self, cipher):
    try:
      raw = base64.b64decode(self._fixBase64(cipher))
      key = hashlib.md5(b'#tips').hexdigest().encode('utf-8')
      decodedBytes = bytearray(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
      decodedText = self._fixBase64(decodedBytes.decode('utf-8', 'ignore'))
      return urllib.parse.unquote(base64.b64decode(decodedText).decode('utf-8', 'ignore'))
    except (ValueError, TypeError):
      return ''

  def _decode2(self, cipher):
    try:
      raw = base64.b64decode(self._fixBase64(cipher)).decode('utf-8', 'ignore')
      charMap = 'PXhw7UT1B0a9kQDKZsjIASmOezxYG4CHo5Jyfg2b8FLpEvRr3WtVnlqMidu6cN'
      return urllib.parse.unquote(''.join(
        charMap[(charMap.find(char) + 59) % 62] if charMap.find(char) != -1 else char
        for char in raw[1::3]
      ).strip())
    except (ValueError, TypeError):
      return ''

  # ======================== 配置
  config = {
    "player": {},
  }
  header = {}

  def localProxy(self, param):
    return [200, 'video/MP2T', '', '']
