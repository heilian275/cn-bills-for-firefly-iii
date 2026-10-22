# -*- coding: utf-8 -*-
"""scripts 各脚本的共享件：stdout 编码、token 读取、Firefly III API 访问（get/post/分页）、锚月窗口。

token 读取和带凭证请求头只在这里实现，各脚本共用；改规则只改本文件。
token 不打印，也不写日志。

各脚本经 `uv run scripts/<名字>.py` 或 `python3 scripts/<名字>.py` 调用时，Python 会把脚本
所在目录排进模块搜索路径第一位，`import _common` 即命中。把单个脚本拷出本目录单独运行会因
缺少本模块而失败；分发以整个 skill 目录为单位，不单发脚本。
"""
import calendar
import json
import os
import sys
import urllib.request
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_token(path=None):
    env = os.environ.get("FIREFLY_III_ACCESS_TOKEN")
    if path:
        # utf-8-sig：Windows PowerShell 5.1 的 Set-Content -Encoding UTF8 会在文件头写 BOM，
        # 按 utf-8 读则首行变成 "\ufeffFIREFLY_III_ACCESS_TOKEN=..."，匹配失败、误报未找到 token。
        with open(path, encoding="utf-8-sig") as f:
            for raw in f:
                s = raw.strip()
                if s.startswith("FIREFLY_III_ACCESS_TOKEN="):
                    return s.split("=", 1)[1].strip().strip('"').strip("'")
    if env:
        return env.strip()
    return None


class Firefly:
    """极简 Firefly III API 客户端。token 只存实例内，不打印。"""

    def __init__(self, url, token):
        self.url = url.rstrip("/")
        self.H = {"Authorization": "Bearer " + token, "Accept": "application/json"}

    def get(self, path, params=None):
        url = self.url + path
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        req = urllib.request.Request(url, headers=self.H)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def post(self, path, payload, timeout=30):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url + path, data=body, method="POST",
                                     headers={**self.H, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def paged(self, path, params=None):
        """分页迭代器：逐页产出 data 数组，自动跟完分页（page[size] 固定 50）。

        页内 HTTP 错误原样抛出，由调用方决定保留部分结果（catch 后即中断）还是放任崩溃。"""
        page = 1
        while True:
            q = dict(params or {})
            q["page[size]"] = 50
            q["page"] = page
            d = self.get(path, q)
            rows = d.get("data", [])
            if rows:
                yield rows
            pag = d.get("meta", {}).get("pagination", {})
            if page >= (pag.get("total_pages") or 1) or not rows:
                return
            page += 1

    def latest_transaction_date(self):
        """库内最后交易日期（YYYY-MM-DD，无交易返回 None）；HTTP 错误抛给调用方自行处理。"""
        anchor = None
        probe = self.get("/api/v1/transactions", {"page[size]": 1, "page": 1})
        for g in probe.get("data", []):
            for j in g.get("attributes", {}).get("transactions", []):
                d = (j.get("date") or "")[:10]
                if d and (anchor is None or d > anchor):
                    anchor = d
        return anchor


def month_window(anchor, months):
    """锚定月所在整月的月初往前数 months 个整月：返回 (start, end)，均为 date。"""
    y, m = int(anchor[:4]), int(anchor[5:7])
    end = date(y, m, calendar.monthrange(y, m)[1])
    m0 = m - (months - 1)
    start = date(y + (m0 - 1) // 12, (m0 - 1) % 12 + 1, 1)
    return start, end
