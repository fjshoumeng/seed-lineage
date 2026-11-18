# seed-lineage · 长出来的知识库，不是写出来的文档

> 你问 agent「这个功能在哪个文件里」，它去递归搜盘三分钟，给你一个猜的答案。
> 更糟的是：你写了文档，它引用的那个文件三个月前就改过了，文档还在那儿装着没事。

`seed-lineage` 是一种**能力**：从任何有固定结构的东西里量出形状 → 长出描述 → 组成能复算身世的树 → 校验不变量。
量出来的索引不需要人工维护，因为对象一变它当场报警。

**这一份实现跑在 DSH 上，它是范例，不是产品，不是标准答案，更不是上限。**

> **发布件**：这份 README 是对外发布物（GitHub `fjshoumeng/seed-lineage`），**不是本机的能力件**。
> 里面所有数字都是**发布那一刻（2026-11-18）**在作者那台机器上量出来的读数，
> 不跟任何一台机器当下的种子对账 —— 要你自己的数，跑 `count_seed.py` / `verify.py`。

**[中文](#中文) | [English](#english)**

---

<a name="中文"></a>
## 中文

### 一 · 这是能力，不是产品

种子不是一套文档模板，是四个动作：

```
1 量形状      —— 从对象里量出「它必然是什么」：位置、分类、形制、计数、指纹
2 长描述      —— 把量到的事实按方向组织成说明（描述出来的，不是人写的）
3 组身世树    —— 每个件写出生标签（谁生的 + 照哪条规律长的 + 什么时候），投影成一棵树
4 校验不变量  —— 重算指纹，对不上说明对象变了，当场红
```

这四个动作**不绑在 DSH 上**。判据要换，因为「必然是什么」换个对象就不一样：

| 对象 | 量什么形状 | 判据换到哪 |
|:--|:--|:--|
| DSH 本体（`app.asar`） | 包、入口、路由、预设、槽位 | `package.json` 的 main/exports、路由 kind |
| 外部桌面程序（Obsidian） | 程序布局、两份 asar 头、库里原生件形制 | 安装包载荷的 PE 头、asar 头形制、`.md`/`.canvas`/`.base`/`.excalidraw.md` |
| `jar` / `war` | 类、清单、依赖、入口类 | `META-INF/MANIFEST.MF` 的 Main-Class |
| npm 依赖树 | 顶层依赖、传递依赖、版本收敛 | `package-lock.json` 的 resolved / integrity |
| docker 镜像层 | 层、层里改了什么、谁覆盖谁 | 层的 digest 与父子指针 |
| 一个代码仓库 | 模块图、导入关系、谁引谁 | import / require 的静态解析结果 |

**判据变了，方法没变。** 真跑通的有两条：DSH 一条，Obsidian 一条（见第四节末「第二个范例」）。
其余的 jar / npm / docker / 模块图仍是方向。那不是「只能用在这两个对象上」，那是「这两条我通过实测了」。

**你这份实现是范例，不是答案。** 它到哪，取决于我们的思想到哪。想想不到的，不是做不到，是还没想到。

```
先天物质（机器上本来就有）  →  先天 skill（自动描述本体现象）
                            →  名片（一句话规律 + 指纹）
                            →  种子（你是谁生的、某能力在哪、下一步往哪长）
                            →  后天件（照名片长出来的你的东西）
                            →  再投一次种子（闭环）
```

四个字概括：**不写文档，长文档。** 写出来的文档，写完那天就开始假，而且它不告诉你它假了；
长出来的文档，对象一变就自己报警。

### 二 · 它能解决什么问题 —— 人的问题

- **接手陌生项目，不知道从哪看起。** 几万个文件没有地图 → 先从本体量出结构与计数，按方向生成说明。量出来的，不是人肉翻的。
- **文档过期了没人知道，它还在骗人。** → 对象一变指纹对不上，当场报警。过期变成一条红，不是一个没人发现的谎。
- **系统越改越乱，加了什么忘了为什么加。** → 每个件必须有出处：`birth.from`（谁生的）、`依据`（照哪条规律长的）、`at`（什么时候）。没出处的进不了树。
- **改一处不知道会影响哪里。** → 锚点先告诉你谁盯着它；改完，盯着它的那份描述会红。拿到的是提醒，不是事后才发现。
- **想知道某某东西到底归谁管。** → `find.cjs <关键词>` 四段命中：归谁管、盯的哪个路径、哪份技能写过它、下一步读哪个文件哪一节。30 毫秒，不搜盘。要知道某一节的正文，`find.cjs --get "名#节"` 直接取出来，不用整份读。
- **想给新来的人一份能看的架构说明。** → 先天 skill 本身就是按方向组织好的架构说明，而且跟着版本自动更新。
- **东西太多，分不清哪些还在用、哪些已经死了。** → 每个件带时刻与指纹，数据全在种子里（见第六节第二层，查询还没写）。
- **一份索引换台机器就得重写。** → 地址三级解析、数字从本体量、校验里没有你的数。换机器量出别的数是对的。

### 三 · 它能解决什么问题 —— agent 的问题

这一段是这套方法独特的地方：它是 agent 给自己用的，不是给人看的报告。

- **不知道自己在哪台机器上、这台机器有什么。** agent 每次从零开始，靠猜和搜 → 种子第一行就是本体地址 + 版本 + 指纹，下面整棵树就是「这台机器有什么」。
- **找东西只能递归搜盘，搜完还是猜。** → 先查种子，30 毫秒给到文件与小节；四段全零才允许搜盘。
- **找对了文件，还得整份读完才知道要什么。** → `--get "名#节"` 只取那一节。skill 会长到近千行，整份读是把负担塞进上下文；按节取才是这个规模下的做法。前提是节名统一（标准节序：这是什么 → 地址 → 端口表 → 数据落点 → 边界 → 年轮）。
- **读过的东西记不住，下次还要重读。** → 量出来的索引进种子，下一次投种子还在。读一次，写进脉络，全树可见。
- **不知道自己写的文档已经过期。** → 它写的那句「这是什么」绑在锚点上；对象一变，它自己那份描述就红，不用等别人发现。
- **不知道自己能做什么、该往哪长。** → 查种子找到该照哪张名片长，名片的「规律一句话」+「判据」就是形状要求。先塑形，再量形。
- **改了什么之后不知道有没有搞坏别的。** → 改完跑 `verify.py`（七组逐项）；盯它的描述会红，红了你必须先看。
- **无法向别的 agent 交代「我这边有什么」。** → 种子就是那份交代：树形、可机读（`seed.json`）、每条带出处。

**它不解决什么**：代码质量好不好、这段代码语义是什么、跨 harness 换一套判据 —— 见文末「局限」。

### 四 · 范例：跑在 DSH 上（实测数字）

这一节是**一台机器的实测账**，摆出来为了证明「这四个动作真能跑起来」，不是为了当标准答案。
读数取到 2026-11-18（发布那一刻）—— 之后本机的种子重投过多少次，这里的数都不跟着变。

```
对象     DSH 桌面版 0.2.2-rc.2，app.asar 208,137,981 字节，sha256 49fd1b08…
量出来   文件 21,682（unpacked 1,678 在外）／预设 4 份 112 行／升级指引 14 个目录
先天件   11 份（dsh-innate 入口 + 10 个方向），同一枚指纹 89de2e2de843
先天名片 10 张（布局 / 插件 / 服务 / 预设 / 端口 / 槽位 / 窗口 / 文档 / 自带skill / 表达）
后天线   65 个顶层后天件，往下共 77 个节点，每个带 birth 五件套
锚点     名片库 10 张 ／ 带锚的名片条目 88 条 ／ 锚条数 226（当日按 frontmatter 口径数的，
         与种子口径 C 不是一个数 —— 两种数法的对照见第五节「口径」）
时刻     88 条 birth.at，最早 2026-10-09，最新 2026-11-17
年轮     5 圈，全在同一枚指纹下
校验     live.py --check 0 个问题；verify.py 97 项全过；二轮 gen_innate 写出 0 份（收敛）
```

> **「锚点」那行是三种数法，别拿一个口径的数去对另一个口径的数**：名片库文件（磁盘上的 `.md`）／
> 带锚的名片条目（种子里锚列表非空的条数）／锚条数（逐条相加，同一个文件被两个件盯就算两条）。
> 第三格记的 226 是当日按 **frontmatter 口径**（`looks_at` 条数，直接读文件、不读种子）数出来的，
> 与种子口径 C **不是同一份数据** —— 差几条、差在哪个节点，`count_seed.py` 会逐条指名道姓打出来。
> 真值一律以它当时的输出为准；写进文档的数就只是**一次读数**。

| 步骤 | 输出 |
|:--|:--|
| 走完四步 `scan → gen_innate → live → verify` | 一份可复算的账，每个数都能重跑复现 |
| 长出先天 skill 与名片 | 11 份 / 10 张，每张带锚指纹 |
| `live.py --check` | `0 个问题` |
| `verify.py` | `97 项校验，全部通过` |

**这些数字只证明流程走通了。** 不证明你的机器也长这样（你的数不一样才是对的），
不证明这是标准答案（换对象判据全换），不证明这是上限（见第六节）。

#### 第二个范例：换了本体、换了语言，照样成立

上面那一节只有一条链撑着。「判据变了、方法没变」这句话，一条链证明不了 —— 它是主张，不是证据。

现在有第二条：**Obsidian（一个外部程序，跟 DSH 无关）身上，同一套四个动作真跑通了一遍**，
量的是它自己的本体，写的是 Node 而不是 Python。

| 四个动作 | DSH 那条链（Python） | Obsidian 那条链（Node） |
|:--|:--|:--|
| 量形状 | `scan.py` | `工具/scan-obsidian.mjs` |
| 长描述 | `gen_innate.py` → 11 份先天 skill | `工具/live-obsidian.mjs` → 1 份 `obsidian-innate` |
| 组身世树 | `live.py` → `seed.json` | `工具/seed-obsidian.mjs` → `基座/seed-obsidian.json` + `.md` |
| 校验不变量 | `verify.py` | `工具/verify-obsidian.mjs`（实测：全绿 19 项，退出码 0） |
| 名片 | 10 张 | 5 张（布局 / 表达 / 加载 / 插件 / 内容形制） |

变的是**本体**（`app.asar` → Obsidian 程序目录）、**语言**（Python → Node）、
**判据**（`package.json` 的 main/exports → 程序布局、asar 头形制、库里四种原生件形制）。
不变的是那四个动作的顺序，和「先天 → skill → 名片 → 种子 → 后天件 → 再投」这个环。

所以这不是「一个只认识 DSH 的工具」，是**一套能反复长出系统的方法** —— 而且它在第二个对象上
连缺什么都一起长出来了：那条链还没有查询器、地址仍写死在五个脚本里、也没有年轮账。
缺件写清楚反而是更强的证据：方法真能换本体，空白自己站在树上。

而且它不只横着换本体，还能**纵向长**：DSH 的种子里有个后天件 `obsidian`，
那个场自己又是完整的一棵树（Obsidian 先天 → 5 名片 → `seed-obsidian` 8 后天件），
里面又长出一个后天件 `Blender`，Blender 自己又是一棵（5 名片 → `seed-blender` 6 后天件，校验全绿 35 项）。
**一颗种子里长出下一颗种子** —— 两层树靠锚/路径缝合（下层不是上层节点里的 `孩子`，上层那个节点 `孩子` 是空的）。
下层账一动，上层盯着它的名片当场红（实测 `obsidian 名片对象变了`）—— 报警跨层生效。
这才是「种子长种子」：一套结构能在一个系统里递归地一层层长下去。长到第三层是当前实际形状，不是无限递归。

至于 `jar` / npm / docker / 模块图 —— 它们**仍然是方向，不是已实现**。真实例证明的是
「方法能换本体、能往纵深长」，不是「任意本体都自动成立」；能不能长，取决于它的形状能不能被量出来（尺子贴着对象造）。

### 五 · 怎么把它展示出来

种子长出来只是一半，另一半是**让人看见**。这一条不规定格式，只讲方法。

**展示什么**：展示的是「树 + 边界」—— 有哪些件、谁生谁、盯的什么路径、哪些地方还是空白。
目的只有一个：让看的人一眼知道「这个系统长成什么样、什么地方没有东西」。

**拿哪份数据展示**：就是 `seed.json`。它是结构化的（节点 + 父 + 依据 + 状态 + 锚），
天然适合渲染，**不需要再单独维护一份展示数据 —— 种子里有什么就能展示什么。**
另外 `live.py --check` 的问题清单就是「边界」那一份，红的地方就是空的地方。

**怎么呈现**（按推荐顺序）：

1. **一份可点击的 HTML 页面**（首选）—— 树按父子关系展开，每个节点能点开看到：
   它是谁生的、依据哪张名片、盯着哪些文件、指纹对没对上。给不熟终端的人看，打开就懂，
   想查什么点进去查，而不是看着一张图和它猜。
2. **结构化数据**（给 agent 看）—— `seed.json` 本身就是可查的，agent 直接读，不需要页面。
3. **终端里的树形文本**（快速瞄一眼，最短的路）。
4. **明确不要**：截一张静态图片当展示。图片不能点、不随种子变化。

**为什么必须是可点的**：**能点开的才算展示，图片是死的。** 一张截图在发布那天就开始假了 ——
这和我们想解决的那个问题是同一件事（文档过期没人知道）。所以展示本身也得是活的：
**从 `seed.json` 现生成，随时能重新生成一遍。**

**用什么形式取决于给谁看**：给 agent 看的用结构化数据，给人看的用可点的页面。

#### 生成那张页面：`render_seed.py`

这一条不是说法，是一条命令。`scripts/render_seed.py` 把 `seed.json` 现生成**一个自包含的 HTML**：

```bash
cd scripts
python render_seed.py                      # 默认取 paths.py 解析到的种子 → 当前目录 seed-tree.html
python render_seed.py <seed.json>          # 指定种子
python render_seed.py <seed.json> -o out.html
python render_seed.py --print-path         # 只打印默认种子在哪
python render_seed.py --verify-idempotent  # 自证幂等：连渲染两次比 sha256
```

生成完用浏览器打开那个文件即可 —— **单文件、不引用任何外网资源（没有 CDN、没有字体、没有图片）**，
双击就能开，断网也能开。

页面里有什么（全部从 `seed.json` 现算，没有一个节点名是写死的）：

| 位置 | 内容 |
|:--|:--|
| 顶部统计 | 节点数 / 名片条目数 / 锚条数 / 去重对象数 / 断锚数（外加先天与后天各几个、空白几个） |
| 树 | 按 `birth.from` 展开 —— `from` 才是父亲；先天在上、后天在下；`from` 指不到的单列「父亲找不到」 |
| 详情 | 点任一节点：name / 短名 / birth 四行（at / from / 依据 / act）/ 它的名片与每条锚（指向的路径在不在）/ 指纹与 seen_at |
| 边界 | 锚指向不存在的东西 → 标红并单列「断锚」表；没有锚或没有 birth 的件单列「空白」表 |

它同时把「断锚」和「空白」显示在树里（节点名后面挂红标），点进去能看到是哪一个锚断了。
界面上还有过滤框与全部展开/收起，节点多的时候不至于翻半天。

**这一张页面每次从 `seed.json` 现生成 —— 种子一变，重跑一遍就是新的。这正是它和静态截图的区别：**
截图不能点、也不知道自己已经过期；这个页面点得开，而且只要重跑一次命令就追上当下。

**幂等**：同一份 `seed.json` 字节跑两遍，输出逐字节相同 —— 因为页面里不含任何**渲染时刻**，只在文件末尾的注释里写生成器与来源。
页头那行「种子数据生成时刻」是 `seed.json` 自带的字段（`生成于`），它是**数据**，不是渲染时刻：种子重投它才变，重跑渲染器它不变。
自己验一遍：`python render_seed.py --verify-idempotent` —— 连渲染两次比 sha256，一致才叫幂等。

前提说清楚：幂等的对象是**同一份种子字节**。种子被重投过（`生成于` 变了、节点变了），出来当然是不一样的页面 ——
那不是不幂等，那是数据变了。这也是它该有的样子。

我们这台机器上，用上面第一条命令生成的那一页，顶部统计是
**节点 88（先天 11 · 后天 77）／名片条目 88／断锚 0／空白 0**；锚条数与去重对象数随种子重投而变化，
以 `count_seed.py` 当前输出为准。

> 这些数字一律用 `python count_seed.py`（同一目录下）复算，别手抄，也别拿一个口径的数去对另一个口径的数。
> 四个口径数的是什么、差在哪一条，那个脚本会逐条打出来 —— 见下一节。

#### 口径：同一件事有几种数法

「锚点 226 还是 227」这种分歧不是谁错，是把两种数法混着比。`scripts/count_seed.py`
把每个口径怎么数写死在代码里，跑一次就是一份确切数字：

```bash
python count_seed.py           # 人看的：每个口径数什么、从哪读、结果多少、差在哪
python count_seed.py --json    # 机读的
```

| 口径 | 数什么 | 从哪读 |
|:--|:--|:--|
| A 名片库文件数 | 名片库这一层里以 `.md` 结尾的实体文件 | `<ASSETS>/名片/` |
| B 带锚的名片条目数 | 种子里面片条目的锚列表非空的条数 | `seed.json` |
| C 锚条数 | 所有名片的锚逐条相加（同一路径被两个件盯算两条） | `seed.json` |
| D 去重对象数 | C 里那些 path 去重后的个数 | `seed.json` |
| E `looks_at` 条数 | 每份 `SKILL.md` 的 `card.looks_at` 逐份相加 | `技能/*/SKILL.md`（不读种子） |
| F birth 条数 | 种子里 `birth.at` 非空的节点数 | `seed.json` |

**E 和 A~D 不是同一份数据**：种子里一个节点挂的是它的「名片」（先天件的名片来自名片库），
而 `SKILL.md` 的 `card:` 段是这份 skill 自己长出来的名片。两条都算对了，差几条、差在哪个节点，
`count_seed.py` 会指名道姓打出来。要比就同一个脚本跑两次比，别横着比。

这一台机器上跑出来的结果是
**名片库 10 张 ／ 带锚的名片条目 88 条 ／ 锚条数、去重对象数均以 `count_seed.py` 当前输出为准**。

种子的价值一半在「记得住」，一半在「看得见」—— **看得见的边界，别人才知道下一步往哪长。**

### 六 · 能长到多远

**上限是思想的上限，不是实际上限。** 今天想到的能做到；想不到的不是做不到，是还没想到。

**第一层 · 今天就能跑（已实测）**

量本体（文件/包/预设/端口/槽位/服务）· 生成先天 skill · 长名片 · 投影种子 · 校验（七组）· 查种子。
全部实测跑通，二轮收敛。

**第二层 · 数据已经在，只差一层查询（不是已有功能）**

种子里已经躺着（括号里是 **2026-11-18 发布时的读数**；本机的数一律 `count_seed.py` 现算，别手抄）：
名片库 10 张、带锚的名片条目 88 条、锚条数 226、88 条 `birth.at`、5 圈年轮。
下面全是「拿这份现成数据写一个查询」的活，**代码还没写**：

| 想做但还没做 | 数据已经够，缺什么 |
|:--|:--|
| 依赖闭包（改这里牵动谁） | 锚点里有 `path`、有 `looks_at` —— 反向建索引即可 |
| 僵尸件识别（哪些一年不动） | 88 条 `birth.at` 在，跟今天比一把 |
| 某一天的系统快照 | 5 圈年轮的指标全留着，可按时刻回放 |
| 跨机器清单体检 | 同一套脚本换一台跑，两份 `seed.json` 对比 |
| 生命周期分级（活 → 低频 → 封存） | 时刻 + 引用数都在，缺一条分级规则 |
| 架构说明书自动生成 | 10 张先天名片已是按方向的架构说明，缺一层拼装导出 |

**数据层已经到了，查询层还没到。** 谁先写这几个查询，谁就拿到第一层的下一批实测。

**第三层 · 路，不是已交付**

这些方向成立，但这一份实现没做，也没实测过：

- `jar` / `war` —— 判据换到 `MANIFEST.MF`
- npm 依赖树 —— 判据换到 lockfile 的 resolved / integrity
- docker 镜像层 —— 判据换到层 digest 与父子指针
- 代码仓库模块图 —— 判据换到 import / require 静态解析

它们共用前三个动作，只有「量什么算必然」要重写。不是「做四个新功能」，是「同一套方法换四次尺子」。

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

### 局限（它做不到什么，以及风险）

**三条明确做不到，别指望它：**

- **不做代码质量判断。** 它量「是什么」，不判「该不该」。架构好坏、写得对不对、有没有更好的写法，不在射程里。
  名片正文里连「失败 / 错误 / 坑」这类评价词都不许出现，校验会扫。
- **不做语义理解。** 它不知道某段代码在业务上是什么意思。「这是什么」「边界在哪」「为什么这么写」仍要人写进正文 ——
  它只负责让那句话变红，不负责替你想出那句话。
- **跨 harness 的判据要重写。** 现在的判据长在 DSH 的形状上（`app.asar` + `runtime.json`、`package.json` 的 main/exports、
  路由按 kind 分表）。换一套宿主，本体形态变了，判据得按新形态重写 —— 方法和七环能照搬，判定那几行不能。
  这不是缺陷，是这类能力的固有形状：**尺子必须贴着对象造。**
- **跑通的是两条路，不是任意对象。** DSH 本体与 Obsidian 程序各一条（见第四节末）；第六节第三层（jar / npm / docker / 模块图）仍是方向，不是已交付。
  别拿它当「已经支持任意对象」用。第二条链也带着缺件：没有查询器、地址写死在五个脚本里、没有年轮账。

**风险：**

- **只读本体。** 全程不动 `app.asar`。先天一个字都不改，后天全落在另一个目录。
- **会写文件**，但只写这三个地方：`<ASSETS>/技能/`、`<ASSETS>/名片/`、`<STATE>/`。
  跑之前建议先把它指向一个临时目录试一遍（`DSH_ASSETS` / `DSH_STATE` 指到 `%TEMP%` 下即可）。
- **不联网。** 全程本地读文件。
- **不同版本数不同。** 别把任何一次的输出当成基线写死 —— 写死的那一刻它就开始假了。
- **跑不出运行期的事。** 谁消费了什么、今天发生了什么、某端口此刻通不通 —— 那些在进程与日志里，不在静态文件里。

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

`seed-lineage` is a **capability**: measure the shape of anything with a fixed structure → grow descriptions →
build a lineage tree whose provenance can be recomputed → verify the invariants. A measured index needs no manual
upkeep, because it flips red the moment its object changes.

**This implementation runs on DSH. It is an example — not a product, not the reference answer, and not the ceiling.**

> **Published artifact**: this README is a published deliverable (GitHub `fjshoumeng/seed-lineage`), **not a capability
> artifact of any local install**. Every number here is a reading taken on the author's machine **at publish time
> (2026-11-18)** and is never reconciled against the seed of whatever machine you are on now — for your own numbers,
> run `count_seed.py` / `verify.py`.

### 1 · This is a capability, not a product
A seed is not a doc template. It is four actions:

```
1 measure the shape   — what the object *necessarily* is: position, class, form, count, fingerprint
2 grow descriptions   — organise the measured facts into per-direction docs (described, not written)
3 build the lineage   — every artifact gets a birth label (parent + which law it followed + when), projected as a tree
4 verify invariants   — recompute the fingerprint; a mismatch means the object changed, so it flips red
```

These four actions **are not tied to DSH**. The criteria change, because "necessarily what" differs per object:

| Object | What you measure | Where the criteria move to |
|:--|:--|:--|
| DSH install (`app.asar`) | packages, entries, routes, presets, slots | `package.json` main/exports, route kind |
| external desktop app (Obsidian) | program layout, asar headers, native file formats | PE header of the payload, asar header shape, the four native formats in a vault |
| `jar` / `war` | classes, manifest, dependencies, entry class | `META-INF/MANIFEST.MF` Main-Class |
| npm dependency tree | direct deps, transitive deps, version convergence | `package-lock.json` resolved / integrity |
| docker image layers | layers, what each changed, which overrides which | layer digest and parent pointers |
| a code repository | module graph, imports, who references whom | static resolution of import / require |

**The criteria change; the method does not.** Two paths are actually proven: DSH, and Obsidian
(see the end of §4). The rest — jar / npm / docker / module graph — are still directions. That does not
mean "these two objects only"; it means "these two paths are measured".

**This implementation is an example, not the answer.** How far it reaches depends on how far our thinking reaches.
What we have not thought of is not impossible — it is just not thought of yet.

```
innate matter (already on disk)  →  innate skills (auto-generated descriptions)
                                 →  cards (one-line law + fingerprint)
                                 →  the seed (who begat what, where things live)
                                 →  acquired artifacts (grown per a card)
                                 →  re-project the seed (loop closes)
```

The whole idea: **don't write the docs — grow them.** A hand-written doc starts lying the day it is finished
and never tells you. A grown one flips red the moment its object changes.

### 2 · Problems it solves — for people

- **Handed an unfamiliar project, no idea where to start.** → measure structure and counts from the installation, then generate per-direction descriptions. Measured, not hand-explored.
- **The doc went stale and nobody knows; it is still lying.** → object changes, fingerprint mismatches, it flips red. Expiry becomes a signal, not a silent lie.
- **The system grows messier; nobody remembers what was added or why.** → every artifact carries `birth.from` (parent), `依据` (which law it followed), `at` (when). No provenance, no place in the tree.
- **Changed one place, unsure what it affects.** → the anchors first tell you who watches it; after the change, that description flips red.
- **Which package provides this service, which plugin registered that route.** → innate skills and cards list them by direction; criteria read declarations, not filenames.
- **Want a readable architecture note for the next person.** → the innate skills *are* that note, organised by direction, and they update with the version.
- **Too many things; which are alive and which are dead.** → every artifact carries a timestamp and a fingerprint; the data is already in the seed (see §6, second layer — the queries are not written).
- **One index per machine, not one index thrown away per machine.** → three-level address resolution, numbers measured, no numbers of mine in the verifier.

### 3 · Problems it solves — for agents

This is the part that is genuinely different: it is for the agent to use on itself, not a report for humans.

- **It does not know which machine it is on or what is on it.** → the first line of the seed is the install address, version and fingerprint; the tree below it is "what this machine has".
- **Finding things means walking the disk, and the answer is still a guess.** → query the seed first: milliseconds to the file and section. Only when all four sections are empty may it walk the disk.
- **It cannot remember what it read; next session it reads it again.** → the measured index is projected into the seed and survives the next projection. Read once, write it into the lineage, visible tree-wide.
- **It does not know its own documentation went stale.** → the sentence "this is what it is" is bound to an anchor; when the object changes, that description flips red without waiting for a human.
- **It does not know what it can do or where it should grow next.** → query the seed for which card to follow; that card's law plus criteria are the shape requirement. Shape first, then measure.
- **After a change it does not know whether it broke something else.** → run `verify.py` (seven groups); descriptions that watch it flip red, and red means look first.
- **It cannot tell another agent "here is what I have".** → the seed *is* that handover: tree-shaped, machine-readable (`seed.json`), every line with provenance.

**Not in scope:** code quality judgement, semantic understanding of the code, and porting the criteria to a
different harness — see Limits.

### 4 · Example: what it looks like running on DSH (measured)

This is the measured ledger of **one machine**, shown to prove the four actions actually run — not as a reference answer.
The reading is taken at 2026-11-18 (publish time): however often the local seed is re-projected afterwards, these numbers stay put.

```
object     DSH desktop 0.2.2-rc.2, app.asar 208,137,981 bytes, sha256 49fd1b08…
measured   21,682 files (1,678 unpacked) / 4 presets, 112 rows / 14 upgrade-guide directories
innate     11 skills (dsh-innate entry + 10 directions), one shared fingerprint 89de2e2de843
cards      10 innate cards (layout / plugin / service / preset / port / slot / window / doc / bundled-skill / express)
acquired   65 top-level acquired artifacts (77 nodes under them), each with the five-part birth label
anchors    10 card files / 88 card entries carrying anchors / 226 anchors (counted that day by the frontmatter
           convention, which is not the same number as seed convention C — see "conventions" in section 5)
time       88 birth.at stamps, earliest 2026-10-09, latest 2026-11-17
rings      5 rings, all under the same fingerprint
verify     live.py --check 0 problems; verify.py 97 checks green; second gen_innate run wrote 0 files
```

> **The `anchors` line holds three ways of counting — never compare one convention against another.** Card files on
> disk / card entries whose anchor list is non-empty / anchors summed one by one (the same file watched by two artifacts
> counts twice). The 226 in the third slot was counted that day by the **frontmatter convention** (`looks_at` entries
> read straight from `SKILL.md`, not from the seed) and is **not the same data** as seed convention C; `count_seed.py`
> prints exactly how far the two differ and on which node. Take the true value from that script's output at the time —
> a number written into a doc is only one reading.

| Step | Output |
|:--|:--|
| the four steps `scan → gen_innate → live → verify` | a reproducible ledger — every number can be re-derived |
| innate skills + cards | 11 skills / 10 cards, each card carrying an anchor fingerprint |
| `live.py --check` | `0 problems` |
| `verify.py` | `97 checks, all green` |

That set only proves the pipeline runs end to end. Your install will yield different numbers — that is correct.
It is not the reference answer (different object, different criteria), and it is not the ceiling (see next).

#### A second example: new object, new language, same structure

One chain proves one chain. The sentence "the criteria change, the method does not" needs a second object
to be more than a claim — so here it is: **the same four actions ran, end to end, on Obsidian**
(an external program that has nothing to do with DSH), this time written in Node instead of Python,
measuring its own object.

| The four actions | The DSH chain (Python) | The Obsidian chain (Node) |
|:--|:--|:--|
| measure the shape | `scan.py` | `tools/scan-obsidian.mjs` |
| grow descriptions | `gen_innate.py` → 11 innate skills | `tools/live-obsidian.mjs` → 1 skill, `obsidian-innate` |
| build the lineage | `live.py` → `seed.json` | `tools/seed-obsidian.mjs` → `base/seed-obsidian.json` + `.md` |
| verify invariants | `verify.py` | `tools/verify-obsidian.mjs` (measured: 19 checks green, exit 0) |
| cards | 10 | 5 (layout / expression / loading / plugin / content format) |

What changed: the **object** (`app.asar` → the Obsidian program directory), the **language**
(Python → Node), the **criteria** (`package.json` main/exports → PE header of the payload, asar header
shape, the four native file formats in a vault). What did not change: the order of the four actions and
the loop innate → skill → card → seed → acquired → re-project.

So this is not "a tool that only knows DSH" — it is **a method that can grow a system repeatedly**.
And on the second object it also grew its own gaps: that chain has no query tool yet, its root path is
still hard-coded in five scripts, and there is no tree-ring ledger. Naming the gaps is the stronger
evidence — the method really transfers, and the empty places show up on the tree by themselves.

And it grows **vertically** too: the DSH seed has an acquired artifact `obsidian`; that field is itself
a whole tree (Obsidian innate → 5 cards → `seed-obsidian` with 8 acquired artifacts), inside which grows
`Blender`, itself another tree (5 cards → `seed-blender` with 6 acquired artifacts, 35 checks green).
**One seed grows the next seed.** The two trees are stitched by anchors / paths — the lower tree is not a
`child` of the upper node (that node's `children` is empty). When the lower ledger changes, the upper card
watching it flips red (measured: `obsidian card object changed`) — the alarm crosses layers. That is what
"seed grows seed" means. Three layers is the actual shape here, not infinite recursion.

`jar` / npm / docker / module graph remain **directions, not shipped**. The real examples prove
"the method transfers to another object and grows deeper", not "any object works automatically". Whether
one grows depends on whether its shape can be measured — the ruler is built against the object.

### 5 · How to show it

Growing the seed is half the job; **making it visible** is the other half. This section fixes no format, only the method.

**What to show**: the tree plus its edges — what exists, who begat whom, which paths are watched, and where
nothing exists yet. One purpose: a reader should see at a glance what the system grew into, and where it is empty.

**Which data to show it from**: `seed.json`. It is already structured (node + parent + 依据 + state + anchors),
so it renders directly — **no separate presentation data to maintain; whatever is in the seed can be shown.**
The problem list from `live.py --check` is the "edges" half: red marks are empty places.

**Ways it can be presented** (in order of preference):

1. **A clickable HTML page** (preferred) — the tree expands by parent/child, and each node opens to show
   who begat it, which card it followed, which files it watches, and whether the fingerprint still matches.
   Anyone who does not live in a terminal understands it on open, and can click into what they want instead
   of squinting at a picture.
2. **Structured data** (for agents) — `seed.json` is already queryable; an agent reads it directly, no page needed.
3. **Tree text in a terminal** (a quick glance; the shortest path).
4. **Deliberately not**: a static screenshot as the showcase. It cannot be clicked and does not follow the seed.

**Why it must be clickable**: **only what you can open counts as a showcase; a picture is dead.** A screenshot
starts lying on the day it ships — which is the very problem this project exists to solve (stale docs nobody
notices). So the showcase has to be live too: **generated from `seed.json` on demand, regenerable at any time.**

**The form follows the audience**: structured data for agents, a clickable page for people.

#### Generating that page: `render_seed.py`

This is a command, not a claim. `scripts/render_seed.py` generates **one self-contained HTML file** from `seed.json`:

```bash
cd scripts
python render_seed.py                      # default seed (resolved by paths.py) → ./seed-tree.html
python render_seed.py <seed.json>          # explicit seed
python render_seed.py <seed.json> -o out.html
python render_seed.py --print-path         # only print where the default seed is
python render_seed.py --verify-idempotent  # prove idempotence: render twice, compare sha256
```

Then open the file in a browser. **Single file, no external resources at all** — no CDN, no web fonts, no images.
It opens offline; double-clicking is enough.

What is on the page (everything computed from `seed.json` at generation time, no node name hard-coded):

| Where | What |
|:--|:--|
| top stats | node count / card entries / anchors / distinct objects / broken anchors (plus innate and acquired counts, blank nodes) |
| tree | expanded by `birth.from` — `from` is the parent; innate on top, acquired below; unresolvable `from` listed as "parent not found" |
| detail | click any node: name / short name / birth four lines (at / from / 依据 / act) / its cards and every anchor (with existence) / fingerprint and seen_at |
| edges | an anchor pointing at a missing path is marked red and tabulated under "broken anchors"; artifacts with no anchor or no birth are tabulated under "blank" |

Those two edge classes also show up in the tree itself (a red tag next to the node name).
There is a filter box and expand/collapse-all for large trees.

**This page is generated from `seed.json` every time — change the seed, rerun the command, and the page is new.
That is exactly the difference between it and a static screenshot:** a screenshot cannot be clicked and does not know
it has gone stale; this page opens and catches up with a single rerun.

**Idempotent**: running it twice on the same `seed.json` bytes produces byte-identical output, because the page
contains no **render time** — the generator and source path appear only in a trailing HTML comment.
The "seed data generated at" line in the header is a field `seed.json` carries (`生成于`); it is **data**, not render
time — it changes when the seed is re-projected, not when the renderer is rerun.
Prove it yourself: `python render_seed.py --verify-idempotent` renders twice and compares sha256.

The precondition matters: idempotence is about **the same seed bytes**. If the seed was re-projected (its `生成于`
or its nodes changed), a different page is correct — that is data changing, not the renderer being non-deterministic.

On our machine, the page from the first command above reports
**88 nodes (11 innate · 77 acquired) / 88 card entries / anchor count and distinct objects from count_seed.py / 0 broken / 0 blank** (a reading; the seed re-projects, so take the script's current output as truth).

> Recompute those with `python count_seed.py` (same directory) — do not copy them by hand, and do not compare
> numbers from different counting conventions. The script prints what each convention counts and where they differ.

#### Conventions: one thing, several ways to count it

"Is it 226 or 227 anchors" is not a disagreement — it is two conventions compared side by side.
`scripts/count_seed.py` writes each convention into code and prints one definite set of numbers:

```bash
python count_seed.py           # human: what each convention counts, where it reads, the result, where they differ
python count_seed.py --json    # machine
```

| Convention | What it counts | Where it reads |
|:--|:--|:--|
| A card files | `.md` files directly under the card library | `<ASSETS>/名片/` |
| B card entries with anchors | card entries in the seed whose anchor list is non-empty | `seed.json` |
| C anchor count | every anchor of every card, summed | `seed.json` |
| D distinct objects | those anchor paths after de-duplication | `seed.json` |
| E `looks_at` entries | `card.looks_at` summed over every `SKILL.md` | `技能/*/SKILL.md` (not the seed) |
| F birth records | nodes whose `birth.at` is non-empty | `seed.json` |

**E is not the same data as A–D**: the seed attaches a node's *card* (innate cards come from the card library), while
the `card:` block in a `SKILL.md` is the card that skill grew for itself. Both are correct; `count_seed.py` names
how far they differ and on which node. Compare like with like — same script, two runs.

On this machine: **10 card files / 88 card entries with anchors / anchor count and distinct objects from count_seed.py** (a reading).

Half the value of a seed is that it *remembers*; the other half is that it *is visible* —
**a visible edge is what tells the next person where to grow.**

### 6 · How far it can grow

**The ceiling is the ceiling of thought, not of what is possible.**

**Layer 1 — runs today (measured).** Measure the install (files / packages / presets / routes / slots / services) ·
generate innate skills · grow cards · project the seed · verify (seven groups) · query the seed. All measured,
second run converges.

**Layer 2 — the data is already there, only a query layer is missing (not an existing feature).**

Already sitting in the seed (in brackets, the **reading at publish time, 2026-11-18**; recompute your own with
`count_seed.py`, never copy them by hand): 10 card files, 88 card entries carrying anchors, 226 anchors,
88 `birth.at` records, 5 rings.
Everything below is "write a query over data that exists". **The code is not written yet.**

| Wanted but not built | Data is enough; what is missing |
|:--|:--|
| dependency closure (change here, what moves) | anchors carry `path` and `looks_at` — just invert the index |
| zombie detection (untouched for a year) | 88 `birth.at` records; compare against today |
| a system snapshot for a given day | 5 rings of metrics are kept; replay by timestamp |
| cross-machine inventory check | run the same scripts elsewhere, diff two `seed.json` files |
| lifecycle grading (live → low-frequency → archived) | timestamps and reference counts exist; missing a rule |
| auto-generated architecture note | the 10 innate cards already are that, by direction; missing the assembly step |

**The data layer has arrived; the query layer has not.** Whoever writes those queries gets the next batch of measurements.

**Layer 3 — a path, not a shipped feature.**

These directions hold, but this implementation has not done them and has not measured them:

- `jar` / `war` — criteria move to `MANIFEST.MF`
- npm dependency tree — criteria move to lockfile resolved / integrity
- docker image layers — criteria move to layer digest and parent pointers
- code repository module graph — criteria move to static import / require resolution

They share the first three actions; only "what counts as necessary" must be rewritten. It is not four new features,
it is the same method with four different rulers.

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

**Three things it explicitly does not do:**

- **No code-quality judgement.** It measures *what is*, never *what should be*. Whether the architecture is good
  is outside its range; evaluation words are scanned for and rejected in card bodies.
- **No semantic understanding.** It does not know what a piece of code means in business terms. "What is this",
  "where are the boundaries", "why was it written this way" still have to be written by a human — the tool only
  makes those sentences flip red when they stop being true.
- **Harness-specific criteria.** The criteria are shaped by DSH (`app.asar` + `runtime.json`, `package.json`
  main/exports, routes split by kind). On another host the matter looks different and the criteria must be
  rewritten — the method and the seven links port, the deciding lines do not. This is not a defect; it is the
  inherent shape of the capability: **the ruler has to be built against the object.**
- **Only one path is proven here.** Layer 3 in §6 (jar / npm / docker / module graph) is a direction, not a
  shipped feature. Do not read this as "works on arbitrary objects".

**Risks:** read-only on the installation; writes only under `技能/`, `名片/`, and the state directory; no network;
numbers differ across versions by design; runtime facts (who consumes what, what happened today) are not measurable
from static files and are deliberately left blank.

### License

MIT

---

Copyright (c) 2026 fjshoumeng
Publishing flow uses [qiaomu-skill-publisher](https://github.com/joeseesun/qiaomu-skill-publisher) by 向阳乔木.
