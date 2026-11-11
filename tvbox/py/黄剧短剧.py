# -*- coding: utf-8 -*-
# 黄剧短剧 TVBox 四壳通用 Python 源（适配 5.8.5+ 规范）
# 站点：https://huangju.net/theater
# 数据后端：https://api.huangju.net
# 仅标准库；网络优先走宿主 self.fetch（需读 Set-Cookie 做 CloudFront 签名），无宿主时 urllib 兜底
import re
import json
import time
import gzip
import base64
import threading
import http.client
from collections import OrderedDict, deque
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider:
        def init(self, extend=""):
            pass

# 未成年相关关键词（命中即跳过，不采集不展示）
_MINOR_KEYS = ["萝莉", "幼女", "未成年", "loli", "teen", "schoolgirl",
               "儿童", "幼童", "童贞", "少女", "正太", "初中生", "小学生"]

_CF_COOKIES = ("CloudFront-Policy", "CloudFront-Signature", "CloudFront-Key-Pair-Id")

# 站点主清单只有 480/720 两档，播放器按带宽自动选档时几乎总是停在 480，画面明显发糊。
# 这里把清晰度拆成独立线路暴露，播放时由爬虫直接锁定对应变体，播放器没有可降档的选项。
_HJ_QUALITY_LINES = (("720", "黄剧720"), ("480", "黄剧480"))
_EPISODE_PREFIX = "hj-episode-v1:"


def _split_episode_token(token):
    """把 'hj-episode-v1:<高度>:<ep_id>' 解析为 (高度, ep_id)；兼容裸 ep_id（默认最高档）。"""
    body = str(token or "").strip()
    if body.startswith(_EPISODE_PREFIX):
        body = body[len(_EPISODE_PREFIX):]
    if ":" in body:
        head, tail = body.split(":", 1)
        if head.isdigit() and tail:
            return head, tail
    return "720", body


# 到 video.huangju.net(CloudFront) 的 TLS 握手实测 2~9 秒且经常超时，每个分片新建连接会把
# 2 秒分片的下载耗时拖到 14~21 秒，播放器必然卡顿。这里按主机维护空闲连接池复用连接。
_POOL_LOCK = threading.Lock()
_POOL = {}
_POOL_MAX_IDLE = 3


def _pool_key(url):
    p = urllib.parse.urlsplit(url)
    scheme = (p.scheme or "https").lower()
    port = p.port or (443 if scheme == "https" else 80)
    return (scheme, p.hostname or "", port)


def _conn_take(key, timeout):
    """从池里取一条还活着的连接，没有就新建。"""
    with _POOL_LOCK:
        idle = _POOL.get(key) or []
        while idle:
            conn = idle.pop()
            if getattr(conn, "sock", None) is not None:
                return conn
            try:
                conn.close()
            except Exception:
                pass
    scheme, host, port = key
    if scheme == "https":
        return http.client.HTTPSConnection(host, port, timeout=timeout)
    return http.client.HTTPConnection(host, port, timeout=timeout)


def _conn_put(key, conn, reusable):
    """用完归还；服务端已关连接或池已满时直接关闭。"""
    if conn is None:
        return
    if not reusable or getattr(conn, "sock", None) is None:
        try:
            conn.close()
        except Exception:
            pass
        return
    with _POOL_LOCK:
        idle = _POOL.setdefault(key, [])
        if len(idle) >= _POOL_MAX_IDLE:
            try:
                conn.close()
            except Exception:
                pass
            return
        idle.append(conn)


def _gunzip(hdrs, body):
    if (hdrs.get("content-encoding") or "").lower() == "gzip" and body[:2] == b"\x1f\x8b":
        return gzip.decompress(body)
    return body


