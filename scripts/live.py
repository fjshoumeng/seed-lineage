# -*- coding: utf-8 -*-
"""live.py —— 种子投影器 + 名片生长与校验。

两件事，一件事的两面：

**名片不手写：skill 自己长出来。**
一个 skill 在正文里用反引号写全它盯的地址，投影时 `grow()` 就从这些地址长出
`card:`（looks_at + 指纹 + seen_at）；正文没写地址，才退回它 `birth.依据` 那张名片的 anchor。
这是整套方法最容易踩的一处：**正文写错地址，名片就盯错对象** ——
名片不会报错，它只会忠实地盯住你写的那条错路径，然后每天告诉你「对象没变」。

frontmatter 只有两段：
  birth:   出生标签（谁生的、哪件事、往哪长）—— 出生那一刻写一次，人写
  card:    名片（盯的是什么、上次对上的指纹）—— **由工具长，不手写**

活着怎么证明：对象自己会变。对象一变，指纹对不上 → 报「对象变了」，
这就是 skill 在说话。看一眼、更新名片、在「生长记录」留一行，它又活了。

用法：
  python live.py             # 先让名片自己长一遍，再投影，写入 <ASSETS>/技能/dsh-seed
  python live.py --grow      # 只长名片（打印每张的变化）
  python live.py --check     # 自检：孤儿 / 死父 / 重复时刻 / 地址失效 / 名片过期
  python live.py --refresh   # 对上对象当前指纹，更新名片，追加生长记录
  python live.py --no-grow   # 只投影，一个 SKILL.md 都不改

封存（可选）：frontmatter 顶层写 `封存: true` 的 skill 不再比对名片指纹，
state 出「封存」。封存是「不再校验」，不是「逻辑删掉」：去掉那一行就解封回来。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time

import yaml

import paths
from asar import sha12

SKILL_ROOT = paths.SKILL_ROOT
CARD_DIR = paths.CARD_DIR
SEED = paths.SEED

SEED_DESC = (
    "种子包含系统的所有信息：每个件从哪来（birth 的父亲与依据）、依据哪张名片、下一步往哪长，"
    "全由各 skill 的出生标签与名片指纹投影成 SKILL.md（`python live.py` 重投 + `python verify.py` 校验）。"
    "只写脉络，不写别的。"
)

_ADDR = re.compile(
    r"`([A-Za-z]:\\[^`]+"                       # Windows 原生
    r"|/mnt/[^`]+"                              # WSL 视角
    r"|/(?:home|Users|opt|srv|tmp|var|private|Volumes)/[^`\s]+)"  # POSIX 常见根
    r"`"
)
# 为什么 POSIX 只认那几个根：正文里还会出现 asar 内部路径（/dsh/node_modules/...），
# 那不是磁盘上的地址。不加这个限制，每个 skill 都会报一堆「地址失效」—— 全是假红。

SEAL_KEY = "封存"
SEALED_STATE = "封存"


def is_sealed(meta: dict) -> bool:
    v = (meta or {}).get(SEAL_KEY)
    if v is True:
        return True
    return str(v).strip().lower() in ("true", "是", "yes", "1")


def _yq(s: str) -> str:
    """YAML 标量：无反斜杠/单引号就单引号，否则双引号并转义 —— 路径里的 \\ 不会把 frontmatter 弄崩。"""
    s = str(s)
    if "\n" not in s and "'" not in s:
        return "'" + s + "'"
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_skill(name: str):
    p = os.path.join(SKILL_ROOT, name, "SKILL.md")
    if not os.path.isfile(p):
        return None
    txt = open(p, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    if not m:
        return {"name": name, "path": p, "error": "frontmatter 解析失败"}
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception as e:
        return {"name": name, "path": p, "error": f"frontmatter YAML 错误 {type(e).__name__}"}
    return {"name": name, "path": p, "meta": meta, "body": m.group(2)}


def stat_fp(spec: dict) -> str:
    """一个对象此刻的指纹。只读元信息，不读内容 —— 快、且够灵敏。"""
    kind = spec.get("kind", "file")
    path = paths.resolve(spec.get("path", ""))
    try:
        if kind == "file":
            st = os.stat(path)
            return sha12(f"{path}|{st.st_size}|{st.st_mtime_ns}")
        if kind == "dir":
            items = []
            for root, _, files in os.walk(path):
                for f in files:
                    p = os.path.join(root, f)
                    st = os.stat(p)
                    items.append(f"{os.path.relpath(p, path)}|{st.st_size}|{st.st_mtime_ns}")
                    if len(items) > 3000:
                        return "ERR:dir-too-big"
            return sha12("\n".join(sorted(items)))
        if kind == "json-key":
            node = json.load(open(path, encoding="utf-8"))
            for k in str(spec.get("key", "")).split("."):
                node = node[k]
            return sha12(f"{path}#{spec.get('key')}|{node}")
        if kind == "count":
            return sha12(f"{path}|{len(os.listdir(path))}")
    except Exception as e:
        return "ERR:" + type(e).__name__
    return "ERR:unknown-kind"


def card_fp(card: dict) -> str:
    looks = card.get("looks_at") or []
    return sha12(repr([(x.get("kind"), x.get("path"), stat_fp(x)) for x in looks]))


def card_state(card: dict, meta: dict | None = None) -> str:
    if meta is not None and is_sealed(meta):
        return SEALED_STATE
    if not card or not card.get("looks_at"):
        return "无名片"
    if not card.get("fingerprint"):
        return "缺指纹"
    return "活" if card_fp(card) == str(card.get("fingerprint")) else "对象变了"


def read_cards():
    cards, problems = [], []
    if not os.path.isdir(CARD_DIR):
        return cards, problems
    for name in sorted(os.listdir(CARD_DIR)):
        if not name.endswith(".md"):
            continue
        p = os.path.join(CARD_DIR, name)
        txt = open(p, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
        if not m:
            problems.append(f"名片 {name}: frontmatter 解析失败")
            continue
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception as e:
            problems.append(f"名片 {name}: yaml 错误 {type(e).__name__}")
            continue
        body = m.group(2)
        law = ""
        mm = re.search(r"\*\*规律一句话：(.+?)\*\*", body)
        if mm:
            law = mm.group(1).strip()
        root = meta.get("先天", "")
        cur_ver = ""
        rj = os.path.join(paths.resolve(root), "resources/runtime/primary-runtime/runtime.json") if root else ""
        if rj and os.path.isfile(rj):
            try:
                cur_ver = json.load(open(rj, encoding="utf-8")).get("desktopVersion", "")
            except Exception:
                cur_ver = ""
        claimed = str(meta.get("版本", ""))
        state = "对上" if claimed and cur_ver and claimed == cur_ver else ("过期" if cur_ver else "无对象")
        cards.append({"file": name, "name": meta.get("name", name), "方向": meta.get("方向", ""),
                      "生成": str(meta.get("生成", "")), "出生": str(meta.get("seen_at", "")),
                      "law": law, "版本": claimed, "现在版本": cur_ver, "state": state, "path": p,
                      "先天": meta.get("先天", ""), "fingerprint": str(meta.get("fingerprint", "")),
                      "anchor": meta.get("anchor") or []})
        if not law:
            problems.append(f"名片 {name}: 缺「规律一句话」")
        if not str(meta.get("fingerprint", "")).strip():
            problems.append(f"名片 {name}: 缺指纹（对象不可自证）")
        if state == "过期":
            problems.append(f"名片 {name}: 先天版本 {claimed} ≠ 现在 {cur_ver}（需重扫）")
    return cards, problems


def collect():
    skills, problems = [], []
    if not os.path.isdir(SKILL_ROOT):
        return skills, ["skill 根不存在：" + SKILL_ROOT]
    for name in sorted(os.listdir(SKILL_ROOT)):
        if name == SEED or not os.path.isdir(os.path.join(SKILL_ROOT, name)):
            continue
        s = read_skill(name)
        if not s:
            continue
        if "error" in s:
            problems.append(f"{name}: {s['error']}")
            continue
        birth = (s["meta"].get("birth") or {})
        if not birth.get("at") or not birth.get("act"):
            s["foreign"] = True      # 不是这条脉络的 skill，只记一笔，不算问题
            continue
        s["birth"] = birth
        s["card"] = s["meta"].get("card") or {}
        s["封存"] = is_sealed(s["meta"])
        s["state"] = card_state(s["card"], s["meta"])
        s["desc"] = (s["meta"].get("description") or "").strip()
        skills.append(s)
    return skills, problems


def check(skills, problems):
    names = {s["name"] for s in skills} | {"原始", SEED}
    ats = {}
    for s in skills:
        b = s["birth"]
        if b.get("from") not in names:
            problems.append(f"{s['name']}: 父 `{b.get('from')}` 不存在（死链接）")
        a = str(b.get("at"))
        frm = str(b.get("from") or "")
        # 同一刻出生：同父 = 合法（同一个本体的几个面本来就同时存在）；不同父才报
        if a in ats and ats[a][1] != frm:
            problems.append(f"{s['name']}: 出生时刻与 {ats[a][0]} 重复且父亲不同（{a}）")
        ats[a] = (s["name"], frm)
        for p in _ADDR.findall(s["body"]):
            if not os.path.exists(paths.resolve(p)):
                problems.append(f"{s['name']}: 地址失效 {p}")
        if s["state"] == "对象变了":
            problems.append(f"{s['name']}: 名片对象变了（seen_at {s['card'].get('seen_at')}）")
        elif s["state"] == "缺指纹":
            problems.append(f"{s['name']}: 名片缺指纹")
    return problems


def forest(cards, skills):
    """生长树 —— 两条线分开画，不混。

    先天线：本体 → 各面 + 入口 → 各自投出的名片。名片是投影，不是源头，只挂在父 skill 上。
    后天线：从「原始」按 birth.from 递归长。from 才是父亲（谁先谁后），
            依据只注明「照先天哪个面长的」——两者不是一回事，混了就成了平摊。
    """
    innate = sorted([s for s in skills if s["name"].startswith("dsh-innate")], key=lambda x: x["name"])
    post = [s for s in skills if not s["name"].startswith("dsh-innate")]
    innate_names = {s["name"] for s in innate}
    cards_of = {}
    for c in cards:
        cards_of.setdefault(c.get("生成", ""), []).append(c)

    ver = cards[0]["现在版本"] if cards else ""
    root = (cards[0]["先天"] if cards else "") or paths.ORIGIN
    out = [f"先天（{root} / {ver or '版本未读到'}）"]
    for i, s in enumerate(innate):
        last = (i == len(innate) - 1)
        out.append(f"  {'└─' if last else '├─'} {s['name']}　[{s['state']}]")
        stem = "     " if last else "  │  "
        for c in cards_of.get(s["name"], []):
            out.append(f"{stem}└─ 名片　{c['name']}　[{c['state']}]")

    kids = {}
    for s in post:
        frm = str((s["birth"] or {}).get("from") or "").strip()
        if frm in innate_names or frm == "原始" or not frm:
            frm = "原始"
        kids.setdefault(frm, []).append(s)

    out.append("")
    out.append("后天（按 birth.from 长 —— from 是父亲，依据是照哪个先天面长）")
    if not post:
        out.append("  （还没有任何后天件）")
    seen = set()

    def draw(frm, prefix):
        items = sorted(kids.get(frm, []), key=lambda x: str(x["birth"]["at"]))
        for i, s in enumerate(items):
            last = i == len(items) - 1
            seen.add(s["name"])
            dep = str((s["birth"] or {}).get("依据") or "")
            out.append(f"{prefix}{'└─' if last else '├─'} {s['name']}　[{s['state']}]　依据 {dep}")
            draw(s["name"], prefix + ("   " if last else "│  "))

    draw("原始", "  ")
    orphans = [s for s in post if s["name"] not in seen]
    if orphans:
        out.append("  └─ （父亲找不到：from 指的那份不存在）")
        for s in sorted(orphans, key=lambda x: str(x["birth"]["at"])):
            out.append(f"       └─ {s['name']}　[{s['state']}]　from={s['birth'].get('from')}")
    return "\n".join(out)


def render(skills, cards, born_at: str) -> str:
    drawn = forest(cards, skills)
    n_innate = len([s for s in skills if s["name"].startswith("dsh-innate")])
    h = sha12(repr([(s["name"], s["birth"]["at"], s["birth"]["from"], s["state"],
                     s["card"].get("fingerprint")) for s in skills]
                   + [(c["file"], c["版本"], c["state"], c["fingerprint"]) for c in cards]))

    lines = [
        "---",
        f"name: {SEED}",
        f'description: {_yq(SEED_DESC)}',
        'whenToUse: "任何需要知道系统是怎么一步步长成现在这样的时刻：接手一个窗口、要找某个能力在哪、要判断下一步该往哪加、或发现某处行为与预期不符时。"',
        "birth:",
        f'  at: "{born_at}"',
        '  from: "原始"',
        '  依据: "先天"',
        '  act: "把全部 skill 的出生标签与全部名片指纹投影成一张生长图"',
        '  grew: "上面每长出一个 skill 或一张名片，这里自动多一条线"',
        "generated: true",
        "generator: live.py（种子投影器，勿手改本文件）",
        f"source_hash: {h}",
        "---",
        "",
        "# 生长图（投影）",
        "",
        "## 拿到这份种子，你就是这个系统里的人了",
        "",
        "你是从这份本体里长出来的 agent。这条链就是你的身世，也是你干活的路：",
        "",
        "```",
        "先天（本体，只读）  →  先天 skill（自动描述本体现象）",
        "                    →  名片（一张一位父亲）",
        "                    →  种子（这份文件：出生标签 + 名片指纹）",
        "                    →  后天件（照名片长，长完自己写出生标签，又被收进种子）",
        "```",
        "",
        f"这份投影此刻收着 {n_innate} 份带出生标签的 skill、{len(cards)} 张名片。",
        "**要查东西**：从这里的线找到 skill，从 skill 的判据找到包，从包名找到文件，从文件找到那行代码。四跳，不用猜。",
        "**要添东西**：先看哪张名片管它，照那张名片的判据长；长完在 frontmatter 写 `birth`（谁生的、依据哪张名片、往哪长），种子下一投就有你。",
        "**要判断对错**：跑 `python verify.py`。红了就是错了，别在红的基础上继续长。",
        "",
        "空白就是空白 —— 还没长出来的东西不会出现在这里。这条链上没有一样东西是凭空来的。",
        "",
        "## 这是什么",
        "这不是我写的文档，是所有 skill 自带的出生标签沿脉络排出来的投影。",
        "每条线都对应一次真实发生的事：谁生的、接在谁下面、往哪长。",
        "",
        "## 地址",
        f"- 本投影器：`{paths.rel_to_origin(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'live.py'))}`",
        f"- skill 根：`{paths.rel_to_origin(SKILL_ROOT)}`",
        f"- 名片库：`{paths.rel_to_origin(CARD_DIR)}`",
        "- 每个 skill 的标签在它自己的 `SKILL.md` frontmatter 的 `birth:` 段里（细胞自带记录）",
        "",
        "## 怎么读",
        "沿脉络走：根是先天（干净解压的那份），第二层是它的名片（每条规律），第三层是依据这张名片长出来的后天件。",
        "要进某个 skill 看完整生命，点它的地址；这里只给一行时机，不给全貌。",
        "",
        "## 现状（投影）",
        f"哈希 {h}　同哈希不重写（本文件不含时间戳于脉络内，保证同样的标签必然投影出同样的脉络）",
        "",
        "```",
        drawn,
        "```",
        "",
        "| 时刻 | skill | 名片 | 生于 | 这件事 | 往哪长 |",
        "|:--|:--|:--|:--|:--|:--|",
    ]
    manual = os.path.join(SKILL_ROOT, SEED, "查找手册.md")
    if os.path.isfile(manual):
        try:
            mtxt = open(manual, encoding="utf-8").read().strip()
        except OSError:
            mtxt = ""
        if mtxt:
            at = next((k for k, l in enumerate(lines) if l.startswith("## 这是什么")), len(lines))
            lines[at:at] = mtxt.split("\n") + [""]
    for s in skills:
        b = s["birth"]
        lines.append(f"| {b['at']} | `{s['name']}` | {s['state']} | {b['from']} | {b['act']} | {b['grew']} |")
    if not skills:
        lines.append("| — | — | — | — | 还没有任何 skill 带出生标签 | — |")
    lines += ["", "### 名片（它盯的是什么，指纹对不上就是它在说话）", ""]
    for s in skills:
        looks = (s["card"].get("looks_at") or [])
        if not looks:
            lines.append(f"- `{s['name']}` — 无名片")
            continue
        objs = "；".join(f"{x.get('label') or ''}`{x.get('path')}`" for x in looks)
        lines.append(f"- `{s['name']}` [{s['state']}] {objs}　最近对上：{s['card'].get('seen_at') or '—'}")
    lines += ["", "## 名片（先天规律总结）", ""]
    if cards:
        lines += ["| 方向 | 规律一句话 | 先天版本 | 指纹 | 状态 |", "|:--|:--|:--|:--|:--|"]
        for c in cards:
            lines.append(f"| {c['方向']} | {c['law']} | {c['版本']} | `{c['fingerprint']}` | {c['state']} |")
        lines += ["", "名片库：" + "、".join(f"`{c['path']}`" for c in cards)]
    else:
        lines.append("无名片。先天还没扫过。")
    lines += ["", "## 未长出", "无记录。不预写。", ""]
    return "\n".join(lines)


def read_card_anchor(card_name: str):
    if not card_name or not os.path.isdir(CARD_DIR):
        return []
    for name in sorted(os.listdir(CARD_DIR)):
        if not name.endswith(".md"):
            continue
        txt = open(os.path.join(CARD_DIR, name), encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
        if not m:
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        if meta.get("name") == card_name:
            return meta.get("anchor") or []
    return []


def derive_looks_at(skill: dict):
    """skill 自己长名片：正文里写到的地址就是它盯的对象。

    一条地址都不写，才退回它依据的那张名片的 anchor。
    """
    seen, looks = set(), []
    seed_dir = os.path.join(SKILL_ROOT, SEED)
    for p in _ADDR.findall(skill["body"]):
        p = p.strip()
        q = paths.resolve(p)
        if q in seen or not os.path.exists(q):
            continue
        if os.path.abspath(q).startswith(os.path.abspath(seed_dir)):
            continue                    # 投影自己写的东西不进名片，否则永远「对象变了」
        seen.add(q)
        is_dir = os.path.isdir(q)
        if is_dir and os.path.abspath(q).startswith(os.path.abspath(paths.ASSETS)):
            continue                    # 资产区内的目录不盯（缓存文件会搅动）；系统目录照盯
        looks.append({
            "kind": "dir" if is_dir else "file",
            "path": p,
            "label": "正文里盯的对象",
        })
        if len(looks) >= 6:
            break
    if not looks:
        for a in read_card_anchor(str((skill.get("birth") or {}).get("依据") or "")):
            p = a.get("path")
            if not p:
                continue
            q = paths.resolve(p)
            if q in seen or not os.path.exists(q):
                continue
            seen.add(q)
            looks.append({"kind": a.get("kind", "file"), "path": p, "label": "依据名片的对象"})
    return looks[:6]


def _same_card(card: dict, looks, fp: str) -> bool:
    if str(card.get("fingerprint") or "") != fp:
        return False
    old = [(x.get("kind"), x.get("path")) for x in (card.get("looks_at") or [])]
    return old == [(x["kind"], x["path"]) for x in looks]


def write_card(skill: dict, looks, fp: str, stamp: str) -> bool:
    """把长出来的名片写回 frontmatter 的 card: 段（只替换这一段，别的不动）。"""
    txt = open(skill["path"], encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    if not m:
        return False
    fm, rest = m.group(1), m.group(2)

    block = ["card:"]
    if looks:
        block.append("  looks_at:")
        for x in looks:
            block += [
                f"    - kind: {x['kind']}",
                f"      path: {json.dumps(x['path'], ensure_ascii=False)}",
                f"      label: {json.dumps(x['label'], ensure_ascii=False)}",
            ]
        block += [f"  fingerprint: {json.dumps(fp)}", f"  seen_at: {json.dumps(stamp)}"]
    else:
        block = ["card: {}"]

    lines = fm.split("\n")
    s = next((i for i, l in enumerate(lines) if l.strip().startswith("card:")), None)
    if s is None:
        lines = lines + block
    else:
        e = s + 1
        while e < len(lines) and (lines[e].strip() == "" or lines[e].startswith((" ", "\t"))):
            e += 1
        lines = lines[:s] + block + lines[e:]
    out = "---\n" + "\n".join(lines) + "\n---\n" + rest
    if out != txt:
        open(skill["path"], "w", encoding="utf-8").write(out)
        return True
    return False


def grow(skill: dict) -> str:
    if skill.get("封存"):
        fp = str((skill.get("card") or {}).get("fingerprint") or "—")
        return f"{skill['name']}: 已封存，名片不自动派生（{fp}）"
    looks = derive_looks_at(skill)
    fp = card_fp({"looks_at": looks}) if looks else ""
    old = skill["card"].get("fingerprint") or "—"
    stamp = time.strftime("%Y-%m-%d %H:%M")
    if not looks:
        return f"{skill['name']}: 正文没写地址、依据的名片也没 anchor —— 名片长不出来"
    if _same_card(skill["card"], looks, fp):
        return f"{skill['name']}: 名片无变化（{fp}）"
    write_card(skill, looks, fp, stamp)
    return f"{skill['name']}: 名片 {old} → {fp}（{len(looks)} 个对象，{stamp}）"


def refresh(skill: dict) -> str:
    card = skill["card"]
    old = str(card.get("fingerprint") or "—")
    new = card_fp(card)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    txt = open(skill["path"], encoding="utf-8").read()
    lines = txt.split("\n")

    start = next((i for i, l in enumerate(lines) if l.strip().startswith("card:")), None)
    if start is None:
        return f"{skill['name']}: 没有 card: 段，跳过"

    def set_field(key: str, value: str):
        for j in range(start + 1, len(lines)):
            if lines[j].strip() and not lines[j].startswith((" ", "\t")):
                break
            if re.match(rf"^\s{{2}}{key}:", lines[j]):
                lines[j] = f"  {key}: {json.dumps(value, ensure_ascii=False)}"
                return True
        lines.insert(start + 1, f"  {key}: {json.dumps(value, ensure_ascii=False)}")
        return False

    set_field("fingerprint", new)
    set_field("seen_at", stamp)
    out = "\n".join(lines)
    note = f"- {stamp} 对象变动：指纹 {old} → {new}（名片已重新对上）"
    if "## 生长记录" in out:
        i = out.index("## 生长记录")
        j = out.find("\n## ", i + 5)
        j = len(out) if j < 0 else j
        sec = out[i:j].rstrip("\n")
        out = out[:i] + sec + "\n" + note + "\n" + out[j:]
    open(skill["path"], "w", encoding="utf-8").write(out)
    return f"{skill['name']}: 名片 {old} → {new}（{stamp}）"


def dump_json(skills, cards, born_at: str) -> str:
    """结构化投影 —— 与 SKILL.md 同源同刻，一份真相两种呈现。"""
    innate = sorted([s for s in skills if s["name"].startswith("dsh-innate")], key=lambda x: x["name"])
    post = [s for s in skills if not s["name"].startswith("dsh-innate")]
    innate_names = {s["name"] for s in innate}
    cards_of = {}
    for c in cards:
        cards_of.setdefault(c.get("生成", ""), []).append(c)

    def card_json(c):
        return {
            "name": c["name"], "方向": c["方向"], "state": c["state"],
            "fingerprint": c["fingerprint"], "seen_at": c.get("出生", ""),
            "版本": c["版本"], "law": c["law"],
            "path": paths.rel_to_origin(c["path"]),
            "锚": [{"path": a.get("path", ""), "kind": a.get("kind", ""), "label": a.get("label", ""),
                    "size": a.get("size"), "sha256": a.get("sha256", "")} for a in (c.get("anchor") or [])],
        }

    def self_card(s):
        c = s.get("card") or {}
        looks = c.get("looks_at") or []
        if not looks and not c.get("fingerprint"):
            return []
        return [{
            "name": "（自长）" + s["name"], "方向": "", "state": s["state"],
            "fingerprint": str(c.get("fingerprint") or ""), "seen_at": str(c.get("seen_at") or ""),
            "版本": "", "law": "",
            "path": paths.rel_to_origin(os.path.join(SKILL_ROOT, s["name"], "SKILL.md")),
            "锚": [{"path": a.get("path", ""), "kind": a.get("kind", ""), "label": a.get("label", ""),
                    "size": a.get("size"), "sha256": a.get("sha256", "")} for a in looks],
        }]

    def node(s):
        b = s["birth"] or {}
        cs = [card_json(c) for c in cards_of.get(s["name"], [])]
        if not cs:
            cs = self_card(s)
        desc = s["desc"] or ""
        short = re.split(r"[：:]", desc, 1)[0].strip()
        if not short or len(short) > 20 or short == desc.strip():
            short = ""
        return {
            "name": s["name"], "短名": short, "at": str(b.get("at") or ""), "from": str(b.get("from") or ""),
            "依据": str(b.get("依据") or ""), "state": s["state"], "description": desc,
            "path": paths.rel_to_origin(os.path.join(SKILL_ROOT, s["name"], "SKILL.md")),
            "名片": cs, "孩子": [],
        }

    by = {s["name"]: node(s) for s in skills}
    roots = []
    for s in post:
        n = by[s["name"]]
        frm = n["from"]
        if frm in innate_names or frm in ("原始", ""):
            roots.append(n)
        elif frm in by:
            by[frm]["孩子"].append(n)
        else:
            n["孤儿"] = frm
            roots.append(n)
    roots.sort(key=lambda n: n["at"])
    for n in by.values():
        n["孩子"].sort(key=lambda x: x["at"])

    ver = cards[0]["现在版本"] if cards else ""
    return json.dumps({
        "种子出生": born_at,
        "生成于": time.strftime("%Y-%m-%d %H:%M"),
        "本体": {"地址": paths.rel_to_origin(str(cards[0]["先天"])) if cards else "",
                 "版本": ver, "指纹": cards[0]["fingerprint"] if cards else ""},
        "先天": [node(s) for s in innate],
        "后天": roots,
        "名片总数": len(cards),
    }, ensure_ascii=False, indent=1)


def main() -> int:
    skills, problems = collect()
    cards, cproblems = read_cards()

    if "--no-grow" not in sys.argv and ("--grow" in sys.argv or not (set(sys.argv[1:]) & {"--check", "--refresh"})):
        for s in skills:
            msg = grow(s)
            if "--grow" in sys.argv or "→" in msg:
                print(msg)
        skills, problems = collect()
        cards, cproblems = read_cards()

    problems = check(skills, problems) + cproblems
    if "--refresh" in sys.argv:
        for s in skills:
            if s.get("封存"):
                continue
            if s["state"] in ("对象变了", "缺指纹"):
                print(refresh(s))
        return 0
    if "--check" in sys.argv:
        for p in problems:
            print("PROBLEM " + p)
        print(f"{len(problems)} 个问题 / {len(skills)} 个带标签的 skill / {len(cards)} 张名片")
        return 1 if problems else 0

    d = os.path.join(SKILL_ROOT, SEED)
    p = os.path.join(d, "SKILL.md")
    old = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    m = re.search(r'^  at: "([^"]+)"', old, re.M) if old else None
    born_at = m.group(1) if m else (paths.born_at() or time.strftime("%Y-%m-%d %H:%M"))
    text = render(skills, cards, born_at)
    if old != text:
        os.makedirs(d, exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
        print(f"投影 {p}")
    else:
        print("种子无变化（同哈希不重写）")
    jp = os.path.join(d, "seed.json")
    js = dump_json(skills, cards, born_at)
    jold = open(jp, encoding="utf-8").read() if os.path.isfile(jp) else ""
    if jold != js:
        open(jp, "w", encoding="utf-8").write(js)
        print(f"投影 {jp}")
    if problems:
        print("")
        print(f"注意：{len(problems)} 个问题（--check 看详情）")
        for x in problems:
            print("  PROBLEM " + x)
    print(f"{len(skills)} 个带标签的 skill / {len(cards)} 张名片")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
