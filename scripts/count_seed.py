# -*- coding: utf-8 -*-
"""count_seed.py —— 把「几个数」各自怎么数写死在代码里，跑一次给一份确切数字。

为什么要有它：同一件事有几种数法，混着比就会得出「226 还是 227」这种没意义的分歧。
数字本身不错，错的是拿 A 口径的数去对 B 口径的数。这个脚本做两件事：

  1 每个口径单独算，并打印「它数的是什么、从哪读、按什么规则数」；
  2 把口径之间的差指出来 —— 差在哪一条、为什么两条都算对了。

四个口径
    口径 A  名片库文件数      <ASSETS>/名片/ 下的 *.md 实体文件，一个方向一张
    口径 B  带锚的名片条目数   种子 seed.json 里，名片条目的 锚 列表非空的条数
    口径 C  锚条数            种子 seed.json 里所有名片条目的 锚 逐条相加
    口径 D  去重对象数        口径 C 那些锚的 path 去重后的个数

另外两个对照口径（不是上面四个，但最容易被混进来）
    口径 E  SKILL.md frontmatter 的 looks_at 条数 —— 直接读文件，不读种子
    口径 F  birth 条数       种子里有 birth.at 的节点数

用法
    python count_seed.py                 # 默认种子（paths.py 解析到的位置）
    python count_seed.py <seed.json>     # 指定种子
    python count_seed.py --json          # 只出一份机读结果
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import paths  # noqa: E402  唯一地址源

try:
    import yaml
except Exception:
    yaml = None


def default_seed() -> str:
    return os.path.join(paths.SKILL_ROOT, paths.SEED, "seed.json")


def walk(nodes, out: list) -> None:
    for n in nodes or []:
        out.append(n or {})
        walk((n or {}).get("孩子") or [], out)


def count_card_files() -> list:
    """口径 A：名片库里的实体文件。判据是「这一层下以 .md 结尾的文件」。"""
    d = paths.CARD_DIR
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d)
                  if f.endswith(".md") and os.path.isfile(os.path.join(d, f)))


def count_looks_at_from_skills() -> dict:
    """口径 E：直接读每份 SKILL.md 的 frontmatter，数 card.looks_at。

    这条和种子口径不是同一份数据：种子里一个节点挂的是「名片」（可能是名片库的先天名片），
    而 SKILL.md 的 card 段是这份 skill 自己长出来的名片。两条都可能对，数出来不同就是不同。
    """
    out = {"files": 0, "with_looks": 0, "looks": 0, "per": {}}
    root = paths.SKILL_ROOT
    if not os.path.isdir(root) or not yaml:
        return out
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name, "SKILL.md")
        if not os.path.isfile(p):
            continue
        out["files"] += 1
        try:
            txt = open(p, encoding="utf-8").read()
        except OSError:
            continue
        m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
        if not m:
            continue
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception:
            continue
        la = (meta.get("card") or {}).get("looks_at") or []
        out["per"][name] = len(la)
        out["looks"] += len(la)
        if la:
            out["with_looks"] += 1
    return out


def analyse(seed_path: str) -> dict:
    seed = json.load(open(seed_path, encoding="utf-8"))
    nodes, raw = [], []
    walk(seed.get("先天") or [], raw)
    walk(seed.get("后天") or [], raw)
    for n in raw:
        nodes.append(n)

    card_entries, with_anchor, anchor_list = 0, 0, []
    kind_of = {}
    per_node = {}
    for n in nodes:
        tot = 0
        for c in n.get("名片") or []:
            card_entries += 1
            anc = c.get("锚") or []
            if anc:
                with_anchor += 1
            for a in anc:
                p = str(a.get("path") or "")
                anchor_list.append(p)
                kind_of.setdefault(p, str(a.get("kind") or ""))
                tot += 1
        per_node[str(n.get("name") or "")] = tot

    files = count_card_files()
    skills = count_looks_at_from_skills()
    uniq = set(anchor_list)
    uniq_kind = {}
    for p in uniq:
        k = kind_of.get(p, "")
        uniq_kind[k] = uniq_kind.get(k, 0) + 1

    # 口径 C 与口径 E 的差，逐节点定位到哪几条
    diffs = []
    for name, tot in sorted(per_node.items()):
        la = skills["per"].get(name)
        if la is None:
            continue
        if la != tot:
            diffs.append({"name": name, "种子锚条数": tot, "frontmatter_looks_at": la})

    return {
        "seed": os.path.abspath(seed_path),
        "A_名片库文件数": len(files),
        "A_文件清单": files,
        "B_带锚的名片条目数": with_anchor,
        "B_名片条目总数": card_entries,
        "C_锚条数": len(anchor_list),
        "C_kind": _kind_count(nodes),
        "D_去重对象数": len(uniq),
        "D_其中file": uniq_kind.get("file", 0),
        "D_其中dir": uniq_kind.get("dir", 0),
        "E_SKILL_md_份数": skills["files"],
        "E_带_looks_at_的份数": skills["with_looks"],
        "E_looks_at_条数": skills["looks"],
        "F_birth条数": sum(1 for n in nodes if str(n.get("at") or "").strip()),
        "节点数": len(nodes),
        "先天节点": len(seed.get("先天") or []),
        "后天顶层节点": len(seed.get("后天") or []),
        "C与E的差": diffs,
        "种子里的名片总数": seed.get("名片总数"),
    }


def _kind_count(nodes) -> dict:
    out = {}
    for n in nodes:
        for c in n.get("名片") or []:
            for a in c.get("锚") or []:
                k = str(a.get("kind") or "")
                out[k] = out.get(k, 0) + 1
    return out


def main(argv) -> int:
    args = [a for a in argv[1:] if not a.startswith("-")]
    as_json = "--json" in argv
    seed_path = os.path.abspath(args[0] if args else default_seed())
    if not os.path.isfile(seed_path):
        print("× 找不到种子：" + seed_path, file=sys.stderr)
        print("  先跑 python live.py 投影出种子，或用参数指定 seed.json 的路径", file=sys.stderr)
        return 2
    r = analyse(seed_path)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    w = 22
    print("数据源：" + r["seed"])
    print("名片库：" + paths.CARD_DIR)
    print("")
    print("── 口径 A · 名片库文件数 " + "-" * 40)
    print("  数什么：名片库这一层里以 .md 结尾的实体文件，一个方向一张")
    print("  从哪读：%s" % paths.CARD_DIR)
    print("  结果  ：%d 张" % r["A_名片库文件数"])
    if r["A_文件清单"]:
        print("  清单  ：" + "、".join(r["A_文件清单"]))
    print("")
    print("── 口径 B · 带锚的名片条目数 " + "-" * 34)
    print("  数什么：种子 seed.json 里，名片条目的 锚 列表非空的条数")
    print("  从哪读：seed.json 的 先天[] / 后天[] 递归展开后的每个节点的 名片[]")
    print("  结果  ：%d 条（名片条目总数 %d 条）" % (r["B_带锚的名片条目数"], r["B_名片条目总数"]))
    print("")
    print("── 口径 C · 锚条数 " + "-" * 44)
    print("  数什么：所有名片条目的 锚 逐条相加（同一个路径被两个件盯，算两条）")
    print("  从哪读：同上")
    print("  结果  ：%d 条（kind 分布：%s）"
          % (r["C_锚条数"], "、".join("%s %d" % (k or "空", v) for k, v in sorted(r["C_kind"].items()))))
    print("")
    print("── 口径 D · 去重对象数 " + "-" * 40)
    print("  数什么：口径 C 那些锚的 path 去重后的个数（一个文件被三个件盯，只算一个）")
    print("  从哪读：同上")
    print("  结果  ：%d 个不同对象（file %d、dir %d）"
          % (r["D_去重对象数"], r["D_其中file"], r["D_其中dir"]))
    print("")
    print("── 对照口径（不是上面四个，但最容易被混进来） " + "-" * 16)
    print("  E · SKILL.md frontmatter 的 looks_at 条数")
    print("      数什么：每份 SKILL.md 的 card.looks_at 逐份相加，不读种子")
    print("      从哪读：%s/*/SKILL.md" % paths.SKILL_ROOT)
    print("      结果  ：%d 条（共 %d 份 SKILL.md，其中 %d 份带 looks_at）"
          % (r["E_looks_at_条数"], r["E_SKILL_md_份数"], r["E_带_looks_at_的份数"]))
    print("  F · birth 条数")
    print("      数什么：种子里 birth.at 非空的节点数")
    print("      结果  ：%d 条（节点总数 %d：先天 %d + 后天全部节点）"
          % (r["F_birth条数"], r["节点数"], r["先天节点"]))
    print("")
    if r["C与E的差"]:
        print("── C 与 E 的差在哪 " + "-" * 40)
        print("  差 %d 条，逐节点：" % (r["C_锚条数"] - r["E_looks_at_条数"]))
        for d in r["C与E的差"]:
            print("    · %s：种子口径 %d 条，frontmatter 口径 %d 条"
                  % (d["name"], d["种子锚条数"], d["frontmatter_looks_at"]))
        print("  原因：种子给一个节点挂的是它「名片」—— 先天件的名片来自名片库，")
        print("        而 SKILL.md 里的 card 段是这份 skill 自己长出来的名片。两条数的是两份数据，")
        print("        两份都对。要比就得说清比的是哪一份。")
        print("")
    print("── 一句话 ─────────────────────────────" + "-" * 10)
    print("  名片库文件 %d 张 ／ 带锚的名片条目 %d 条 ／ 锚 %d 条 ／ 去重对象 %d 个"
          % (r["A_名片库文件数"], r["B_带锚的名片条目数"], r["C_锚条数"], r["D_去重对象数"]))
    print("  这四个数是四种数法，别横着比。要比就同一个脚本跑两次比。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
