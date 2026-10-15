# QODER_PARITY — 融合分支上的能力对账（2026-10-14）

命令依据：`fusion/QODER_EXECUTION_ORDER.md` 第 2、3、7 条与交付节。
配套明细：`QODER_FEATURES_r1.csv`（32 行 × 10 列，逐行带 `文件:行号` 证据）、`MERGE_RISK_r1.md`、
`PHASE0_BASELINE_r1.md`、`slice1/ACCEPTANCE_RUBRIC_r1.md`、`QODER_HANDOFF_CODEX_r1.md`。
本文件只写结论与判定尺；数字全部本机亲测，凡引用他人之处都标了出处。

## 0. 基线与口径（先钉住可复跑的数）

| 项 | 融合基线 `594f9a4e75` | Qoder 产品树 `eeb8b8d2fd` | 量法 |
|---|---|---|---|
| 后端能否起 | **能**，health 200 | **能**，health 200 | 同一枚 `CityNexus/.venv` 3.12.14，无新建环境 |
| `/openapi.json` 路径数 | **249** | **159** | 活口拉文档，非正则抓源码 |
| 空库自举表数 | **93** | （切片尺里另记） | `sqlite_master`，同一支探针两棵树对跑 |
| `frontend/src` ts/tsx 文件 | **124** | **157** | `git ls-tree -r` |
| `tsc -p tsconfig.typecheck.json --noEmit` | **0 error** | **0 error** | 各塞一枚坏文件做反向对照，均立刻报 TS2322 ⇒ 绿是真的 |
| 全量套件 | 见 §5 前值 | **1921 passed / 18 failed / 2 errors / 309.28s** | 移植源自带 2 枚 ERROR 在 `test_qoder_boli_party_size_divisor.py` |
| 两叉真实差量 | 6839 files（6378 A / 241 M / 220 D） | | `git diff --shortstat`，非 GitHub 截断 300 |

**路由集合差（活口 openapi，纠正我先前口径）**：Qoder-only **11** 条 / 融合基线独有 **101** 条。
先前我报过「12 条」，其中 `{journey_id}/experience` 是误计——它来自 `main.py:8546` 函数体里的 f-string，
真路由在 `main.py:5490`，两棵树都已注册。⇒ 「谁文件长抄谁」在路由层同样错：基线比 Qoder 多 90 条路径。

11 条 Qoder-only：`collections`、`collections/{folder_id}/items`、`demo/scene/ensure`、
`journeys/{id}/abort`、`calendar.ics`、`checkins`、`member-role-limits`、`members/self-exit`、
`members/{member_id}/role`、`poi-import/add`、`poi-import/parse`。

## 1. **融合树上**彻底没有用户入口的 7 条（parity-A 扫描时判的 7 条；**本尖现读只剩 2 条成立**，见本节末尾的计数更正）

> **措辞更正（19:05，我自己写的那句会误导）**：这一节判的是**融合分支**那一侧。移植源不是这样——源树 `eeb8b8d2fd` 里收藏与打卡/足迹两条**有界面且已注册**（`v8PanelRegistry.tsx:6/:246/:30/:420`、`TripItinerary.tsx:24/:586`；`features/collections/` 5 枚文件、`features/checkin/` 6 枚），台上树与权威尖 `f6e936c8e85e` 同样有。融合基线这两处目录命中 0、注册表 grep 命中 0，所以「没有入口」只对融合成立。CSV 的 `state` 列按源树记的 `LIVE_IN_UI` 与此不冲突。
> 更要紧的是这带出一条冲突面：源树界面按「调用者自报身份」写（`collections.ts:63` 拼 `?traveler_id=`，`:45` 不带 `Authorization`），而我这轮把后端那扇门改成了只认签名令牌、且**不接受点名**。原样搬必红两次（401 与 422）。三处非改不可的接法在 `SLICE1_UI_PORT_SEAM_r1.md`。

打卡 check-in、足迹 footprint、收藏 collections、导入地点 POI import、日历 .ics 导出、行程长图 poster、中止行程 abort。
判定方式不是我猜文件夹：`v8PanelRegistry.tsx` 无该项、`routes/v8Routes.ts` 无该项、`LocaleContext.tsx` 词典无该 Tab、`data-testid` 不出现在 render 里。

