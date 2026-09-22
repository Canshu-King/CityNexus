# HJ-P2 第一份读数（承诺密集型旅行者）· finding `d4b04a0f/01`

- 车道：HJ-P2（SESSION `d4b04a0f`），人设 = 承诺密集型旅行者；单据 ORD-0120 / P1–P4 用户优先级率令
- 时间：2026-09-22 19:2x（+08）
- 走法：**只用可见 UI**（真人顺序点击），未用 API 造任何"成功"；本文件里出现的 API 只有 3 次 `mode=ro` 只读探测和 2 次 `GET`
- 本文是**外部可读证据**：每条断言都带一个审计者能自己解析的坐标（见第 5 节），本地不可解析的坐标已按执行令（第五条）明确标 `LOCAL-ONLY`

---

## 1. 先更正我自己：18:52 那句"屏幕上没有任何失败/原因文案"是错的

我当时写：`POST …/agent/comm → 200`、`GET /plans → 200 但 0 条`，"**屏幕上没有任何失败或原因**"。

**同一次走查（18:17）我自己截的图就是反例**：屏上有一张具名失败卡——

> 「**这次排不出方案：数据不够，不是你说的不对**」
> 「这座城我们还没有任何地点数据，所以不是你描述得不对——是没有东西可排。（服务器给的原因编号：**`CATALOG_EMPTY`**）」
> 「▶ 技术详情」 + 主动作按钮「**换一座有数据的城市**」

截图（已发布，见第 5 节）：`r6_04_named_failure.png`。

**错误性质**：我用一次过早的 DOM 读数下了"无文案"的存在性结论。过早是事实，**具体为什么过早我不编成因**（可能是排期结果尚未回填，也可能是我读的选择器没覆盖那张卡）——我只撤结论，不猜机制。
**纪律更正**：从这条起，"屏上没有 X"这类否定断言必须配**同屏截图**或**整屏 `innerText` 快照**，否则不写。

⇒ 因此"AI 不可用还让按钮可点"这件事**不构成静默失败**：产品确实解释了原因、给了编号、给了出路。**下面第 2 节把它降级**，并把真正卡住我这条车道的事实（第 3 节）提为第一 finding。

---

## 2. 保留的事实（不升级为缺陷）：主按钮的门禁与"AI 可用性"无关

同屏两个时刻（截图 `r6_03_drawer.png` = 空输入；`r6_04_named_failure.png` = 已输入）：

| 时刻 | 输入框 | 「开始规划」 | 抽屉那句 AI 提示 |
|---|---|---|---|
| 空输入 | 空 | 浅蓝、`disabled=true`（native） | 挂着 |
| 我照提示打字（「第一天一定要去拙政园，票已经买好了，不能改时间。」） | ≥8 字 | **深蓝、可点** | **仍然挂着** |

线上产物字节（不是本地构建）里这条门禁是：

```text
"data-testid":"plan-ai-submit", disabled:x||c.trim().length<8
```

`x`=请求进行中，`c`=输入内容；持有 AI 可用性的变量 `D`（同一段里 `"data-ai-state":D` 用它渲染那句提示）**不在表达式里**。
源码同一条：`frontend/src/features/planning/PlanWithAiSheet.tsx:867`（tip `b41b4cc` 与 `25165d9` 上 blob 相同，见第 5 节）。

**我的判级**：`POLISH / 设计不一致`，**不是 HUMAN_BLOCKER**。理由：抽屉那句「现在提交不会真的由 AI 规划，结果会走其它路径」是在**明说允许提交并预告后果**，所以按钮可点与文案并不矛盾；`aiState` 不进门禁是有意的回退路径设计的可能性很大（我不下结论，交给写这行的车道说明意图）。
**这条我 18:52 判重了。**

---

## 3. 第一 finding（真正阻塞承诺密集场景的那条）：目的地不做解析、按字面成码，行程照建，"这座城没有数据"要等用户走完三步才说

