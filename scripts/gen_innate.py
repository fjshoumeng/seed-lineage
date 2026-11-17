# -*- coding: utf-8 -*-
"""gen_innate.py —— 先天 skill 与先天名片生成器（自动，不手写）。

一句话：**先天 skill 不是写的，是从本体自动描述出来的现象。**

它做三件事，顺序不能换：
    1 读 scan.py 量出来的账（regularity.json）—— 自己不重复扫
    2 按方向把「这个方向必然是什么」描述成一份 SKILL.md（dsh-innate-<方向>）
    3 同时写一张名片（名片 = 这份 skill 的规律总结，挂在它下面）

它与名片同源同指纹：asar + runtime.json 一字节没变，这份描述就还是对的。
同指纹不重写（否则每次跑都刷新 seen_at，种子永远「被人改过」）。

**空白就是空白**：某个方向在这份本体里量不出东西（比如没有 webServer 那个包），
就不产出那一份 —— 不预写、不占位。换一台机器多长出一份，那是对的。

方向是可增减的：DIRECTIONS 里加一条就多一个方向，名片跟着自动长出来。

用法：
    python gen_innate.py            # 量、写（同指纹不重写）
    python gen_innate.py --force    # 强制重写
    python gen_innate.py --dry      # 只打印会写什么
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

import paths
from asar import Asar, anchor_fp, file_anchor
from scan import scan

RING = os.path.join(paths.STATE, "先天年轮.json")


def yq(s) -> str:
    """YAML 里放字符串：一律双引号 + JSON 转义，反斜杠不会被 yaml 吃掉。"""
    return json.dumps(str(s), ensure_ascii=False)


# ── 各方向的补充测量（只量必然，不评价） ──────────────────────────────────────

def scan_services(a: Asar) -> dict:
    """服务名 → 提供者包；再用 consumers 数出谁在用。

    判据只有两类调用：`.provide("x")` 与 `super(ctx, "x")`；注入项来自 static inject。
    中文文案、注释、字符串里的词一概不参与 —— 只认调用。
    """
    pkgs = sorted({"/".join(n.split("/")[3:5]) for n in a.names()
                   if n.startswith("/dsh/node_modules/@") and len(n.split("/")) > 5})
    providers = defaultdict(set)
    inj = Counter()
    for p in pkgs:
        for cand in ("lib/index.js", "lib/index.mjs", "index.js"):
            f = f"/dsh/node_modules/{p}/{cand}"
            if a.exists(f):
                t = a.read(f)
                for m in re.finditer(r'\.provide\(\s*"([a-zA-Z][\w.]*)"', t):
                    providers[m.group(1)].add(p)
                for m in re.finditer(r'super\(ctx,\s*"([a-zA-Z][\w.]*)"', t):
                    providers[m.group(1)].add(p)
                for m in re.finditer(r'static inject = \[([^\]]*)\]', t):
                    for x in m.group(1).split(","):
                        x = x.strip().strip("\"'")
                        if x:
                            inj[x] += 1
                m = re.search(r"const inject = \[([^\]]*)\]", t)
                if m:
                    for x in m.group(1).split(","):
                        x = x.strip().strip("\"'")
                        if x:
                            inj[x] += 1
                break
    return {
        "scanned_at": time.strftime("%Y-%m-%d %H:%M"),
        "packages": len(pkgs),
        "services": {n: {"providers": sorted(v), "consumers": inj.get(n, 0)} for n, v in providers.items()},
        "injected_without_provider": {n: c for n, c in inj.items() if n not in providers},
    }


def scan_ports(a: Asar) -> dict:
    """路由只有两种 kind：exact 与其余全落 prefixes。端口号来自启动参数。"""
    out = {"kinds": [], "exact_table": False, "port_cfg": False, "desktop_port": "", "host": ""}
    for p in ("@deepseek-ai/dsh-host-webserver/lib/index.js",):
        try:
            src = a.read("/dsh/node_modules/" + p)
        except Exception:
            return out
        out["kinds"] = sorted(set(re.findall(r'kind\s*===?\s*"([a-z]+)"', src)))
        out["exact_table"] = ("this.exact" in src and "this.prefixes" in src)
        out["port_cfg"] = "this.config.port" in src
    try:
        host = a.read("/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/index.js")
        m = re.search(r"args:\s*\[([^\]]*)\]", host)
        args = re.findall(r'"([^"]*)"', m.group(1)) if m else []
        if "--port" in args:
            i = args.index("--port")
            out["desktop_port"] = args[i + 1] if i + 1 < len(args) else ""
        out["host"] = "dsh-desktop-host"
    except Exception:
        pass
    return out


def scan_windows(a: Asar) -> dict:
    """界面插件的判据：包名 + exports['./client'] 或 package.json 的 dsh.client。"""
    ns = a.names()
    base = "/dsh/node_modules/@deepseek-ai/"
    dirs = sorted({n[len(base):].split("/")[0] for n in ns if n.startswith(base)})
    ui = [d for d in dirs if d.startswith("dsh-client-ui-")]
    cl = [d for d in dirs if d.startswith("dsh-client-") and not d.startswith("dsh-client-ui-")]
    missing = []
    for d in ui + cl:
        try:
            pk = json.loads(a.read(f"{base}{d}/package.json"))
        except Exception:
            missing.append(d)
            continue
        if "./client" not in (pk.get("exports") or {}) and not (pk.get("dsh") or {}).get("client"):
            missing.append(d)
    return {"ui": ui, "client": cl, "missing_client_entry": missing}


# ── 方向定义：加一条就多一个方向，名片跟着自动长 ───────────────────────────────

def directions(s: dict, a: Asar, svc: dict, ports: dict, wins: dict) -> list:
    """返回 [(方向key, 方向中文, 规律一句话, 计数行[], 骨架行[], 判据行[])]。

    某个方向量不出东西就返回空列表 —— 调用方据此不产出（空白就是空白）。
    """
    out = []
    total_pkg = s["packages"] + s["pkg_plain"]

    # 布局
    if s["files"]:
        inner = s["files"] - s["unpacked"]
        out.append((
            "layout", "布局",
            "每个件必有位置和父层，没有凭空出现的件。",
            [f"- asar 内条目：**{s['files']}**",
             f"- 其中 unpacked（真身在 `app.asar.unpacked`）：**{s['unpacked']}**",
             f"- 落在 asar 数据区（有 offset）：**{inner}**",
             f"- 顶层结构项：**{len(s['tops'])}** —— {'、'.join('/' + t for t in s['tops'])}"],
            ["```",
             "resources/app.asar                     索引 + 数据（offset 相对 base）",
             "resources/app.asar.unpacked/           标 unpacked 的条目真身",
             "```"],
            ["- 任一要件必须能回答两问：在树的哪一层、数据在哪（asar 内 offset / unpacked 真身）。",
             "- 答不出第二问的件不存在 —— 读 header 时若某项既无 offset 也没标 unpacked，就是读错了，不是本体缺件。",
             "- 位置由包名与目录决定，不按文件名猜。"]))
    # 插件
    if total_pkg:
        out.append((
            "plugin", "插件",
            "每个包必有 package.json 宣告身份，入口由 main / exports 显式宣告，不按文件名猜。",
            [f"- 包总数：**{total_pkg}**",
             f"- `@scope/name` 形：**{s['pkg_scoped']}**　平铺形：**{s['pkg_plain']}**",
             f"- 声明 exports 的包：**{s['exports_have']}/{s['pkg_total']}**",
             f"- 入口文件里带 Config schema 的包：**{s['config_have']}/{s['pkg_total']}**"],
            ["```",
             "<包>/package.json      name / version / main / exports / dsh",
             "  main       单入口（字符串），Node 按它找",
             "  exports['.'] 新的入口宣告（字符串或条件对象）",
             "  'dsh.bundle' 发布档标记；'dsh.client' 界面半的入口",
             "```"],
            ["- 找不到某个能力的归属，先看包名，再看那个包的 package.json 的 main / exports，最后才读实现。",
             "- 分母是 0 的比值是空检查，不能当通过：先确认包数 > 0。",
             "- 无 main 的包靠 exports 或 Node 默认的 index.js —— 这是两种合法形制，不是缺件。"]))
    # 服务
    if svc.get("services"):
        srv = svc["services"]
        no_prov = [k for k, v in srv.items() if not (v or {}).get("providers")]
        top = sorted(srv.items(), key=lambda kv: -(kv[1].get("consumers") or 0))[:5]
        out.append((
            "service", "服务",
            "每个服务名必有提供者；consumers 为 0 即没人用，但它仍然是一个服务名。",
            [f"- 服务名：**{len(srv)}**",
             f"- 无提供者的服务名：**{len(no_prov)}**",
             f"- 定义了却没找到提供者的注入项：**{len(svc.get('injected_without_provider') or {})}**",
             "- consumers 最高的几个：" + "；".join(f"`{k}` {v.get('consumers')}" for k, v in top)],
            ["```",
             "提供者：.provide(\"<服务名>\") 或 super(ctx, \"<服务名>\")",
             "消费者：static inject = [...] 里出现的名字，按出现次数计",
             "```"],
            ["- 问「某服务谁提供」：查 services.json 的 providers 列表。",
             "- 注入项里没提供者的那些是允许的（可选依赖），单独列出，不算缺件。"]))
    # 预设
    if s["preset_rows"]:
        out.append((
            "preset", "预设",
            "每个预设行必有 id；行分两类——组行（cordis:group）与插件行，组行以 config 列表再嵌一层。",
            [f"- 预设文件：**{len(s['presets'])}** 个（解析成功 {s['preset_files_parsed']}）",
             f"- 行：**{s['preset_rows']}**　有 name 的 {s['preset_with_name']}",
             f"- 组行（name = cordis:group）：**{s['preset_groups']}**",
             f"- 文件名：{'、'.join(s['presets'])}"],
            ["```yaml",
             "- id: <行 id>                       # 必有",
             "  name: '<插件包名 | cordis:group>'",
             "  config: …                         # 组行是子行列表；插件行是该插件 Config 的取值",
             "```"],
            ["- 解析预设必须用能认 `!js` 标签的 loader；用严格 safe_load 会整份失败，量成 0 行，而 0 行会让「每行必有 id」空过。",
             "- 行序不带加载语义（官方原文）：先后不由行位置决定。"]))
    # 文档
    if s["upgrade_guides"]:
        vers = [g for g in s["upgrade_guides"] if re.match(r"^v\d+\.\d+", g)]
        out.append((
            "doc", "文档",
            "升级指引按版本建目录，一个版本一个目录，目录名即版本号。",
            [f"- 升级指引目录项：**{s['upgrade_guide_count']}**",
             f"- 其中版本目录：**{len(vers)}** —— {'、'.join(vers) or '无'}",
             f"- 非版本项（如 README）：{s['upgrade_guide_count'] - len(vers)}"],
            ["```",
             "dsh/docs/upgrade-guide/<版本>/   ← 目录名即版本号",
             "dsh/docs/upgrade-guide/README.md ← 索引，不算版本目录",
             "```"],
            ["- 中文档只在 asar 里，不动磁盘；找不到某版说明时按目录名对版本号。",
             "- 版本目录数 = 升级指引项数 − 非版本项，别把 README 数进去。"]))
    # 自带 skill
    if s["bundled_skills"]:
        out.append((
            "skill", "自带skill",
            "每个自带 skill 必有 name 与 description；缺任一则整份不加载。",
            [f"- 自带 skill：**{len(s['bundled_skills'])}** 个 —— {'、'.join(s['bundled_skills'])}",
             "- 头部字段出现次数：" + "；".join(f"`{k}` {v}" for k, v in
                                            Counter(s["skill_field_hits"]).most_common(8))],
            ["```",
             "/dsh/node_modules/@deepseek-ai/dsh-agent-preset/skills/<名>/SKILL.md",
             "  ---",
             "  name: <必填，缺了整份不加载>",
             "  description: <必填，缺了整份不加载>",
             "  ---",
             "```"],
            ["- 加自己的 skill，先照这条：name + description 两个字段齐，否则文件在、目录里有、也看不见。",
             "- 自带 skill 的头部字段就是加载器的判据，不按目录名猜。"]))
    # 端口
    if ports.get("kinds") or ports.get("exact_table"):
        out.append((
            "port", "端口",
            "路由按 kind 分进 exact 与 prefixes 两张表，只有 exact 被显式识别，其余全落 prefixes。",
            [f"- 显式识别的 kind：**{', '.join(ports.get('kinds') or []) or '无'}**",
             f"- 两张表都在：**{'是' if ports.get('exact_table') else '否'}**",
             f"- 端口来自 Config：**{'是' if ports.get('port_cfg') else '否'}**",
             f"- 桌面壳启动参数 `--port`：**{ports.get('desktop_port') or '（没读到）'}**"],
            ["```",
             "webServer.route({ kind: 'exact'   , path })   → this.exact",
             "webServer.route({ kind: 'prefix'  , path })   → this.prefixes",
             "进程真正监听的端口来自启动参数（桌面壳常传 --port 0 = 让内核自选）",
             "```"],
            ["- 端口号不要写死：启动参数可能是 0，真实端口落在运行期（进程的监听表 / 启动参数回执）。",
             "- 问「某路由谁挂的」：按 path 前缀反查包，再看 kind 是 exact 还是 prefix。"]))
    # 窗口
    if wins.get("ui") or wins.get("client"):
        out.append((
            "window", "窗口",
            "每个界面插件都声明了 client 入口（exports['./client'] 或 package.json 的 dsh.client）。",
            [f"- 界面插件（dsh-client-ui-*）：**{len(wins.get('ui') or [])}**",
             f"- 客户端基础设施（dsh-client-*）：**{len(wins.get('client') or [])}**",
             f"- 没有声明 client 入口的：**{len(wins.get('missing_client_entry') or [])}**"],
            ["```",
             "dsh-client-ui-<名>/package.json",
             "  exports['./client'] 或 dsh.client   ← 两者之一，声明界面半",
             "```"],
            ["- 判据只认 package.json 的 client 入口宣告，不认包名之外的中文文案。",
             "- 界面分三层，某元素来自哪个包的哪一格，按包名 + 槽位调用反查。"]))
    return out


# ── 写片：先天 skill 与名片 ──────────────────────────────────────────────────

DESC = {
    "layout": "要查本体里有什么文件、共多少、按什么形态排：读本文件「计数」与「骨架」；数字全由 scan.py 只读扫描本体得出、可复跑复现。只描本体，不描后天件。",
    "plugin": "要查本体有哪些包、包的入口由谁宣告、怎么翻到具体那个文件：读本文件「骨架」与「判据」；判据看 package.json 的 main / exports 与导出语句本身，不按文件名猜。只描本体。",
    "service": "要查某服务名归哪个包提供、谁在用它：读本文件「计数」（consumers 降序即谁在用）；consumers=0 即没人用。只描本体。",
    "preset": "要查本体自带哪些模式、每个模式装了哪些插件行：读本文件「计数」；判据是模式定义逐行可解析。只描本体。",
    "doc": "要查本体的文档在哪、什么形制、有多少：读本文件「计数」；基准是官方原样解压的那份本体。只描本体。",
    "skill": "要查本体自带哪些 skill、头部 frontmatter 什么规矩：读本文件「判据」；缺 name 或 description 的整份不加载 —— 加 skill 先照这条。只描本体。",
    "port": "要查本体注册了哪些路由、两种 kind 各是什么：读本文件「判据」；kind 只有 exact 与其余全落 prefixes。只描本体。",
    "window": "要查界面分几层、某界面元素来自哪个包：读本文件「计数」与「判据」；判据看包名与 client 入口宣告。只描本体。",
}
WHEN = {
    "layout": "要问布局上的一个具体问题是「在哪 / 是什么形制 / 有多少」时；怀疑手上的结论不是从本体量出来的时。",
    "plugin": "要知道某个能力归哪个包、它的入口是哪个文件时。",
    "service": "要知道某服务谁提供、谁在消费时。",
    "preset": "要知道本体自带哪些模式、某个模式装了哪些行时。",
    "doc": "要找本体里的文档、升级指引时。",
    "skill": "要加自己的 skill、或查自带 skill 的头部规矩时。",
    "port": "要知道路由挂在哪、端口从哪来时。",
    "window": "要知道界面元素来自哪个包、界面分几层时。",
}


def skill_md(key, label, law, counts, skeleton, rules, s, anchors, fp, born) -> str:
    head = [
        "---",
        f"name: dsh-innate-{key}",
        f"description: {yq(DESC.get(key, ''))}",
        f"whenToUse: {yq(WHEN.get(key, ''))}",
        "birth:",
        f'  at: "{born}"',
        '  from: "原始"',
        '  依据: "先天"',
        f'  act: "从 {s["version"]} 本体自动描述出{label}现象（位置/形制/计数），不手写"',
        '  grew: "本体换版本时重跑 gen_innate.py，描述随本体变；指纹只认 asar + runtime.json"',
        "生成: gen_innate.py",
        f"版本: {s['version']}",
        f"fingerprint: {fp}",
        "anchor:",
    ]
    for x in anchors:
        head += [f'  - path: "{paths.rel_to_origin(x["path"]).replace(chr(92), "/")}"',
                 f"    size: {x['size']}",
                 f'    sha256: "{x["sha256"]}"']
    head.append("---")
    body = [
        "",
        f"# 先天 skill · {label}",
        "",
        f"**规律一句话：{law}**",
        "",
        f"> 盯的对象（照这份本体量的，不是标准答案）：`{paths.rel_to_origin(paths.ASAR)}`"
        f"（{anchors[0]['size']:,} 字节）、`{paths.rel_to_origin(paths.RUNTIME)}`（{anchors[1]['size']:,} 字节）。",
        "> 指纹与本层全部先天名片同源：本体一字节没变，这份描述就还是对的。",
        "> 换一台机器、换一个版本，这里的数会不同 —— 不同是对的，相同才需要解释。",
        "",
        "## 计数（本体量出来的）",
        "",
        *counts,
        "",
        "## 骨架",
        "",
        *skeleton,
        "",
        "## 判据",
        "",
        *rules,
        "",
        "## 复跑",
        "",
        "```",
        "python scan.py         # 1 扫本体，写 regularity.json 与锚",
        "python gen_innate.py   # 2 长出先天 skill 与名片（同指纹不重写）",
        "python live.py         # 3 投影成种子",
        "python verify.py       # 4 全链校验",
        "```",
        "",
    ]
    return "\n".join(head + body)


def card_md(key, label, law, counts, s, anchors, fp, gen, stamp, state_label="state") -> str:
    head = [
        "---",
        f"name: {yq('名片-' + label)}",
        f"方向: {yq(label)}",
        f"先天: {yq(paths.ORIGIN)}",
        f"版本: {yq(s['version'])}",
        f"fingerprint: {yq(fp)}",
        f"seen_at: {yq(stamp)}",
        f"生成: {yq(gen)}",
        "anchor:",
    ]
    for x in anchors:
        head += [f"  - kind: {yq(x['kind'])}",
                 f"    path: {yq(x['path'])}",
                 f"    label: {yq(x.get('label', ''))}",
                 f"    size: {x['size']}",
                 f"    sha256: {yq(x['sha256'])}"]
    head.append("---")
    body = [
        "",
        f"# 先天名片 · {label}",
        "",
        f"**规律一句话：{law}**",
        "",
        f"> 这张名片由先天 skill `{gen}` 长出来（不是手写、也不是直接扫本体）。",
        f"> 指纹 `{fp}` 与本层全部名片同源：本体一字节没变，这张名片就还是对的。",
        "",
        "## 计数（本体量出来的）",
        "",
        *[c for c in counts if c.strip().startswith("-")],
        "",
        f"## 变化",
        "",
        f"（指纹见 frontmatter；变动历史见 `{state_label}` 下的 先天年轮.json。）",
        "",
    ]
    return "\n".join(head + body)


def read_rings() -> list:
    try:
        with open(RING, encoding="utf-8") as fh:
            return json.load(fh).get("圈") or []
    except (OSError, ValueError):
        return []


def update_ring(metrics: dict, fp: str, s: dict) -> list:
    """年轮：本体每变化一次留一圈。同指纹不加圈。"""
    rings = read_rings()
    last = rings[-1] if rings else {}
    if last and last.get("指纹") == fp:
        return rings
    ring = {"时刻": time.strftime("%Y-%m-%d %H:%M"), "版本": s["version"], "指纹": fp,
            "变了什么": "首次登记" if not rings else "asar 或 runtime.json 与上一圈不同",
            **metrics}
    rings.append(ring)
    os.makedirs(os.path.dirname(RING), exist_ok=True)
    with open(RING, "w", encoding="utf-8") as fh:
        json.dump({"圈": rings}, fh, ensure_ascii=False, indent=2)
    return rings


def keep_card_block(old: str, new: str) -> str:
    """重写一份 skill 时保住它自己的 `card:` 段。

    名片是 live.py 从正文地址长出来的，不归本生成器管。这里若整份覆盖，
    会把刚长出来的名片抹掉 → live.py 下次又长一遍 → 两份文件互相改，永远不收敛。
    """
    if not old:
        return new

    def block(txt: str) -> str:
        m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
        if not m:
            return ""
        lines = m.group(1).split("\n")
        s = next((i for i, l in enumerate(lines) if l.strip().startswith("card:")), None)
        if s is None:
            return ""
        e = s + 1
        while e < len(lines) and (lines[e].strip() == "" or lines[e].startswith((" ", "\t"))):
            e += 1
        return "\n".join(lines[s:e])

    cb = block(old)
    if not cb:
        return new
    m = re.match(r"^(---\n)(.*?)(\n---\n)", new, re.S)
    if not m:
        return new
    lines = m.group(2).split("\n")
    # 新文本自己的 card 段（如果有）先拿掉，再接旧的
    s = next((i for i, l in enumerate(lines) if l.strip().startswith("card:")), None)
    if s is not None:
        e = s + 1
        while e < len(lines) and (lines[e].strip() == "" or lines[e].startswith((" ", "\t"))):
            e += 1
        lines = lines[:s] + lines[e:]
    return m.group(1) + "\n".join(lines) + "\n" + cb + m.group(3) + new[m.end():]


def main() -> int:
    paths.require_origin()
    paths.require_runtime()
    force = "--force" in sys.argv
    dry = "--dry" in sys.argv
    os.makedirs(paths.SKILL_ROOT, exist_ok=True)
    os.makedirs(paths.CARD_DIR, exist_ok=True)
    os.makedirs(paths.STATE, exist_ok=True)

    try:
        with open(paths.REGULARITY, encoding="utf-8") as f:
            s = json.load(f)
        # 账过期（换了本体）就别拿旧账长新描述
        if s.get("root") != paths.ORIGIN or s.get("version") != paths.version():
            raise ValueError
    except (OSError, ValueError):
        print("没有可用的扫描账（或账已过期），先跑 scan.py")
        s = scan()
    print(f"先天 {s['root']}　版本 {s['version']}　文件 {s['files']}　包 {s['packages'] + s['pkg_plain']}")

    a = Asar(paths.ASAR)
    svc = scan_services(a)
    with open(paths.SERVICES, "w", encoding="utf-8") as f:
        json.dump(svc, f, ensure_ascii=False, indent=1)
    ports = scan_ports(a)
    wins = scan_windows(a)

    anchors = [file_anchor(paths.ASAR, "先天本体（app.asar）"),
               file_anchor(paths.RUNTIME, "运行时清单（runtime.json）")]
    fp = anchor_fp(anchors)
    born = paths.born_at()
    stamp = time.strftime("%Y-%m-%d %H:%M")
    state_label = paths.rel_to_origin(paths.STATE)

    rings = update_ring({"文件": s["files"], "包": s["packages"] + s["pkg_plain"]}, fp, s)
    print(f"锚指纹 {fp}　年轮 {len(rings)} 圈")

    written, skipped = [], []
    for key, label, law, counts, skeleton, rules in directions(s, a, svc, ports, wins):
        d = os.path.join(paths.SKILL_ROOT, f"dsh-innate-{key}")
        sp = os.path.join(d, "SKILL.md")
        text = skill_md(key, label, law, counts, skeleton, rules, s, anchors, fp, born)
        old = open(sp, encoding="utf-8").read() if os.path.isfile(sp) else ""
        text = keep_card_block(old, text)
        if force or old != text:
            if dry:
                print(f"[dry] 会写 {sp}")
            else:
                os.makedirs(d, exist_ok=True)
                with open(sp, "w", encoding="utf-8") as f:
                    f.write(text)
                written.append(sp)
        else:
            skipped.append(sp)

        cp = os.path.join(paths.CARD_DIR, f"{label}.md")
        ctext = card_md(key, label, law, counts, s, anchors, fp, f"dsh-innate-{key}", stamp, state_label)
        cold = open(cp, encoding="utf-8").read() if os.path.isfile(cp) else ""
        # 名片同指纹不重写（否则 seen_at 每次都变，种子永远「被人改过」）
        same = (bool(cold) and f'fingerprint: "{fp}"' in cold
                and cold.split("---", 2)[-1] == ctext.split("---", 2)[-1])
        if force or not same:
            if dry:
                print(f"[dry] 会写 {cp}")
            else:
                with open(cp, "w", encoding="utf-8") as f:
                    f.write(ctext)

    print(f"先天 skill 写出 {len(written)} 份，未变 {len(skipped)} 份")
    for p in written:
        print("  + " + p)
    cards = sorted(f for f in os.listdir(paths.CARD_DIR) if f.endswith(".md"))
    print(f"名片 {len(cards)} 张：{'、'.join(cards)}")
    print("")
    print("下一步：python live.py　（让每个 skill 从自己正文里的地址长出名片，再投影成种子）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