> **计数更正（2026-10-15 03:20，import 尖 `41fbb9c731`）**：这七条到本尖只剩 **2 条**成立——行程长图 poster、中止行程 abort。
> 收藏 / 打卡 §9 接通，导入地点 §11 接通，**日历 `.ics` 导出 §12 接通**。
> 两条量法上的要紧事：
> 1. **日历这条按上面那四层判会永远判成「没入口」**——它不是 Tab，是行程面板默认子页里的一枚按钮，
>    现读融合树：`v8PanelRegistry.tsx` 命中 **0**、`v8Routes.ts` 命中 **0**，而词典 **20** 行、带 `calendar` 的文件 **10** 枚。
>    ⇒ 「注册表里有」是入口的**一种**形状，不是唯一形状；切片 4 那三件套要按形状分别量，不能一条 grep 通吃。
> 2. **`abort` 这枚 token 在本树有 13 枚文件的命中，但没有一枚是中止行程**——全是 `AbortError` / `AbortController`
>    （`journeyContinuation.ts:161`、`V8Experience.tsx:373-375` 等）。精确 token `journey-abort` / `abortJourney` 命中 **0**，
>    而源树两处都在（`v8PanelRegistry.tsx:450` 的 `testId: "journey-abort"`、`features/abort/` 四枚文件）。
>    ⇒ 判「abort 有入口」必须先打掉同名 token；这条与 §7 那条「`grep -c` 退出码」是同一类读数错法。

半缺 2 条（后端在、前端不读）：
- 分享接收方：融合 `main.py:6546/6617/6663` 门在，前端只有 `generated/api.ts:488` 的类型，**零组件读** ⇒ `BACKEND_ONLY`
- pending 落位/采纳：融合 `PendingSetPanel.tsx:332` 自印 `pending-no-place-door`

## 2. 建表机制（本轮最贵的一条，任何人做移植都会踩）

融合树这条路径上**没有 `Base.metadata.create_all`、也不靠 alembic**：
`backend/app/db/session.py:19` `SCHEMA_PATH = ROOT/"db"/"schema.sql"`，`ROOT = parents[2]` ⇒ 真文件是 **`backend/db/schema.sql`**（不在 `app/` 下），
`session.py:741 ensure_schema()` 用 `raw.executescript(sql)`，执行前还跑 5 个历史清理函数。
`backend/db/schema.sql`：融合 **89 个 CREATE TABLE / 90150 B**，Qoder **61 / 56773 B**，融合里 `collection` 字样命中 **0**。

**已实测（21:46 复跑，删库重启，同一支探针打两棵树）**：空库上调 `ensure_schema()` ⇒ 融合基线 **93 张**、我这枚 import 尖 **96 张**，
新增的三张正是 `collection_folders`、`collection_items`、`journey_checkins`，`REMOVED_TABLES = []`（移植没有吃掉任何一张既有表）；
索引同步 **228 → 236**。`UNIQUE (folder_id, place_id)` 在 `collection_items` 的 DDL 里（并另生两枚 `sqlite_autoindex_collection_items_1/2`），
`journey_checkins` 的耐久约束是 `UNIQUE (journey_id, target_key)`（不是可被 SET NULL 级联洗掉的 `activity_id`），
命名索引 `idx_journey_checkins_journey_stamped`、`idx_collection_items_folder_added`、`idx_collection_folders_owner` 都在；
`git grep create_all` 于 `backend/app` 仍 **0 命中**。
⇒ 基线 93 张 + 这三枚 = 96，建表这条腿只从 `schema.sql` 走通，不靠 ORM。原始输出：`parity/_boot_tables_r6.txt`。

⇒ **只加 ORM 模型类不会长出表**；只 `git diff` 挑「谁新」会一次删掉对方 28 张表。

## 3. 鉴权口径：移植必须升级，不许照抄 —— **已在 import 分支活口量到「读不到」**

细节与布景拆分见 `SLICE1_AUTH_ACCEPT_r1.md`（证据 `parity/_auth_accept_r1.json`，18:26 在 8122 上现读）。
一句话：`GET /api/v1/collections?traveler_id=<别人的 uuid>` 不带凭据，源树 `eeb8b8d2fd` 回 **200**（18:05 实测泄漏过
`names=["WeekendShelf"]`），import 分支 `6a734148f0` 回 **401**；B 持自己的合法凭据列架回 **200 / count=0**，
`B_sees_A_shelf = false`；拿 A 的凭据去点名 B 回 **422** —— 因为门上**已经没有 `traveler_id` 这个入参**
（`app/main.py:26973 def list_collections(request, session)`；`traveler_id: str = Query` 在 import 树命中 **0**，源树 1），
是结构性无法点名，不只是被拦。

四处源证据仍然成立（说明这不是我误读源树）：
1. `traveler_id: str = Query` 计数：融合 main.py **0** / Qoder main.py **1**（唯一那次就是 `GET /api/v1/collections`）
2. docstring：`What this version does *not* do is authenticate it -- the id is asserted by whoever calls`
3. DDL 注释：`asserted, not authenticated; the anonymous read is still this product's default`
4. **活口实测**：8123 上完全不带 `Authorization`，只把别人的 uuid 写进 query ⇒ **200 / count=1 / names=["WeekendShelf"]**

而 charter 的 non-negotiable stop condition 写着 `unsigned cross-member read/write succeeds`；
融合树自带缝：`app/traveler_principal.py: resolve_journey_member_principal(...)→principal.traveler_id`、`member_has_capability(...)`
（`main.py:2035-2042`、`:2184` 在用），且融合 `core/config.py` 有 `traveler_auth_secret`（Qoder config 命中 **0**）。

