# -*- coding: utf-8 -*-
"""asar.py —— 读先天本体的形制 + 锚（字节数与 sha256）。

asar 头形制（先天事实，别猜，猜错就整体错位）：

    头 8 字节  = 两个 uint32：第一个恒为 4，第二个是 header pickle 的长度
    base       = 8 + 第二个值
    pickle[4:8]= JSON 串长度（uint32）
    JSON       = 从 pickle 第 8 字节起，长度取上面那个值
    文件数据    = 从 base 起连续排列；每个条目的 offset **相对 base**

最常见的错：把 JSON 从头 12 字节起算，或者 offset 从文件 0 算 ——
两种都能把 header 读出来，但读 package.json 会读出几位乱码，
于是「包名对不上」却看不出错在哪。下面 read() 的两处偏移就是这条线的全部内容。

条目两种承载，必居其一（没有第三种）：
    · 头里有 offset  → 数据在 asar 内，按 base+offset 读
    · 头里标 unpacked → asar 内只有索引，真身在同级 app.asar.unpacked/<同一路径>

指纹规矩：名片指纹 = 它盯的那几个对象「此刻的样子」（kind|path|size|files|sha256）。
对象一变指纹就变 —— 指纹是对象的自述，不是我们对它的评价。
"""
from __future__ import annotations

import hashlib
import json
import os
import struct


class Asar:
    def __init__(self, path: str):
        self.path = path
        if not os.path.isfile(path):
            raise FileNotFoundError(f"asar 不存在：{path}")
        self.f = open(path, "rb")
        self.f.seek(0)
        head = self.f.read(8)
        if len(head) < 8:
            raise ValueError(f"asar 太短，读不出头：{path}（{len(head)} 字节）")
        magic, hdrlen = struct.unpack("<II", head)
        if magic != 4:
            raise ValueError(f"asar 头第一个 uint32 = {magic}，应为 4：{path}（不是 asar 或已损坏）")
        hb = self.f.read(hdrlen)
        strlen = struct.unpack("<I", hb[4:8])[0]
        self.h = json.loads(hb[8:8 + strlen].decode("utf-8"))
        self.base = 8 + hdrlen
        self._names = None
        self._unpacked = None

    def names(self) -> list:
        if self._names is None:
            out = []

            def w(node, pre=""):
                for k, v in node.get("files", {}).items():
                    cur = pre + "/" + k
                    if "files" in v:
                        w(v, cur)
                    else:
                        out.append(cur)

            w(self.h)
            self._names = out
        return self._names

    def unpacked_names(self) -> list:
        """header 里标了 unpacked:true 的那些 —— 真身落在 app.asar.unpacked。"""
        if self._unpacked is None:
            out = []

            def w(node, pre=""):
                for k, v in node.get("files", {}).items():
                    cur = pre + "/" + k
                    if "files" in v:
                        w(v, cur)
                    elif v.get("unpacked"):
                        out.append(cur)

            w(self.h)
            self._unpacked = out
        return self._unpacked

    def exists(self, p: str) -> bool:
        node = self.h
        for part in p.strip("/").split("/"):
            if part not in node.get("files", {}):
                return False
            node = node["files"][part]
        return ("offset" in node) or bool(node.get("unpacked"))

    def read(self, p: str) -> str:
        node = self.h
        for part in p.strip("/").split("/"):
            node = node["files"][part]
        if "offset" not in node:
            if node.get("unpacked"):
                q = os.path.join(os.path.dirname(self.path), "app.asar.unpacked",
                                 p.strip("/").replace("/", os.sep))
                with open(q, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            raise KeyError(p + "：既无 offset 也没标 unpacked")
        self.f.seek(self.base + int(node["offset"]))
        return self.f.read(node["size"]).decode("utf-8", "replace")

    def dirs_of(self, prefix: str) -> list:
        out = set()
        plen = len(prefix.rstrip("/")) + 1
        for n in self.names():
            if n.startswith(prefix.rstrip("/") + "/"):
                rest = n[plen:]
                if "/" in rest:
                    out.add(rest.split("/")[0])
        return sorted(out)


def sha256_file(path: str, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha12(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:12]


def file_anchor(path: str, label: str = "") -> dict:
    st = os.stat(path)
    return {"kind": "file", "path": path, "label": label,
            "size": st.st_size, "sha256": sha256_file(path)}


def dir_anchor(path: str, label: str = "") -> dict:
    items = []
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            total += st.st_size
            items.append(f"{os.path.relpath(p, path)}|{st.st_size}")
    items.sort()
    return {"kind": "dir", "path": path, "label": label,
            "files": len(items), "size": total, "sha256": sha12("\n".join(items))}


def anchor_fp(anchors) -> str:
    """名片指纹 = 它盯的那几个对象此刻的样子。对象一变，指纹就变。"""
    parts = []
    for x in anchors:
        parts.append("|".join(str(x.get(k, "")) for k in ("kind", "path", "size", "files", "sha256")))
    return sha12("\n".join(parts))


def verify_anchor(x: dict) -> bool:
    p = x.get("path")
    try:
        if x.get("kind") == "dir":
            return dir_anchor(p)["sha256"] == x.get("sha256")
        return sha256_file(p) == x.get("sha256") and os.path.getsize(p) == x.get("size")
    except Exception:
        return False
