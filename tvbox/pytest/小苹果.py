#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File  : 小苹果.py
# Author: DaShenHan&道长-----先苦后甜，任凭晚风拂柳颜------
# Author's Blog: https://blog.csdn.net/qq_32394351
# Date  : 2024/11/10

import sys

sys.path.append('..')
try:
    from base.spider import BaseSpider
except ImportError:
    from t4.base.spider import BaseSpider


class Spider(BaseSpider):  # 元类 默认的元类 type
    module = None

    def getDependence(self):
        # return ['base_spider']
        return []

    def getName(self):
        return "小苹果"

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
            "电影": "1",
            "剧集": "2",
            "综艺": "3",
            "动漫": "4"
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

    host = "http://item.xpgtv.xyz"
    header = {
        'User-Agent': 'okhttp/3.12.11',
        'version': 'XPGBOX com.phoenix.tv1.3.3',
        'token': 'dlsrzQiVkxgxYnpvfhTfMJlsPK3Y9zlHl+hovVfGeMNNEkwoyDQr1YEuhaAKbhz0SmxUfIXFGORrWeQrfDJQZtBxGWY/wnqwKk1McYhZES5fuT4ODVB13Cag1mDiMRIi8JQuZCJxQLfu8EEFUShX8dXKMHAT5jWTrDSQTJXwCDT2KRB4TUA7QF0pZbpvQPLVVzXf',
        'user_id': 'XPGBOX',
        'token2': 'XFxIummRrngadHB4TCzeUaleebTX10Vl/ftCvGLPeI5tN2Y/liZ5tY5e4t8=',
        'hash': 'c56f',
        'timestamp': '1727236846'
    }

    def homeVideoContent(self):
        rsp = self.fetch(f"{self.host}/api.php/v2.main/androidhome", headers=self.header)
        root = rsp.json()['data']['list']
        videos = []
        for vodd in root:
            for vod in vodd['list']:
                videos.append({
                    "vod_id": vod['id'],
                    "vod_name": vod['name'],
                    "vod_pic": vod['pic'],
                    "vod_remarks": vod['score']
                })
        result = {
            'list': videos
        }
        if self.module:
            result = self.module.homeVideoContent()
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = f'{self.host}/api.php/v2.vod/androidfilter10086?page={pg}&type={tid}'
        rsp = self.fetch(url, headers=self.header)
        root = rsp.json()['data']
        videos = []
        for vod in root:
            videos.append({
                "vod_id": vod['id'],
                "vod_name": vod['name'],
                "vod_pic": vod['pic'],
                "vod_remarks": vod['score']
            })
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, array):
        _id = array[0]
        url = f'{self.host}/api.php/v3.vod/androiddetail2?vod_id={_id}'
        rsp = self.fetch(url, headers=self.header)
        root = rsp.json()['data']
        node = root['urls']
        d = [it['key'] + "$" + f"http://c.xpgtv.net/m3u8/{it['url']}.m3u8" for it in node]
        vod = {
            "vod_name": root['name'],
            'vod_play_from': '小苹果',
            'vod_play_url': '#'.join(d),
        }
        result = {
            'list': [
                vod
            ]
        }
        return result

    def searchContent(self, key, quick=False, pg=1):
        url = f'{self.host}/api.php/v2.vod/androidsearch10086?page={pg}&wd={key}'
        rsp = self.fetch(url, headers=self.header)
        root = rsp.json()['data']
        videos = []
        for vod in root:
            videos.append({
                "vod_id": vod['id'],
                "vod_name": vod['name'],
                "vod_pic": vod['pic'],
                "vod_remarks": vod['score']
            })
        result = {
            'list': videos
        }
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 0
        result["url"] = id
        result["header"] = self.header
        return result

    def localProxy(self, params):
        return [200, "video/MP2T", ""]


if __name__ == '__main__':
    from t4.core.loader import t4_spider_init

    spider = Spider()
    t4_spider_init(spider)
    print(spider.homeContent(True))
    print(spider.homeVideoContent())
    print(spider.detailContent([123014]))
    print(spider.playerContent('01', 'http://c.xpgtv.net/m3u8/YlcrYS9DdmZwWlh5a3FWaTFJUGJUVDRUTkcxUWpVQzg=.m3u8', None))
    print(spider.searchContent('斗罗大陆'))
