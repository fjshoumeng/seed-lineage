# 发布检查记录（dry-run）

日期：2026-11-17
对象：`D:\DSH-本地插件包\外部技能\seed-growth`
工具：`qiaomu-skill-publisher-main/scripts/publish_skill.py --dry-run`
**只做 --dry-run，未发布。** 公开还是私有要老板拍板。

## 最终结果

```
🔍 检查 Skill: D:\DSH-本地插件包\外部技能\seed-growth

✅ SKILL.md 验证通过 (name: seed-growth)
✅ gh CLI 已就绪
✅ GitHub 用户: fjshoumeng
✅ GitHub 仓库名: seed-growth
✅ LICENSE 已存在
✅ README.md 已存在
✅ README 质量检查通过

🏁 Dry run 完成。实际发布命令:
   python3 ...publish_skill.py D:\DSH-本地插件包\外部技能\seed-growth \
     --github-user fjshoumeng --repo-name seed-growth
```

退出码 0。

## 提示过又被修掉的问题（按出现顺序）

| # | 报错 / 现象 | 根因 | 修法 |
|--:|:--|:--|:--|
| 1 | `UnicodeDecodeError: 'gbk' codec can't decode byte 0xac` | 发布脚本用 `open(path)` 不指定编码，在 Windows 上默认 GBK；SKILL.md 是 UTF-8 中文 | 不改脚本（不是我们的文件），改用 `PYTHONUTF8=1` 运行。**记一笔：Windows 用户跑这个发布器都得带这个环境变量** |
| 2 | `[错误] 未找到 gh CLI` | 发布器用 `which gh` 判断，`which` 是 Unix 命令，Windows 上没有 | 在临时目录放一个 `which.cmd`（内容是 `where %1`）并前置到 PATH。`gh` 本身是装好的、已登录 `fjshoumeng` |
| 3 | `[错误] 无法获取 GitHub 用户名` | 上一行里的 `gh api user --jq '.login'` 在 Windows 下走 sh 语义拿不到输出；且目录没有 git origin | 显式传 `--github-user fjshoumeng` |
| 4 | README 是**脚本自动生成**的通用模板 | 目录里没有 README，发布器就套模板，而那个模板讲的是"怎么发布 skill"，与本技能内容无关；还挂着别人的版权（向阳乔木 / joeseesun） | **重写 README**：价值主张 / 首屏证据 / 前置条件 checkbox / 完整安装与五步跑法 / 使用示例 / 风险限制 / 常见问题（10 条）/ 致谢 / 中英双语。重写后 `✅ README.md 已存在`，质量检查通过 |
| 5 | LICENSE 版权人写成 `DSH Agent` | 发布器按参数填的占位 | 改成 `fjshoumeng`（账号名），与 README 末尾一致 |

## 硬规则核对

- **`description` 用 `|` 块标量** —— 是。里面含冒号、顿号、破折号、`→` 箭头，都在块标量里安全。
- **README 无占位** —— 无 `TODO`、无 `特性 1`、无 `[问题 N]`、无 `your-org/your-repo`。
  这些正是发布器 `check_readme_quality()` 会拦的 10 个正则，逐个比对过。
- **README 七要素** —— 价值主张 ✅ / 首屏证据（实测数字表）✅ / 前置条件 checkbox ✅ /
  完整安装步骤（含验证命令）✅ / 自然语言使用示例 ✅ / 风险与限制 ✅ / 常见问题 ≥3 条（实际 10 条）✅ /
  致谢（qiaomu-skill-publisher + 原始工具链）✅

## 反向验证（确认校验真的会拦，不是摆设）

另建一个临时目录，把 `description` 写成 **非块标量 + 含冒号 + 含双引号**：

```yaml
description: 教一台机器从本体里长出种子: 冒号没引号，还有"双引号"
```

结果：

```
❌ 验证失败:
   - YAML 语法错误: mapping values are not allowed here
   常见原因: description 含未转义的引号或特殊字符
   修复方法: 改用 | 块标量格式:
     description: |
       ...
```

退出码 1。→ **校验是有效的，本技能能过不是因为它没查。**

## 边界

- 没有 `--private`，没有推仓库，没有 `npx skills` 真装验证。
- 公开 / 私有、仓库名、是否同步到 `~/.agents/skills`，都等老板定。

---

## 后续（2026-11-17 追记）

**上面全文里的 `seed-growth` 是历史记录的原样，不改。** 那个名字已弃用。

