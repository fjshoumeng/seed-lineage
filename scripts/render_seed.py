# -*- coding: utf-8 -*-
"""render_seed.py —— 把 seed.json 现生成一张可点击的自包含 HTML。

为什么要有它：展示只有两种形态是活的 —— 结构化数据（给 agent）和可点的页面（给人）。
截图是死的：发布那天就开始假，而且它不会告诉你它假了。这一张页面每次从 seed.json 现生成，
种子一变重跑一遍就是新的，这就是它和静态图片的区别。

输入
    seed.json 路径。不给就取 paths.py 解析到的种子位置（<ASSETS>/技能/dsh-seed/seed.json）。

输出
    一个单文件 HTML（默认 ./seed-tree.html，或用 -o 指定）。不外链任何资源：没有 CDN、
    没有字体文件、没有图片，双击就能开、断网也能开。

页面里有什么
    顶部统计     节点数 / 名片条目数 / 锚条数 / 去重对象数 / 断锚数 —— 全部从 seed.json 现算
    树           按 birth.from 展开（from 才是父亲）：先天在上，后天在下，孤儿单独标出
    详情         点任一节点：name / 短名 / birth 四行（at / from / 依据 / act）/ 名片与它的锚 /
                 指纹与 seen_at / 这条描述盯的 SKILL.md 在不在
    边界         断锚标红并单列一栏；没有锚或没有 birth 的件单列「空白」一栏

幂等
    同一份 seed.json 跑两遍，输出逐字节一致：正文里没有任何时间戳，
    只在文件末尾的注释里写生成器与来源路径。

用法
    python render_seed.py                          # 默认种子 → ./seed-tree.html
    python render_seed.py <seed.json>              # 指定种子
    python render_seed.py <seed.json> -o out.html  # 指定输出
    python render_seed.py --print-path             # 只打印默认种子在哪
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import paths  # noqa: E402  唯一地址源（别在这里写死任何盘符路径）

try:
    import yaml
except Exception:            # pragma: no cover —— 没有 PyYAML 也能出页面，只是 act 会缺
    yaml = None

DEFAULT_OUT = "seed-tree.html"
BIRTH_KEYS = ("at", "from", "依据", "act", "grew")


# ── 读数据 ──────────────────────────────────────────────────────────────────

def default_seed() -> str:
    return os.path.join(paths.SKILL_ROOT, paths.SEED, "seed.json")


def read_birth(skill_path: str) -> dict:
    """birth 段在 SKILL.md 的 frontmatter 里（细胞自带记录），seed.json 只投影了一部分。

    seed.json 的节点带 at / from / 依据，不带 act 与 grew。为了把 birth 四行都摆出来，
    这里回读节点自己的 SKILL.md —— 数据仍然取自真实文件，不是写死的常量。
    """
    if not yaml or not skill_path or not os.path.isfile(paths.resolve(skill_path)):
        return {}
    try:
        txt = open(paths.resolve(skill_path), encoding="utf-8").read()
    except OSError:
        return {}
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return {}
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}
    b = meta.get("birth")
    return b if isinstance(b, dict) else {}


def flatten(nodes, group: str, out: list) -> None:
    for n in nodes or []:
        n = dict(n or {})
        n["_group"] = group
        out.append(n)
        flatten(n.get("孩子") or [], group, out)


def build(seed: dict, seed_path: str) -> dict:
    raw = []
    flatten(seed.get("先天") or [], "先天", raw)
    flatten(seed.get("后天") or [], "后天", raw)

    # 路径存在性缓存：去重对象远少于锚条数，一次判一次
    exists_cache: dict = {}

    def exists(p: str) -> bool:
        if p not in exists_cache:
            try:
                exists_cache[p] = os.path.exists(paths.resolve(p))
            except Exception:
                exists_cache[p] = False
        return exists_cache[p]

    nodes, used = [], {}
    for i, n in enumerate(raw):
        name = str(n.get("name") or "").strip()
        nid = "n%d" % i
        while nid in used:                      # 重名也各占一格，别把两个件并成一个
            nid += "_"
        used[nid] = name
        birth = read_birth(str(n.get("path") or ""))
        cards = []
        for c in n.get("名片") or []:
            anchors = []
            for a in c.get("锚") or []:
                ap = str(a.get("path") or "")
                anchors.append({
                    "path": ap,
                    "kind": str(a.get("kind") or ""),
                    "label": str(a.get("label") or ""),
                    "exists": exists(ap) if ap else False,
                })
            cards.append({
                "name": str(c.get("name") or ""),
                "方向": str(c.get("方向") or ""),
                "state": str(c.get("state") or ""),
                "fingerprint": str(c.get("fingerprint") or ""),
                "seen_at": str(c.get("seen_at") or ""),
                "版本": str(c.get("版本") or ""),
                "law": str(c.get("law") or ""),
                "path": str(c.get("path") or ""),
                "anchors": anchors,
            })
        anchor_total = sum(len(c["anchors"]) for c in cards)
        anchor_broken = sum(1 for c in cards for a in c["anchors"] if not a["exists"])
        at = str(n.get("at") or birth.get("at") or "")
        frm = str(n.get("from") or birth.get("from") or "")
        dep = str(n.get("依据") or birth.get("依据") or "")
        act = str(birth.get("act") or "")
        grew = str(birth.get("grew") or "")
        blank = []
        if not cards:
            blank.append("没有名片")
        elif anchor_total == 0:
            blank.append("名片没有锚")
        if not at:
            blank.append("没有 birth.at")
        if not frm:
            blank.append("没有 birth.from")
        if not dep:
            blank.append("没有 birth.依据")
        nodes.append({
            "id": nid,
            "name": name,
            "短名": str(n.get("短名") or ""),
            "at": at,
            "from": frm,
            "依据": dep,
            "act": act,
            "grew": grew,
            "state": str(n.get("state") or ""),
            "description": str(n.get("description") or ""),
            "path": str(n.get("path") or ""),
            "path_ok": exists(str(n.get("path") or "")) if n.get("path") else False,
            "group": n["_group"],
            "cards": cards,
            "anchor_total": anchor_total,
            "anchor_broken": anchor_broken,
            "blank": blank,
            "act_known": bool(act),
        })

    by_name = {}
    for n in nodes:
        by_name.setdefault(n["name"], n["id"])

    children, roots = {}, []
    for n in nodes:
        frm = n["from"]
        pid = by_name.get(frm) if (frm and frm != n["name"]) else None
        if pid:
            children.setdefault(pid, []).append(n["id"])
        else:
            roots.append(n["id"])
    for k in children:
        children[k].sort(key=lambda i: (nodes[int(i[1:].rstrip("_"))]["at"], nodes[int(i[1:].rstrip("_"))]["name"]))

    innate_ids = [n["id"] for n in nodes if n["group"] == "先天"]
    post_ids = [i for i in roots if i not in innate_ids]

    all_paths = [a["path"] for n in nodes for c in n["cards"] for a in c["anchors"]]
    broken = [{"node": n["name"], "node_id": n["id"], "path": a["path"], "kind": a["kind"]}
              for n in nodes for c in n["cards"] for a in c["anchors"] if not a["exists"]]
    blanks = [{"node": n["name"], "node_id": n["id"], "why": n["blank"]} for n in nodes if n["blank"]]

    stats = {
        "节点数": len(nodes),
        "先天节点": len(innate_ids),
        "后天节点": len(nodes) - len(innate_ids),
        "名片条目数": sum(len(n["cards"]) for n in nodes),
        "锚条数": len(all_paths),
        "去重对象数": len(set(all_paths)),
        "断锚数": len(broken),
        "空白节点数": len(blanks),
        "orphan_count": sum(1 for n in nodes if n["from"] and n["from"] not in by_name and n["from"] not in ("原始", "")),
    }

    # 种子里自带的时间字段（种子出生 / 生成于）是**数据**的一部分，不是渲染时刻：
    # 它们随 seed.json 变，但不会因为「现在几点」而变。本脚本不写任何渲染时刻，
    # 所以同一份 seed.json 字节跑两遍，输出必然逐字节相同（`--verify-idempotent` 可自证）。
    seed_meta = {
        "种子出生": str(seed.get("种子出生") or ""),
        "生成于": str(seed.get("生成于") or ""),
        "本体": seed.get("本体") or {},
        "名片总数": seed.get("名片总数"),
        "source": seed_path,
    }
    return {"seed": seed_meta, "stats": stats, "nodes": nodes,
            "children": children, "roots": roots,
            "先天": innate_ids, "后天": post_ids,
            "broken": broken, "blanks": blanks}


# ── 出页面 ──────────────────────────────────────────────────────────────────

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>种子：系统长成什么样（__TITLE__）</title>
<style>
:root{
  --bg:#0f1216; --panel:#161b22; --panel2:#1c232c; --line:#2a3441;
  --fg:#dfe6ee; --dim:#8b98a8; --accent:#63b3ed;
  --ok:#5fd39a; --warn:#f0b742; --bad:#f87171; --sealed:#8b9dc3;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg);
  font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",system-ui,sans-serif}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
code,.mono{font-family:ui-monospace,Consolas,"Courier New",monospace;font-size:12.5px}
header{padding:18px 22px 10px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#121821,#0f1216)}
h1{font-size:17px;margin:0 0 2px;font-weight:600;letter-spacing:.3px}
.sub{color:var(--dim);font-size:12.5px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 2px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px 13px;min-width:96px}
.stat b{display:block;font-size:19px;line-height:1.2;font-weight:600}
.stat span{color:var(--dim);font-size:11.5px}
.stat.bad b{color:var(--bad)}
.stat.zero b{color:var(--ok)}
.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:8px 22px 0;color:var(--dim);font-size:12.5px}
.toolbar input{background:var(--panel);border:1px solid var(--line);color:var(--fg);
  border-radius:6px;padding:5px 9px;width:220px;font:inherit;font-size:12.5px}
.toolbar button{background:var(--panel);border:1px solid var(--line);color:var(--fg);
  border-radius:6px;padding:4px 10px;font:inherit;font-size:12.5px;cursor:pointer}
.toolbar button:hover{border-color:var(--accent)}
main{display:grid;grid-template-columns:minmax(340px,44%) 1fr;gap:0;align-items:start}
#tree{padding:14px 10px 60px 22px;border-right:1px solid var(--line);min-height:60vh;
  max-height:calc(100vh - 190px);overflow:auto}
#detail{padding:16px 22px 60px;position:sticky;top:0;max-height:calc(100vh - 20px);overflow:auto}
.sec{color:var(--dim);font-size:11.5px;letter-spacing:1px;margin:16px 0 6px;text-transform:uppercase}
.tnode{position:relative;padding:1px 0}
.row{display:flex;align-items:baseline;gap:6px;flex-wrap:nowrap;padding:2px 6px;border-radius:5px;cursor:pointer}
.nameblock{flex:1 1 auto;min-width:0;overflow-wrap:anywhere}
.tags{display:flex;gap:5px;flex-wrap:wrap;flex:0 0 auto;align-items:baseline}
.row:hover{background:var(--panel2)}
.row.sel{background:#1d2b3a;box-shadow:inset 2px 0 0 var(--accent)}
.tw{width:14px;flex:0 0 14px;color:var(--dim);font-size:11px;user-select:none;text-align:center}
.tw.leaf{opacity:0}
.nm{color:var(--fg)}
.leafname{color:var(--dim)}
.tag{font-size:10.5px;padding:0 5px;border-radius:4px;border:1px solid var(--line);color:var(--dim)}
.tag.ok{color:var(--ok);border-color:#2c5a44}
.tag.warn{color:var(--warn);border-color:#5a4a1c}
.tag.sealed{color:var(--sealed);border-color:#39445c}
.tag.bad{color:var(--bad);border-color:#5c2b2b}
.kids{margin-left:14px;border-left:1px dashed #232c37;padding-left:2px}
.hidden{display:none}
h2{font-size:15px;margin:18px 0 6px;font-weight:600}
h3{font-size:12px;color:var(--dim);margin:16px 0 4px;letter-spacing:.6px;font-weight:600}
.kv{display:grid;grid-template-columns:74px 1fr;gap:2px 10px;font-size:13px}
.kv dt{color:var(--dim)}
.kv dd{margin:0;word-break:break-all}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid}
.badge.ok{color:var(--ok);border-color:#2c5a44}
.badge.warn{color:var(--warn);border-color:#5a4a1c}
.badge.bad{color:var(--bad);border-color:#5c2b2b}
.badge.sealed{color:var(--sealed);border-color:#39445c}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0}
.card .hd{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
.law{color:#c8d4e2;font-size:12.5px;border-left:2px solid var(--line);padding-left:8px;margin:6px 0}
ul.anchors{margin:4px 0 0;padding-left:16px}
ul.anchors li{margin:1px 0}
.broken{color:var(--bad)}
.gone{color:var(--bad);font-weight:600}
.muted{color:var(--dim)}
.empty{color:var(--dim);font-style:italic}
.warnbox{border:1px solid #5c2b2b;background:#241618;border-radius:8px;padding:10px 12px;margin:10px 0}
.warnbox b{color:var(--bad)}
#bottom{padding:6px 22px 40px;border-top:1px solid var(--line)}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:500}
footer{color:#5b6675;font-size:11.5px;padding:10px 22px 30px}
noscript{display:block;padding:20px;color:var(--warn)}
@media (max-width:900px){
  main{grid-template-columns:1fr}
  #tree{border-right:none;border-bottom:1px solid var(--line);max-height:none}
  #detail{position:static;max-height:none}
}
</style>
</head>
<body>
<header>
  <h1>种子 · 系统长成什么样</h1>
  <div class="sub">数据源 <code>__SRCPATH__</code>　种子出生 <span class="mono">__BORN__</span>　本体 <span class="mono">__ORIGIN__</span></div>
  <div class="sub" title="这是 seed.json 里记着的时刻，不是本页渲染的时刻；本页不记录自己的渲染时刻，所以同一份种子重跑出来的页面逐字节相同。">种子数据生成时刻 <span class="mono">__GEN__</span>　<span class="muted">（seed.json 自带字段，非本页渲染时刻 —— 本页不写渲染时刻，故同一份种子重跑＝同一份输出）</span></div>
  <div class="stats" id="stats"></div>
</header>
<div class="toolbar">
  <input id="q" placeholder="过滤节点名 / 短名 / 路径">
  <button data-act="expand">全部展开</button>
  <button data-act="collapse">全部收起</button>
  <span id="hint" class="muted"></span>
</div>
<main>
  <div id="tree"></div>
  <div id="detail"><p class="empty">点左边任一节点看它是什么、谁生的、盯的哪些对象。</p></div>
</main>
<div id="bottom"></div>
<footer>这一页每次都从 seed.json 现生成：种子一变，重跑 <code>python render_seed.py</code> 就是新的。它不是截图。</footer>
<noscript>这一页靠 JavaScript 把 seed.json 的内容铺开。请用允许脚本的浏览器打开（双击即可，不需要联网）。</noscript>
<script id="seed-data" type="application/json">__DATA__</script>
<script>
(function(){
  var D = JSON.parse(document.getElementById('seed-data').textContent);
  var N = {}, byId = {};
  D.nodes.forEach(function(n){ byId[n.id] = n; });
  D.nodes.forEach(function(n){ (N[n.id] = N[n.id] || []); });
  var collapsed = {}, selected = null, filter = '';

  function el(tag, cls, txt){
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt !== undefined && txt !== null) e.textContent = txt;
    return e;
  }
  function stateTag(s){
    var m = {'活':'ok','封存':'sealed','对上':'ok','对象变了':'warn','过期':'warn','缺指纹':'warn','无名片':'bad'}[s];
    return el('span','tag '+(m||''), s||'—');
  }
  function fmt(n){ return (n===null||n===undefined)?'—':String(n); }

  // ── 顶部统计：全部从这个 JSON 现算 ──
  var S = D.stats;
  var order = [['节点数',S['节点数'],'先天 '+S['先天节点']+' · 后天 '+S['后天节点']],
               ['名片条目数',S['名片条目数'],'每条一个父亲'],
               ['锚条数',S['锚条数'],'looks_at 展开后'],
               ['去重对象数',S['去重对象数'],'锚指向的不同路径'],
               ['断锚数',S['断锚数'],'锚指向不存在的路径'],
               ['空白节点数',S['空白节点数'],'没有锚或没有 birth']];
  var statsBox = document.getElementById('stats');
  order.forEach(function(it){
    var d = el('div','stat'+(it[0]==='断锚数'?(it[1]?' bad':' zero'):'')+(it[0]==='空白节点数'&&!it[1]?' zero':''));
    d.appendChild(el('b',null,String(it[1])));
    d.appendChild(el('span',null,it[0]));
    var s = el('div','sub'); s.style.fontSize='11px'; s.textContent = it[2];
    d.appendChild(s);
    statsBox.appendChild(d);
  });

  // ── 树 ──
  function match(n){
    if (!filter) return true;
    var q = filter.toLowerCase();
    return (n.name+' '+(n['短名']||'')+' '+(n.description||'')+' '+(n.path||'')).toLowerCase().indexOf(q) >= 0;
  }
  function subtreeHas(n){
    if (match(n)) return true;
    return (N[n.id]||[]).some(function(k){ return subtreeHas(byId[k]); });
  }
  function nodeRow(n, depth){
    var wrap = el('div','tnode');
    var row = el('div','row'+(selected===n.id?' sel':''));
    row.dataset.id = n.id;
    var kids = N[n.id] || [];
    var tw = el('span','tw'+(kids.length?'':' leaf'), kids.length ? (collapsed[n.id]?'▸':'▾') : '·');
    tw.dataset.toggle = n.id;
    row.appendChild(tw);
    var nb = el('span','nameblock');
    var nm = el('span','nm', n.name || '（无名）');
    if (n.group === '先天') nm.style.color = 'var(--accent)';
    nb.appendChild(nm);
    if (n['短名']) nb.appendChild(el('span','leafname','　· '+n['短名']));
    row.appendChild(nb);
    var tags = el('span','tags');
    if (n.anchor_broken) tags.appendChild(el('span','tag bad', n.anchor_broken+' 断锚'));
    tags.appendChild(stateTag(n['state']));
    row.appendChild(tags);
    wrap.appendChild(row);
    if (kids.length){
      var box = el('div','kids'+(collapsed[n.id]?' hidden':''));
      box.dataset.kids = n.id;
      kids.forEach(function(k){ if (subtreeHas(byId[k])) box.appendChild(nodeRow(byId[k], depth+1)); });
      wrap.appendChild(box);
    }
    return wrap;
  }
  function renderTree(){
    var tree = document.getElementById('tree');
    tree.innerHTML = '';
    tree.appendChild(el('div','sec','先天（本体这一层，只读基准）'));
    D['先天'].forEach(function(id){ if (subtreeHas(byId[id])) tree.appendChild(nodeRow(byId[id],0)); });
    tree.appendChild(el('div','sec','后天（按 birth.from 长 —— from 是父亲，依据是照哪条规律长的）'));
    if (!D['后天'].length) tree.appendChild(el('div','empty','（还没有任何后天件）'));
    D['后天'].forEach(function(id){ if (subtreeHas(byId[id])) tree.appendChild(nodeRow(byId[id],0)); });
    var orphan = D.nodes.filter(function(n){ return n.from && !byId[n.from] && n.from !== '原始' && n.from !== ''; });
    if (orphan.length){
      tree.appendChild(el('div','sec','父亲找不到（from 指的那一份不在这张种子里）'));
      orphan.forEach(function(n){ tree.appendChild(nodeRow(n,0)); });
    }
    document.getElementById('hint').textContent = filter
      ? ('过滤「'+filter+'」：命中 '+D.nodes.filter(function(n){return subtreeHas(n);}).length+' 个节点（含父）')
      : '共 '+D.nodes.length+' 个节点';
  }

  // ── 详情 ──
  function anchorLine(a){
    var li = el('li');
    var c = el('span','mono'+(a.exists?'':' broken'), a.path || '（空路径）');
    li.appendChild(c);
    li.appendChild(el('span','muted','　'+a.kind + (a.label?('　'+a.label):'')));
    li.appendChild(a.exists ? el('span','muted','　存在') : el('span','gone','　不存在（断锚）'));
    return li;
  }
  function showDetail(id){
    selected = id;
    var n = byId[id], d = document.getElementById('detail');
    d.innerHTML = '';
    var h = el('h2', null, n.name || '（无名）');
    d.appendChild(h);
    var meta = el('div','sub');
    meta.appendChild(stateTag(n['state']));
    meta.appendChild(el('span','muted','　'+(n.group==='先天'?'先天':'后天')+'　'+(n['短名']||'')));
    d.appendChild(meta);

    d.appendChild(el('h3',null,'birth（四行）'));
    var kv = el('dl','kv');
    [['at',n.at],['from',n.from],['依据',n['依据']],['act',n.act||'—（这条记录没写 act）'],
     ['grew',n.grew||'—']].forEach(function(p){
      kv.appendChild(el('dt',null,p[0]));
      var dd = el('dd');
      dd.appendChild(el('span', p[0]==='at'?'mono':'', p[1]||'—'));
      kv.appendChild(dd);
    });
    d.appendChild(kv);

    d.appendChild(el('h3',null,'它自己'));
    var kv2 = el('dl','kv');
    kv2.appendChild(el('dt',null,'描述'));
    kv2.appendChild(el('dd',null, n.description || '—'));
    kv2.appendChild(el('dt',null,'文件'));
    var ddf = el('dd');
    ddf.appendChild(el('span','mono'+(n.path_ok?'':' broken'), n.path || '—'));
    if (!n.path_ok) ddf.appendChild(el('span','gone','　（不在这台机器上）'));
    kv2.appendChild(ddf);
    kv2.appendChild(el('dt',null,'锚'));
    kv2.appendChild(el('dd',null, n.anchor_total + ' 条' + (n.anchor_broken?('，其中 '+n.anchor_broken+' 条断'):'')));
    d.appendChild(kv2);

    d.appendChild(el('h3',null,'名片（'+(n.cards.length)+' 条）'));
    if (!n.cards.length) d.appendChild(el('p','empty','这条没有名片 —— 它自己不盯任何对象，指纹无处可比。'));
    n.cards.forEach(function(c){
      var box = el('div','card');
      var hd = el('div','hd');
      hd.appendChild(el('b',null,c.name || '（无名片）'));
      if (c['方向']) hd.appendChild(el('span','tag',c['方向']));
      hd.appendChild(stateTag(c['state']));
      if (c['版本']) hd.appendChild(el('span','muted mono','本体 '+c['版本']));
      box.appendChild(hd);
      if (c.law) box.appendChild(el('div','law',c.law));
      var kv3 = el('dl','kv');
      kv3.appendChild(el('dt',null,'指纹'));
      kv3.appendChild(el('dd','mono', c.fingerprint || '—（缺指纹）'));
      kv3.appendChild(el('dt',null,'seen_at'));
      kv3.appendChild(el('dd','mono', c.seen_at || '—'));
      kv3.appendChild(el('dt',null,'名片'));
      var dd3 = el('dd');
      dd3.appendChild(el('span','mono', c.path || '—'));
      kv3.appendChild(dd3);
      box.appendChild(kv3);
      var ul = el('ul','anchors');
      if (!c.anchors.length) ul.appendChild(el('li','empty','没有锚：名片不指向任何对象'));
      c.anchors.forEach(function(a){ ul.appendChild(anchorLine(a)); });
      box.appendChild(el('div','muted','它盯的对象（'+c.anchors.length+'）'));
      box.appendChild(ul);
      d.appendChild(box);
    });
    renderTree();
    d.scrollTop = 0;
  }

  // ── 边界：断锚 + 空白 ──
  function renderBottom(){
    var b = document.getElementById('bottom');
    b.innerHTML = '';
    b.appendChild(el('h2',null,'边界'));
    b.appendChild(el('p','sub','空白就是空白：锚指向不存在的东西就标红（断锚），没有锚或没有 birth 的件单列在这里。它们不会被补成假的。'));

    b.appendChild(el('h3',null,'断锚（'+D.broken.length+'）'));
    if (!D.broken.length){
      b.appendChild(el('p','empty','0 条 —— 每一条锚都指向这台机器上真实存在的对象。'));
    } else {
      var t1 = el('table');
      var h = el('tr'); ['节点','锚指向的路径','类型'].forEach(function(x){ h.appendChild(el('th',null,x)); });
      t1.appendChild(h);
      D.broken.forEach(function(x){
        var tr = el('tr');
        var td = el('td'); var a = el('a','', x.node); a.href = '#'; a.dataset.jump = x.node_id; td.appendChild(a); tr.appendChild(td);
        tr.appendChild(el('td','mono broken', x.path));
        tr.appendChild(el('td',null, x.kind || '—'));
        t1.appendChild(tr);
      });
      b.appendChild(t1);
    }

    b.appendChild(el('h3',null,'空白节点（'+D.blanks.length+'）'));
    if (!D.blanks.length){
      b.appendChild(el('p','empty','0 个 —— 每个节点都有 birth（at / from / 依据）且至少有一条锚。'));
    } else {
      var t2 = el('table');
      var h2 = el('tr'); ['节点','缺什么'].forEach(function(x){ h2.appendChild(el('th',null,x)); });
      t2.appendChild(h2);
      D.blanks.forEach(function(x){
        var tr = el('tr');
        var td = el('td'); var a = el('a','', x.node); a.href = '#'; a.dataset.jump = x.node_id; td.appendChild(a); tr.appendChild(td);
        tr.appendChild(el('td',null, x.why.join('、')));
        t2.appendChild(tr);
      });
      b.appendChild(t2);
    }
  }

  // ── 交互 ──
  document.addEventListener('click', function(e){
    var t = e.target;
    if (t.dataset && t.dataset.toggle){
      var id = t.dataset.toggle;
      collapsed[id] = !collapsed[id];
      renderTree();
      return;
    }
    if (t.dataset && t.dataset.jump){
      e.preventDefault();
      showDetail(t.dataset.jump);
      document.querySelector('#tree .row.sel');
      var row = document.querySelector('.row[data-id="'+t.dataset.jump+'"]');
      if (row){
        var p = row.parentNode;
        while (p && p.id !== 'tree'){ if (p.classList && p.classList.contains('kids')){ p.classList.add('hidden'); } p = p.parentNode; }
        row.scrollIntoView({block:'center'});
        row.click();
      }
      return;
    }
    var row = t.closest ? t.closest('.row') : null;
    if (row && row.dataset.id){ showDetail(row.dataset.id); }
    var btn = t.dataset && t.dataset.act;
    if (btn === 'expand'){ collapsed = {}; renderTree(); }
    if (btn === 'collapse'){ D.nodes.forEach(function(n){ if ((N[n.id]||[]).length) collapsed[n.id] = true; }); renderTree(); }
  });
  document.getElementById('q').addEventListener('input', function(e){
    filter = e.target.value.trim();
    renderTree();
  });

  renderTree();
  renderBottom();
})();
</script>
</body>
</html>
<!-- 生成器：seed-lineage/scripts/render_seed.py　来源：__SRCPATH__　本页不含时间戳，同一份 seed.json 同一份输出。 -->
"""


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")     # 别让内容里的 </script> 提前截断
    meta = data["seed"]
    origin = meta["本体"] or {}
    html = PAGE
    html = html.replace("__DATA__", payload)
    html = html.replace("__TITLE__", esc(origin.get("版本") or "seed"))
    html = html.replace("__SRCPATH__", esc(meta["source"]))
    html = html.replace("__BORN__", esc(meta["种子出生"] or "—"))
    html = html.replace("__GEN__", esc(meta["生成于"] or "—"))
    html = html.replace("__ORIGIN__",
                        esc((origin.get("地址") or "—") + " " + (origin.get("版本") or "")).strip())
    return html


