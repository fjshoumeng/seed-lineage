# -*- coding: utf-8 -*-
"""scan.py —— 扫先天，量规律，写锚。

只量「必然是什么」：位置 / 分类 / 骨架 / 计数 / 指纹。
不评价、不比较、不判断「对不对」—— 覆盖率回答「填了多少」，那不是一个规律。

三个动作各有边界：
    · 量必然：全部样本都成立才写（每个件必有承载、每个包必有 package.json）
    · 数清单：包名、预设文件名、自带 skill 名 —— 数出来是什么就是什么
    · 写锚：asar 与 runtime.json 的字节数 + sha256 —— 这是后面所有指纹的基准

不问「有多少个缺」就下结论：本脚本第一版对空集合也能打出 100%，
所以每个比值都同时打印分母；分母是 0 的那行是空检查，不能当通过。

复跑：
    python scan.py            # 打印 + 写 regularity.json 与 先天锚-<版本>.json
    python scan.py --print    # 只打印，不动文件
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

import yaml

import paths
from asar import Asar, anchor_fp, file_anchor, sha256_file


def _yml(text: str):
    """本体里的 yml 带 !js 自定义标签（如 !js URLSearchParams）。

    yaml.safe_load 遇到它会整份解析失败 —— 那样预设在所有机器上都会量成「0 行」，
    而 0 行又会让「每行必有 id」这条规律空过。所以这个 loader 必须带着走。
    """
    class L(yaml.SafeLoader):
        pass

    def js(loader, suffix, node):
        if isinstance(node, yaml.ScalarNode):
            return node.value
        if isinstance(node, yaml.SequenceNode):
            return [loader.construct_object(x) for x in node.value]
        if isinstance(node, yaml.MappingNode):
            return {loader.construct_object(k): loader.construct_object(v) for k, v in node.value}
        return None

    L.add_multi_constructor("tag:yaml.org,2002:js", js)
    L.add_multi_constructor("!js", js)
    return yaml.load(text, Loader=L)


def scan(root: str = None) -> dict:
    root = root or paths.ORIGIN
    asar_path = os.path.join(root, "resources", "app.asar")
    rt = json.load(open(os.path.join(root, "resources", "runtime", "primary-runtime", "runtime.json"),
                        encoding="utf-8"))
    a = Asar(asar_path)
    names = a.names()

    pkgs = sorted({"/".join(n.split("/")[3:5]) for n in names
                   if n.startswith("/dsh/node_modules/@") and len(n.split("/")) > 5})
    extra = sorted({n.split("/")[3] for n in names
                    if n.startswith("/dsh/node_modules/") and not n.startswith("/dsh/node_modules/@")
                    and len(n.split("/")) > 4})

    pkg_fields = Counter()
    cfg_have = exports_have = 0
    for p in pkgs:
        pj = f"/dsh/node_modules/{p}/package.json"
        if not a.exists(pj):
            continue
        try:
            d = json.loads(a.read(pj))
        except Exception:
            raw = a.read(pj)
            d = {}
            for k in ("name", "version", "main", "exports", "peerDependencies", "dependencies"):
                if f'"{k}"' in raw:
                    d[k] = True
        for k in d:
            pkg_fields[k] += 1
        if "exports" in d:
            exports_have += 1
        for cand in ("lib/index.js", "lib/index.mjs", "index.js"):
            fp = f"/dsh/node_modules/{p}/{cand}"
            if a.exists(fp):
                if "Config = z.object(" in a.read(fp):
                    cfg_have += 1
                break

    presets = sorted({n.split("/")[-1] for n in names
                      if "/dsh-web-app/presets/" in n and n.endswith(".yml")})
    row_detail = {"rows": 0, "groups": 0, "with_name": 0, "files_parsed": 0}
    for name in presets:
        p = f"/dsh/node_modules/@deepseek-ai/dsh-web-app/presets/{name}"
        if not a.exists(p):
            continue

        def walk(items):
            if isinstance(items, dict):
                if "id" in items and "name" in items:
                    row_detail["rows"] += 1
                    row_detail["with_name"] += 1
                    if items.get("name") == "cordis:group":
                        row_detail["groups"] += 1
                for v in items.values():
                    walk(v)
            elif isinstance(items, list):
                for v in items:
                    walk(v)

        try:
            walk(_yml(a.read(p)) or [])
            row_detail["files_parsed"] += 1
        except Exception:
            pass

    sk_dirs = sorted({n.split("/")[6] for n in names
                      if n.startswith("/dsh/node_modules/@deepseek-ai/dsh-agent-preset/skills/")
                      and n.endswith("/SKILL.md")})
    sk_fields = Counter()
    for d in sk_dirs:
        p = f"/dsh/node_modules/@deepseek-ai/dsh-agent-preset/skills/{d}/SKILL.md"
        m = re.match(r"^---\n(.*?)\n---", a.read(p), re.S)
        if m:
            for k in (_yml(m.group(1)) or {}):
                sk_fields[k] += 1

    ug = sorted({n.split("/")[7] for n in names if "/docs/upgrade-guide/" in n})
    tops = sorted({n.split("/")[1] for n in names if len(n.split("/")) > 1})

    unpacked = a.unpacked_names()
    return {
        "root": root,
        "version": rt.get("desktopVersion", ""),
        "payload_digest": rt.get("payloadDigest", ""),
        "asar_bytes": os.path.getsize(asar_path),
        "asar_sha256": sha256_file(asar_path),
        "files": len(names),
        "unpacked": len(unpacked),
        "tops": tops,
        "packages": len(pkgs),
        "pkg_scoped": len([p for p in pkgs if p.startswith("@")]),
        "pkg_plain": len(extra),
        "pkg_field_hits": dict(pkg_fields),
        "pkg_total": len(pkgs),
        "exports_have": exports_have,
        "config_have": cfg_have,
        "presets": presets,
        "preset_rows": row_detail["rows"],
        "preset_groups": row_detail["groups"],
        "preset_with_name": row_detail["with_name"],
        "preset_files_parsed": row_detail["files_parsed"],
        "bundled_skills": sk_dirs,
        "skill_field_hits": dict(sk_fields),
        "upgrade_guides": ug,
        "upgrade_guide_count": len(ug),
    }


def report(s: dict) -> None:
    total_pkg = s["packages"] + s["pkg_plain"]
    print(f"先天：{s['root']}　版本 {s['version']}")
    print(f"app.asar {s['asar_bytes']/1048576:.1f} MB　sha256 {s['asar_sha256'][:16]}…")
    print(f"文件 {s['files']} 个（asar 内 {s['files'] - s['unpacked']} / unpacked {s['unpacked']}）")
    print(f"包 {total_pkg}（@{s['pkg_scoped']} + 平铺 {s['pkg_plain']}）")
    print(f"顶层：{', '.join('/' + t for t in s['tops'])}　（{len(s['tops'])} 项）")
    print(f"Config schema {s['config_have']}/{s['pkg_total']}　exports {s['exports_have']}/{s['pkg_total']}"
          f"　—— 分母 {s['pkg_total']}，分母为 0 时这两行是空检查")
    print(f"预设 {len(s['presets'])} 个文件（解析成功 {s['preset_files_parsed']}）/ "
          f"{s['preset_rows']} 行 / {s['preset_groups']} 组")
    print(f"自带 skill {len(s['bundled_skills'])} 个：{', '.join(s['bundled_skills']) or '无'}")
    print(f"升级指引目录 {s['upgrade_guide_count']} 个：{', '.join(s['upgrade_guides']) or '无'}")
    print("")
    print("以上数字都是「这台机器上那份本体」的数。换一台机器、换一个版本，这些数会不同 ——")
    print("不同是对的；相同才需要解释。")


def main() -> int:
    paths.require_origin()
    paths.require_runtime()
    paths.print_resolution()
    s = scan()
    report(s)
    if "--print" not in sys.argv:
        os.makedirs(paths.STATE, exist_ok=True)
        with open(paths.REGULARITY, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)

        asar = file_anchor(paths.ASAR, "先天本体（app.asar）")
        rt = file_anchor(paths.RUNTIME, "运行时清单（runtime.json）")
        anchor = {
            "version": s["version"],
            "payloadDigest": s["payload_digest"],
            "asar": asar,
            "runtime": rt,
            "unpacked_files": s["unpacked"],
            "asar_files": s["files"],
            "packages": s["packages"] + s["pkg_plain"],
            "preset_rows": s["preset_rows"],
            "upgrade_guides": s["upgrade_guide_count"],
            "fingerprint": anchor_fp([asar, rt]),
        }
        out = os.path.join(paths.ANCHOR_DIR, f"先天锚-{s['version'] or 'unknown'}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(anchor, f, ensure_ascii=False, indent=1)
        print("")
        print(f"写出 {paths.REGULARITY}")
        print(f"写出 {out}")
        print(f"锚指纹 {anchor['fingerprint']}　（= app.asar + runtime.json 二者此刻的样子）")
        print("")
        print("下一步：python gen_innate.py　（从这份扫描数据长出先天 skill 与名片）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