**未决判定（不许沉默）**：源树 `test_a_shelf_is_answered_to_its_owner_and_to_nobody_else`
（`tests/test_qoder_ord0444_collections.py:414`，第 419/423 行都断言 200）把未鉴权写进了契约。
融合版必须**改写并加强**成「B 点名 A 的 uuid 也拿不到」，**不许删断言凑绿**。

consent 落差一并记：`consent` 命中 融合 185 / Qoder 4，`provider_consent` 17 / 0。
融合树 consent 没有独立路由（openapi `consent` 前缀 0 条），是请求体字段 + 模块级强制。

## 4. 覆盖危险面（11 个点名文件全是 M）

「整文件覆盖」在任何一侧都错：基线独有如 main **175 个 handler**、models **35**、schemas **57**、`citynexus.ts` **93 个符号**、
`AgentToolGateway` 基线 2998 行 vs Qoder 1078 行、`ensure_schema` 1685 vs 1123；
反向 `openapi` 生成物与 `V8Experience.tsx` 是 **Qoder 更长**。同名不同行为的真冲突集中在
`generate_replan` −585、`_accept_replan_executing` −284、`seed_demo` −146。
Workbox `public/sw.js` 两树 211 行**完全相同** ⇒ 离线腿不是冲突源。
`core/config.py` 采「**反向不移植**」：真实城市腿与签名默认值基线更实（`traveler_auth_secret`/`city_search_*`/`live_valhalla_test_provider` 只有基线有），
四项 `real_city_enabled=false / live_valhalla_url=None / real_city_mode=replay / IMPACT_TIMEOUT_SECONDS=10` 两树逐字一致。

## 5. 我的命令第 7 条（R107/R108 导入后还得在、还得能用）——当前触达真值

存活（8121 活口 openapi）：`pocket-walk` 4 条、`pocket-walk/go` 1 条、`walk` 8、`guardian` 14、`operator` 10、`discovery` 6。
`LiveRecovery` 确有壳内入口：`v8PanelRegistry.tsx:181-198` `id:"live"`、`surface:"route"`、`testId:"live-recovery"`、`when: s.route==="live"`。

**但 GO MODE 只有半条腿**（详见 `QODER_HANDOFF_CODEX_r1.md` §一）：
全 `frontend/src` 提到 `pocket-walk` 的只有 2 个文件；`GoMode` 组件命中 **0**；
写门 `transitionBootstrapPocketWalkGo` 只有 `BootstrapDiscoveryPanel.tsx` 一个调用者；
**读门 `getBootstrapPocketWalkGo` 零调用点**；`go_progress` 只挂在 `BootstrapPocketWalkResponse`（save 的响应，`citynexus.ts:1878/:1892`）；
而该面板唯一渲染点 `V8Experience.tsx:1644-1650` 的注释自认它故意在 `.v8-product-shell` 之外、无底部主导航（`Amendment F #1`）。
⇒ charter Phase 4(B) 的 `reload to see persisted state` 在当前 UI 不可能通过；Journey 一旦 ACTIVE 就没有 GO 入口，与 `no hidden test-only route` 冲突。
判责：这属 Codex 的 `fusion/codex-journey-20261014` 管辖，我不在 import 分支顺手改；已在交接件里给出接线建议。

## 6. 我这一侧的残差风险

台上演示树 `cca117cf1a` 与命令指定的移植源 `eeb8b8d2fd` **不是同一棵**：mirror 领先 48 提交、台上领先 18 提交，
`git diff --numstat eeb8b8d2fd cca117cf1a -- backend/app frontend/src` = **+3091 / −10956**（`englishCountNoun` mirror 27 / stage 10）
⇒ mirror 更前进，选它作源是对的。但台上独有 3091 行集中在
`stay_mobility.py` +2056/−2227（带 `party_size` 行为回归臂）、`V8Experience.tsx` +110/−208、`PlanWithAiSheet.tsx`、`JourneyTrialSetup.tsx`、`CopilotDock.tsx`、`main.tsx`。
**待主人裁定**：这 18 枚要不要一并进 fusion，还是只认 mirror。按 charter `never overwrite their newer product fixes`，默认应按可评审 cherry-pick 补进 fusion 而非丢弃。

## 7. 移植顺序（按端到端用户价值降序，每片=路由+API+schema+UI+一条测试）