- 目录已改名：`外部技能\seed-growth` → `外部技能\seed-lineage`
- SKILL.md `name:` → `seed-lineage`，正文自称同步
- README 标题 / 正文 / 安装命令 → `fjshoumeng/seed-lineage`，`ls ~/.agents/skills/seed-lineage/`
- GitHub 仓库名 → `seed-lineage`，公开发布
- LICENSE 版权人不变（`fjshoumeng`）

改名同时降级了正文里的具体量数：文件数 / 包数 / 预设行数这类「我这一台机器的数」不再罗列，
只保留「走完四步、8 份 skill、97 项校验全过」证明流程走通。理由同上文记的那条 ——
写死的数就是文档开始假的那一刻。

上面第 32 行、第 34 行记的两个 Windows 坑**依然有效**，本次发布照样要带：
`PYTHONUTF8=1`、前置 `which.cmd`、显式 `--github-user fjshoumeng`。

## 发布结果（2026-11-17）

```
https://github.com/fjshoumeng/seed-lineage   公开（PUBLIC），默认分支 main，13 个文件
```

- dry-run 退出码 **0**（改名与降级之后重跑的那一次）
- 发布器末尾仍打印 `❌ 验证失败: 真实安装失败：临时目录中没有生成 .agents/skills/<name>/SKILL.md`
  —— 这是发布器 `verify_skill()` 在 Windows 上的误报：它查的是
  `os.path.join(tmpdir, ".agents", ...)`，而 `tmpdir` 在 Windows 是 `%TEMP%`，
  `npx skills` 把 skill 装到**当前工作目录**下，两边不是同一个地方。
- 同一件事手工复核过，通过：在空目录里跑
  `npx skills add fjshoumeng/seed-lineage --skill seed-lineage --yes`
  → `✓ .\.agents\skills\seed-lineage`，`SKILL.md` 在，`name: seed-lineage` 正确。
  仓库 `--list` 也报 `Found 1 skill`。
- 仓库内容按 blob sha 与本地 `HEAD` 逐个比对：README / SKILL.md / LICENSE / .gitignore / 脚本全部一致。
- `state/`（量出来的中间账）**没进仓库**：里面带本机绝对路径，而且每台机器不一样 —— 进了仓库就变成标准答案。

还没做：`npx skills` 装到 `~/.agents` 之后没在本机当技能跑过一遍（只有发布器那步同步了一份副本）。

---

## 追记（2026-11-18 · 补第二个真实例）

改动范围：只动文档正文 —— `SKILL.md` 新增「第二个范例：换了本体、换了语言，照样长出完整结构」一节
（位于「这份技能要压平的是什么麻烦」与「范例：它跑在 DSH 上」之间），`README.md` 中英各加对应一小节，
并同步三处「只跑通一条」的说法与两处判据对照表。`scripts/` 下**没有改任何脚本**，
Obsidian 的工具脚本**没有搬进 `scripts/`**（它是例子，不是零件）；`LICENSE` 未动；`description` 未动。

dry-run（同一套 Windows 三件套依然有效：`PYTHONUTF8=1`、前置 `which.cmd`、显式 `--github-user fjshoumeng`）：

```
python publish_skill.py D:\DSH-本地插件包\外部技能\seed-lineage --dry-run --github-user fjshoumeng --repo-name seed-lineage
✅ SKILL.md 验证通过 (name: seed-lineage)   ✅ gh CLI 已就绪   ✅ GitHub 用户: fjshoumeng
✅ GitHub 仓库名: seed-lineage              ✅ LICENSE 已存在  ✅ README.md 已存在
✅ README 质量检查通过                      🏁 Dry run 完成，退出码 0
```

校验链状态（本次改动前后逐项一致，**没有因为这次改动新增任何红项**）：

| 链 | 项数 | 未通过 | 本次影响 |
|:--|--:|--:|:--|
| 发布版 `scripts/verify.py` | 273 | 5 | 0（5 条与上表同为改前既有：种子被重投 + 4 张名片 seen_at） |
| 本机 `工具/dsh-skillmap/verify.py` | 365 | 5 | 0（同一批） |

改前基线两份完整输出留存在工作区 `baseline-发布版-verify.txt` / `baseline-本机-verify.txt`，可逐行比对。

一处操作留痕（诚实记）：提交前工作区里已有**另一件活的**未提交改动（`SKILL.md` 「方法类判据=有没有一句总述」那 12 行）。
本次把它从提交里排除（只提交本任务自己的改动），提交后原样放回工作区 —— 那条改动仍未提交，归它自己的活收口。


