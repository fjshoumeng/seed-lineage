# scripts/ · 最小可跑集

把 `scan → gen_innate → live → verify` 这条链跑起来所需的一切，就这些文件。

## 依赖

| 依赖 | 版本 | 用来干什么 | 检查 |
|:--|:--|:--|:--|
| Python | 3.8+ | 除 `find.cjs` 之外的全部 | `python --version` |
| PyYAML | 6.x | 读 SKILL.md / 预设的 frontmatter | `python -c "import yaml; print(yaml.__version__)"` |
| Node | 18+ | **只有** `find.cjs`（查种子） | `node --version` |

装 PyYAML：`pip install pyyaml`

> 为什么 PyYAML 是硬依赖而不是可选：本体里的预设文件带 `!js` 自定义标签
> （例如 `!js URLSearchParams`）。用严格的 `yaml.safe_load` 会整份解析失败，
> 预设就会量成 **0 行**；而 0 行会让「每行必有 id」这条规律**空过**——
> 检查绿了，但什么都没检查。这是这套工具里最容易骗过自己的一个点。

## 最小跑法

```bash
cd scripts

python paths.py        # 0 核对地址：四个值分别从哪来
python scan.py         # 1 扫本体 → state/regularity.json + 先天锚-<版本>.json
python gen_innate.py   # 2 长出先天 skill 与名片
python live.py         # 3 长名片 + 投影成种子
python live.py --check # 4 自检（期望 0 个问题）
python verify.py       # 5 全链（期望全部通过）
```

然后查东西：

```bash
node find.cjs <关键词> [更多关键词…]
```

## 把它展示出来 / 把数字钉死

两件不参与主链、但决定「别人能不能看见、能不能对上数」的事：

```bash
python render_seed.py        # 读种子 → 一个自包含 HTML（默认 ./seed-tree.html）
python count_seed.py         # 四个口径各自的数 + 差在哪（加 --json 出机读）
```

`render_seed.py` 出的是**单文件页面**：不外链任何资源，双击能开、断网能开；
树按 `birth.from` 展开，节点可点开看 birth 四行、名片与每条锚、指纹与 seen_at；
断锚标红单列，没有锚或没有 birth 的件单列「空白」；顶部统计全部从种子现算。
**种子一变重跑一遍就是新的** —— 这就是它和截图的区别。同一份种子字节跑两遍，输出逐字节一致（页面里不含渲染时刻）；
页头「种子数据生成时刻」是 seed.json 自带的 `生成于`，是数据不是渲染时刻。
自证：`python render_seed.py --verify-idempotent`（连渲染两次比 sha256）。

`count_seed.py` 把口径写死在代码里，避免「226 还是 227」这种拿两种数法横着比的分歧：

| 口径 | 数什么 |
|:--|:--|
| A 名片库文件数 | 名片库这一层里以 `.md` 结尾的实体文件 |
| B 带锚的名片条目数 | 种子里名片条目的锚列表非空的条数 |
| C 锚条数 | 所有名片的锚逐条相加（同一路径被两个件盯算两条） |
| D 去重对象数 | C 里那些 path 去重后的个数 |
| E `looks_at` 条数 | `SKILL.md` frontmatter 的 `card.looks_at`，不读种子 |
| F birth 条数 | 种子里 `birth.at` 非空的节点数 |

E 与 A~D 不是同一份数据，脚本会把差几条、差在哪个节点打出来。要比就同一个脚本跑两次比。

## 地址怎么定

不设任何环境变量也能跑（自动探测），但建议第一次显式指定，省得它猜：

```bash
# Windows（cmd）
set DSH_ORIGIN=D:\你的DSH安装目录
set DSH_ASSETS=D:\你的落点目录
set DSH_STATE=D:\你的落点目录\state

# PowerShell
$env:DSH_ORIGIN="D:\你的DSH安装目录"

# macOS / Linux
export DSH_ORIGIN=/你的/dsh/目录
```