| 序 | 切片 | 为什么先 | 状态 |
|---|---|---|---|
| 1 | **Collections 收藏 + Check-in 打卡/足迹** | 融合侧 0 命中、纯加法（3 模型 + 20 schema + 9 service + 37 路由），一次恢复两条 Tab；但必须做鉴权升级与 `schema.sql` 建表 | **已落地**：后端 + 手契约 + 表 + 前端 + 守门测试，行为数见 §9 |
| 2 | POI import 导入地点 | `poi_import.py` 是零内部依赖的叶子模块，前端 `features/poiimport/` 4 文件；入口在 discover（与 1 共用唯一入口） | **已落地**（2026-10-15 00:06，见 §11）。**更正这行的「入口在 discover」**：源树那个入口是 discover 面板上的 `onOpenPreparePlaces` 触发腿，本片没搬（还要改另一片面板），融合树上这扇门的来路只有抽屉/URL |
| 3 | Calendar .ics 导出 + abort | `calendar_export.py` 同样零依赖叶子；`abort` 只 1 路由 | **导出这一半已落地**（2026-10-15 03:20，尖 `41fbb9c731`，见 §12）：`calendar_export.py` 逐字搬、门从匿名改成认签名令牌、玻璃真点一次出 2879 B / 9 VEVENT。**`abort` 这一半我没并进本片**，判成切片 3b 独立走：它不是「1 路由」那么小——门上要 `live_view`（融合两枚尖该字段命中 **0**、源树 `main.py` **5** 处 / `services.py` **2** 处 / `class JourneyLiveView` 源树 1 枚融合 0 枚 / `schema.sql` 两列 `aborted_at`+`abort_reason` 融合 **0**），且 `v8PanelRegistry.tsx:445-447` 的注释自认「面板读服务器的 `live_view`，绝不从 `status` 自己推状态」⇒ 只搬路由会搬出一枚说谎的按钮。前端闭包量过：`features/abort/` **4 枚文件全缺**（Panel 10894 B / ts 2690 B / Copy 7720 B / css 1871 B），依赖里 `rawFacts.ts`、`v8Formatting.ts` **逐字相同**，`CnxMeasuredFacts.tsx`（2839 vs 4676）、`v8Types.ts`（6721 vs 7938）、`LocaleContext.tsx`（113918 vs 202499）**存在但不同** ⇒ 又是 r77 那种「窄抄漏依赖闭包」的形状，先按文件比再抄。**加分项**：本片在共享词典里需要的键是 **0**（源树 `LocaleContext.tsx` 里 `abort.` 命中 0，句子在自家 `journeyAbortCopy.ts`），号令者「一杖最多三枚键」那条在这里根本不触发 |
| 4 | 成员角色三件套（role-limits / self-exit / role） | 动权限，需与融合 `member_has_capability` 对齐，风险高、价值中 | 待 |
| 5 | `demo/scene/ensure` | **HOLD**：这是布景/维护工具，不是产品能力；且需 demo token（本机空库实测 **403**）。按 charter `distinguish product additions from evidence-only` 不进产品 | 判定为不移植 |
| 6 | 生成物（openapi/`generated/api.ts`） | 放最后靠合并后重生成，不手抄 | 待 |

## 8. 我不能确认的（不写成就绪）

- ~~融合基线全量套件红面**前值**正在跑~~ ⇒ **已取到**（22:31，同一枚 `CityNexus/.venv` 解释器、各自新库、同机）：
  基线 `594f9a4e75` **272 failed / 1901 passed / 7 errors / 510.23s**，import 尖 **156 / 2055 / 7 / 415.30s**。
  两枚数**不能直接比大小**（已用同根单跑证明红面主要是测试互踩：`test_solver_runtime_gate.py` 整套红 15、单跑 20 全绿）。
  **本条原先写的「可比的是名集合差：1 枚，而那枚两棵树单跑都红」已经被实测推翻两次并在此更正**：
  那 1 枚（r87）单跑会翻面（基线 6 趟 3 红 3 绿），而**同一枚尖**跑两趟时红名集合自己就动了 2 枚
  （`SAME_TIP_SAMPLES_FLIPPED 2`）。所以尺换成两趟稳定差集：`RED_ONLY_IN_SLICE2_STABLE_IN_BOTH_SAMPLES 0`
  ⇒ 可说的仍是「移植没有引入新的失败」，但依据是「两趟都没有稳定多出来的红名」，不是任何一枚单趟读数。详见 `QODER_RESULT.md` §1。
- 融合树的 `vite build` / 真机 PWA 在 fusion 上还没跑过（磁盘 4585 MB、node_modules 799 MB，目前靠 junction 只读借用，未验证可写场景）。
- parity-A 的 `LIVE_IN_UI` 是**静态**四层证明（路由表∧注册表词典∧testid 落在 render）。
  其中收藏、打卡/足迹两条已由 §9 的界面守门**在真数据上点开并写通过**，导入地点一条已由 §11 的活口点开并写通过
  （`when` 门为真、`collect-entry` 在非空 plan 上可用）；
  其余三条（行程长图 poster、abort、成员角色）仍是静态层，没开页没点按钮。
  ~~`.ics` 导出~~ ⇒ **已由 §12 打掉这一格**：390×844 Chromium 上真按一次、Chromium 自己收下文件
  （`2879 B` / 9 枚 VEVENT / 88 对 CRLF），另有一腿无凭据 **401 且下载 0 枚**；回执在 `reports/qoder-ord0496-calendar/`。