### 3.1 真人顺序读数（1/1，我自己的副本库、我自己的 profile）

```text
新建行程 → 目的地输入「苏州」→ 向导确认屏显示「苏州之旅」→ 提交创建
  → 21 秒后枢纽就绪：「苏州之旅 / 9月23日 10:00 — 9月25日 20:00 · 2 位旅行者 · 3 天」
  → 屏上此刻没有任何"这座城没有地点数据"的提示；反而给了三个动作：
     「AI 帮我规划」「试用其他城市」「打开行程工作台」
  → 我点「AI 帮我规划」→ 打字 → 点「开始规划」→ POST …/agent/comm 200
  → 这时才出现第 1 节那张卡：CATALOG_EMPTY「这座城我们还没有任何地点数据」
```

⇒ **告知发生在承诺之后，不在承诺之前**：用户已经花掉一次创建（我这一轮 journeys 3→5）、填完行程参数、写好描述，才知道这座城根本排不出东西。对"承诺密集型"人设这正是最坏的位置——我已经把这趟当成真事了。

### 3.2 机器侧证（只读，`mode=ro`，两库对照）

```text
places 表按 city_code 分布（两库完全一致）：
  我的副本 _hjp2_r6.db      : CNX-DEMO 8, CN-BEIJING 8        （合计 16 行）
  线上库 _live.db（只读探测）: CNX-DEMO 8, CN-BEIJING 8        （合计 16 行）
我这两条行程的 journeys.city_code：
  f34c8ff0…  = CN-HANGZHOU     ← 库里 0 个 place
  68f8c7a1…  = CN-苏州         ← 字面量：城市码是"CN-" + 用户输入的原文，不是解析出来的
对照：库里已有的三条行程 city_code 都是 CN-BEIJING 或 CNX-DEMO（有数据的那两座）
catalog_hydration_operations 行数：我的副本 0 / 线上库 0
  （这张表的列里就有 pending_destination_label / resolver_query_normalized / canonical_destination_id，
   形状正是为"用户写的名字还没对上 canonical"准备的。它 0 行只说明：**这条流程没往里排队**。
   "该不该排"是 ANYWHERE 车道的问题，我不替它下结论。）
```

数据文件与逐字段读数：`isolation_receipt_r7.json`（第 5 节已发布）。

### 3.3 判类与影响

- 分类：**`HUMAN_BLOCKER` + `TRUTH_DEFECT`**
  - `TRUTH_DEFECT`：`journeys.city_code = "CN-苏州"` 是一个**造出来的**码，不是解析结果；屏上却把它当"已确认的目的地"呈现（标题「苏州之旅」、枢纽日期齐全、0 个 place 支撑）。
  - `HUMAN_BLOCKER`：它把我这条车道**唯一要演的东西**（建硬承诺 → 执行 → 中断 → 重规划 → 接受方案）挡在第一步之后——没有 place 就没有方案，没有方案就没有 `PLANNED`，没有 `PLANNED` 就没有可保护的承诺。我 18:52 报的 blocker 成因（"方案生成被 AI 门禁卡死"）**是错的**，正确成因是**这两座城在这座库里没有任何地点数据**。
- **跨车道可复用的一条事实（建议号令者转给 HJ-P1/P3/P4）**：在这座线上库上，**只有 `CN-BEIJING` 与 `CNX-DEMO` 有 place 行**；选别的城市做承诺密集场景，一定会走到 `CATALOG_EMPTY`，那不是产品坏了，是数据面就只有两座城。
- 复现条件：任意输入一个库里没有地点数据的城市名（杭州、苏州都命中）；1/1。
- 我没有做的：没改 localStorage、没调 API 伪造数据、没为了让方案出现而换成北京后谎称是原场景（下一步我就用北京重走，并**明确标注那是另一条场景**）。

### 3.4 最小判据（不猜实现）

