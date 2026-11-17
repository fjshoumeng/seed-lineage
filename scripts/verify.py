# -*- coding: utf-8 -*-
"""verify.py —— 全链校验：本体 / 锚 / 扫描 / 名片 / 种子 / skill / 时序，每一环都得自己站住。

判什么（任何一条不成立，这一层就不算立起来）：

  1 本体读得对      读得出来、头形制没错位、包名与目录一致
  2 锚对得上        字节数 + sha256 + desktopVersion + payloadDigest
  3 扫描的数与锚一致 文件数 / 包数 / 预设行数 / 指引目录数
  4 名片            一张一个父亲、anchor 自证、指纹自洽、有规律一句话、无评价词
  5 种子            投影与文件一致（没人手改）
  6 skill           出生标签齐、依据连着、名片对得上、正文地址存在
  7 时序            儿子不早于父亲

这一份校验里**没有我们的数字**：所有期望值都从锚与扫描账里读。
换一台机器、换一份本体，它照样能判 —— 判的是「这条链自洽不自洽」，不是「是不是我们那份」。

复跑：python verify.py
退出码：0 全绿；1 有未通过项。
"""
from __future__ import annotations

import json
import os
import re
import sys

import yaml

import live
import paths
import scan as _scan   # 借它那个能处理 !js 标签的 YAML loader
from asar import Asar, anchor_fp, verify_anchor

FAILS = []
CHECKS = 0
BANNED = ("失败", "错误", "坑", "教训")


def ck(cond, msg):
    global CHECKS
    CHECKS += 1
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        FAILS.append(msg)
    return bool(cond)


