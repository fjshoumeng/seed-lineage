# -*- coding: utf-8 -*-
"""paths.py —— 唯一地址源（可移植版）。

解析一个值走三级，取到就停，并把「这个值是从哪一级来的」打印出来：

    1 环境变量      DSH_ORIGIN / DSH_ASSETS / DSH_STATE / DSH_HOME
    2 自动探测      从本脚本所在位置向上找、看各平台常见安装位置
    3 默认值        相对本脚本（不假设任何绝对路径）

四个值：
    ORIGIN   先天物质所在目录。其下有 resources/app.asar 与
             resources/runtime/primary-runtime/runtime.json
    ASSETS   长出来的东西的落点。其下有 技能/ 与 名片/
    STATE    量出来的中间账（regularity.json / 先天锚-<版本>.json / services.json）
    HOME     DSH 的 home 目录（只读判断用；本工具集不往里写）

规矩：任何脚本都不许再写死 D:\ 开头的路径，一律从这里取。
解析结果每次运行都打印（print_resolution），对不上当场能看出来。
"""
from __future__ import annotations

import json
import os
import re
import sys

NT = os.name == "nt"
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT_OF_TOOL = os.path.dirname(HERE)   # 本工具集所在的那一层（scripts 的父）

# ── 三个入口地址的解析 ────────────────────────────────────────────────────────

_ASAR_REL = os.path.join("resources", "app.asar")
_RUNTIME_REL = os.path.join("resources", "runtime", "primary-runtime", "runtime.json")


def _has_origin(p: str) -> bool:
    return bool(p) and os.path.isfile(os.path.join(p, _ASAR_REL))


def _upward_roots(levels: int = 5, kids: int = 300) -> list:
    """从脚本位置向上：每一层自己 + 每一层的直接子目录（限个数，别拖死）。"""
    out, d = [], HERE
    for _ in range(levels):
        out.append(d)
        try:
            names = sorted(os.listdir(d))[:kids]
        except OSError:
            names = []
        for k in names:
            q = os.path.join(d, k)
            if os.path.isdir(q):
                out.append(q)
                # macOS 的 .app 包：Resources 在 Contents 下
                if k.endswith(".app"):
                    out.append(os.path.join(q, "Contents"))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return out


def _platform_roots() -> list:
    """各平台常见安装位置。不做递归，只列一层的目录名。"""
    out = []
    home = os.path.expanduser("~")
    if NT:
        # 盘符根下的第一层（安装时很多人直接装在 D:\<某个名字>）
        for letter in "CDEFGH":
            root = letter + ":\\"
            if not os.path.isdir(root):
                continue
            try:
                for k in sorted(os.listdir(root))[:200]:
                    out.append(os.path.join(root, k))
            except OSError:
                pass
        for env in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "APPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            for sub in ("Programs", "Local", ""):
                d = os.path.join(base, sub) if sub else base
                try:
                    for k in sorted(os.listdir(d))[:200]:
                        out.append(os.path.join(d, k))
                except OSError:
                    pass
    elif sys.platform == "darwin":
        for base in ("/Applications", os.path.join(home, "Applications")):
            try:
                for k in sorted(os.listdir(base)):
                    if k.endswith(".app"):
                        out.append(os.path.join(base, k, "Contents"))
            except OSError:
                pass
    else:
        for base in ("/opt", os.path.join(home, ".local/share"), os.path.join(home, "Applications")):
            try:
                for k in sorted(os.listdir(base))[:200]:
                    out.append(os.path.join(base, k))
            except OSError:
                pass
    return out


def find_origin():
    """(路径, 来源说明)"""
    env = os.environ.get("DSH_ORIGIN", "").strip()
    if env:
        return os.path.abspath(env), "环境变量 DSH_ORIGIN"
    for c in _upward_roots():
        if _has_origin(c):
            return os.path.abspath(c), "自动探测（脚本位置附近）"
    for c in _platform_roots():
        if _has_origin(c):
            return os.path.abspath(c), "自动探测（平台常见安装位置）"
    return "", "未找到（下面列出探过的位置）"


def find_assets():
    """(路径, 来源说明)。判据：这一层下面同时有 技能/ 或 名片/。

    顺序很重要：先看脚本自己旁边有没有 assets/（自带工作目录），再向上找。
    反过来会先撞上一个外面早就在用的资产区，然后往别人的目录里写东西。
    """
    env = os.environ.get("DSH_ASSETS", "").strip()
    if env:
        return os.path.abspath(env), "环境变量 DSH_ASSETS"

    local = os.path.join(SKILL_ROOT_OF_TOOL, "assets")
    if os.path.isdir(local):
        return os.path.abspath(local), "默认值（脚本旁的 assets/）"

    def looks_like(p):
        try:
            names = set(os.listdir(p))
        except OSError:
            return False
        return ("技能" in names) or ("名片" in names)

    for c in _upward_roots(levels=4, kids=60):
        if looks_like(c):
            return os.path.abspath(c), "自动探测（脚本位置附近，含 技能/ 或 名片/）"
    return os.path.abspath(local), "默认值（脚本旁的 assets/，尚不存在，运行时会建）"


def find_state():
    env = os.environ.get("DSH_STATE", "").strip()
    if env:
        return os.path.abspath(env), "环境变量 DSH_STATE"
    return os.path.abspath(os.path.join(SKILL_ROOT_OF_TOOL, "state")), "默认值（脚本旁的 state/）"