```text
1. 目的地输入步：若该名字对不上任何 canonical/有数据的城市，屏幕在【创建之前】就要说；
   并且「试用其他城市」这类出路要在同一屏，而不是在失败之后才出现。
2. journeys.city_code 不得由用户原文拼接得到；拼出来的值要么拒，要么在屏上标"未解析"。
3. 反例门：新建一座无数据的城市 → 断言创建前屏上出现"没有地点数据"文案；
   若只在提交后出现 ⇒ 红。
```

---

## 4. 隔离收据（执行令要求的形状：副本库 + 行数差）

| 库 | 打开方式 | journeys | travelers | plan_versions | commitments | constraints | bookings | 我的两条 id |
|---|---|---|---|---|---|---|---|---|
| 我的副本 `_hjp2_r6.db` 走查前 | `sqlite mode=ro` | 3 | 3 | 19 | 1 | 3 | 1 | — |
| 我的副本 第一次创建后 | `mode=ro` | 4 | 4 | 19 | 1 | 3 | 1 | +杭州 `f34c8ff0` |
| 我的副本 第二次创建后（final） | `mode=ro` | **5** | **5** | **19** | 1 | 3 | 1 | +苏州 `68f8c7a1` |
| 线上库 `_live.db`（只读复探，19:1x） | `mode=ro` | **3** | **3** | **19** | **1** | 3 | 1 | **0 命中** |
| 另一共享库 `_preview.db`（只读复探） | `mode=ro` | 31 | 45 | 9 | 0 | 3 | 0 | **0 命中** |

- `plan_versions` 全程 19：**我一个方案都没生成**——第 3 节就是它的成因。
- 三个库的**主文件 stat（size+mtime）在探测前后逐项相同** ⇒ 我这轮的只读探测没写任何东西（WAL 的 `-wal/-shm` mtime 可能被只读打开刷新，这一点收据里也记了）。
- 库绑定方式与强度：见 `isolation_receipt_r7.json` 的 `store_binding`——我是用"号令者 19:10 自己写的 P0 读数 `3/3/19/1/1` 与 `_live.db` 逐项吻合"来推断线上库身份的，**不是**读到了那个 uvicorn 进程的环境变量；这条按推断记，不按观察记。
- 端口/进程归属：本车道自起 `127.0.0.1:8453`（**后端 uvicorn**）/`:8493`（**前端 vite preview**，浏览器打开的是这一支），bind-test 后起，**收尾已停**；未占 `:4781/:4782/:8693`；未新建隧道；未出网。
- 禁令自查：本轮**没按**「重置到场景起点」、**没写**任何共享库、**没上传**任何 `.db`/凭据（发布前跑的是本车道自带的禁载物拒绝，见第 5 节末）。

---

## 5. 可解析坐标（`EXTERNALLY_READABLE_EVIDENCE`）

仓库/分支：`Canshu-King/CityNexus` @ `commander/control`
目录：`evidence/hjp2_d4b04a0f/ord0120_r7/`
每个文件都由 `live_checks/publish_evidence.py` 发布并做**逐字节回读**（`BYTE-LEVEL MATCH`），blob sha1 = git 对象号本身。

```text
PlanWithAiSheet.tsx              38,447 B  blob 8d58cfe9faf10562fe86164faa817bc7bbe0a769  commit d617536793ec
deployed_artifact_excerpt.txt     3,175 B  blob 13b58e3dfa7ec49a634faffd65f764d6fac6e1e6  commit 0f9e041ecbe7
isolation_receipt_r7.json        16,354 B  blob 46145e5ca335db579e5b20b27280c27eacf4400b  commit (republished)
r6_03_drawer.png                221,739 B  blob fda2415e998dc1036cd3a4b3f09eb5792deef84e  commit ac019f7f721a
r6_04_named_failure.png         262,308 B  blob b9d27f10a49aa3f829f6ccbf86a9389e341e0df3  commit 71e31d0c7135
finding_hjp2_reading_01.md  （本文件，坐标见 manifest.json / 账本交付行）
```

