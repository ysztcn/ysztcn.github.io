# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。

from base.spider import Spider
import re,sys,urllib3,requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.append('..')

class Spider(Spider):
    host = 'https://323433ssdfd.top'
    # Worker 地址：decode 接口请求体由 WASM 生成，需要在 Worker 中完成
    _worker_url = 'https://ddys-play.yszt.dpdns.org/api/decode'
    # 原站 web 端禁止 CO4K 平台解码（PLATFORM_NOT_ALLOWED），其 token 用 co 平台身份可正常换取
    _decode_alias = {'CO4K': 'co'}

    def _web_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json',
            'X-Client': '8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a',
            'web-sign': 'ddtvf65f3a83d6d9ad6f',
        }

    def homeContent(self, filter):
        response = self.fetch(
            f'{self.host}/api.php/web/index/home',
            headers=self._web_headers(), verify=False
        ).json()
        categories = response['data']['categories']
        videos, classes = [], []
        for cat in categories:
            type_name = cat.get('type_name') or cat.get('type_en') or ''
            classes.append({'type_id': type_name, 'type_name': type_name})
            videos.extend(self._arr2vods(cat.get('videos') or []))
        return {'class': classes, 'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        response = self.fetch(
            f'{self.host}/api.php/web/filter/vod',
            headers=self._web_headers(),
            verify=False,
            params={'type_name': tid, 'page': pg, 'sort': 'hits'}
        ).json()
        data = response.get('data', [])
        pagecount = response.get('pageCount', 999)
        return {'list': self._arr2vods(data), 'pagecount': pagecount, 'page': pg}

    def searchContent(self, key, quick, pg='1'):
        response = self.fetch(
            f'{self.host}/api.php/web/search/index',
            headers=self._web_headers(),
            verify=False,
            params={'wd': key, 'page': pg, 'limit': 15}
        ).json()
        data = response.get('data', [])
        pagecount = response.get('pageCount', 999)
        return {'list': self._arr2vods(data), 'pagecount': pagecount, 'page': pg}

    def _build_line(self, show_code, need_parse, play_url_str):
        """'第1集$url#第2集$url' 转成 '第1集$线路@是否解码@原始地址'，解码平台名按别名映射"""
        decode_from = self._decode_alias.get(show_code, show_code)
        urls = []
        for url_item in play_url_str.split('#'):
            if '$' in url_item:
                episode, url = url_item.split('$', 1)
                urls.append(f"{episode}${decode_from}@{need_parse}@{url}")
        return urls

    def detailContent(self, ids):
        response = self.fetch(
            f'{self.host}/api.php/web/vod/get_detail',
            headers=self._web_headers(),
            verify=False,
            params={'vod_id': ids[0]}
        ).json()
        data = response['data'][0]
        shows, play_urls = [], []
        raw_shows = data.get('vod_play_from', '').split('$$$')
        raw_urls_list = data.get('vod_play_url', '').split('$$$')
        players_map = {p['from']: p for p in (response.get('vodplayer') or [])}
        for show_code, urls_str in zip(raw_shows, raw_urls_list):
            p_info = players_map.get(show_code)
            if not p_info:
                continue
            urls = self._build_line(show_code, int(p_info.get('decode_status') or 0), urls_str)
            if urls:
                play_urls.append('#'.join(urls))
                shows.append(p_info.get('show') or show_code)
        # 合并聚合源（站外直链与爱奇艺/腾讯等），接口失败时保留详情页线路
        known_codes = set(raw_shows)
        try:
            agg_data = self.fetch(
                f'{self.host}/api.php/web/internal/search_aggregate',
                headers=self._web_headers(),
                verify=False,
                params={'vod_id': ids[0]}
            ).json().get('data') or []
        except Exception:
            agg_data = []
        for item in agg_data:
            show_code = item.get('vod_play_from') or ''
            if not show_code or show_code in known_codes:
                continue
            known_codes.add(show_code)
            urls = self._build_line(show_code, int(item.get('decode_status') or 0), item.get('vod_play_url') or '')
            if urls:
                play_urls.append('#'.join(urls))
                shows.append(item.get('site_name') or show_code)
        video = {
            'vod_id': data.get('vod_id'),
            'vod_name': data.get('vod_name'),
            'vod_pic': data.get('vod_pic'),
            'vod_remarks': data.get('vod_remarks'),
            'vod_year': data.get('vod_year'),
            'vod_area': data.get('vod_area'),
            'vod_actor': data.get('vod_actor'),
            'vod_director': data.get('vod_director'),
            'vod_content': data.get('vod_content'),
            'vod_play_from': '$$$'.join(shows),
            'vod_play_url': '$$$'.join(play_urls),
            'type_name': data.get('vod_class')
        }
        return {'list': [video]}

    def _worker_decode(self, raw_url, play_from):
        """调 Worker 换取播放地址，失败返回空串"""
        try:
            r = requests.get(
                self._worker_url,
                params={'url': raw_url, 'vodFrom': play_from},
                headers={'User-Agent': 'okhttp/4.12.0'},
                timeout=15, verify=False
            )
            j = r.json()
            if j.get('code') == 200:
                return j.get('data', '')
        except Exception:
            pass
        return ''

    def playerContent(self, flag, vid, vip_flags):
        play_from, need_parse, raw_url = vid.split('@', 2)
        # NBY 线路 token 含 | 分隔符，WASM 不支持，去掉 | 后部分
        if '|' in raw_url:
            raw_url = raw_url.split('|', 1)[0]
        url = raw_url
        if int(need_parse or 0) == 1:
            url = self._worker_decode(raw_url, play_from) or raw_url
        # 解码失败留下的长视频平台网页地址，交给系统解析
        jx = 1 if re.search(r'(?:www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili)\.com', url) else 0
        return {
            'jx': jx, 'parse': 0, 'url': url,
            'header': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        }

    def _arr2vods(self, arr):
        videos = []
        for i in arr:
            type_name = i.get('type_name') or ''
            vod_class = i.get('vod_class') or ''
            if vod_class:
                type_name = f"{type_name},{vod_class}" if type_name else vod_class
            videos.append({
                'vod_id': i['vod_id'],
                'vod_name': i['vod_name'],
                'vod_pic': i['vod_pic'],
                'vod_remarks': i['vod_remarks'],
                'type_name': type_name,
                'vod_year': i.get('vod_year')
            })
        return videos

    def init(self, extend=''):
        pass

    def homeVideoContent(self):
        response = self.fetch(
            f'{self.host}/api.php/web/index/home',
            headers=self._web_headers(), verify=False
        ).json()
        videos = self._arr2vods((response.get('data') or {}).get('recommend') or [])
        return {'list': videos}

    def getName(self):
        return '多多追剧'

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass
