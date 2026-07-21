"""
TEMU 成本计算器 - CJ 匹配一键启动脚本
======================================
启动本地 CORS 代理（端口 8765）+ HTTP 服务器（端口 8080），
并自动打开浏览器访问 http://127.0.0.1:8080/temu.html

使用方法：
  双击 start_cj.py 或在命令行执行：
  python start_cj.py

依赖：Python 3.7+（无需额外安装包，全部使用标准库）
======================================
"""
import subprocess
import sys
import os
import time
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
import json
import ssl
import gzip
import math
import re

# ──── 配置 ────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CJ_API_BASE = "https://developers.cjdropshipping.com/api2.0/v1"
LISTEN_PORT = 8765
HTTP_PORT = 8080
CACHE_FILE = os.path.join(SCRIPT_DIR, "cj_temu_cache.json")

# ──── 日志 ────
_lock = threading.Lock()

def log(msg):
    ts = time.strftime("%H:%M:%S")
    with _lock:
        print(f"[{ts}] {msg}", flush=True)

# ──── 缓存加载 ────
_cache = {}
_last_cache_load = 0

def load_cache():
    global _cache, _last_cache_load
    try:
        if os.path.exists(CACHE_FILE):
            mtime = os.path.getmtime(CACHE_FILE)
            if mtime > _last_cache_load:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    _cache = json.load(f)
                _last_cache_load = mtime
                total = sum(len(v.get("connections", [])) for v in _cache.values())
                log(f"缓存加载: {len(_cache)} 个店铺, {total} 条关联")
    except Exception as e:
        log(f"缓存加载失败: {e}")

# ──── CORS 代理 ────
FAKE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def _send_json(handler, code, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "*")
    handler.send_header("Content-Type", "application/json;charset=UTF-8")
    handler.send_header("Content-Length", len(body))
    handler.end_headers()
    handler.wfile.write(body)

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log(fmt % args)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def _handle(self):
        load_cache()
        method = self.command
        raw_path = self.path

        if not raw_path.startswith("/proxy"):
            _send_json(self, 404, {"result": False, "message": "Invalid path"})
            return

        target_path = raw_path[len("/proxy"):]

        # getAccessToken → 实时请求 CJ API
        if target_path == "/authentication/getAccessToken":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            self._forward_real(method, target_path, body)
            return

        # getShops → 从缓存构建
        if target_path == "/shop/getShops":
            shops = []
            for shop_id, entry in _cache.items():
                shops.append({
                    "id": shop_id,
                    "name": entry.get("name", ""),
                    "aliasName": entry.get("name", ""),
                    "type": "Temu",
                    "status": 1
                })
            _send_json(self, 200, {"success": True, "code": 0, "message": None, "data": shops})
            return

        # connection → 从缓存分页返回
        if target_path.startswith("/product/conn/connection"):
            qs = target_path.split("?", 1)[1] if "?" in target_path else ""
            params = {}
            for p in qs.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v

            shop_id = params.get("shopId", "")
            page = int(params.get("page", "1"))
            page_size = int(params.get("pageSize", "500"))

            entry = _cache.get(shop_id)
            if not entry:
                _send_json(self, 200, {"success": True, "code": 0, "message": None,
                           "data": {"list": [], "total": 0, "totalPages": 0}})
                return

            all_conns = entry.get("connections", [])
            total = len(all_conns)
            total_pages = max(1, math.ceil(total / page_size))
            start = (page - 1) * page_size
            end = start + page_size
            page_data = all_conns[start:end]

            _send_json(self, 200, {
                "success": True, "code": 0, "message": None,
                "data": {"list": page_data, "total": total, "totalPages": total_pages}
            })
            return

        # 其他 → 转发 CJ API
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        self._forward_real(method, target_path, body)

    def _forward_real(self, method, target_path, body):
        target_url = CJ_API_BASE + target_path
        ctx = ssl.create_default_context()

        for attempt in range(3):
            try:
                if method == "GET":
                    req = urllib.request.Request(target_url, method="GET")
                else:
                    req = urllib.request.Request(target_url, data=body, method=method)

                req.add_header("User-Agent", FAKE_UA)

                skip = {k.lower() for k in ["host", "connection", "proxy-connection",
                                              "keep-alive", "transfer-encoding", "te",
                                              "trailer", "upgrade", "origin", "referer", "user-agent"]}
                for key, value in self.headers.items():
                    if key.lower() not in skip:
                        req.add_header(key, value)

                if body and "content-type" not in {k.lower() for k in self.headers.keys()}:
                    req.add_header("Content-Type", "application/json")

                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    resp_body = resp.read()
                    ct = resp.headers.get("Content-Type", "")

                    # gzip 解压
                    content_encoding = resp.headers.get("Content-Encoding", "")
                    if "gzip" in content_encoding.lower():
                        try:
                            resp_body = gzip.decompress(resp_body)
                        except Exception:
                            pass

                    # Cloudflare 检测
                    if ("json" not in ct.lower() and resp_body[:100].strip().startswith(b"<!")) or \
                       b"cloudflare" in resp_body[:500].lower():
                        time.sleep(2)
                        continue

                    self.send_response(resp.status)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "*")
                    if ct:
                        self.send_header("Content-Type", ct)
                    self.send_header("Content-Length", len(resp_body))
                    self.end_headers()
                    self.wfile.write(resp_body)
                    return

            except urllib.error.HTTPError as e:
                err_body = e.read()
                if b"cloudflare" in err_body[:500].lower():
                    time.sleep(2)
                    continue
                _send_json(self, e.code, {"result": False, "message": f"CJ API Error: {e.code}"})
                return

            except Exception as e:
                if attempt < 2:
                    time.sleep(1)
                    continue
                _send_json(self, 502, {"result": False, "message": str(e)})
                return

# ──── HTTP 静态文件服务器 ────
class StaticHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            path = "/temu.html"
        file_path = os.path.join(SCRIPT_DIR, path.lstrip("/"))

        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            content_types = {
                ".html": "text/html;charset=UTF-8",
                ".css": "text/css",
                ".js": "application/javascript",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
            }
            ct = content_types.get(ext, "application/octet-stream")
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", len(content))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_error(500)
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        pass  # 静态文件不打印日志

def start_proxy():
    server = HTTPServer(("127.0.0.1", LISTEN_PORT), ProxyHandler)
    log(f"CORS 代理启动: http://127.0.0.1:{LISTEN_PORT}/proxy")
    server.serve_forever()

def start_http():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), StaticHandler)
    log(f"HTTP 服务器启动: http://127.0.0.1:{HTTP_PORT}")
    server.serve_forever()

# ──── 主入口 ────
if __name__ == "__main__":
    print("=" * 52)
    print("  TEMU 成本计算器 - CJ SPU 匹配")
    print("=" * 52)

    # 检查缓存文件
    if not os.path.exists(CACHE_FILE):
        print(f"\n⚠ 缓存文件不存在: {CACHE_FILE}")
        print("  CJ 匹配功能仍然可用，但首次匹配需从 CJ API 实时拉取（较慢）")
    else:
        load_cache()

    # 启动代理
    t1 = threading.Thread(target=start_proxy, daemon=True)
    t1.start()

    # 启动 HTTP 服务器
    t2 = threading.Thread(target=start_http, daemon=True)
    t2.start()

    time.sleep(1)

    url = f"http://127.0.0.1:{HTTP_PORT}/temu.html"
    print(f"\n✅ 全部就绪！正在打开浏览器...")
    print(f"   {url}")

    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 已关闭")