- precache 8 条名单我无法复现（`v10-sw.js` 是构建产物，命令禁 build），只引主人今日实测与 `vite.config.ts:52-56` 自记。
- ~~`catalog_hydration_operations.py` 两侧是否改同一函数没读完 ⇒ 导入地点的合并冲突强度是未知项。~~
  ⇒ **本片已把它打掉一半**：该文件在两棵树上都存在，而整条分支的 `backend/app` 面只有 5 枚文件、**全是纯插入**
  （`git diff --stat 594f9a4e75..HEAD -- backend/app` ⇒ `db/models.py +138`、`main.py +1206`、`poi_import.py +244`、`schemas.py +245`、`services.py +128`，`1961 insertions(+), 0 deletions(-)`），
  里面**没有** `catalog_hydration_operations.py`。切片 2 自己那一份是 `main.py +251 / −0`、`schemas.py +67 / −0` 与两枚新文件。
  ⇒ 与 codex 那条车道合并时的冲突面只剩 `main.py` 里的插入点本身。
  该文件与导入是否共享函数，仍属未读，但已不是本片的未知项。

## 9. 切片1 前端落地（2026-10-14 21:46，import 尖 `85b48a27d7`）

**先认一条我报错的**：板上 §四 我写过「这两片的界面不需要动 app 词典」。不成立。
`FootprintPanel.tsx` 读 `t("checkin.title")`，所以融合词典必须有一枚键。亲测口径：`grep -c '"checkin.title"' frontend/src/i18n/LocaleContext.tsx` = **2**
（一枚键 × 两个语种），提交形状 = **1 键 / 1 commit**（`9a723b35c2`），符合号令者 10-10「字典单独一枝、一杖最多三枚键」。
其余句子一律待在这片的私有词表里（`checkinCopy.ts` / `collectionCopy.ts` / `footprintCopy.ts`），与 `features/access/accessCopy.ts` 同法——
这不是偏好，是为了不再让每条车道在同一枚串行化点上排队重写。

| 尺 | 数 | 复跑命令 |
|---|---|---|
| 这尖上超出基线的提交 | **18** | `git rev-list --count 594f9a4e75..HEAD` |
| 前端移植件 | **10 文件 / 1623 行** | `git show --stat 2231d7b6cc` |
| app 词典键 | **1 键 / 2 语种行** | `grep -c '"checkin.title"' frontend/src/i18n/LocaleContext.tsx` |
| 类型闸 | 两份配置各 **RC=0** | `npx tsc --noEmit -p tsconfig.check.json`、`-p tsconfig.typecheck.json` |
| 界面守门 | **5 passed（布景 1 + 四条腿 4）/ 21.6s / RC=0** | 见 `reports/qoder-ord0510/*.json`，跑法在 `qoder_import/SLICE1_UI_PORT_SEAM.md` §4 |

四条腿各自钉住的一件事（数值取自当轮输出，不是推算）：
1. **足迹行来自读门**：`stamps_on_server_before=0 → 1`，屏上 `21:43 Arrival 没写备注 网页端打的`，日区 `Asia/Shanghai`；
2. **重复打卡只说不写**：门回 **409**，句子带服务器自己的时刻（`10月14日 21:43`）而**无 uuid、无 reason_code**，屏上数目 `2 枚` 前后不动，服务器侧 `2 → 2`；
3. **收藏以读门为准**：首按 `已收在 收藏架 r3` 且 `items_after_first_tap=1`，再按 `这一枚已经在这个架子上。 · 已收在 收藏架 r3` 而 `item_count_after_repeat=1`；
4. **归属由凭据决定**：换旅客只见空态；**无凭据时收藏读门请求数 = 0**（不是请求被拒，是根本没问）。

**还没接通的两条腿（别按「就绪」读）**：`footprintRead.ts` 未移植——它要 `mapPanelCopy.ts` 里 6 枚 `footprint*` 键，融合树没有，且只有地图面读它；
`vite build` / 真机 PWA 在这条分支上从没跑过。§1 那句「融合侧没有入口」现在只剩 **4 条**成立（导入地点 POI import、日历 `.ics` 导出、行程长图 poster、中止行程 abort）——
打卡、足迹、收藏三条已由本节接通（`checkin`/`collections` 两条目录在树上命中不再为 0，注册表各多一枚 `route` 面板，`TripItinerary` 挂上两条写腿）。

## 10. 走查落盘 + 交付件归位（2026-10-14 22:11，import 尖 `fbca9536d3`）