# 播放器串行取清单和分片，上游任何一次抖动都会把缓冲抽干，表现为播几秒就停下来等。
# 实测同一个主机的并发连接会把带宽打到单连接的 1/5(单连接 3.4~5.0 Mbps，2 条连接
# 0.74 Mbps，4 条连接 0.13 Mbps)，所以所有回源排队交给一个取流线程串行执行：
# 播放器正在等的排到队首，预取的排到队尾，结果进内存缓存，同一时刻只有一条连接在跑。
_PREFETCH_AHEAD = 12
_CACHE_MAX_BYTES = 32 * 1024 * 1024
_CACHE_TTL = 300
_UP_TIMEOUT = 20       # 单次回源的 socket 超时
_LANE_WAIT = 120       # 播放器等一片的最长时间
_LOCK = threading.Condition()
_CACHE = OrderedDict()   # (kind, eid, key) -> (内容, 类型, 时间戳)
_CACHE_BYTES = [0]
_FLIGHT = {}             # job -> Event，已排队或正在取的对象
_HIGH = deque()          # 播放器正在等的任务
_LOW = deque()           # 预取任务
_SEG_ORDER = {}          # eid -> [分片地址...]，用于顺着清单往后预取
_PRE_MARK = [None, -2]   # [当前集, 播放器最近取到第几片]，预取窗口以此为起点
_LANE_THREAD = None


def _cached(job):
    """命中返回 (内容, 类型, 时间戳)，未命中或过期返回 None。调用方必须持有 _LOCK。"""
    item = _CACHE.get(job)
    if not item:
        return None
    if time.time() - item[2] > _CACHE_TTL:
        _CACHE.pop(job, None)
        _CACHE_BYTES[0] -= len(item[0])
        return None
    _CACHE.move_to_end(job)
    return item


def _seg_window():
    """当前集预取窗口内的分片任务。调用方必须持有 _LOCK。"""
    eid = _PRE_MARK[0]
    order = _SEG_ORDER.get(eid) or []
    if not order:
        return []
    i = _PRE_MARK[1]
    return [("seg", eid, u) for u in order[i + 1:i + 1 + _PREFETCH_AHEAD]]


def _mark_episode(eid, order):
    """登记这一集的分片顺序，预取窗口从第 0 片开始。"""
    with _LOCK:
        _SEG_ORDER[eid] = order
        _PRE_MARK[0], _PRE_MARK[1] = eid, -1
        _enqueue_locked([("seg", eid, u) for u in order[:_PREFETCH_AHEAD]])


def _store(job, data, ctype):
    with _LOCK:
        old = _CACHE.get(job)
        if old:
            _CACHE_BYTES[0] -= len(old[0])
        _CACHE[job] = (data, ctype, time.time())
        _CACHE_BYTES[0] += len(data)
        while _CACHE_BYTES[0] > _CACHE_MAX_BYTES and _CACHE:
            _, (b, _, _) = _CACHE.popitem(last=False)
            _CACHE_BYTES[0] -= len(b)


def _push_locked(job, urgent):
    """排一个任务并返回它的等待事件。调用方必须持有 _LOCK。

    已经排队或正在取的任务不重复排；播放器在等的任务如果只排在预取队列里，提到队首。
    """
    ev = _FLIGHT.get(job)
    if ev is None:
        ev = threading.Event()
        _FLIGHT[job] = ev
        (_HIGH if urgent else _LOW).append(job)
        _LOCK.notify()
    elif urgent and job in _LOW:
        _LOW.remove(job)
        _HIGH.append(job)
        _LOCK.notify()
    return ev


def _enqueue_locked(jobs, urgent=False):
    for job in jobs:
        if not _cached(job):
            _push_locked(job, urgent)


def _enqueue(jobs, urgent=False):
    with _LOCK:
        _enqueue_locked(jobs, urgent)


def _fetch_one(spider, kind, eid, key, urgent=False):
    """取一个对象，返回 (内容, 类型)；失败返回 None。

    命中缓存直接返回，否则把任务排给取流线程再等结果，保证同一时刻只有一条到
    CloudFront 的连接在工作。
    """
    job = (kind, eid, key)
    with _LOCK:
        hit = _cached(job)
        if hit:
            return hit[0], hit[1]
        ev = _push_locked(job, urgent)
    if not ev.wait(_LANE_WAIT):
        return None
    with _LOCK:
        hit = _cached(job)
        return (hit[0], hit[1]) if hit else None


def _run_job(spider, job):
    """取流线程执行一个任务：回源、写缓存、通知等待方。"""
    kind, eid, key = job
    try:
        value = spider._upstream(kind, eid, key, _UP_TIMEOUT)
        if value:
            _store(job, value[0], value[1])
    finally:
        with _LOCK:
            ev = _FLIGHT.pop(job, None)
        if ev is not None:
            ev.set()


