#!/usr/bin/env node
/**
 * find.cjs —— 先查种子，不扫盘。
 *
 * 用法：
 *   node find.cjs <关键词> [关键词2 …]              按关键词定位到「哪个文件#哪一节」
 *   node find.cjs --get "<skill名>#<节名>"           直接取那一节正文（不用再开文件）
 *
 * 查四类（都来自种子与技能正文，不扫盘）：
 *   ① 后天件名字 / 短名命中      → 谁管的、活没活、在哪
 *   ② 名片锚路径命中             → 这个对象被哪个物质盯着
 *   ③ 后天技能正文命中           → 哪个 SKILL.md、命中几处、在哪一节
 *   ④ 先天技能正文命中           → 本体现象里提没提
 *
 * 输出：一行一条命中 + 末尾一句「下一步读哪个文件#哪一节」。
 * 记账：每次调用追加 <STATE>/查询日志.jsonl（关键词 / 各类命中数 / 耗时）。
 *
 * 地址从环境变量来（与 paths.py 同一套名字），取不到就在脚本附近向上找「有 技能/ 或 名片/ 的一层」。
 */
'use strict'

const fs = require('node:fs')
const path = require('node:path')

function findAssets() {
  if (process.env.DSH_ASSETS) return path.resolve(process.env.DSH_ASSETS)
  const has = (p) => {
    try {
      const n = fs.readdirSync(p)
      return n.includes('技能') || n.includes('名片')
    } catch { return false }
  }
  let d = path.dirname(path.resolve(__filename))
  for (let i = 0; i < 5; i++) {
    if (has(d)) return d
    for (const k of fs.readdirSync(d).slice(0, 60)) {
      const q = path.join(d, k)
      try { if (fs.statSync(q).isDirectory() && has(q)) return q } catch { /* 读不到就跳过 */ }
    }
    const up = path.dirname(d)
    if (up === d) break
    d = up
  }
  return path.join(path.dirname(path.resolve(__filename)), 'assets')
}

const ASSETS = findAssets()
const STATE = process.env.DSH_STATE ? path.resolve(process.env.DSH_STATE) : path.join(path.dirname(path.resolve(__filename)), 'state')
const SKILL_ROOT = path.join(ASSETS, '技能')
const SEED = path.join(SKILL_ROOT, 'dsh-seed', 'seed.json')
const LOG = path.join(STATE, '查询日志.jsonl')

/* ---------------- --get：按「名#节」取一节正文 ---------------- */

const HEAD_RE = /^##\s+(.+?)\s*$/gm
/** 去括号注解与空白，供宽容比较：端口 → 端口表（agent 工具） */
const loose = (s) => String(s || '')
  .replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').replace(/\s+/g, '').toLowerCase()

