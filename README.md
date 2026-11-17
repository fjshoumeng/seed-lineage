# seed-lineage · 长出来的知识库，不是写出来的文档

> 你问 agent「这个功能在哪个文件里」，它去递归搜盘三分钟，给你一个猜的答案。
> 更糟的是：你写了文档，它引用的那个文件三个月前就改过了，文档还在那儿装着没事。

`seed-lineage` 让这台机器从自己的本体长出索引 —— **文档不再需要人工维护，因为它每次都是量出来的；对象一变，它当场报警。**

不是抄一份别人的说明书，是让每台机器量出自己的数、长出自己的一套，并且**永远知道自己有没有过期**。

**[中文](#中文) | [English](#english)**

---

<a name="中文"></a>
## 中文

### 它到底做什么

```
先天物质（机器上本来就有）  →  先天 skill（自动描述本体现象）
                            →  名片（一句话规律 + 指纹）
                            →  种子（你是谁生的、某能力在哪、下一步往哪长）
                            →  后天件（照名片长出来的你的东西）
                            →  再投一次种子（闭环）
```

四个字概括：**不写文档，长文档。**

因为写出来的文档，写完那天就开始假，而且它不会告诉你它假了。
长出来的文档，对象一变就自己报警。

### 你会得到什么

在临时目录里对你的真实本体跑完整链，**我这一台机器**的结果是：

| 步骤 | 输出 |
|:--|:--|
| 走完四步 `scan → gen_innate → live → verify` | 一份可复算的账，字典里每一个数都能重跑复现 |
| 长出先天 skill | 8 份 skill + 对应名片，每张名片带一枚锚指纹 |
| `live.py --check` | `0 个问题` |
| `verify.py` | `97 项校验，全部通过` |

**这组数只证明流程走通了，不是标准答案。** 你的机器量出来是别的数 —— 那是对的。
我没有把「多少文件、多少包」这类量写在这里，因为写死的那一刻，文档就开始假了；这正是这套东西要解决的问题，它自己不该犯。

### 装上

```bash
npx skills add fjshoumeng/seed-lineage
```

装完确认：

```bash
ls ~/.agents/skills/seed-lineage/SKILL.md
```

然后把 `scripts/` 拷到你打算放工具的地方（**别**放进本体目录），直接跑：

```bash
cd scripts
python paths.py        # 先看它把你的本体找在哪了
```

### 你可以这样对它说

- 「接手这个 DSH，先搞清楚里面都有什么。」
- 「这个功能在哪个包里？别搜盘，查种子。」
- 「我要加个插件，该照哪张名片长？」
- 「本体升级了，所有描述重扫一遍。」
- 「这张名片为什么红了？变了什么？」

### 它能给你什么（以及不能）

**能：**

- 从零建立一份**可复算**的系统索引 —— 每一条数字都能重跑复现，不是人抄的。
- 让每份知识**自带保质期**：对象一变，指纹对不上，立刻能看见。
- 换版本不推倒重来：数字从本体量，不写死。
- 给新东西一个固定落点：写 `birth`（谁生的、照哪张名片长），下次投影自动进树。

**不能：**

- 不改你的本体（全程只读）。
- 不替你判断架构好坏（它量「是什么」，不判「该不该」）。
- 跑不出运行期的事（谁消费了什么、今天发生了什么，那些在进程与日志里）。
- 不保证不同版本长一个样 —— 不一样是设计。

### 前置条件

- [ ] **Python 3.8+** —— 检查：`python --version`；没有就 https://www.python.org/downloads/
- [ ] **PyYAML** —— `pip install pyyaml`；检查：`python -c "import yaml; print(yaml.__version__)"`（YAML 里有 `!js` 自定义标签，解析器不对会把预设量成 0 行）
- [ ] **Node 18+**（只有 `find.cjs` 用；不用查种子可以不装）—— 检查：`node --version`
- [ ] **有一份 DSH 本体** —— 判据：某个目录下同时有 `resources/app.asar` 与 `resources/runtime/primary-runtime/runtime.json`
- [ ] **知道本体在哪** —— 不确定就跑 `python paths.py`，它会告诉你是从环境变量、自动探测还是默认值取的

### 完整跑法（五步）

```bash
cd scripts

python paths.py        # 0 核对地址：四个值从哪来、本体两个文件多大
python scan.py         # 1 扫本体 → state/regularity.json + 先天锚-<版本>.json
python gen_innate.py   # 2 长出先天 skill 与名片
python live.py         # 3 长名片 + 投影成种子
python live.py --check # 4 自检（期望 0 个问题）
python verify.py       # 5 全链（期望全部通过）
```

每一步的期望输出、常见错、错在哪，在 `SKILL.md` 的「第三部分 · 生成过程」里逐条写了。

地址对不上时显式指定：

```bash
# Windows
set DSH_ORIGIN=D:\你的DSH安装目录
# macOS / Linux
export DSH_ORIGIN=/你的/dsh/目录
```

### 三件事想清楚再上手

1. **先塑形、再量形。** 把新东西先长成判据允许的样子，再去量它。
   反过来给一堆随便长的材料写兼容层 —— 特例越写越多，最后量的是兼容层，不是东西本身。
2. **名片不手写。** 正文里写全它盯的地址（反引号包住），名片自己会从这些地址长出来。
   **写错地址，名片就盯错对象** —— 而且它不报错，只会每天告诉你「对象没变」。
3. **红了先看，再刷。** 指纹对不上 = 对象在说话。允许「一红就刷」，指纹就退化成装饰。

### 常见问题

| 现象 | 原因 | 怎么办 |
|:--|:--|:--|
| `× 找不到先天物质`，退出码 2 | `DSH_ORIGIN` 指错，或本体压根不在这台机器上 | 跑 `python paths.py` 看探过哪些位置；判据是「该目录下 `resources/app.asar` 存在」。指到 `...\resources` 是差一层，要去掉末尾 |
| `ORIGIN（空）` | 自动探测没命中，又没设环境变量 | 显式 `set DSH_ORIGIN=...`。别反复重试 —— 那只是在重复同一个错 |
| 预设量出 **0 行** | 用了严格 YAML 解析器，遇到 `!js` 标签整份失败 | 用 `scan.py` 里那个带多构造器的 loader；并且把「行数 > 0」也当一条检查，否则 0 行会让「每行必有 id」空过 |
| 读 `package.json` 读出几位乱码、包名对不上 | asar 头偏移算错 3 字节 | 头 8 字节两个 uint32（第二个是 pickle 长度），`base = 8 + 它`，pickle `[4:8]` 是 JSON 长度，条目 offset **相对 base** |
| 某 skill 一直「名片长不出来」 | 正文一条地址都没写，`依据` 那张名片也没有 anchor | 正文里写全它盯的地址；地址必须指向**真实存在**的东西 |
| 一堆「地址失效」假红 | 地址正则把 asar 内部路径 `/dsh/node_modules/...` 当磁盘路径了 | 只认盘符开头、`/mnt/` 开头的、以及 `/(home\|Users\|opt\|srv\|tmp\|var\|private\|Volumes)/` 开头的 |
| 树是平摊的，所有东西都挂在根上 | `from` 和 `依据` 混用了 | `from` 只写父亲（`原始` 或另一个 skill 名），决定层级；`依据` 写先天名片名，只是注解 |
| `种子与投影一致` 红 | 有人手改了种子 | 种子是投影 —— 改原因（skill 里的 birth），别改结果 |
| `gen_innate.py` 每次重写全部文件 | 生成的正文里混进了时间戳 | 正文里只允许 `seen_at` 带时刻，且只在指纹变了时更新 |
| `gen_innate.py` 把 `card:` 段抹了 | 生成器整份覆盖 frontmatter | 重写前保住 `card:` 整段 —— 名片归投影器管，不归生成器管；否则两个工具互相改，永不收敛 |

### 风险与限制

- **只读本体。** 全程不动 `app.asar`。先天一个字都不改，后天全落在另一个目录。
- **会写文件**，但只写这三个地方：`<ASSETS>/技能/`、`<ASSETS>/名片/`、`<STATE>/`。
  跑之前建议先把它指向一个临时目录试一遍（`DSH_ASSETS` / `DSH_STATE` 指到 `%TEMP%` 下即可）。
- **不联网。** 全程本地读文件。
- **不同版本数不同。** 别把任何一次的输出当成基线写死 —— 写死的那一刻它就开始假了。

### 致谢

方法论与原始工具链出自本机工作区（`dsh-skillmap`）。本技能是把它**可移植化 + 讲清楚为什么**的版本：
去掉写死的 `D:\` 路径、换成三级地址解析、补上七环因果、把踩过的坑写成判据。

发布流程用 [qiaomu-skill-publisher](https://github.com/joeseesun/qiaomu-skill-publisher)（向阳乔木）。

### License

MIT

---

<a name="english"></a>
## English

> Ask your agent "which file implements this feature" and it recursively greps the disk for three minutes, then guesses.
> Worse: the doc you wrote points at a file that changed three months ago, and the doc still sits there pretending nothing happened.

`seed-lineage` makes the machine grow its own index **from its own installation** — you stop maintaining docs by hand,
because every entry is measured, and the moment the object changes it flips red.

### What it does

```
innate matter (already on disk)  →  innate skills (auto-generated descriptions)
                                 →  cards (one-line law + fingerprint)
                                 →  the seed (who begat what, where things live)
                                 →  acquired artifacts (grown per a card)
                                 →  re-project the seed (loop closes)
```

The whole idea: **don't write the docs — grow them.** A hand-written doc starts lying the day it's finished
and never tells you. A grown one flips red the moment its object changes.

### What you get

Running the full chain against a real install, on *my* machine:

| Step | Output |
|:--|:--|
| the four steps `scan → gen_innate → live → verify` | a reproducible ledger — every number can be re-derived |
| innate skills | 8 skills + their cards, each card carrying an anchor fingerprint |
| `live.py --check` | `0 problems` |
| `verify.py` | `97 checks, all green` |

That set only proves the pipeline runs end to end; it is **not** a reference answer.
Your install will yield different numbers — that's correct, not a bug.
File and package counts are deliberately absent: pinning a number is exactly how a doc starts lying.

### Install

```bash
npx skills add fjshoumeng/seed-lineage
```

Then copy `scripts/` somewhere outside your DSH install directory and:

```bash
cd scripts
python paths.py        # see where it located your installation
```

### Prerequisites

- [ ] Python 3.8+ (`python --version`)
- [ ] PyYAML (`pip install pyyaml`)
- [ ] Node 18+ (only for `find.cjs`)
- [ ] A DSH install: some directory containing `resources/app.asar` and
      `resources/runtime/primary-runtime/runtime.json`

### The commands

```bash
python paths.py        # 0 where am I pointing?
python scan.py         # 1 measure the installation
python gen_innate.py   # 2 grow innate skills + cards
python live.py         # 3 grow cards, project the seed
python verify.py       # 4 verify the whole chain
```

### Three things worth knowing before you start

1. **Shape first, measure second.** Make new artifacts conform to the criteria, then measure.
   Bolting a compatibility layer onto arbitrary material means you end up measuring the layer.
2. **Never hand-write a card.** Write the addresses it watches in backticks in the body; the card grows
   from them. Wrong address → the card watches the wrong object, silently, forever.
3. **Look before you refresh.** A fingerprint mismatch means the object is talking. Allow blind refreshes
   and the fingerprint becomes decoration.

### Limits

Read-only on the installation. Writes only under `技能/`, `名片/`, and the state directory.
No network. Numbers differ across versions by design — pinning them is how they start lying.

### License

MIT

---

Copyright (c) 2026 fjshoumeng
Publishing flow uses [qiaomu-skill-publisher](https://github.com/joeseesun/qiaomu-skill-publisher) by 向阳乔木.