def _lane_worker(spider):
    while True:
        with _LOCK:
            while not _HIGH and not _LOW:
                # 队列空了就补当前集的预取窗口，补满后仍没有任务才继续等
                _enqueue_locked(_seg_window())
                if _HIGH or _LOW:
                    break
                _LOCK.wait()
            job = _HIGH.popleft() if _HIGH else _LOW.popleft()
        _run_job(spider, job)


def _follow(eid, url):
    """记住播放器取到了第几片，并把预取窗口补满。"""
    order = _SEG_ORDER.get(eid) or []
    try:
        i = order.index(url)
    except ValueError:
        return
    with _LOCK:
        if i > _PRE_MARK[1]:
            _PRE_MARK[0], _PRE_MARK[1] = eid, i
        _enqueue_locked(_seg_window())


def _pre_start(spider):
    """取流线程全局只跑一个，重复调用不会多出线程。"""
    global _LANE_THREAD
    with _LOCK:
        if _LANE_THREAD is not None and _LANE_THREAD.is_alive():
            return
        _LANE_THREAD = threading.Thread(target=_lane_worker, args=(spider,))
        _LANE_THREAD.name = "hj-lane"
        _LANE_THREAD.daemon = True
        _LANE_THREAD.start()


def _seg_urls_of(text, base_url):
    """媒体清单里的分片绝对地址（跳过注释和子清单）。"""
    base_dir = base_url.rsplit("/", 1)[0] + "/"
    urls = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        au = urllib.parse.urljoin(base_dir, s)
        if not au.split("?")[0].endswith(".m3u8"):
            urls.append(au)
    return urls


# 播放走自建本地服务：壳的 do=py 通道在不同壳上行为不一致，播放器直连本服务最稳
_PROXY_STATE = {"port": 0, "server": None, "spider": None}
_PROXY_LOCK = threading.Lock()
_PROXY_PORT_RANGE = (19978, 19998)


class _ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "hj-proxy"

    def log_message(self, *args):
        return None

    def do_HEAD(self):
        self._serve(False)

    def do_GET(self):
        self._serve(True)

    def _serve(self, with_body):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        params = {k: v[0] for k, v in query.items()}
        status, ctype, content = _PROXY_STATE["spider"].localProxy(params)
        body = content.encode("utf-8") if isinstance(content, str) else content
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if with_body:
            self.wfile.write(body)


class _ProxyServer(ThreadingHTTPServer):
    # Windows 的 SO_REUSEADDR 允许重复绑定同一端口，热重载后旧模块的服务会继续占着端口收请求，
    # 返回改动前的清单。关掉复用，端口被占就顺延到下一个，保证服务代码和返回的地址一致。
    allow_reuse_address = False
    daemon_threads = True


def _start_proxy_server(spider):
    """启动本机播放服务，返回端口；已启动或端口耗尽时返回已知结果。"""
    with _PROXY_LOCK:
        if _PROXY_STATE["server"] is not None:
            _pre_start(spider)
            return int(_PROXY_STATE["port"])
        for port in range(_PROXY_PORT_RANGE[0], _PROXY_PORT_RANGE[1]):
            try:
                server = _ProxyServer(("127.0.0.1", port), _ProxyHandler)
            except OSError:
                continue
            _PROXY_STATE["port"] = port
            _PROXY_STATE["server"] = server
            _PROXY_STATE["spider"] = spider
            threading.Thread(target=server.serve_forever, daemon=True).start()
            _pre_start(spider)
            return port
    return 0


