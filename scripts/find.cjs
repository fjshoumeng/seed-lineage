#!/usr/bin/env node
/**
 * find.cjs —— 先查种子，不扫盘。
 *
 * 用法：node find.cjs <关键词> [关键词2 …]
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

const words = process.argv.slice(2).filter((w) => w && !w.startsWith('--'))
if (words.length === 0) {
  console.log('用法：node find.cjs <关键词> [更多关键词…]')
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