| 变量 | 含义 | 判据 |
|:--|:--|:--|
| `ORIGIN` | 先天物质所在目录 | 该目录下有 `resources/app.asar` |
| `ASSETS` | 长出来的东西的落点 | 运行时会建 `技能/` 与 `名片/` |
| `STATE` | 量出来的中间账 | 运行时会建 |
| `HOME` | DSH 的 home | 只读判断用，本工具集不往里写 |

**建议先在临时目录试一遍**：把 `DSH_ASSETS` 与 `DSH_STATE` 指到 `%TEMP%` 下，
确认整链绿了再指向你的正式落点。所有写操作只落在这两个目录里，本体全程只读。

## 文件

| 文件 | 干什么 | 会不会写盘 |
|:--|:--|:--|
| `paths.py` | 唯一地址源：三级解析 + 每次打印来源 | 否 |
| `asar.py` | 读 asar 头与条目、算 file/dir 锚与指纹 | 否 |
| `scan.py` | 扫本体，量规律，写 `regularity.json` 与锚 | 是（STATE） |
| `gen_innate.py` | 从扫描账长出先天 skill 与先天名片 | 是（ASSETS/技能、名片） |
| `live.py` | 名片生长 + 种子投影 + 自检 | 是（各 SKILL.md 的 card 段、种子的种子目录） |
| `verify.py` | 全链校验（七组，判自洽不判像不像我） | 否 |
| `find.cjs` | 先查种子，不扫盘 | 是（STATE/查询日志.jsonl） |
| `render_seed.py` | 读种子 → 一个自包含 HTML（树 + 边界，可点） | 是（只写你指定的 HTML） |
| `count_seed.py` | 四个口径各数一遍，并指出差在哪 | 否 |

补跑的前置关系：`scan` 必须在 `gen_innate` 前（后者读前者的账）；
`live` 必须在 `gen_innate` 后（否则没有先天 skill 可投影）；
`verify` 永远最后。

## 常见错

| 现象 | 原因 | 怎么办 |
|:--|:--|:--|
| `× 找不到先天物质`，退出码 2 | `DSH_ORIGIN` 指错 / 本机没装 | 跑 `python paths.py` 看探过哪些位置；判据是「`resources/app.asar` 存在」。指到 `...\resources` 是差一层 |
| `预设 0 行` | YAML loader 认不出 `!js` 标签 | 用 `scan.py` 里的 `_yml`；别换回 `safe_load` |
| `包 0 个` / `文件 0 个` | ORIGIN 错了，或 asar 头偏移算错 3 字节 | 先 `paths.py`，再看 `asar.py` 的 `base` 与 offset |
| `名片长不出来` | 那个 skill 正文一条地址都没写 | 正文写全它盯的地址（反引号），指向真实存在的文件 |
| 一堆「地址失效」假红 | 正则把 asar 内部路径当磁盘路径 | 只认盘符、`/mnt/`、以及 `/(home\|Users\|opt\|srv\|tmp\|var\|private\|Volumes)/` 开头 |
| `gen_innate.py` 把 `card:` 抹了 | 生成器整份覆盖 frontmatter | 已内置 `keep_card_block()` 保住这一整段；改生成器时别把这层去掉 |
| 每次跑都重写全部文件 | 正文里混进了时间戳 | 只允许 `seen_at` 带时刻，且只在指纹变了时更新 |

## 换一份本体

从第 1 步重来（`scan.py`）。**别跳。** 跳了就是拿旧账长新描述，
数字对不上还找不到原因 —— 因为账本身已经过期了。

新版 `runtime.json` 不在 `primary-runtime/` 下的话，改 `paths.py` 里 `RUNTIME` 那一行。

## 这些脚本里没有的东西

- 不写死任何 `D:\` 开头的路径（原来那版写死了两处，换台机器就跑不起来）。
- 不写死任何版本号、任何计数（版本从 `runtime.json` 读，计数从本体量）。
- 不写死任何一个"标准答案"数字。**你的数和我的不同是正常的。**