class Spider(_BaseSpider):
    # ---------------- 基础配置 ----------------
    def getDependence(self):
        return ""

    def getName(self):
        return "黄剧短剧"

    def init(self, extend=""):
        self.HOST = "https://huangju.net"
        self.API = "https://api.huangju.net"
        self.UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        self.headers = {
            "User-Agent": self.UA,
            "Accept": "application/json, text/plain, */*",
            "Origin": self.HOST,
            "Referer": self.HOST + "/",
        }
        self._categories = None
        self._mem = {}
        try:
            self._load_categories()
        except Exception:
            self._categories = []

    # ---------------- 工具函数 ----------------
    def _is_minor(self, text):
        if not text:
            return False
        t = str(text).lower()
        for k in _MINOR_KEYS:
            if k.lower() in t:
                return True
        return False

    def _clean(self, v):
        if v is None:
            return ""
        return str(v).strip()

    def _cover(self, item):
        return item.get("coverUrl") or item.get("cover") or ""

    def _remarks(self, item):
        status = item.get("status")
        total = item.get("totalEpisodes")
        if total:
            return ("全%s集" % total) if status == "completed" else ("更新至%s集" % total)
        return ""

    def _vod(self, item):
        return {
            "vod_id": "%s-%s" % (item.get("slug", ""), item.get("id")),
            "vod_name": self._clean(item.get("title")),
            "vod_pic": self._cover(item),
            "vod_remarks": self._remarks(item),
        }

    def _cache_get(self, key):
        fn = getattr(self, "getCache", None)
        try:
            if callable(fn):
                v = fn(key)
                if v is not None:
                    return v
        except Exception:
            pass
        # 内置兜底缓存（宿主无 getCache 时也能生效）
        try:
            item = self._mem.get(key)
            if item and item[1] > time.time():
                return item[0]
            if item:
                self._mem.pop(key, None)
        except Exception:
            pass
        return None

    def _cache_set(self, key, value, ttl):
        fn = getattr(self, "setCache", None)
        try:
            if callable(fn):
                fn(key, value, ttl)
        except Exception:
            pass
        try:
            if value is None:
                self._mem.pop(key, None)
            else:
                self._mem[key] = (value, time.time() + float(ttl or 300))
        except Exception:
            pass

    # ---------------- HTTP（可读响应头） ----------------
    def _http_alive(self, url, h, timeout):
        """复用连接发 GET，返回 (status, headers_lower_dict, body_bytes)。连接异常时抛出。"""
        cur = url
        for _hop in range(4):
            key = _pool_key(cur)
            parts = urllib.parse.urlsplit(cur)
            path_q = parts.path + (("?" + parts.query) if parts.query else "")
            conn = _conn_take(key, timeout)
            try:
                conn.request("GET", path_q, headers=h)
                resp = conn.getresponse()
                body = resp.read()
                reusable = not resp.will_close
                status = int(resp.status or 0)
                hdrs = {}
                for k, v in resp.getheaders():
                    lk = k.lower()
                    if lk == "set-cookie":
                        hdrs[lk] = (hdrs[lk] + "\n" + v) if lk in hdrs else v
                    else:
                        hdrs.setdefault(lk, v)
                _conn_put(key, conn, reusable)
                conn = None
            except Exception:
                _conn_put(key, conn, False)
                raise
            if status in (301, 302, 303, 307, 308):
                loc = hdrs.get("location") or ""
                if loc:
                    cur = urllib.parse.urljoin(cur, loc)
                    continue
            return status, hdrs, body
        return 0, {}, b""

    def _http(self, url, headers=None, cookie=None, timeout=10):
        """返回 (status, headers_lower_dict, body_bytes)；失败返回 (0, {}, b"")

        优先复用连接直连（CloudFront 握手太慢，必须复用），失败退回宿主 HTTP，再退回 urllib。
        set-cookie 必须逐条保留，CloudFront 签名是三条分开下发的。
        """
        h = dict(self.headers)
        h.update(headers or {})
        if cookie:
            h["Cookie"] = cookie

        # 1) 复用连接直连；池里的连接可能已被服务端回收，失败就换新连接再试一次
        for _retry in range(2):
            try:
                status, hdrs, body = self._http_alive(url, h, timeout)
                if status:
                    return status, hdrs, _gunzip(hdrs, body)
                break
            except Exception:
                continue

        # 2) 宿主 requests 会话（能完整读响应头）
        fetch = getattr(self, "fetch", None)
        if callable(fetch):
            try:
                resp = fetch(url, headers=h, timeout=timeout, allow_redirects=True)
                hdrs = {}
                try:
                    raw_headers = resp.raw.headers
                    pairs = raw_headers.getlist("Set-Cookie") if hasattr(raw_headers, "getlist") else []
                except Exception:
                    pairs = []
                for k, v in resp.headers.items():
                    k = k.lower()
                    if k == "set-cookie":
                        continue
                    hdrs.setdefault(k, v)
                if pairs:
                    hdrs["set-cookie"] = "\n".join(pairs)
                elif resp.headers.get("set-cookie"):
                    hdrs["set-cookie"] = resp.headers.get("set-cookie")
                return int(resp.status_code or 0), hdrs, _gunzip(hdrs, resp.content or b"")
            except Exception:
                pass

        # 3) urllib 兜底（无第三方依赖）
        try:
            req = urllib.request.Request(url, headers=h)
            resp = urllib.request.urlopen(req, timeout=timeout)
            status = resp.getcode()
            raw = resp.read()
            hdrs = {}
            for k, v in resp.headers.items():
                k = k.lower()
                if k == "set-cookie":
                    hdrs[k] = (hdrs[k] + "\n" + v) if k in hdrs else v
                else:
                    hdrs.setdefault(k, v)
            return status, hdrs, _gunzip(hdrs, raw)
        except urllib.error.HTTPError as e:
            try:
                raw = e.read() or b""
            except Exception:
                raw = b""
            hdrs = {}
            for k, v in (e.headers or {}).items():
                k = k.lower()
                if k == "set-cookie":
                    hdrs[k] = (hdrs[k] + "\n" + v) if k in hdrs else v
                else:
                    hdrs.setdefault(k, v)
            return e.code, hdrs, raw
        except Exception:
            return 0, {}, b""

    def _json(self, path, params=None):
        url = self.API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        status, _, raw = self._http(url)
        if status != 200 or not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8", "ignore") or "{}")
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _json_list(self, path):
        url = self.API + path
        status, _, raw = self._http(url)
        if status != 200 or not raw:
            return []
        try:
            data = json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            return []
        return data if isinstance(data, list) else []

    # ---------------- 分类 ----------------
    def _load_categories(self):
        data = self._json_list("/categories")
        result = []
        for c in data:
            if not isinstance(c, dict):
                continue
            slug = self._clean(c.get("slug"))
            name = self._clean(c.get("name"))
            if not slug or not name:
                continue
            try:
                count = int(c.get("dramaCount") or 0)
            except Exception:
                count = 0
            if len(slug) > 24 or "," in name or len(name) > 8 or count <= 0:
                continue
            if not re.search(r"[\u4e00-\u9fff]", name):
                continue
            if self._is_minor(name) or self._is_minor(slug):
                continue
            result.append({"type_id": slug, "type_name": name})
        seen = set()
        uniq = []
        for c in result:
            if c["type_id"] in seen:
                continue
            seen.add(c["type_id"])
            uniq.append(c)
        self._categories = uniq

    def homeContent(self, *args):
        try:
            if not self._categories:
                self._load_categories()
            filters = {}
            for c in self._categories:
                filters[c["type_id"]] = [
                    {
                        "key": "sort",
                        "name": "排序",
                        "init": "hot",
                        "value": [
                            {"n": "最热", "v": "hot"},
                            {"n": "最新", "v": "new"},
                        ],
                    }
                ]
            return {"class": self._categories, "filters": filters}
        except Exception:
            return {"class": [], "filters": {}}

    def homeVideoContent(self, *args):
        try:
            data = self._json("/dramas", {"sort": "hot", "page": 1})
            return self._parse_page(data, 1)
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    # ---------------- 分类分页 ----------------
    def _extend(self, v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and v.strip():
            try:
                d = json.loads(v)
                return d if isinstance(d, dict) else {}
            except Exception:
                return {}
        return {}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            tid = str(tid or "")
            try:
                pg = max(1, int(pg or 1))
            except Exception:
                pg = 1
            extend = self._extend(extend)
            sort = self._clean(extend.get("sort")) or "hot"
            params = {"category": tid, "page": pg, "sort": sort}
            data = self._json("/dramas", params)
            return self._parse_page(data, pg)
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    def _parse_page(self, data, pg):
        items = data.get("items") or []
        try:
            total = int(data.get("total") or 0)
        except Exception:
            total = 0
        try:
            size = int(data.get("pageSize") or len(items) or 20)
        except Exception:
            size = len(items) or 20
        pagecount = int(total // size) + (1 if total % size else 0) if size else 1
        pagecount = max(pagecount, 1)
        # 服务端会把越界页夹到末页，以它返回的 page 为准，避免壳子翻页错位
        try:
            cur = int(data.get("page") or 0)
        except Exception:
            cur = 0
        if cur <= 0:
            cur = pg
        cur = min(max(cur, 1), pagecount)
        lst = [self._vod(x) for x in items if isinstance(x, dict) and not self._is_minor(x.get("title"))]
        return {"page": cur, "pagecount": pagecount, "limit": size, "total": total, "list": lst}

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        try:
            if isinstance(ids, str):
                ids = [x for x in re.split(r"[,&]", ids) if x]
            vod_list = []
            for vid in (ids or []):
                vid = str(vid).strip()
                if not vid:
                    continue
                data = self._json("/dramas/" + urllib.parse.quote(vid, safe="-"))
                if not data or data.get("id") is None:
                    # 兜底：纯数字 id 时接口不认，用 "-{id}" 形式可直达
                    if vid.isdigit():
                        data = self._json("/dramas/-" + vid)
                if not data or data.get("id") is None:
                    continue
                episodes = data.get("episodes") or []
                ep_rows = []
                for ep in episodes:
                    if not isinstance(ep, dict) or not ep.get("playable", True):
                        continue
                    ep_id = ep.get("id")
                    if ep_id is None:
                        continue
                    ep_name = self._clean(ep.get("title")) or ("第%s集" % ep.get("epNo"))
                    ep_rows.append((ep_name, ep_id))
                if not ep_rows:
                    continue
                # 每个清晰度一条线路，第一条是最高档，壳子和面板默认播它
                play_from = [name for _, name in _HJ_QUALITY_LINES]
                play_url = [
                    "#".join("%s$%s%s:%s" % (n, _EPISODE_PREFIX, q, i) for n, i in ep_rows)
                    for q, _ in _HJ_QUALITY_LINES
                ]
                vod = {
                    "vod_id": "%s-%s" % (data.get("slug", ""), data.get("id")),
                    "vod_name": self._clean(data.get("title")),
                    "vod_pic": self._cover(data),
                    "vod_remarks": self._remarks(data),
                    "vod_year": self._clean(data.get("year")),
                    "vod_area": self._clean(data.get("region")),
                    "vod_content": self._clean(data.get("description") or data.get("seoDescription")),
                    "vod_play_from": "$$$".join(play_from),
                    "vod_play_url": "$$$".join(play_url),
                }
                if not self._is_minor(vod["vod_name"]):
                    vod_list.append(vod)
            return {"list": vod_list}
        except Exception:
            return {"list": []}

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg="1"):
        try:
            key = str(key or "")
            try:
                pg = max(1, int(pg or 1))
            except Exception:
                pg = 1
            data = self._json("/dramas", {"q": key, "page": pg})
            return self._parse_page(data, pg)
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    # ---------------- 播放 ----------------
    def _proxy_base(self):
        fn = getattr(self, "getProxyUrl", None)
        try:
            base = fn() if callable(fn) else ""
        except Exception:
            base = ""
        if not base:
            base = "http://127.0.0.1:9978/proxy?do=py"
        return base

    def _play_signed(self, ep_id):
        """取播放地址并抓取 CloudFront 签名 Cookie。返回 (m3u8_url, cookie_str)

        注意：签名 Cookie 是 /play 接口本身下发的（不是视频域），所以必须直读响应头。
        """
        cached = self._cache_get("cf:%s" % ep_id)
        if isinstance(cached, dict) and cached.get("u") and cached.get("c") \
                and cached.get("e", 0) > time.time():
            return cached["u"], cached["c"]

        api_url = self.API + "/play/" + urllib.parse.quote(str(ep_id), safe="")
        status, hdrs, raw = self._http(api_url, timeout=20)
        if status != 200 or not raw:
            return "", ""
        try:
            data = json.loads(raw.decode("utf-8", "ignore") or "{}")
        except Exception:
            return "", ""
        if not isinstance(data, dict):
            return "", ""
        url = self._clean(data.get("url"))
        if not url:
            return "", ""

        sc = hdrs.get("set-cookie") or ""
        pairs = re.findall(r"(CloudFront-[A-Za-z-]+)=([^;,\s]+)", sc)
        ck = {}
        for k, v in pairs:
            if k in _CF_COOKIES:
                ck[k] = v
        if not ck:
            # 没拿到签名，直连必然 403，但仍返回地址让上层能报错
            return url, ""
        cookie = "; ".join("%s=%s" % (k, ck[k]) for k in _CF_COOKIES if k in ck)

        # 缓存到签名过期（expiresAt 是秒级时间戳，兜底 6 小时）
        ttl = 21600
        try:
            exp = int(data.get("expiresAt") or 0)
            if exp > time.time():
                ttl = max(60, min(21600, exp - time.time() - 60))
        except Exception:
            pass
        self._cache_set("cf:%s" % ep_id, {"u": url, "c": cookie, "e": time.time() + ttl}, ttl)
        return url, cookie

    def _get_cookie(self, ep_id):
        cached = self._cache_get("cf:%s" % ep_id)
        if isinstance(cached, dict) and cached.get("c") and cached.get("e", 0) > time.time():
            return cached["c"]
        _, cookie = self._play_signed(ep_id)
        return cookie

    def _pick_variant(self, master_url, want_q, cookie):
        """按分辨率高度从主清单挑出对应清晰度变体；站点没有该档时取最高的一档。"""
        try:
            want = int(want_q)
        except Exception:
            want = 0
        key = "var:%s:%s" % (want, master_url)
        hit = self._cache_get(key)
        if isinstance(hit, str) and hit:
            return hit
        status, _, body = self._http(master_url, {"Accept": "*/*"}, cookie, timeout=15)
        if status != 200 or not body:
            return ""
        rows = []
        base_dir = master_url.rsplit("/", 1)[0] + "/"
        for attr, uri in re.findall(r"#EXT-X-STREAM-INF:([^\n]*)\n([^\n#]+)", body.decode("utf-8", "ignore")):
            m = re.search(r"RESOLUTION=(\d+)x(\d+)", attr)
            rows.append((int(m.group(2)) if m else 0, urllib.parse.urljoin(base_dir, uri.strip())))
        if not rows:
            return ""
        rows.sort(key=lambda x: -x[0])
        picked = next((u for h, u in rows if h == want), rows[0][1])
        self._cache_set(key, picked, 3600)
        return picked

    def _local_base(self):
        """自建服务地址；端口耗尽时退回壳的 do=py 代理。"""
        port = _start_proxy_server(self)
        if not port:
            return self._proxy_base()
        return "http://127.0.0.1:%d/hj.m3u8" % port

    def _proxy_url(self, **params):
        q = urllib.parse.urlencode(params)
        base = self._local_base()
        return base + ("&" if "?" in base else "?") + q

    def _rewrite_m3u8(self, body, base_url, ep_id):
        out = []
        base_dir = base_url.rsplit("/", 1)[0] + "/"
        for line in body.splitlines():
            s = line.strip()
            if not s:
                out.append(line)
                continue
            if s.startswith("#"):
                # 处理 #EXT-X-KEY / #EXT-X-MAP 里的 URI="..."
                def _sub(m):
                    u = m.group(2)
                    au = urllib.parse.urljoin(base_dir, u)
                    enc = base64.urlsafe_b64encode(au.encode()).decode().rstrip("=")
                    return m.group(1) + self._proxy_url(type="seg", eid=ep_id, u=enc) + m.group(3)
                out.append(re.sub(r'(URI=")([^"]+)(")', _sub, s))
                continue
            au = urllib.parse.urljoin(base_dir, s)
            enc = base64.urlsafe_b64encode(au.encode()).decode().rstrip("=")
            if au.split("?")[0].endswith(".m3u8"):
                out.append(self._proxy_url(type="play", eid=ep_id, u=enc))
            else:
                out.append(self._proxy_url(type="seg", eid=ep_id, u=enc))
        return "\n".join(out) + "\n"

    def playerContent(self, *args):
        try:
            ep_id = str(args[1]) if len(args) > 1 else ""
            if not ep_id:
                return {"parse": 0, "jx": 0, "url": "", "header": {"User-Agent": self.UA},
                        "format": "application/x-mpegURL"}
            q, ep_id = _split_episode_token(ep_id)
            url = self._proxy_url(type="play", eid=ep_id, q=q)
            # 播放器建立连接的同时，后台把这一档的清单和开头几片先取好，起步不用干等
            _enqueue([("pl", ep_id, q)])
            header = {"User-Agent": self.UA, "Referer": self.HOST + "/"}
            return {"parse": 0, "jx": 0, "url": url, "header": header,
                    "format": "application/x-mpegURL"}
        except Exception:
            return {"parse": 0, "jx": 0, "url": "", "header": {"User-Agent": self.UA},
                    "format": "application/x-mpegURL"}

    # ---------------- 本地代理 ----------------
    def localProxy(self, params=None):
        p = params or {}
        typ = str(p.get("type") or "")
        eid = str(p.get("eid") or "")
        q = str(p.get("q") or "")
        raw_u = str(p.get("u") or "")
        if not typ or not eid:
            return [404, "text/plain", "bad request"]
        try:
            if raw_u:
                raw_u += "=" * (-len(raw_u) % 4)
                target = base64.urlsafe_b64decode(raw_u.encode()).decode("utf-8")
            else:
                target = ""
        except Exception:
            return [400, "text/plain", "bad url"]

        # 播放器正在要的对象排到取流队列队首，其余回源(预取)都在它后面串行执行
        if typ == "seg" and target:
            hit = _fetch_one(self, "seg", eid, target, urgent=True)
            if not hit:
                return [502, "text/plain", "upstream error"]
            _follow(eid, target)
            return [200, hit[1], hit[0]]

        if typ == "play":
            if raw_u:
                hit = _fetch_one(self, "sub", eid, target, urgent=True)
            else:
                # 带 q 时下发单档媒体清单，播放器没有可降档的选项，清晰度不会掉到 480
                hit = _fetch_one(self, "pl", eid, q, urgent=True)
            if not hit:
                return [502, "text/plain", "upstream error"]
            return [200, hit[1], hit[0]]

        return [404, "text/plain", "bad request"]

    def _fetch_media(self, url, eid, timeout):
        """带签名 Cookie 回源；失败时刷新 Cookie 再试一次（签名约 6 小时过期）。"""
        h = {"Accept": "*/*", "Referer": self.HOST + "/"}
        status, hdrs, body = self._http(url, h, self._get_cookie(eid), timeout=timeout)
        if status == 200 and body:
            return status, hdrs, body
        self._cache_set("cf:%s" % eid, None, 0)
        _, cookie2 = self._play_signed(eid)
        if cookie2:
            status, hdrs, body = self._http(url, h, cookie2, timeout=timeout)
        return status, hdrs, body

    def _build_playlist(self, eid, want_q, target="", timeout=20):
        """取一份清单并改写成分片走本服务的地址。

        媒体清单顺便记下分片顺序并把开头几片排进预取，播放器起步就不用干等。
        """
        url, cookie = self._play_signed(eid)
        if not url:
            return ""
        if not target:
            target = (self._pick_variant(url, want_q, cookie) or url) if want_q else url
        elif not target.startswith("http"):
            target = urllib.parse.urljoin(url.rsplit("/", 1)[0] + "/", target)
        status, hdrs, body = self._fetch_media(target, eid, timeout)
        if status != 200 or not body:
            return ""
        text = body.decode("utf-8", "ignore")
        if not text.lstrip().startswith("#EXTM3U"):
            return ""
        if "EXT-X-STREAM-INF" not in text:
            _mark_episode(eid, _seg_urls_of(text, target))
        return self._rewrite_m3u8(text, target, eid)

    def _upstream(self, kind, eid, key, timeout):
        """真正回源。kind: seg=分片(地址) pl=单档清单(清晰度) sub=子清单(地址)。失败返回 None。"""
        if kind == "seg":
            status, hdrs, body = self._fetch_media(key, eid, timeout)
            if status != 200 or not body:
                return None
            ctype = (hdrs.get("content-type") or "").split(";")[0]
            if not ctype:
                ctype = "video/mp2t" if key.split("?")[0].endswith(".ts") else "application/octet-stream"
            return body, ctype
        text = self._build_playlist(eid, "" if kind == "sub" else key,
                                    key if kind == "sub" else "", timeout)
        if not text:
            return None
        return text, "application/vnd.apple.mpegurl"

    # ---------------- 其余标准接口 ----------------
    def isVideoFormat(self, url):
        if not url:
            return False
        u = url.lower().split("?")[0]
        return u.endswith(".m3u8") or u.endswith(".mp4") or u.endswith(".ts")

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return {}

    def destroy(self):
        pass
