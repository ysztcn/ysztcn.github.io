#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File  : NO视频.py
# Author: DaShenHan&道长-----先苦后甜，任凭晚风拂柳颜------
# Author's Blog: https://blog.csdn.net/qq_32394351
# Date  : 2024/11/10

import sys

sys.path.append('..')
try:
    from base.spider import BaseSpider
    from base.htmlParser import jsoup
except ImportError:
    from t4.base.spider import BaseSpider
    from t4.base.htmlParser import jsoup


class Spider(BaseSpider):  # 元类 默认的元类 type
    module = None
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
    }
    host = "https://www.novipnoad.net"
    jsp = jsoup(host)

    def getDependence(self):
        # return ['base_spider']
        return []

    def getName(self):
        return "NO视频"

    def init(self, extend=""):
        print(f"============依赖列表:{extend}============")
        ext = self.extend
        print(f"============ext:{ext}============")
        # 装载模块，这里只要一个就够了
        if isinstance(extend, list):
            for lib in extend:
                if '.Spider' in str(type(lib)):
                    self.module = lib
                    break

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "电影": "movie",
            "剧集": "tv",
            "综艺": "shows",
            "动画": "anime",
            "音乐": "music",
            "短片": "short",
            "其他": "ohter"
        }
        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })

        result['class'] = classes
        # if (filter):
        #     result['filters'] = self.config['filter']
        return result

    def homeVideoContent(self):
        result = {
            'list': []
        }
        if self.module:
            result = self.module.homeVideoContent()
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = f'{self.host}/{tid}/page/{pg}/'
        r = self.fetch(url, headers=self.headers)
        ret = r.text
        pdfa = self.jsp.pdfa
        pdfh = self.jsp.pdfh
        pd = self.jsp.pd
        aList = pdfa(ret, '.video-listing-content&&.qv_tooltip')
        videos = []
        for a in aList:
            na = pdfh(a, '.qv_tooltip&&title')
            name = pdfh(na, 'a&&title')
            realname = self.regStr(name, "】(.*?)【")
            remark = self.regStr(name, "(【.*?】)")
            pic = pd(a, 'img&&data-original', url)
            vid = pd(a, 'a&&href', url)
            videos.append({
                "vod_id": vid,
                "vod_name": realname,
                "vod_pic": pic,
                "vod_remarks": remark
            })

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, array):
        tid = array[0]
        vod = {
            "vod_id": tid,
            "vod_name": "",
            "vod_pic": "",
            "type_name": "",
            "vod_content": "有情提醒：请别相信影片中的广告，以防被骗。",
            "vod_play_from": "精彩线路",
            "vod_play_url": "播放$" + tid
        }
        result = {
            'list': [
                vod
            ]
        }
        return result

    def searchContent(self, key, quick=False, pg=1):
        url = f'https://www.novipnoad.net/?s={key}'
        r = self.fetch(url, headers=self.headers)
        ret = r.text
        pdfa = self.jsp.pdfa
        pdfh = self.jsp.pdfh
        pd = self.jsp.pd
        aList = pdfa(ret, '.search-listing-content&&.video-item')
        videos = []
        for a in aList:
            name = pdfh(a, 'a&&title')
            pic = pd(a, 'img&&data-original', url)
            mark = ''
            content = pdfh(a, 'p&&Text')
            vid = pd(a, 'a&&href', url)
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": mark,
                "vod_content": content
            })

        result = {
            'list': videos
        }
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 1
        result["playUrl"] = ""
        result["url"] = id
        result["header"] = self.headers
        result["click"] = "document.getElementById('player-embed').click()"
        return result

    def localProxy(self, params):
        return [200, "video/MP2T", ""]


if __name__ == '__main__':
    from t4.core.loader import t4_spider_init

    spider = Spider()
    t4_spider_init(spider)
    print(spider.homeContent(True))
    print(spider.homeVideoContent())
    print(spider.categoryContent('movie', 1, True, {}))
    print(spider.detailContent(['https://www.novipnoad.net/movie/147890.html']))
    # print(spider.detailContent(['https://www.novipnoad.net/tv/hongkong/137568.html']))
    print(spider.playerContent('精彩线路', 'https://www.novipnoad.net/movie/147890.html', None))
    print(spider.searchContent('大厦'))