def find_home():
    env = os.environ.get("DSH_HOME", "").strip()
    if env:
        return os.path.abspath(env), "环境变量 DSH_HOME"
    return os.path.abspath(os.path.join(os.path.expanduser("~"), ".dsh")), "默认值（~/.dsh）"


ORIGIN, ORIGIN_SRC = find_origin()
ASSETS, ASSETS_SRC = find_assets()
STATE, STATE_SRC = find_state()
HOME, HOME_SRC = find_home()
DSH_HOME = HOME

SKILL_ROOT = os.path.join(ASSETS, "技能")
CARD_DIR = os.path.join(ASSETS, "名片")
ANCHOR_DIR = STATE
REGULARITY = os.path.join(STATE, "regularity.json")
SERVICES = os.path.join(STATE, "services.json")
SEED = "dsh-seed"

RES = os.path.join(ORIGIN, "resources") if ORIGIN else ""
ASAR = os.path.join(RES, "app.asar") if RES else ""
UNPACKED = os.path.join(RES, "app.asar.unpacked") if RES else ""
RUNTIME = os.path.join(RES, "runtime", "primary-runtime", "runtime.json") if RES else ""

_MNT = re.compile(r"^/mnt/([a-zA-Z])/(.*)$")
_WIN = re.compile(r"^([a-zA-Z]):[\\/](.*)$")


def resolve(p) -> str:
    """把任一写法落到当前系统能 open 的形式。"""
    p = str(p)
    if NT:
        m = _MNT.match(p)
        return f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\") if m else p
    m = _WIN.match(p)
    return f"/mnt/{m.group(1).lower()}/{m.group(2).replace(chr(92), '/')}" if m else p


def rel_to_origin(p) -> str:
    """给人看的地址：一律 Windows 原生写法（资料里两种写法并存，统一到这里）。"""
    p = str(p)
    m = _MNT.match(p)
    if m:
        p = f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\")
    return p


def runtime() -> dict:
    with open(resolve(RUNTIME), encoding="utf-8") as f:
        return json.load(f)


def version() -> str:
    try:
        return runtime().get("desktopVersion", "")
    except Exception:
        return ""


def born_at() -> str:
    """先天自己的出生时刻：取 app.asar 的写盘时刻。

    它是本体被造出来的那一刻；被拷到本机只算搬家（CreationTime），不算出生。
    对象一变这个值自己跟着变 —— 先天的时间永远是本体的时间，不手写。
    """
    import time as _t
    try:
        return _t.strftime("%Y-%m-%d %H:%M", _t.localtime(os.path.getmtime(resolve(ASAR))))
    except OSError:
        return ""


# ── 解析结果打印（每次运行都打，人一眼能核对） ────────────────────────────────

def print_resolution(stream=None) -> None:
    stream = stream or sys.stdout
    rows = [
        ("ORIGIN", ORIGIN, ORIGIN_SRC, _has_origin(ORIGIN)),
        ("ASSETS", ASSETS, ASSETS_SRC, os.path.isdir(ASSETS)),
        ("STATE", STATE, STATE_SRC, os.path.isdir(STATE) or True),
        ("HOME", HOME, HOME_SRC, os.path.isdir(HOME)),
    ]
    stream.write("── 地址解析 ─────────────────────────────────────────────\n")
    for k, v, src, ok in rows:
        flag = "存在" if ok else "缺失"
        stream.write(f"  {k:<7}{v or '（空）'}\n")
        stream.write(f"  {'':<7}来源：{src}　[{flag}]\n")
    if ORIGIN:
        for label, p in (("app.asar", ASAR), ("runtime.json", RUNTIME)):
            try:
                size = os.path.getsize(p)
                stream.write(f"  本体 {label:<13}{size:,} 字节  {p}\n")
            except OSError:
                stream.write(f"  本体 {label:<13}读不到  {p}\n")
    stream.write("────────────────────────────────────────────────────────\n")


def require_origin() -> None:
    """ORIGIN 不可用就当场说清楚，别让后面静默量出 0。"""
    if _has_origin(ORIGIN):
        return
    print_resolution()
    print("")
    print("× 找不到先天物质：这一层下面必须有 resources/app.asar", file=sys.stderr)
    print(f"  当前 ORIGIN = {ORIGIN or '（空）'}（来源：{ORIGIN_SRC}）", file=sys.stderr)
    print("  探过的地方（每层只列一层，没递归）：", file=sys.stderr)
    tried = [c for c in (_upward_roots(levels=2, kids=8) + _platform_roots()[:40]) if c]
    for c in tried[:12]:
        print(f"    · {c}", file=sys.stderr)
    if len(tried) > 12:
        print(f"    … 另探了 {len(tried) - 12} 处", file=sys.stderr)
    print("  没有命中的话，显式指定（这一步别无脑重试，先确认装在哪）：", file=sys.stderr)
    if NT:
        print('    set DSH_ORIGIN=D:\\你的DSH安装目录   （该目录下应有 resources\\app.asar）',
              file=sys.stderr)
    else:
        print("    export DSH_ORIGIN=/path/to/dsh   （该目录下应有 resources/app.asar）", file=sys.stderr)
    raise SystemExit(2)


def require_runtime() -> None:
    p = resolve(RUNTIME)
    if os.path.isfile(p):
        return
    print_resolution()
    print("", )
    print(f"× 找不到运行时清单：{RUNTIME}", file=sys.stderr)
    print("  它必须在 <ORIGIN>/resources/runtime/primary-runtime/runtime.json", file=sys.stderr)
    print("  版本号与 payloadDigest 只在它这里；缺了它，指纹没有第二名可对。", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    print_resolution()