号令者 Deliverables 要的两件都在**指定路径**上了：本文件 `fusion/QODER_PARITY.md`（原先错放在
`fusion/qoder_import/` 下，已 `git mv` 归位，命令写的是路径不是目录），和 `fusion/QODER_RESULT.md`
（SHA / 受影响的测试 / 界面入口 / 新旧动作 / 还欠什么）。

| 尺 | 数 | 复跑 |
|---|---|---|
| 界面守门 + 走查（同一条权威栈） | **6 passed / 24.0s / RC=0**，runId `uiportr10`，库 `_e2e_uiportr10.db`，后端 :8110 | `SLICE1_UI_PORT_SEAM.md` §4–§5 |
| 走查存档 | 7 枚 390×844 PNG + `walk_manifest.json`（每屏字节 + sha256 前 12 位）；7 枚摘要互不相同是**断言**，不是备注 | `reports/qoder-ord0510-walk/` |
| 全量 A/B（同解释器、各自新库） | 基线 **272F/1901P/7E/510.23s**，本尖 **156F/2055P/7E/415.30s** ⇒ 只认 `FAILED` 名集合差：**1 枚**，两棵树单跑都红 | `QODER_RESULT.md` §1 |

三条量具教训（都红在我这边，不对产品负责的部分见 `SLICE1_UI_PORT_SEAM.md` §5）：PNG 摘要必须互异、
`filter({ has: [data-state="fresh"] })` 是自我作废的定位器、spec 不在项目类型闸里（补了一行 `tsc` 并做了反向对照）。

## 11. 切片2 落地：从文本导入地点（2026-10-15 00:30，尖 `9a3b7ff0fb`，本片共 11 枚提交已入库）

细节与接缝推理在 `qoder_import/SLICE2_POI_IMPORT_SEAM.md`，数值在 `QODER_RESULT.md` §6。这里只记对**本文件口径**有影响的部分：

| 尺 | 数 | 复跑 |
|---|---|---|
| 后端 | `poi_import.py` 244 行纯函数 + 两扇门（`main.py:27714` parse / `:27795` add）+ 6 枚契约（`schemas.py:1690` 起）；`main.py +251/−0`、`schemas.py +67/−0` ⇒ **纯插入** | `pytest -q tests/test_qoder_ord0437_poi_import.py` ⇒ **9 passed / RC=0**（本趟 2.63s；耗时每趟会变，计数不会） |
| 前端 | 面板 **837** 行 + 私有词表 426 行 + 候选卡 131 行 + css 87 行；其中**三枚逐字相同**（`diff` 0 行），面板只有 `travelerId` 那一处改动 | `npx tsc -p tsconfig.check.json --noEmit` 等三枚 **各 0 错误行** |
| app 词典 | **9 枚 `poiImport.card*` + 1 枚 `nav.import`**（两语各 10 行），分 4 枚「一杖最多三枚键」的词典枝提交。源树另有 4 枚（`favoriteNotWired`/`newJourney`/`newJourneyNotWired`/`readBackError`）**在源树自己没有读者**（实测 grep 命中 0）⇒ 不搬 | `_slice2_dict_closure_r2.py` ⇒ `WANTED_KEYS 9 / MISSING_KEY_COUNT 0 / PRESENT_KEYS 822`；玻璃上实测 **7 枚**（`ARM_FILE_CARD_KEYS_PROVEN_ON_GLASS 7`、`…_DOOR_ONLY 2`） |
| 依赖闭包 | 13 枚节点，融合树缺文件 **0**，与源树不同 **7**（都是本树已有的共享件：collections 两件、`LocaleContext`、`errorReceipt`、`plural`、`rejectionFacts`、面板自身） | `_slice2_closure_r1.py` |
| 活口 | 权威栈 **7 passed / 28.1s**（`slice2r5`，存档那趟），另两趟独立新库 `slice2r2` 7 passed / 32.1s、`slice2r3` 7 passed / 28.3s；红面留在名单里：`slice2r1` 2 failed / 5 passed、`slice2r4` 1 failed / 6 passed。走查从 7 屏变 **8 屏 / 8 枚互异摘要** | `bash _run_e2e_slice2_r1.sh <RUN_ID>` |
| 回归 | 同一尖跑**两趟**：`SAME_TIP_SAMPLES_FLIPPED 2`、`RED_ONLY_IN_SLICE2_STABLE_IN_BOTH_SAMPLES 0`（单趟那枚 `RED_ONLY_IN_SLICE2 1` 在第二趟翻回绿，另有一枚绿翻红）；47 枚自有测试在三趟整套里 0 红。r44 那枚固定演示行程上的 `AgentRun` 计数：两棵树单跑各 **3 passed**，且**各重复 20 趟 0 红**（我的 POI 文件同地板 `0 / 20`）；把它与我的文件塞进**同一进程**连跑累计 **53 趟 1 趟红**，那趟没留日志 ⇒ 按未结记，不写成「我的文件不踩别人」 | `python _slice2_failed_nameset_r1.py`（自带 reader 自检，且现在读两枚样本）、`SOLO_REPEAT_*` / `POI_THEN_R44_*` |
| 落地面 | `git merge-base --is-ancestor 594f9a4e75 HEAD` ⇒ **YES**（不是入账工 12:53 通播里那种「不相交」）；codex 车道枝超基线 **0** 枚；远端三枚 fusion 尖现读全部 `594f9a4e75` ⇒ **没推** | `_slice2_landed_r1.py` 的 `BASELINE_IS_ANCESTOR_OF_HEAD` / `CODEX_LANE_COMMITS_OVER_BASELINE` / `REMOTE_FUSION_TIPS_LIVE_LINES 3` |
| 产品代码面 | **27 文件 / +8086 / −32**（pathspec `backend/app backend/tests frontend/src`，不含 `frontend/e2e`）——**必须在提交之后取**；上一版在未跟踪状态取到 21/+6092，少算 6 枚新文件 | `git diff --stat 594f9a4e75 -- backend/app backend/tests frontend/src` |

