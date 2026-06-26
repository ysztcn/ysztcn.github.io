# coding=utf-8
#!/usr/bin/env python3
import re
import sys
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
import json

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from pathlib import Path
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "影视工厂"

    def init(self, extend=""):
        self.host = "https://www.ysgc02.cc"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.host
        }
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)
        self.retry_count = 3
        self.timeout = 30

        self.tidMap = {
            '1': 'd2',   # 电影
            '2': 'd1',   # 连续剧
            '4': 'd3',   # 动漫
        }

    def fetch(self, url, timeout=None):
        if timeout is None:
            timeout = self.timeout
        for i in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=timeout, verify=False)
                response.encoding = 'utf-8'
                if response.status_code == 200:
                    return response
                else:
                    print(f"请求失败，状态码: {response.status_code}")
            except Exception as e:
                print(f"请求失败 ({i+1}/{self.retry_count}): {e}")
                if i < self.retry_count - 1:
                    time.sleep(1)
        return None

    def homeContent(self, filter):
        result = {
            "class": [
                {'type_id': '2', 'type_name': '电视剧'},
                {'type_id': '1', 'type_name': '电影'},
                {'type_id': '4', 'type_name': '动漫'},
            ],
            "filters": self._get_filters(),
            "list": []
        }
        rsp = self.fetch(self.host)
        if rsp and rsp.status_code == 200:
            result['list'] = self._extract_videos_from_html(rsp.text)
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 99, "limit": 20, "total": 1980}
        site_tid = self.tidMap.get(tid, 'd1')
        url = f"{self.host}/type/{site_tid}-{pg}.html" if int(pg) > 1 else f"{self.host}/type/{site_tid}.html"
        rsp = self.fetch(url)
        if rsp and rsp.status_code == 200:
            result['list'] = self._extract_videos_from_html(rsp.text)
            pagecount = self._extract_pagecount(rsp.text)
            if pagecount:
                result['pagecount'] = pagecount
        return result

    def searchContent(self, key, quick, pg=1):
        result = {"list": []}
        search_key = urllib.parse.quote(key)
        url = f"{self.host}/search/--.html?wd={search_key}"
        rsp = self.fetch(url)
        if rsp and rsp.status_code == 200:
            result['list'] = self._extract_videos_from_html(rsp.text)
        return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        url = f"{self.host}/a/b{vid}.html"
        rsp = self.fetch(url)
        if not rsp or rsp.status_code != 200:
            return result

        html = rsp.text
        play_from, play_url = self._extract_play_info(html, vid)
        if play_from and play_url:
            result['list'] = [{
                'vod_id': vid,
                'vod_name': self._extract_title(html),
                'vod_pic': self._extract_pic(html),
                'type_name': self._extract_category(html),
                'vod_year': self._extract_year(html),
                'vod_area': self._extract_area(html),
                'vod_actor': self._extract_actor(html),
                'vod_director': self._extract_director(html),
                'vod_content': self._extract_desc(html),
                'vod_remarks': self._extract_remarks(html),
                'vod_play_from': "$$$".join(play_from),
                'vod_play_url': "$$$".join(play_url)
            }]
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 1, "playUrl": "", "url": ""}
        if id:
            result["url"] = self._fix_url(f"/player/{id}")
        return result

    def _get_filters(self):
        return {
            "1": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "动作片", "v": "6"}, {"n": "喜剧片", "v": "7"},
                {"n": "爱情片", "v": "8"}, {"n": "科幻片", "v": "9"}, {"n": "恐怖片", "v": "11"},
                {"n": "剧情片", "v": "10"}, {"n": "战争片", "v": "12"}, {"n": "纪录片", "v": "21"},
                {"n": "悬疑片", "v": "32"}, {"n": "动画片", "v": "33"}, {"n": "犯罪片", "v": "34"},
                {"n": "奇幻片", "v": "35"}, {"n": "其他片", "v": "60"}
            ]}],
            "2": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "国产剧", "v": "13"}, {"n": "港台剧", "v": "14"},
                {"n": "日剧", "v": "15"}, {"n": "韩剧", "v": "33"}, {"n": "欧美剧", "v": "16"},
                {"n": "海外剧", "v": "17"}
            ]}],
            "4": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "国产动漫", "v": "31"}, {"n": "日本动漫", "v": "32"},
                {"n": "欧美动漫", "v": "42"}, {"n": "其他动漫", "v": "43"}
            ]}]
        }

    def _extract_videos_from_html(self, html):
        videos = []
        soup = BeautifulSoup(html, 'html.parser')

        items = soup.select('ul.stui-vodlist > li')
        if not items:
            items = soup.select('ul.stui-vodlist__text > li')

        for item in items:
            link = item.select_one('a[href*="/a/b"]')
            if not link:
                continue

            href = link.get('href', '')
            vid_match = re.search(r'/a/b(\d+)\.html', href)
            if not vid_match:
                continue

            vid = vid_match.group(1)
            title = link.get('title', '') or link.get_text(strip=True) or ''

            pic = link.get('data-original', '') or ''
            pic = self._fix_url(pic)

            note = ''
            note_elem = item.select_one('.pic-text') or link.select_one('.text-muted')
            if note_elem:
                note = self._simplify_remarks(note_elem.get_text(strip=True))

            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': note
            })

        return videos

    def _extract_pagecount(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        page_links = soup.select('.stui-page a')
        nums = []
        for a in page_links:
            text = a.get_text(strip=True)
            if text.isdigit():
                nums.append(int(text))
        return max(nums) if nums else None

    def _extract_play_info(self, html, vid):
        play_from, play_url = [], []
        soup = BeautifulSoup(html, 'html.parser')

        playlist = soup.select_one('.stui-content__playlist')
        if not playlist:
            playlist = soup.select_one('ul.stui-content__playlist')
        if not playlist:
            playlist = soup

        source_name = "聚合云播"
        source_elem = soup.select_one('.playlist .title, .b.playlist .title, .stui-pannel-box.b.playlist .stui-pannel_hd .title')
        if source_elem:
            name = source_elem.get_text(strip=True)
            if name:
                source_name = name

        episodes = []
        for a in playlist.find_all('a', href=re.compile(r'/player/')):
            href = a.get('href', '')
            ep_name = a.get_text(strip=True) or ''
            ep_id = href.replace('/player/', '').replace('.html', '')
            if ep_id:
                episodes.append(f"{ep_name}${ep_id}")

        if episodes:
            play_from = [source_name]
            play_url = ["#".join(episodes)]

        return play_from, play_url

    def _extract_title(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        title_elem = soup.select_one('h1.title')
        if title_elem:
            return title_elem.get_text(strip=True)
        return ""

    def _extract_pic(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.select_one('.stui-content__thumb img.lazyload')
        if img:
            pic = img.get('data-original', '') or img.get('src', '') or ''
            return self._fix_url(pic)
        return ""

    def _extract_category(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        data_p = soup.select_one('.stui-content__detail .data')
        if data_p:
            span = data_p.find('span', string=re.compile(r'类型'))
            if span:
                a = span.find_next_sibling('a')
                if a:
                    return a.get_text(strip=True)
        return ""

    def _extract_year(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        data_p = soup.select_one('.stui-content__detail .data')
        if data_p:
            span = data_p.find('span', string=re.compile(r'年份'))
            if span:
                a = span.find_next_sibling('a')
                if a:
                    return a.get_text(strip=True)
        return ""

    def _extract_area(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        data_p = soup.select_one('.stui-content__detail .data')
        if data_p:
            span = data_p.find('span', string=re.compile(r'地区'))
            if span:
                a = span.find_next_sibling('a')
                if a:
                    return a.get_text(strip=True)
        return ""

    def _extract_actor(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        data_ps = soup.select('.stui-content__detail .data')
        for p in data_ps:
            span = p.find('span', string=re.compile(r'主演'))
            if span:
                actors = []
                for sib in span.find_next_siblings():
                    if sib.name == 'a':
                        actors.append(sib.get_text(strip=True))
                return " ".join(actors) if actors else ""
        return ""

    def _extract_director(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        data_ps = soup.select('.stui-content__detail .data')
        for p in data_ps:
            span = p.find('span', string=re.compile(r'导演'))
            if span:
                directors = []
                for sib in span.find_next_siblings():
                    if sib.name == 'a':
                        directors.append(sib.get_text(strip=True))
                return " ".join(directors) if directors else ""
        return ""

    def _extract_desc(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        desc = soup.select_one('.stui-content__detail .desc')
        if desc:
            span = desc.find('span')
            if span:
                span.extract()
            return desc.get_text(strip=True)
        return ""

    def _simplify_remarks(self, text):
        text = re.sub(r'更至更新至', '更至', text)
        text = re.sub(r'第(?=\d+)', '', text)
        text = re.sub(r'集全$', '集', text)
        return text

    def _extract_remarks(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        remark = soup.select_one('.stui-content__thumb .pic-text')
        if remark:
            return self._simplify_remarks(remark.get_text(strip=True))
        return ""

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith('//'):
            return 'http:' + url
        if url.startswith('/'):
            return self.host.rstrip('/') + url
        if not url.startswith('http'):
            return self.host + url
        return url

if __name__ == "__main__":
    spider = Spider()
    spider.init()

    home_result = spider.homeContent({})
    print(f"首页分类: {[c['type_name'] for c in home_result['class']]}")
    print(f"首页视频数量: {len(home_result['list'])}")
    for i, item in enumerate(home_result['list'][:5], 1):
        print(f"{i}. 标题: {item['vod_name']}, ID: {item['vod_id']}, 备注: {item['vod_remarks']}")

    print("\n测试分类页（电影）:")
    cat_result = spider.categoryContent("1", 1, None, None)
    print(f"电影数量: {len(cat_result['list'])}")
    for i, item in enumerate(cat_result['list'][:3], 1):
        print(f"{i}. 标题: {item['vod_name']}, ID: {item['vod_id']}")

    print("\n测试搜索功能:")
    search_result = spider.searchContent("仙逆", False, 1)
    print(f"搜索结果数量: {len(search_result['list'])}")
    for i, item in enumerate(search_result['list'][:5], 1):
        print(f"{i}. 标题: {item['vod_name']}, ID: {item['vod_id']}, 图片: {item['vod_pic']}")

    if search_result['list']:
        first_video = search_result['list'][0]
        detail_result = spider.detailContent([first_video['vod_id']])
        if detail_result['list']:
            video_info = detail_result['list'][0]
            print(f"\n视频详情:")
            print(f"标题: {video_info['vod_name']}")
            print(f"类型: {video_info['type_name']}")
            print(f"年份: {video_info['vod_year']}")
            print(f"地区: {video_info['vod_area']}")
            print(f"演员: {video_info['vod_actor']}")
            print(f"导演: {video_info['vod_director']}")
            print(f"简介: {video_info['vod_content'][:100]}...")
            print(f"播放源: {video_info['vod_play_from']}")
            print(f"播放列表: {video_info['vod_play_url'][:200]}...")