def main() -> int:
    paths.require_origin()
    paths.require_runtime()
    paths.print_resolution()

    ver = paths.version()
    ap = os.path.join(paths.ANCHOR_DIR, f"先天锚-{ver}.json")
    if not ck(os.path.isfile(ap), f"锚存在（{ap}）"):
        print("\n先跑：python scan.py")
        return 1
    anchor = json.load(open(ap, encoding="utf-8"))

    # ── 1 读得对 ─────────────────────────────────────────────────────────────
    a = Asar(paths.ASAR)
    ns = a.names()
    ck(len(ns) > 0, f"asar 索引读得出条目（{len(ns)} 个）")
    # 每个包读自己的 package.json：名字必须与目录一致 —— 这一条能抓出 3 字节错位
    # 包根只取「应用层第一层」那一组（与 scan.py 同一口径），别把包内子路径的
    # package.json 当包根 —— 那些文件本来就不叫目录名（如 @google/genai/node）。
    pkg_roots = []
    for n in ns:
        if not n.startswith("/dsh/node_modules/") or not n.endswith("/package.json"):
            continue
        part = n[len("/dsh/node_modules/"):-len("/package.json")]
        if part.count("/") <= 1:          # name 或 @scope/name，正好是包根
            pkg_roots.append(part)
    pkg_roots = sorted(pkg_roots)[:12]
    bad_name = []
    for r in pkg_roots:
        try:
            d = json.loads(a.read("/dsh/node_modules/" + r + "/package.json"))
            if d.get("name") != r:
                bad_name.append(f"{r} ≠ {d.get('name')}")
        except Exception as e:
            bad_name.append(f"{r}: {type(e).__name__}")
    ck(not bad_name, f"读 {len(pkg_roots)} 个包的 package.json，名字与目录一致"
       + (f"（不合 {bad_name[:3]}）" if bad_name else ""))

    # ── 2 锚 ────────────────────────────────────────────────────────────────
    ck(os.path.getsize(paths.ASAR) == anchor["asar"]["size"],
       f"asar 字节 = 锚里的 {anchor['asar']['size']:,}")
    ck(verify_anchor(anchor["asar"]), "asar sha256 与锚一致")
    ck(verify_anchor(anchor["runtime"]), "runtime.json sha256 与锚一致")
    rt = paths.runtime()
    ck(rt.get("desktopVersion") == anchor["version"], f"desktopVersion = {rt.get('desktopVersion')}")
    ck(rt.get("payloadDigest") == anchor["payloadDigest"], "payloadDigest 与锚一致")
    ck(anchor_fp([anchor["asar"], anchor["runtime"]]) == anchor["fingerprint"],
       f"锚指纹自洽 {anchor['fingerprint']}")

    # ── 3 扫描的数 ──────────────────────────────────────────────────────────
    reg = json.load(open(paths.REGULARITY, encoding="utf-8"))
    ck(reg["files"] == anchor["asar_files"], f"文件数 {reg['files']} = 锚 {anchor['asar_files']}")
    ck(reg["packages"] + reg["pkg_plain"] == anchor["packages"],
       f"包数 {reg['packages'] + reg['pkg_plain']} = 锚 {anchor['packages']}")
    ck(reg["preset_rows"] == anchor["preset_rows"], f"预设行 {reg['preset_rows']} = 锚 {anchor['preset_rows']}")
    ck(reg["upgrade_guide_count"] == anchor["upgrade_guides"],
       f"升级指引项 {reg['upgrade_guide_count']} = 锚 {anchor['upgrade_guides']}")
    ck(reg["preset_files_parsed"] == len(reg["presets"]),
       f"预设文件全部可解析（{reg['preset_files_parsed']}/{len(reg['presets'])}）"
       "—— 少一个就说明 loader 认不出 !js 标签，行数会假小")
    ck(reg["preset_rows"] > 0, f"预设行 > 0（{reg['preset_rows']}）—— 等于 0 时「每行必有 id」是空检查")
    ck(reg["pkg_total"] > 0, f"包数 > 0（{reg['pkg_total']}）—— 等于 0 时 exports / Config 比值是空检查")

    # ── 4 名片 ──────────────────────────────────────────────────────────────
    files = sorted(f for f in os.listdir(paths.CARD_DIR) if f.endswith(".md")) if os.path.isdir(paths.CARD_DIR) else []
    innate_dirs = [d for d in os.listdir(paths.SKILL_ROOT)
                   if d.startswith("dsh-innate-")
                   and os.path.isfile(os.path.join(paths.SKILL_ROOT, d, "SKILL.md"))] \
        if os.path.isdir(paths.SKILL_ROOT) else []
    ck(len(files) == len(innate_dirs),
       f"名片 {len(files)} 张 = 先天 skill {len(innate_dirs)} 份（一张一名片）")
    fp_all, gens = set(), set()
    for f in files:
        txt = open(os.path.join(paths.CARD_DIR, f), encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
        if not ck(bool(m), f"名片 {f} frontmatter 可切"):
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        anc = meta.get("anchor") or []
        gen = str(meta.get("生成", "")).strip()
        gens.add(gen)
        ck(bool(gen) and os.path.isfile(os.path.join(paths.SKILL_ROOT, gen, "SKILL.md")),
           f"名片 {f} 有父（生成: {gen}）")
        ck(all(verify_anchor(x) for x in anc), f"名片 {f} anchor 自证（{len(anc)} 个对象）")
        ck(str(meta.get("fingerprint", "")) == anchor_fp(anc), f"名片 {f} 指纹自洽")
        ck("规律一句话" in body, f"名片 {f} 有规律一句话")
        hit = [w for w in BANNED if w in body]
        ck(not hit, f"名片 {f} 无评价词" + (f"（命中 {hit}）" if hit else ""))
        ck(str(meta.get("版本", "")) == ver, f"名片 {f} 版本 = 本体版本 {ver}")
        fp_all.add(str(meta.get("fingerprint", "")))
    if files:
        ck(len(fp_all) == 1, f"名片同源指纹（{len(fp_all)} 种）")
        ck(gens == set(innate_dirs), f"名片与先天 skill 一一对应（{len(gens)} 个父）")

    # ── 5 种子 ──────────────────────────────────────────────────────────────
    skills, problems = live.collect()
    cards, cproblems = live.read_cards()
    seedp = os.path.join(paths.SKILL_ROOT, paths.SEED, "SKILL.md")
    if ck(os.path.isfile(seedp), "种子文件存在"):
        seed = open(seedp, encoding="utf-8").read()
        m = re.search(r'^  at: "([^"]+)"', seed, re.M)
        born = m.group(1) if m else ""
        ck(seed == live.render(skills, cards, born), "种子与投影一致（没人手改）")

    # ── 6 skill ─────────────────────────────────────────────────────────────
    bad_fm = []
    for name in sorted(os.listdir(paths.SKILL_ROOT)) if os.path.isdir(paths.SKILL_ROOT) else []:
        p = os.path.join(paths.SKILL_ROOT, name, "SKILL.md")
        if not os.path.isfile(p):
            continue
        m = re.match(r"^---\n(.*?)\n---", open(p, encoding="utf-8").read(), re.S)
        if not m:
            bad_fm.append(f"{name}(无 frontmatter)")
            continue
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception as e:
            bad_fm.append(f"{name}(YAML: {str(e).splitlines()[0][:40]})")
            continue
        if not meta.get("name") or not meta.get("description"):
            bad_fm.append(f"{name}(缺 name/description)")
    ck(not bad_fm, "每份 SKILL.md frontmatter 可解析且 name/description 齐"
       + (f"：{bad_fm}" if bad_fm else ""))
    ck(len(skills) >= 1, f"{len(skills)} 个 skill 带出生标签")
    ck(not (problems or cproblems),
       "live 自检 0 个问题" if not (problems or cproblems) else f"live 自检：{problems + cproblems}")
    for s in skills:
        ck(bool(s["card"].get("fingerprint")), f"{s['name']} 名片有指纹")
        if s["state"] == live.SEALED_STATE:
            ck(live.is_sealed(s["meta"]), f"{s['name']} 已封存（指纹不比对，其余照验）")
            continue
        ck(s["state"] == "活", f"{s['name']} 名片对象没变（{s['state']}）")

    # ── 7 时序：儿子不能早于父亲 ──────────────────────────────────────────────
    born = {s["name"]: str((s["birth"] or {}).get("at") or "") for s in skills}
    frm = {s["name"]: str((s["birth"] or {}).get("from") or "") for s in skills}
    bad = [f"{n}（{born[n]}）早于父亲 {f}（{born[f]}）" for n, f in frm.items()
           if f in born and born.get(f) and born.get(n) and born[n] < born[f]]
    ck(not bad, f"时序：{len(frm)} 节都不早于自己的父亲" + (f"（{bad[:3]}）" if bad else ""))

    print()
    print(f"{CHECKS} 项检查，{'全部通过' if not FAILS else str(len(FAILS)) + ' 项未通过'}")
    for f in FAILS:
        print("  × " + f)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