三条**必须带走**的口径结论：

1. **`GET /api/v1/places` 不是导入用的那份目录。** 读门带 `provider_key.notin_(_SERVER_OWNED_PLACE_PROVIDERS)`（`main.py:16206`，元组 `:17901`），解析门只排结构类目（`main.py:27749`，注释在 `:27742` 自认这是故意的）。实测种子城 `CN-TIANJIN` 的 9 枚 `Place` 全带 `citynexus-v9-domain` ⇒ 读门对这座城 **0 行**。谁要写导入相关的测试，布景词汇不能从那扇读门取。
2. **`travelerId` 这条 prop 在本树没有门可用**，删它连带删掉一枚空态分支（见 `SLICE2_POI_IMPORT_SEAM.md` §3）。这是切片 1 那三处改动的第四条同款后果。
3. **`MISSING_EXPORT_COUNT 1`（`dictionaryText`）不是破口**：要它的是**源树**的 `errorReceipt.ts:20`，本树那枚文件没有任何 import，本树词典也不导出它。它记的是「源树那枚文件不能整枚盖过来」。
   **切片 3 已把这条读干净（03:20 现读，绝对路径逐树数，不再用一条 `cd` 后的相对 grep）**：`dictionaryText` 在
   源树 `frontend/src` 命中 **30** 处、在融合尖与融合基线各命中 **0** 处（`i18n/LocaleContext.tsx` 也不导出它）。
   ⇒ 日历这一片**没用到它**（本尖 `features/trip/` 与 `lib/` 命中 0），所以它不是切片 3 的依赖；
   仍是切片 4 的口径：**源树的组件 import 面比融合树的导出面宽**，整枚文件盖过来会红在收集期。
   **顺带记一枚我这轮的量具错**：第一次核这条时我在同一条命令里 `cd` 到源树后又用相对路径读「融合树」，
   于是同一枚 30 被打印了两遍、看着像两棵树相同。凡是「两棵树对拍」的数，每条腿必须自带绝对路径。

## 12. 切片 3 落地：日历 `.ics` 导出（2026-10-15 03:25，尖 `41fbb9c731`，本片 6 枚提交、3 枚只动词典）

细节在 `qoder_import/SLICE3_CALENDAR_EXPORT_SEAM.md`，逐条数值在 `QODER_RESULT.md` §8。这里只记对**本文件口径**有影响的部分。
**切片 3 起，被引用的量具全在仓库里**：`review/ord0496/slice3_gates_r1.py`（一条命令打全 §0/§1 的数）、
`glass_can_go_red_r1.py`（三枚玻璃反向对照）、`xproc_floor_r1.py`（别人那枚闸的空白对照）——不再出现「裸文件名不带目录」的引用。