**交叉校验（这是本条最有说服力的一处）**：`PlanWithAiSheet.tsx` 发布后的远端 blob sha1 = `8d58cfe9faf10562fe86164faa817bc7bbe0a769`，与本地
`git rev-parse HEAD:frontend/src/features/planning/PlanWithAiSheet.tsx` **完全相同** ⇒ 审计者在 `commander/control` 上打开的那份，就是树里那个 git 对象本身，逐字节；
第 2/3 节引用的 `:383-392`、`:741`、`:867` 行号可在那份文件上直接核对。

**更正记录 @19:3x（本文件重发一次）**：第一版把本车道的端口角色写反了（`isolation_receipt_r7.json` 里把 uvicorn 记成 `:8493`，本文件第 4 节把 `:8453` 标成前端）。
按 `backend2.log`（`Uvicorn running on http://127.0.0.1:8453`）与车道自己的导航 URL（浏览器打开 `:8493`）更正后重发：

```text
isolation_receipt_r7.json   1e78ebd6ad431c439b05b091273b507d57d5fa7e  ->  46145e5ca335db579e5b20b27280c27eacf4400b
finding_hjp2_reading_01.md  c0149e3927c7eb535bd55b583632c50b88d2381a  ->  新值见 manifest.json（本文件不能自含自己的对象号）
```
旧 blob 在 git 里仍可解析（内容寻址，删不掉），**以新值为准**；本车道除这两处端口角色外的读数未变。

**必须点明的不可解析坐标（按第五条"不写就等于没交"的反面，我主动写）**：

```text
LOCAL-ONLY, no resolvable coordinate:
  工作树尖 b41b4cc / 25165d9 / 522c414 / 56d20ec  —— 均未 push，GitHub 两仓解析不到（号令者 18:54 已实测 422）
  我的副本库 D:/moodle/_qoder_hjp2_r6_20260922/_hjp2_r6.db —— 禁载物，**故意不上传**
  线上产物 index-BCF4ptyk.js 的取回 URL —— 公网隧道主机名每次重启会换，
    耐久坐标是它的 sha256 f3bda3d696d37cd1750e646a98ea6151c64d59247517c937b198dd369251d0e9（1,230,082 B）
    与其中的字节偏移 377,945（按钮表达式）/ 374,954（AI 状态段落），两者都抄在 deployed_artifact_excerpt.txt 里
```

**发布器安全边界（第六条 ③ 的自查）**：`publish_evidence.py` 目前没有机械禁载物拒绝，所以本车道用了自带护栏的包装
`publish_safe_r7.py`：拒 `.db/.sqlite/.key/.pem/.env/token/cookie/credential/auth` 文件名、拒 `SQLite format 3\0` 魔数、
`repo_path` 只许 `evidence/hjp2_d4b04a0f/**` 且拒 `..`。三条负例实测全部 `rc=2 REFUSED`（含"拿我自己的副本库去传"这一条）。
凭据文件只被发布器读取、未被打印。

---

## 6. 我还没测的（避免把没做的算进成绩）

- 「换一座有数据的城市」这个主动作按钮**没有点过**——它是否直接跳到北京、是否保留我已填的日期/人数，未知。
- 「▶ 技术详情」展开后印什么，没看。
- 用**有数据的城市（北京）**重走一遍完整承诺链（建硬承诺 → 执行 → 中断 → 重规划 → 接受方案 → 回 Wallet 复核）——这是第 3 节 blocker 的解法，我下一步就做；做完会另发一条读数，并明确它是**另一条场景**，不追改本节结论。
- 「我的」屏假空态三屏卡：仍**未复验**，成因已按第 3.2 节更正（不是 AI 门禁，是无地点数据 ⇒ 无方案）。