function runGet(spec) {
  const raw = String(spec || '')
  const i = raw.indexOf('#')
  if (i < 0) return { ok: false, msg: '格式：--get "<skill名>#<节名>"（中间要有一个 #）' }
  const wantSkill = raw.slice(0, i).trim()
  const wantSec = raw.slice(i + 1)

  let dirs = []
  try {
    dirs = fs.readdirSync(SKILL_ROOT, { withFileTypes: true })
      .filter((d) => d.isDirectory()).map((d) => d.name)
  } catch { return { ok: false, msg: `读不到技能根：${SKILL_ROOT}` } }

  let dir = dirs.includes(wantSkill) ? wantSkill : null
  let fuzzy = false
  if (!dir) {
    const hits = dirs.filter((d) => d.toLowerCase().includes(wantSkill.toLowerCase()))
    if (hits.length === 1) { dir = hits[0]; fuzzy = true }
    else if (hits.length > 1) return { ok: false, msg: `skill 名「${wantSkill}」命中多个：${hits.join(', ')}（写全名）` }
    else return { ok: false, msg: `没有这个 skill：「${wantSkill}」` }
  }

  const p = path.join(SKILL_ROOT, dir, 'SKILL.md')
  let txt
  try { txt = fs.readFileSync(p, 'utf8') } catch { return { ok: false, msg: `读不到 ${p}` } }

  const heads = []
  HEAD_RE.lastIndex = 0
  let m
  while ((m = HEAD_RE.exec(txt))) heads.push({ t: m[1].trim(), i: m.index })
  if (!heads.length) return { ok: false, msg: `${dir} 的 SKILL.md 没有 ## 节` }

  const q = loose(wantSec)
  if (!q) return { ok: false, msg: '没给节名' }
  let hit = heads.find((h) => h.t === String(wantSec).trim()) || heads.find((h) => loose(h.t) === q)
  let others = []
  if (!hit) {
    const starts = heads.filter((h) => loose(h.t).startsWith(q))
    const inc = heads.filter((h) => loose(h.t).includes(q))
    const cand = starts.length ? starts : inc
    if (!cand.length) {
      return {
        ok: false,
        msg: `${dir} 没有「${wantSec}」这一节。它实际有这些节：\n` +
          heads.map((h) => `  · ${h.t}`).join('\n'),
      }
    }
    hit = cand[0]
    others = cand.slice(1).map((h) => h.t)
  }

  const after = hit.i + `## ${hit.t}`.length
  const rest = txt.slice(after)
  const nx = rest.search(/^##\s+/m)
  let body = (nx < 0 ? rest : rest.slice(0, nx)).replace(/^\s*\n/, '').replace(/\s+$/, '')

  // 本节正文是原文取出来的，里面可能带着**这一台机器**的绝对落点。
  // 原样打印，别人复制这行命令去跑必然不对（他机器上没有这个目录）。
  // 所以只把「本机 ASSETS」这一层换成 <ASSETS> 占位：仍看得出结构，又不指死本机。
  // 判据是「这一层的绝对路径」，不是随便一个盘符路径 —— 别的盘符路径是别人正文里的事实，不归这里改。
  body = maskAssets(body)

  const note = []
  if (fuzzy) note.push(`skill 名按包含匹配到 ${dir}`)
  if (others.length) note.push(`另有相近节：${others.join(' / ')}`)
  return { ok: true, dir, title: hit.t, body, note }
}

/** 把正文里出现的本机 ASSETS 绝对落点换成 <ASSETS>（两种分隔符都认）。
 *
 * 两条判据，缺一个就会错：
 *   后面必须是分隔符或边界 —— 否则 D:\a\b 会把 D:\a\bc 也啃掉一半；
 *   但**正好等于资产根**那一处要换（行尾、空白、引号、反引号后面都算边界）。
 * 只换这一层，别的盘符 / 别的用户目录一律原样保留：那些是别人正文里的事实，不归这里改。
 */
function maskAssets(s) {
  if (!s) return s
  const forms = new Set([ASSETS, ASSETS.split(path.sep).join('/')])
  let out = s
  for (const f of forms) {
    if (!f) continue
    const esc = f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    // 后面紧跟分隔符 → 深路径；(?!\w) 拦住 a\bc 这种同前缀不同目录
    const re = new RegExp(esc + '(?=$|[\\\\/]|(?!\\w))', 'g')
    out = out.replace(re, '<ASSETS>')
  }
  return out
}

const argvAll = process.argv.slice(2)

if (argvAll.includes('--get')) {
  const gi = argvAll.indexOf('--get')
  const spec = argvAll[gi + 1]
  if (!spec) {
    console.log('用法：node find.cjs --get "<skill名>#<节名>"')
    console.log(`当前 ASSETS = ${ASSETS}`)
    process.exit(2)
  }
  const t1 = Date.now()
  const res = runGet(spec)
  if (!res.ok) {
    console.log(res.msg)
    try {
      fs.mkdirSync(STATE, { recursive: true })
      fs.appendFileSync(LOG, JSON.stringify({ 取节: spec, 命中: false, 耗时ms: Date.now() - t1, 时刻: new Date().toISOString() }) + '\n')
    } catch { /* 记账失败不影响查找 */ }
    process.exit(1)
  }
  // 干净输出：只给那一节正文；提示走 stderr，不污染正文
  if (res.note.length) console.error(`# ${res.dir} 「${res.title}」 （${res.note.join('；')}）`)
  console.log(res.body)
  try {
    fs.mkdirSync(STATE, { recursive: true })
    fs.appendFileSync(LOG, JSON.stringify({
      取节: spec, 命中: true, skill: res.dir, 节: res.title, 字节: res.body.length,
      耗时ms: Date.now() - t1, 时刻: new Date().toISOString(),
    }) + '\n')
  } catch { /* 记账失败不影响查找 */ }
  process.exit(0)
}

const words = argvAll.filter((w) => w && !w.startsWith('--'))
if (words.length === 0) {
  console.log('用法：')
  console.log('  node find.cjs <关键词> [更多关键词…]            # 定位到「哪个文件#哪一节」')
  console.log('  node find.cjs --get "<skill名>#<节名>"           # 直接取那一节正文')
  console.log(`当前 ASSETS = ${ASSETS}`)
  process.exit(2)
}
const t0 = Date.now()
const kw = words.map((w) => w.toLowerCase())
const hit = (s) => kw.some((k) => String(s || '').toLowerCase().includes(k))

let seed
try {
  seed = JSON.parse(fs.readFileSync(SEED, 'utf8'))
} catch (e) {
  console.log(`读不到种子：${e.message}`)
  console.log(`  期望位置：${SEED}`)
  console.log('  先跑：python live.py（把各 skill 的出生标签投影成种子）')
  process.exit(2)
}

const out = []
const next = []
const stat = { 名字: 0, 锚: 0, 技能正文: 0, 先天: 0 }

/* ① 名字 / 短名 —— 后天件 */
out.push('【① 后天件（名字 / 短名命中）】')
const walk = (nodes, depth) => {
  for (const e of nodes || []) {
    const name = e.name || ''
    const short = e['短名'] || ''
    if (hit(name) || hit(short)) {
      stat.名字++
      out.push(`${'  '.repeat(depth)}· ${name}${short ? `（${short}）` : ''}　[${e.state || '?'}]　${e.path || ''}`)
      if (e.path) next.push(`${e.path}　← ${name}`)
    }
    walk(e['孩子'], depth + 1)
  }
}
walk(seed['先天'], 0)
walk(seed['后天'], 0)
if (!stat.名字) out.push('  （无）')

/* ② 名片锚路径 */
out.push('【② 名片锚路径命中】')
const cardsHit = []
const scanCards = (nodes) => {
  for (const e of nodes || []) {
    for (const c of e['名片'] || []) {
      for (const a of c['锚'] || []) {
        if (hit(a.path) || hit(a.label)) {
          stat.锚++
          cardsHit.push(`${e.name} 的「${c.name}」盯 ${a.path}${a.size ? `（${a.size} 字节）` : ''}`)
        }
      }
    }
    scanCards(e['孩子'])
  }
}
scanCards(seed['先天'])
scanCards(seed['后天'])
out.push(...(cardsHit.length ? cardsHit : ['  （无）']))

/* ③ ④ 技能正文 */
const readBody = (p) => {
  try {
    const t = fs.readFileSync(p, 'utf8')
    const m = t.match(/^---\n[\s\S]*?\n---\n([\s\S]*)$/)
    return m ? m[1] : t
  } catch { return '' }
}
const listDirs = (p) => {
  try { return fs.readdirSync(p).filter((d) => fs.statSync(path.join(p, d)).isDirectory()) } catch { return [] }
}
const post = []
const innate = []
for (const d of listDirs(SKILL_ROOT)) {
  const p = path.join(SKILL_ROOT, d, 'SKILL.md')
  if (!fs.existsSync(p)) continue
  const body = readBody(p)
  if (!body) continue
  const lower = body.toLowerCase()
  const n = kw.reduce((s, k) => s + lower.split(k).length - 1, 0)
  if (!n) continue
  const sec = body.split('\n').filter((l) => /^#{2,3}\s/.test(l.toLowerCase().replace(/#/g, '#')))
  const lines = body.split('\n')
  let where = ''
  for (let i = 0; i < lines.length; i++) {
    if (!hit(lines[i])) continue
    for (let j = i; j >= 0; j--) if (/^#{2,3}\s/.test(lines[j])) { where = lines[j].replace(/^#+\s*/, ''); break }
    break
  }
  const row = `${d}　命中 ${n} 处${where ? `　首处节：${where}` : ''}　${p}`
  next.push(`${p}${where ? `#${where}` : ''}　← ${d}（命中 ${n} 处）`)
  if (d.startsWith('dsh-innate')) innate.push(row)
  else post.push(row)
}
out.push('【③ 后天技能正文命中】')
out.push(...(post.length ? post.slice(0, 8) : ['  （无）']))
out.push('【④ 先天技能正文命中】')
out.push(...(innate.length ? innate.slice(0, 8) : ['  （无）']))
stat.技能正文 = post.length
stat.先天 = innate.length

const ms = Date.now() - t0
console.log(out.join('\n'))
console.log('')
const four = stat.名字 + stat.锚 + stat.技能正文 + stat.先天
console.log(`【下一步】${next.length
  ? next[0]
  : '四条全零：这个词不在种子与技能正文里。这时才允许搜盘，先 glob 定范围，别对 node_modules / .venv 递归。'}`)
console.log(`（${ms} ms　名字 ${stat.名字} / 锚 ${stat.锚} / 技能正文 ${stat.技能正文} / 先天 ${stat.先天}` +
  `${four === 0 ? '　—— 四条全零' : ''}）`)

try {
  fs.mkdirSync(STATE, { recursive: true })
  fs.appendFileSync(LOG, JSON.stringify({
    关键词: words, 命中: stat, 耗时ms: ms, 时刻: new Date().toISOString(),
  }) + '\n')
} catch { /* 记账失败不影响查找 */ }