| 尺 | 数 | 复跑 |
|---|---|---|
| 后端 | `backend/app/calendar_export.py` **351 行、与源树逐字节相同**（纯函数、零内部依赖）；门 `@app.get("/api/v1/journeys/{journey_id}/calendar.ics")` 落在 `main.py:27391`，本片 `main.py +228 / −0` ⇒ **纯插入**；源树那三枚 helper 不是整枚盖过来：`_calendar_journey` **重建**、`_calendar_activities` 与 `get_journey_calendar` **逐字搬 + 加一枚参数**，出处自记在 `main.py:27250-27253` | `pytest -q backend/tests/test_qoder_ord0496_calendar_export.py` ⇒ **17 passed / 2.52s** |
| 鉴权口径 | 源树那扇门**匿名可读**（谁点到都能拿走别人的整份日历）；按 §3「移植必须升级」改成只认签名令牌，并且**不接受 `?traveler_id=` 点名**（`_calendar_scope_param` 在 `main.py:27296` 就是为拒这一次而存在） | 活口两腿：带凭据 ⇒ 下载 **1** 枚；无凭据 ⇒ **401 且下载 0 枚** |
| 前端 | 行程面板默认子页挂导出按钮（`TripItinerary.tsx +42/−1`，`--numstat` 现读）+ 客户端 `calendarExport.ts` **160 行**。**没有新 Tab、没有新路由** ⇒ §1 那四层判据在这条上必然读成「注册表 0 / 路由 0」，入口形状不同（见 §1 计数更正第 1 条） | 三枚 `tsc` 闸 **各 0 错误行** |
| app 词典 | **9 枚 `calendar.*`**（两语各 9 行 = 18 行），分 **3 枝**「一杖最多三枚键」提交（3,3,3）。全枝审计 `DICTIONARY_BRANCH_COMMITS 8 / KEYS_ADDED_TOTAL 20 / OVER_3_KEYS 0`，逐枝 3,3,3,3,3,3,1,1 | `python review/ord0496/slice3_gates_r1.py`；反向对照 `--run-control dictclass`（进程内换字符类 ⇒ 总数 20→18、自检 BROKEN、rc=1，**不落盘**） |
| 玻璃 390×844 | **真按一次 ⇒ 浏览器收下文件**：`2879 B`、**9 枚 VEVENT**、`DTSTART/DTEND/UID/DTSTAMP` 各 9、**88 对 CRLF**、裸 LF **0**、超 75 octet 的行 **0**、最长行 **75**；文件名带行程自己的标题。存档 `reports/qoder-ord0496-calendar/`（manifest 自带 `run` 与 `grammar`） | `python review/ord0496/glass_can_go_red_r1.py` ⇒ BASELINE `rc=0 / 2 passed`；三枚对照各 `rc=1` ⇒ `CONTROLS_RAN=3 CONTROLS_THAT_BIT=3`；被改文件逐字节修回 |
| 回归 | 同根**每尖两趟**共四趟：切片 2 尖 `155/2065/7`、`155/2065/7`；本尖 `156/2081/7`、`155/2082/7`。差集 `RED_IN_BOTH_SLICE3_AND_IN_NEITHER_SLICE2_SAMPLE **0**`，`SAME_TIP_SAMPLES_FLIPPED 1`；唯一那枚在两趟都红的 `g3_xproc` 经空白对照判定**与本尖无关**（臂文件两树同 sha `07fdf6c97187a6dd`、基线 **2/16** 红反而多于本尖 **1/16**） | `python review/ord0496/slice3_gates_r1.py` 的 `SAMPLE`/`MEMBERSHIP_TABLE`；`python review/ord0496/xproc_floor_r1.py --repeat 8` |
| 契约面 | **0 处**：`contracts/openapi.yaml`（167236 B）与 `frontend/src/generated/api.ts`（265557 B）各 grep `calendar\|\.ics\|vevent` 命中 **0**（两枚文件都在，命中为零——与 §11 第 3 条同一条规矩） | `grep -c -i -E 'calendar\|\.ics\|vevent' <file>`，先 `test -f` 再数 |
| 产品代码面 | 本片 **6 文件 / +1988 / −1**（pathspec `backend/app backend/tests frontend/src`，提交之后取）；整条分支到本尖 **30 文件 / +10074 / −33**，含证据件 **61 / +12506 / −41** | `git diff --stat f9abba3fde..HEAD -- backend/app backend/tests frontend/src`；`git diff --stat 594f9a4e75..HEAD …` |

三条**必须带走**的口径结论：

1. **入口有两种形状，parity 的四层判据只认第一种。** 日历这条是「面板内按钮」：注册表 0、路由 0、词典 20 行、含 `calendar` 的文件 10 枚。
   谁继续用 §1 那张尺判切片 4，会把「已接通」判成「没入口」。
2. **`abort` 这枚 token 会骗人**：融合树 13 枚文件命中，全是 `AbortError`/`AbortController`；精确 `journey-abort`/`abortJourney` **0**。
   源树两处都在（`v8PanelRegistry.tsx:450`、`features/abort/` 四枚文件）。
3. **切片 3b（abort）不是「1 路由」那么小**：`v8PanelRegistry.tsx:445-447` 自认「面板读服务器的 `live_view`，绝不从 `status` 自己推状态」，
   而 `live_view` 在两棵融合树命中 **0**（源树 `main.py` 5 处 / `services.py` 2 处 / `class JourneyLiveView` 1 枚 / `schema.sql` 两列）。
   ⇒ 只搬路由会搬出一枚说谎的按钮；前端闭包另需 `features/abort/` **4 枚文件**，其中 3 枚依赖文件两树不同（`CnxMeasuredFacts` 2839 vs 4676、`v8Types` 6721 vs 7938、`LocaleContext` 113918 vs 202499）。
   **共享词典键需求 0 枚**（源树句子在自家 `journeyAbortCopy.ts`）⇒ 「一杖三枚键」那条在这里不触发。