def main(argv) -> int:
    args = [a for a in argv[1:]]
    out = None
    if "-o" in args:
        i = args.index("-o")
        out = args[i + 1]
        del args[i:i + 2]
    elif "--out" in args:
        i = args.index("--out")
        out = args[i + 1]
        del args[i:i + 2]
    if "--print-path" in args:
        print(default_seed())
        return 0
    if "--verify-idempotent" in args:
        return verify_idempotent()
    seed_path = args[0] if args else default_seed()
    seed_path = os.path.abspath(seed_path)
    if not os.path.isfile(seed_path):
        print("× 找不到种子：" + seed_path, file=sys.stderr)
        print("  先跑 python live.py 投影出种子，或用参数指定 seed.json 的路径", file=sys.stderr)
        return 2
    try:
        seed = json.load(open(seed_path, encoding="utf-8"))
    except Exception as e:
        print("× 读种子失败：%s：%s" % (type(e).__name__, e), file=sys.stderr)
        return 2

    data = build(seed, seed_path)
    html = render_html(data)
    out_path = os.path.abspath(out or DEFAULT_OUT)
    d = os.path.dirname(out_path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    old = open(out_path, encoding="utf-8").read() if os.path.isfile(out_path) else ""
    if old != html:
        open(out_path, "w", encoding="utf-8", newline="\n").write(html)
        print("写出 %s（%.1f KB）" % (out_path, len(html.encode("utf-8")) / 1024.0))
    else:
        print("无变化 %s（同一份种子同一份输出）" % out_path)

    s = data["stats"]
    print("节点 %d（先天 %d · 后天 %d）／名片条目 %d／锚 %d 条（去重 %d 个对象）／断锚 %d／空白 %d"
          % (s["节点数"], s["先天节点"], s["后天节点"], s["名片条目数"],
             s["锚条数"], s["去重对象数"], s["断锚数"], s["空白节点数"]))
    if not any(n["act_known"] for n in data["nodes"]):
        print("提示：没有 PyYAML 或 SKILL.md 读不到，detail 里的 birth.act 会显示「没写 act」")
    print("打开：用浏览器打开上面这个文件（离线可开，不引用任何外网资源）")
    print("自证幂等：python render_seed.py --verify-idempotent（同一份种子连续渲染两次比 sha256）")
    return 0


def verify_idempotent() -> int:
    """自证：同一份种子字节，连续渲染两次，比 sha256。

    只说「幂等」不算数 —— 这一条让人自己跑一遍就能看见。它也说明了前提：
    比的是「同一份 seed.json」，不是「同一个路径」。种子被重投过（`生成于` 变了）
    自然出不同的页面，那不是不幂等，那是数据变了。
    """
    import hashlib

    seed_path = default_seed()
    if not os.path.isfile(seed_path):
        print("× 找不到种子：" + seed_path, file=sys.stderr)
        return 2
    raw = open(seed_path, "rb").read()
    seed = json.loads(raw.decode("utf-8"))
    a = render_html(build(seed, seed_path)).encode("utf-8")
    b = render_html(build(json.loads(raw.decode("utf-8")), seed_path)).encode("utf-8")
    ha, hb = hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()
    print("种子      %s" % seed_path)
    print("种子字节  %s（%d 字节）" % (hashlib.sha256(raw).hexdigest()[:16], len(raw)))
    print("第 1 次   %s（%d 字节）" % (ha, len(a)))
    print("第 2 次   %s（%d 字节）" % (hb, len(b)))
    print("结论      %s" % ("一致 —— 输出不含渲染时刻，同一份种子必然同一份页面"
                           if ha == hb else "不一致 —— 输出里混进了非数据的时刻，这是缺陷"))
    return 0 if ha == hb else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
