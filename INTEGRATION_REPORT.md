# CityNexus — 前端 A/B 整合 + 真种子 + 视觉验收（Qoder 集成线，2026-09-19）

按裁决顺序执行：`authoritative baseline` → `v6 truth integration` → `以 truth-integrated commit 建
frontend/apple-pass1-visual-integration` → `A/B 人工 reconcile` → `真种子 + 可读截图`。
全部在 `D:\moodle\_qoder_integration_20260919`（主仓的 git clone），**主仓工作树与 HEAD 未被改动**，
运行中的 `:8000` / `:8011` 后端未被打断。

## 1. 提交链（可复核）

| commit | 内容 |
|---|---|
| `380e6ff` | `chore(baseline)`：把主仓现状冻结为权威基线（6542 文件；`backend/app`、`backend/tests`、`data`、`frontend/src`、`frontend/e2e`、docs、contracts、evals）。主仓此前只有 5 个 9/5 的文档提交，**全部源码 untracked**。用 `commit-tree` 建立，不移动 HEAD、不改文件。 |
| `b12f24f` | `feat(truth)`：v6 truth hardening 落地。 |
| `e330ac2` | `feat(frontend)` A 组：Apple 视觉 / IA。 |
| `a2124c0` | `fix(frontend)` B 组：前置类型 / 行为修复。 |
| `cfb2b4a` | `test(frontend)`：真种子 setup project + 双主题对比度门，以及它暴露的浅色 AA 缺陷。 |

## 2. 基线冻结的可复现性

- 树 `2d01138d…`，6542 个文件，62.9 MB；`*.zip` / `node_modules` / `dist` / `.venv` / `*.db` /
  `storybook-static` / `_*/` 暂存目录被排除，只留源码、种子与证据报告。
- 主仓部分源码是 CRLF，副本是 LF；比较一律按 EOL 归一后进行，commit message 里写明。
- 主仓 `backend/app`、`frontend/src` 自隔离副本建立（9/18 15:02）后**无任何源码漂移**（0 个更新文件），
  所以副本与主仓可互换作参照。

## 3. v6 truth integration：主仓基线上复跑

先做等价性核验：隔离副本基线 `c6f9024` 的 40 个非文档源码文件与主仓磁盘内容 **0 处不一致**
（EOL 归一后），因此整合不是"重新推导"，而是逐 blob 搬运 GPT 已验收的状态。

同一环境（清 `DEEPSEEK_API_KEY` / `CITYNEXUS_AI_API_KEY`，`CITYNEXUS_AI_ENABLED=false`，
`CITYNEXUS_DATABASE_URL` 指向独立文件）：

| 树 | 结果 |
|---|---|
| `380e6ff` 基线 | 762 passed / 15 skipped / **0 failed**（49.4s） |
| `b12f24f` +v6 | 827 passed / 15 skipped / **0 failed**（50.9s） |

NEW-vs-baseline = ∅，且新增 65 条 truth 测试全绿。注意：这比隔离副本记录的
`2 failed(aiv3_02, v18_3)` 更好——那两条只在 AI key 存在时失败（副本的 blocker 4 正是为此而设）。

## 4. A/B reconcile（裁决要求的拆分）

`iso/master..qoder-frontend` 的 20 个文件按裁决拆成 A(9) + B(11)，两块都能 3-way 干净落到
truth-integrated 树上，**没有降级任何主线代码**：

- A：`design-tokens.css`、`V8Experience.tsx`、`LiveRecovery.tsx`、4 个 `qoder-*` 门 + 2 个共享 helper。
  `V8Experience.tsx` / `LiveRecovery.tsx` 是 truth 线与 Apple 线都碰过的文件，用 3-way（base = 副本
  `master`）合并，两条线的改动同时保留。
- B：`main.tsx`、`v10Execution.ts`、`v8Types.ts`、`MapPanel.tsx`、`AgentComposer.tsx`、
  `PlanComparison.tsx`、`PushCapabilityCard.tsx`、`SortableActivityList.tsx`、V12 story、
  `package.json`、`tsconfig.typecheck.json`。
  逐项核对当前版本：`v8Types.ts` 在本仓是 CRLF，直接取 Apple 分支的 LF 副本会让 diff 变成
  46 行重写（并可能悄悄覆盖主线），因此改为**就地插入两个字段**，净 diff 只有 2 行。
  B 组净效果：11 文件 +35 / −17。

整合树门禁：`typecheck:all` 0 错、`vite build` 通过、28 条 `qoder-*` 门全绿。

## 5. 真种子环境（裁决要求的第 0 步）

新增 `frontend/e2e/_qoderRealSeed.setup.ts`（Playwright setup project，跑在 config 自己起的
webServer 之后；`globalSetup` 不行，那时端口还没监听）。它只走产品公开面：

```
POST /api/v1/demo/reset
POST /inbox/import + /inbox/{id}/confirm  ×3（ARRIVAL / MID_TRIP / DEPARTURE）
/v8/discover → 真实城市发现（sealed replay）→ SELECTED plan version
localStorage["citynexus.v8.journey_id"] → 持久化成 storageState 供全部用例复用
```

无 SQL 写入、无 `route.fulfill` 假路由。日志会打印 `selectedPlan=PLAN VERSION SELECTED v1 · <uuid>`。

端口改为 env 可覆盖（`CITYNEXUS_E2E_PORT` / `CITYNEXUS_BACKEND_PORT`），默认值不变，
这样集成环境不必占用主仓的 `:8000`。

### 15 条 legacy 的重新分类（这次是在真种子上跑出来的）

| 类别 | 数量 | 证据 |
|---|---|---|
| **旧 `/` Journey Mode 界面已被 V8 shell 取代** | 8 | `golden`、`live-autopilot-v5`、`predictive-real-city-v6`、`product-hardening`×5。全部死在同一处：`getByTestId('journey-status')` 不存在。axe 的页面快照显示访问 `/` 渲染的是 V8 shell（Today / Live Journey / Map / Trip Studio 导航）。这是**规格过期**，不是缺种子、也不是 A/B 回归。 |
| **V8 界面文案 / DOM 漂移** | 4 | `product-v8`×2（期望 heading `Your next city, already considered.`、导航按钮 `AI`）、`v10-live-execution`（期望 `read-only ready`）、`real-world-trip-operations-v9`（`locator.fill` 超时）。 |
| **真种子后恢复通过** | 3 | `v10-inbox`、`v10-quality-budget`、`v13-5-fully-grounded` 等——此前只因缺种子失败。 |

对照实验（同一份种子，10 个 spec 文件）：

| 树 | legacy 结果 |
|---|---|
| `b12f24f` truth-only（无 A/B） | 12 failed / 3 passed |
| `a2124c0` +A+B | 13 failed / 2 passed |

差的那 1 条是 `v10-accessibility`：**Apple 线造成的真实回归**（见下）。除此之外 A/B 零新增失败。
全量套件：无种子 30 passed / 15 failed → 有种子 **34 passed / 12 failed**。

## 6. 视觉阶段抓到的两个真缺陷

### 6.1 axe 的 AA 失败 = Apple 线引入（已修）

`v10-accessibility` 在整合后失败，axe 给出精确数据：

```
color-contrast  serious  fg #0a66ff  bg #f5f5f7  4.42:1  (10px bold uppercase)
expected 4.5:1   <p class="v8-kicker">Live Journey · saved 19 Sept, 13:43</p>
```

根因：Apple 调色板把 `--v8-indigo` 从 `#4658d9`（5.74:1）重绑为 `--cn-accent #0a66ff`。
作为链接色没问题，作为 10px 文本就跌破 AA。**深色门抓不到它，因为门只 emulate 了 dark。**

把门改成双主题后，浅色主题一次性暴露 15–48 条/屏（扫描器还先把"未 token 化的近白面"在浅色下
误判成违规——那一层按定义只属于深色，已在 `_qoderContrastScan.ts` 里按 scheme 关闭）。
逐条修完后 dark 0 / light 0：

| 缺陷 | 处理 |
|---|---|
| `.v8-kicker` 4.42:1（Apple 重绑引入） | 新增 `--cn-accent-text #0a5cd6`（画布 5.49 / 白 5.97） |
| `.cn-hero-label` 3.33:1（Apple 新类用了 tertiary 墨色） | 改 `--cn-ink-secondary`（4.66） |
| "All clear" 4.04:1（Apple 的 attention clear 态） | 新增 `--cn-success-text`（light `#17672f` / dark `#30d158`） |
| outline 按钮边框 1.2:1（既有硬编码 `#d9ddea`，dark 侧早已修、light 侧漏了） | 浅色 `--cn-control-border` 提到 `#7d8797`（3.63 / 3.33） |
| 侧栏 tagline / nav group / nav button / breadcrumb `/` / sync 副文本 / mode chip 边框 | 统一取 token，2.4–3.9:1 → AA |

### 6.2 截图才能看见的问题（未擅自修，交裁决）

`reports/visual-integration/` 有 32 张可读 PNG（Today + Live × 360/412/430/desktop × light/dark，
各含首屏与整页）。全部 0 横向溢出。肉眼审查结论：

1. **Today 的语言切换渲染了两次**：顶栏一个小 `EN`，hero 下方一个**全宽超大** `EN`
   （DOM 里就是 `topbar-language` 与 `home-language` 两个 testid）。第二个在首屏抢焦点。
2. **Today hero 在真实数据下 CTA 泛滥**：`试用其他城市` / `AI 帮我规划` / `打开行程工作台` /
   `查看实时行程` 四个按钮 + 两个语言键。`qoder-today-hero` 的"≤1 primary CTA"门只在**空/预旅行分支**
   触发，正是裁决当初点名的"positive branch 需真种子才能验证"——现在验证了，**不成立**。
3. **Live 首屏被两个 secondary 动作占住**：`更新位置`、`报告降雨` 以全宽同权重压在
   `现在 Old Town Gate` 之上，Current 不再是第一眼。
4. **地图诚实空态过高**：约 400px 的"尚未获取地图位置"块把"当前没有需要你决定的调整"推到折叠线下。
5. **Copilot dock 与底部内容重叠**：`下一段路程方式` 面板只露出一行就被 dock 压住，文字被裁。
6. **头像文字溢出**：右上角蓝色 avatar 里的 `DE` 压在圆外（light 图里是 `D` 被裁）。
7. **文案粘连 / 未本地化**：`每人每天约 ¥500这是按你的预算平均下来的参考值`（缺分隔）；
   `下一步 · Riverside Museum · transit · 时长待定`（`transit` 未译）。

这些属于产品 IA / DOM 决策（哪个语言键该留、哪个 CTA 是 primary），不在"reconcile 不降级"的授权内，
因此只记录不动手。

### 6.3 Live 关键状态截图（`reports/visual-integration/states/`）

L0–L4 只有 `qoder-live-structure.spec.ts` 的 route fixture 能构造（真种子 journey 没有开着的
disruption），所以给该 spec 加了一个默认关闭的 `QODER_CAPTURE_STATES=1` 截图出口
（断言未改，捕获后把配色恢复成进入前的主题）。产出 L1/L2/L3 × light/dark。

`L2-proposal-ready-light.png` 是这批里最要紧的一张：**"方案 A · 推荐怎么改" 提案卡被 Copilot dock
压在下面，只露出标题，Accept CTA 不在首屏**。也就是说第 (e) 项不是"边缘文字被裁"的装饰问题，
而是**决策态下主操作被遮挡**；配合第 (d) 项（地图空态约 400px），真正需要用户点的那一下
被推到了折叠线以下。这条门的断言（Accept 唯一、disruption 进入首屏）仍然通过，
因为它量的是 bounding rect 与"Copilot 不与 Accept 相交"，而截图显示的是**视觉层叠与首屏优先级**——
两者不是一回事，这正是肉眼阶段存在的理由。

补看 L1 与 dark 两张后，可以把结论收紧成三条跨状态、跨主题的规律：

1. **Copilot dock 遮挡内容态是常态，不是 L2 偶发**：L1 里"选择下段交通"被裁掉半行，
   L2 里提案卡只剩标题，light / dark 一致。
2. **头像文字溢出跨主题**：light 显示成被裁的 `D`，dark 显示成压在圆外的 `XI`——
   是 avatar 尺寸与内容宽度的固定冲突，不是配色问题。
3. **地图诚实空态在两主题下都是首屏最大的一块**（light 是浅灰绿、dark 是纯黑空洞），
   它把"现在/接下来/需要你决定"三件事整体下移；dark 侧的观感问题不是发灰发亮，而是**空**。

这三条都不需要改真值逻辑，属于布局与层叠决策，因此仍归"待裁决"，不擅自动手。

## 7. 请给的裁决

- A/B 整合是否接受（`FRONTEND_APPLE_PASS1_INTEGRATED_ON_TRUTH_BASELINE`？）；
- 6.1 的浅色 AA 修复与双主题门是否作为这条线的正式延续收下；
- 6.2 的 7 项视觉缺陷：哪些进入 Apple 线下一轮，哪些归主线（语言键重复、Copilot 遮挡、头像溢出
  看起来是主线既有 DOM）；
- 那 8 条 `/` 旧界面 legacy：迁移到 V8 shell 断言，还是标记为过期归档。

## 8. "A 能不能单独并"——实测答案：不能

裁决建议 A 优先保留、B 逐项 reconcile，隐含"A 至少可以先走"。用三个 worktree 在**同一份
`tsconfig.check.json`** 下实测：

| 树 | 类型错误数 |
|---|---|
| `b12f24f` truth-only 基线 | **17** |
| 基线 + 只并 A（`e330ac2` 的内容） | **14** |
| 基线 + A + B（`a2124c0`） | **0** |

读法：

- A 自己**不新增**任何类型错误，还顺带清掉 3 个（`V8Experience.tsx` / `LiveRecovery.tsx` 的改动本身是类型安全的）；
- 但 A 单独并进来仍然编不过，**B 是 A 的前置**，不是可选项；
- 更关键：B 里 `v8Types.ts` 新增的 `acknowledged` / `no_alternative` 两个字段，报错方是
  **truth 线自己的组件** `src/features/recovery/RecoveryRequiredPanel.tsx:45-46`。
  也就是说这两个字段属于主线编译前置，而不是 Apple 线的私货——逐项 reconcile B 时它们必须进，
  否则 authoritative 分支自己就红。

`vite build` 在 A-only 下能过（vite 不做类型检查），所以"能 build"不能作为 A 可独立合并的证据。

## 9. 那 8 条 `/` legacy：不是过期不可修，实测只差一行入口

旧界面没有被删除，它被**显式挪到 `/legacy`**（`src/main.tsx` 的 `App()`：默认入口渲染
`V8Experience`，`path.startsWith("/legacy")` 才渲染 `LegacyApp`，注释写明"legacy 仅供内部/向后兼容访问"）。

探针实验（临时把 `golden.spec.ts` 的 `page.goto("/")` 改成 `/legacy`，跑完已还原，未提交）：

| 断言 | 改前 | 改后 |
|---|---|---|
| `journey-status` 存在 | element(s) not found | 元素存在，`data-source="backend"` 已满足 |
| 状态文本 | — | 实际 `PLANNED · backend truth`，spec 期望 `ACTIVE` |

所以这 8 条的成本是：每条 1 行入口路径 + 把状态期望对齐当前后端真值（journey 在被选中 plan 之后是
`PLANNED`，不再是 `ACTIVE`）。**期望值不该为了变绿而改**，因此这里只交结论，不交改动——
需要 owner/裁决确认"PLANNED 是否就是今天该断言的真值"。

（同一探针还顺带说明：真种子 harness 与 legacy 界面是兼容的，`data-journey-id` 正是种子建出来的
`22222222-…` journey。）

## 10. pass-8 裁决后的收口（证据卫生三项）

裁决接受 `FRONTEND_APPLE_PASS1_AB_RECONCILED_ON_TRUTH_V6_BASELINE` 与
`INTEGRATION_TRUTH_GATES_PASS`，并把视觉阶段记为
`FRONTEND_APPLE_PASS1_VISUAL_INTEGRATION_BLOCKED`。他点的三个证据卫生问题都补了：

1. **门改名**：`qoder-dark-audit.spec.ts` → `qoder-contrast-audit.spec.ts`，describe/test 标题、
   报告目录 `reports/contrast-audit/`、文件名 `contrast-audit-*.json` 全部跟上；
   `summarise()` 里那个把 light 行打成 `(dark)` 的标签删了。
   顺手把 focus-ring 那半条门也真的从"只量 dark"改成 dark+light 都走——
   名字改成两主题而实现仍只测 dark，就是他批评的那种"标签撒小谎"。
   **这一改立刻抓到 4 条 light 违规**：`.v8-product-shell button:focus-visible` 的
   `outline: 3px solid #9aa8ff` 在 #f5f5f7 上只有 2.05–2.23:1（要求 3:1）。
   修法是让 outline-color 走 `--cn-accent-text`（画布 5.49:1 / dark 5.76:1）；
   第一次覆盖没生效，因为赢下 specificity 的是 `button:focus-visible` 而不是
   `:focus-visible`——补上该选择器后 8 组对比度 + 双主题 focus 全 0。
2. **truth_baseline.log**：v1 包 README 声称有、实际没打进 zip，所以基线对照无法独立复算。
   v2 包已包含 `truth_baseline.log`（762/0）与 `truth_patched.log`（827/0），
   README 清单与 zip 内容逐条核对一致。
3. **MapPanel 的行为 delta**：`failIfMajorPerformanceCaveat: false` 连同解释它的注释
   （"瓦片服务不可达时别让用户对着空盒子看，受限网络很常见"）被 Apple 分支的 GeoJSON
   typing 修复一起删掉了。maplibre 自身默认确实是 false，行为可能等效，但这条注释承载的是
   产品意图，不该藏进"前置类型修复"四个字里 —— 已把该行与注释恢复回源码，
   并在此处明列为 reconciliation delta。

## 11. 下一轮范围（照裁决，不扩面）

Apple 线只做 #1 重复语言入口、#2 Today CTA 层级（有 active journey 时唯一 primary 是
"查看实时行程"，"AI 帮我规划"降级、"试用其他城市"归创建路径、"打开行程工作台"降 tertiary）、
#3 Live 次级动作层级（Current → Map → Disruption/Replan → 更新位置·报告降雨 → mode/evidence）、
#4 地图诚实空态高度；主线做 #5 Copilot 遮挡（统一 bottom clearance）、#6 avatar 溢出、#7 文案粘连与
`transit` 未本地化；测试债做 8 条 legacy 的 capability mapping 与 4 条当前 V8 规格重写。
Trips / Copilot 主页面 / Onboarding 继续不碰。

---

# pass-9 收口（按裁决范围，不扩面）

## 12. Apple P0 四项

| # | 裁决 | 落地 |
|---|---|---|
| 1 | Today 重复语言入口 | 删掉 hero 区的 `home-language`（topbar 已拥有该控件，全仓无其它引用）。 |
| 2 | Today 唯一 primary | `AI 帮我规划 / 试用其他城市 / 打开行程工作台` 从四个堆叠全宽按钮变成一行 quiet 文本动作（`.v8-hub-actions` 此前**在仓库里根本没有 CSS 规则**，这就是它们渲染成"按钮联合国大会"的直接原因）。门同步升级：旧断言只数 hero **内部**的 primary，所以紧贴其上的全宽 `.v8-primary` 门是看不见的；现在要求整屏可见 primary ≤1 且必须是 `today-hero-cta`。**非空过已证明**：把 `hub-plan-with-ai` 改回 `.v8-primary` 立刻 FAIL 并点名两个按钮。 |
| 3 | Live 次级动作层级 | `更新位置 / 报告降雨` 移出 Live intro，落到 Disruption/Replan 之后的 compact 行，顺序成为 Current → Map → Disruption/Replan → utilities → mode/evidence。 |
| 4 | 地图诚实空态高度 | 第一次修完全无效：Apple 的 240/208 规则带 `!important`，而 CSS 里 **min-height 优先于 max-height**，盒子仍是 240px。在同一 register 里豁免后 97px，Live 地图带从 2065px 页高压到 228px。 |

门侧诚实化：`qoder-live-structure` 现在打印它量的是哪个分支
（`[live-map] branch=honest-empty-state height=97px`）。曾尝试给 mock 加坐标去真正验证 240/208
分支，结果 maplibre 开始拉 style/tiles，离线 harness 直接挂起、dark 审计还把地图 canvas 算成违规 ——
已回退并写明"该分支需要联网环境"，而不是留一条时隐时现的绿灯。

## 13. 主线三项（单独提交，归属清楚）

- **#5 Copilot 遮挡**：`.v8-content` 统一预留 `124px + safe-area` 底部带；决策态 dock 收成右对齐 pill
  （原来 yield 后仍是 230px 宽横条，正好盖住全宽 Accept）。注意第一版把留白加在 `.v8-page` 上，
  而 Today/Live 会连续渲染多个 `.v8-page`，每个都加 124px，把决策块推下去 124px —— 首屏门以 8px
  之差抓到。门侧同时把"是否遮挡"改为在**决策被滚到视口中央**时测量：`scrollIntoViewIfNeeded`
  会把按钮留在视口底边，而那正是 pill 所在的位置，旧断言其实是在赌滚动位置而不是在设计保证。
- **#6 avatar 溢出**：加 `overflow/nowrap/flex:none`，两字符不再压在圆外。
- **#7 文案与本地化**：advisory 的 text 与 hint 由 inline 相邻改为块级（消除
  `每人每天约 ¥500这是按你的预算…`）；Live 的 leg 行原本把 provider 枚举原样插进中文句子
  （`transit`），现在走 `modeLabel()`，与全站其它 mode 呈现一致。

## 14. 种子升级：从"能跑"到"跑的是真东西"

`demo/reset` 给的是一天 CNX-DEMO 行程，stay-aware optimizer 返回 **0 个 option**。这个事实悄悄污染了
之前所有在它上面得出的判断：Stay Explorer 只能显示空态、恢复链没有可保护的住宿、Today 只有一天
时间线、地图永远没有 marker。种子改为通过产品 API 建两晚 CN-TIANJIN 行程并真实 generate + select：
`options=4 chosen=… (Haihe Riverside Hotel)`、`trialWizard=false`、`live-journey-current=true`，
地图第一次渲染出真 marker。

它立刻抓到三个此前不可见的缺陷：

1. Today 在真实 disruption 下出现**第二个 primary**（attention band 的 `Review in Live`，与 hero 同目标）
   —— 裁决 #2 的第二个实例，已降级。
2. `current` 地图 marker 白字 10px on `#d65e56` = **3.75:1**。改用 `--cn-accent-solid`（两主题都是
   `#0a66ff`，白字 4.82:1）；第一版用 `--cn-accent-text`，在 dark 下 `#0a84ff` 只有 3.49:1，
   双主题门当场拦下。
3. 多日时间线的 `DAY n` 与副文本灰（`#9aa4b3` 2.52、`#6c7889` 4.48/3.8）此前从未被审计到，
   因为根本没有多日卡片。统一到 `--cn-ink-secondary`。

## 15. 门禁与套件现状

- `qoder-*` 29 条全绿；contrast 在 Today/Live × light/dark × 390/1280 **全部 0**，
  focus ring 也改成两主题都量（改名 `qoder-contrast-audit` 后立刻发现 light 下 4 条
  `button:focus-visible` 的 `#9aa8ff` outline 只有 2.05–2.23:1）。
- 全量 Playwright：31 passed / 15 failed。其中 8 条是已定性的 `/` legacy（见
  `docs/LEGACY_E2E_MIGRATION.md`），4 条当前产品 spec 已按现状重写（locale 固定、
  `hub.title`→`today-heading`、`AI`→`Copilot`、`read-only ready`→`available offline`、
  硬编码 4 张 offer 卡改为记录分支、AgentComposer testid→Copilot dock）。
- **新发现的测试基建缺陷**：`v10-inbox / v10-quality-budget / v10-accessibility` 固定 locale 后
  单跑 9 秒 4 passed，放进串行全量又红 —— 因为整套共用一个后端与一个 SQLite journey，
  前面的 spec 会 reset / 重新 select。没有靠调整顺序掩盖，作为独立缺陷记录。

## 16. 截图里仍然看得见、但我没有动手的

1. 真地图渲染后，地图左半约 40% 是未加载瓦片的浅灰底（右侧天津城区正常）—— 视觉上不平衡，
   但属于瓦片可用性/地图视野问题，不是配色。
2. 5 号 marker 被"路线上下文 · 8 段路程"信息条压掉一半。
3. dock 在 Today 首屏仍会压住 hero 之后的内容（已预留底部带，滚动后可完全避开；
   是否要在首屏就完全让位属于产品取舍）。

请复验这三条的归属，以及 pass-9 的四项 P0 是否达到
`FRONTEND_APPLE_PASS1_VISUALLY_ACCEPTED_FOR_MERGE`。

## 17. 我自己在收尾期间造成并已修复的事故（如实记录）

清理两个临时对照 worktree 时用了 `git worktree remove --force`，而它们的
`node_modules` 是我先前用 **Windows junction** 指向集成树
`_qoder_integration_20260919/frontend/node_modules` 的。删除过程把集成树的
`node_modules/.bin` 一起抽走（375M / 389 项，`tsc` 与 `vite` 消失，`npx tsc`
开始去下载一个叫 `tsc@2.0.3` 的无关假包）。

处置：从 `D:\moodle\_qoder_th_20260918\frontend\node_modules` 用
`robocopy /E /XO` 补齐回 409M，并在同一 HEAD（`7870270`，工作树 0 行改动）上重跑：

| 检查 | 结果 |
|---|---|
| `tsc -p tsconfig.typecheck.json --noEmit` | 0 错误 |
| `vite build` | 通过（7.16s） |
| `npx playwright test e2e/qoder-*` | 29 passed |
| 后端全量（同环境、独立 DB） | 827 passed / 15 skipped / 0 failed（68.5s） |

教训与遗留：

- **junction 不能当 worktree 的 `node_modules` 来源**；要隔离就得真复制。
- 两个残留空壳目录（`_qoder_a_only`、`_qoder_truth_baseline`）已安全清掉：先用
  `os.rmdir` 删除 reparse point 本身（它不跟随链接），确认两个真实
  `node_modules` 仍是 409M / 399 项之后，才 `shutil.rmtree` 删壳目录。
  直接 `rm -rf` 会顺着 junction 再咬一口，这一步不能省序。
- 其它 lane（Astra / Sol）被裁决为把我的树当只读输入，所以这条恢复记录也写给它们：
  当前 HEAD 的工具链与门禁状态是完好的，上面四项可复现。

---

# pass-10 极窄 closeout（按 pass-9 裁决的五条，不扩面）

## 18. 四条 blocker 的结果

| blocker | 裁决要求 | 落地 | 证据 |
|---|---|---|---|
| 1 marker 被 route-context 压住 | 不许 z-index 互相霸凌；要让地图知道 overlay 占了空间 | fitBounds 的 padding 从统一 42 改为实测 caption 高度 + 16px 安全间隙（只加大 bottom） | live-412x915-light.png：5 号 marker 完整可见，未被信息条截断 |
| 2 Today 大 dock 压内容 | idle -> compact pill；active conversation / meaningful task -> expanded dock | CopilotDock 新增 idleCompact = !open && !sending && !yieldToSurface，复用决策态已验证够用的 pill 形态（暴露 data-idle-compact 供断言） | 同批截图里 dock 已是右下角小胶囊；底部导航仍保留 Copilot 入口，不再双重邀请 |
| 3 半灰地图定性 | 等 style loaded + idle + 记录 tile 错误后再拍，据此分类 | capture-visual.mjs 加 tile 请求监听与静默等待（quiet 1.5s / 上限 20s），每屏输出 tiles/failed/settled/waited | 16/16 屏全部 settled 且地图完整 -> 之前那帧半灰是 harness 抢拍，属 evidence timing，结案。**但每屏仍有 6-12 个 tile.openstreetmap.org 请求失败**（本网络不可达），说明"瓦片源不可达时 canvas 留灰区"是真实产品韧性缺口，不是截图问题 |
| 4 E2E journey 隔离 | 每 spec 自建 journey / 自持 journey_id / 自设 localStorage；不许调顺序或 retry 掩盖 | 新增 e2e/_qoderFreshJourney.ts（只走公开 API，两晚 CN-TIANJIN），接入 v10-inbox、v10-accessibility、v10-quality-budget、product-v8 | 全量 31 passed / 15 failed -> 35 passed / 11 failed；恢复的正是"单跑绿、全量红"那四条 |

## 19. 还没消掉的跨 spec 污染（如实上报）

qoder-live-structure 的 map-height 门：单跑 7 秒 2 passed，放进全量就红。
所以 blocker 4 是显著缓解而非结案——整套仍共用一个 SQLite 文件，任何写状态的 spec
都是共享资源。裁决里提到的下一步（per-worker / per-suite 临时 DB）我没有做，因为它要改
harness 的启动方式，会波及 Codex Sol 与 Astra 两条 lane 的只读输入约定，应该由你决定
是否在这个时点动它。

## 20. 一条自我纠错

pass-9 里我提交过一个"让 Live 的『现在』标签不再折行"的 commit，它其实什么都没改：
存在性守卫写的是子串 `.v8-live-label {`，而这个子串已经出现在深色主题的
`.v8-product-shell .v8-live-label {` 里，于是脚本判定"规则已存在"直接跳过写入。
重拍截图时才发现标签仍然两行。现在换成不会误匹配的守卫，并确认单行。
这正是你反复警告的"安慰剂修复"那一类，区别是这次是门和截图抓住的，不是我抓住的。

## 21. 请判

1. Blocker 1/2/3 是否足以签发 FRONTEND_APPLE_PASS1_VISUALLY_ACCEPTED_FOR_MERGE。
2. 瓦片源不可达时的灰区：算产品韧性 blocker，还是算环境限制（本网络无法访问 OSM）。
3. Blocker 4 的部分完成（35/11，仍有一条跨 spec 污染）是否继续挡住
   INTEGRATION_CANDIDATE_READY_FOR_MAIN，以及是否授权我做 per-worker 临时 DB
   （它会改变 harness 启动方式，影响其它 lane 的只读输入约定）。
4. 你提的"最终 release candidate 前用干净 checkout + 自己的 lockfile npm ci 重建一次"
   我留到 integration freeze 执行，不在这轮占用视觉线收口。

---

# pass-11 integration evidence closeout

按裁决只做三件事，没有扩面。

## 22. ① map-height 的真相：不是数据库污染

你的判断方向对，而且实际比"旧断言没迁移"还多一层。同一个文件里两处矛盾 + 一处竞态：

- Phase 4 仍硬断言 238–242 / 200–216，而 Phase 2 已承认无可信坐标时走 honest empty state（≤156px）。
  同一 fixture，两条互相矛盾的规则，旧的输了。
- 门还在面板**切换中**读取。诊断输出直接自相矛盾：`branch=rendered-map height=208px`，
  而同一时刻页面上那个节点其实是 97px 的 empty 面板。

现在统一成一个 helper：先等 `[data-testid=v8-map-empty]` 或真地图 canvas 出现，再读，再按分支断言。
三个 Live 状态一致报告 `branch=honest-empty-state height=97px`，因为 mock fixture 本来就没有可信坐标。
240/208 的区间**保留写在代码里但没有可达路径**（需要真坐标 + 瓦片访问），没有偷偷删掉。

顺带按你的 evidence hygiene 纠正了 `capture-visual.mjs` 的注释：它等的不是 MapLibre style/idle，
而是"看起来像 tile 的请求 1.5 秒内不再新增"（20 秒上限），而且它根本拿不到 map 实例。
证据不变，描述不再越界。

## 23. ② HEAD 与数字对齐

`COMMITS.txt` 之前只到 `f34d50e`，而报告声明 `f5117f4`——包确实不能自证。
本轮重跑并把清单、报告、README、`fe_full_pass11.json` 全部对齐到**同一次运行**：

| 项 | 值 |
|---|---|
| HEAD | `dafe091`（pass-11 ① 之后） |
| 全量 Playwright | **35 expected / 11 unexpected / 0 flaky**（stats 块原样引用，306.3s） |
| `qoder-*` | 29 passed（含 branch-aware map 门 10 passed） |
| contrast | Today/Live × light/dark × 390/1280 全 0 |
| 后端同环境 | 827 passed / 15 skipped / 0 failed（基线 762 / 0） |

之前 34/12 与 35/11 的差别来自我引用了不同次运行，这是记账错误，不是产品差异，已按单次运行固定。

## 24. ③ 三条当前 spec 的定性：全是规格漂移，没有一条是共享状态

关键实验：把这三条**单独**跑（同一 HEAD，setup 种子相同），结果与全量一致地失败。

| spec | 首个失败点 | 单跑 | 全量 | 定性 |
|---|---|---|---|---|
| `product-v8` mobile composition | `getByTestId('v8-agent-submit')` 永不出现（60s timeout） | 失败 | 失败 | **规格漂移**：AgentComposer 那套控件已被 Copilot dock 取代，`v8-agent-submit` 在 src 里不存在。我上一轮只改了 `v8-agent-composer`→`v18-copilot-dock`，漏了 submit 这一步 |
| `real-world-trip-operations-v9` | `getByLabel('Reservation JSON')` 永不出现（60s timeout） | 失败 | 失败 | **规格漂移**：`bookings.reservationJson` 这个 i18n key 还在字典里，但已没有任何组件使用它，即 bookings 页的 JSON 粘贴入口在当前产品里不是这个形状 |
| `v10-live-execution` | heading `Choose your next leg.` not found | 失败 | 失败 | **规格漂移（待定位）**：`live.title` 的 en 值确实就是这句，所以问题不在文案，而在该 spec 没接入 per-spec journey（我没把它列进 pass-10 的四条），页面停在 setup 向导。属于 fixture 归属未完成，不是产品坏了 |

**因此按你设的门槛，测试基础设施改造不该授权**：没有任何一条呈现
"同一 HEAD、单跑稳定 PASS、全量稳定 FAIL" 的形态。`workers: 1` 下 per-worker DB
本来也无效，这一点你已指出。剩下的红灯是三条规格需要按当前产品重写，
其中 `v10-live-execution` 只需补上它自己的 journey 归属。

## 25. 请判

1. ①②③ 是否构成 `BLOCKED_ON_E2E_EVIDENCE_CLOSEOUT` 的解除条件，还是仍要求我先把这三条重写到绿。
2. `v10-live-execution` 我判断是"fixture 归属未完成"，是否直接按 pass-10 的方式接入 `_qoderFreshJourney` 即可。
3. `product-v8` 的 Copilot 提交步骤与 `v9` 的预订导入入口，需要按**当前**产品形状重写断言：
   这两处涉及"当前认可的行为是什么"，我不替你定，请你或负责人给出目标断言，或者授权我按现状调查后提出草案。

---

# pass-12（2026-09-19 19:0x，HEAD `2875aba`）

按裁决只做三条当前产品规格的迁移 + 文档纠正 + 门禁复跑，没有碰那 8 条 legacy。

## 26. 三条迁移的结果，以及每条"没有削弱断言"的证据

| spec | 迁移内容 | 保留/替换掉的断言 | 非空转证明 |
|---|---|---|---|
| `v10-live-execution` | 接入 `_qoderFreshJourney`（`createFreshJourney` + `useJourney`），文案对齐现行 `exec.readOnlyReady` | 时钟、证据链断言一字未改 | 单跑 2 passed；去掉 journey ownership 会退回 `Choose your next leg.` 失败 |
| `product-v8` mobile composition | 导航改用现行 `data-testid`（`nav-agent`/`nav-trips`/`nav-me`/`nav-hub`）；Copilot 步骤改成真实交互；Bookings 走 Trips 标签页 | 旧的 `v8-agent-submit` + `Mission captured` 换成 `v15-copilot-input` → `v15-copilot-submit` → `v15-intent` + `v15-mode`；Me 屏换成 `v8-me` + 现行标题 | 你上一轮判定"断言 dock 可见"是穿了新衣服的空转，成立，已按你的意见改成**发送一句话并观察服务端回执**；`v15-intent`/`v15-mode` 只有在拿到 response 后才渲染 |
| `real-world-trip-operations-v9` | 预订录入改走消费者手工表单（`inbox-tab-manual` → 字段 → `manual-submit` → `v13-2-confirm`），钱包列表通过 Advanced 展开后核对；后半段链路切到桌面宽度 | 行李感知恢复链（`active_plan.legs == activities-1`、`LUGGAGE_DROP`/`CHECK_IN` 角色、amap `wgs84` 链接、`Location updated · accuracy 12 m`、`Autopilot recovered the exposed leg`）全部保留 | 单跑 2 passed，且 `reports/product-v9/ui/live-journey-mobile.png` 现在能看见"NEXT · LEAVE BY / Luggage drop · Haihe Riverside Hotel / NAVIGATE →"，离线截图能看见种子酒店进了 24 小时快照 |

一处**主动披露的替换**：v9 原来还断言 bookings 页标题 `Your real reservations, protected.`。
该标题属于被折叠的开发者工作台，我没有把它塞回消费者路径，而是以 `inbox-tab-manual` 与
`v10-inbox-draft` 的存在作为"到达 Bookings 面"的证据——覆盖面略窄了一点，但不再依赖被折叠的入口。

## 27. 计划外的第 9 条红灯：不是漂移，是前端套件一直在借用别人的后端

第一次全量跑出 **37 expected / 9 unexpected**，多出来的是 `v13-5-fully-grounded`。逐层定位：

1. 它**单跑也失败**，页面停在 `Composing city evidence…`，即 `expect` 的 10s 预算内服务端没返回 → 排除我这三条迁移造成的跨 spec 污染。
2. 用同样的三步直接打 API（`demo/reset` → 三次 `inbox/import`+`confirm` → `real-city/intelligence`）：
   请求 **201 成功但耗时 15.5s**，因为应答的 `:8000` 后端 `ai: enabled`，语义组合走 DeepSeek，而校园网出口当前很慢。
3. 根因是环境归属：`_qoder_integration_20260919` **没有自己的 venv**，`playwright.config.ts` 的
   `backendPython` 因此退化成系统 `python`（3.10，`ImportError: StrEnum` 起不来），而 `reuseExistingServer: true`
   让套件静默复用了 `:8000` 上那个由别的 lane 起的进程（命令行是 uv 的 cpython-3.12，不是本仓代码）。
   也就是说：**过去几轮"前端 e2e 通过"的证据，后端可能根本不是被集成的那份代码**，AI 开关和数据库也不由这次 HEAD 决定。
   这同时解释了"同一 HEAD、不同数字"（34/12 → 35/11 → 37/9）。

受控复现（本轮权威数字的来源，未改任何 harness 代码，只是显式给环境）：

```
DEEPSEEK_API_KEY= CITYNEXUS_AI_API_KEY= CITYNEXUS_AI_ENABLED=false \
CITYNEXUS_PYTHON='D:\moodle\CityNexus\.venv\Scripts\python.exe' \
CITYNEXUS_BACKEND_PORT=8021 CITYNEXUS_E2E_PORT=4194 \
CITYNEXUS_DATABASE_URL='sqlite:///./_p12_full.db' \
  npx playwright test --reporter=json
```

结果：**38 expected / 8 unexpected / 0 flaky**，与你预测的分毫不差，且 8 条正是已分类的 legacy 8 条。
`v13-5` 在该环境下通过。
*（pass-13 更正）* 我原来写"13.0s 通过"是记账口径错误：13.0s 是那次 `npx playwright test` 的整条命令墙钟
（含两个 webServer 启动与 `real-seed` setup 项目），`fe_full_pass12_isolated.json` 里 `v13-5` 自身的
result duration 是 **1221 ms**。真正慢的是借用 `:8000` 那次的外部 AI 路径（另行直调端点约 15.5s，
测试自身 10990 ms 后在 10000 ms 预算上超时）。两个数字分属不同层，不该混着引用。
两次运行的 JSON 都进包（`fe_full_pass12_shared8000.json` 与
`fe_full_pass12_isolated.json`），因为前者本身就是这个环境归属缺陷的证据。

## 28. 门禁数字（全部来自同一次受控运行，HEAD `2875aba`）

| 门禁 | 结果 |
|---|---|
| 全量 Playwright | 38 expected / 8 unexpected / 0 flaky（188.8s，`workers: 1`） |
| 其中 `qoder-*` | 28 passed / 0 failed（同一 JSON 按文件聚合，见下表） |
| 其中两条对比度门 | `qoder-contrast-audit` 4 passed、`qoder-live-structure` 9 passed。审计 JSON：8 屏（Today/Live × light/dark × 390/1280）共扫描 1740 个节点，**violations 0**；borderWarnings 每屏 2（dark）/4（light），与 pass-11 提交的 JSON 逐字节相同（本轮无视觉回归，文件未变更） |
| `typecheck` / `typecheck:all` | 0 error |
| `vite build` | 成功（PWA generateSW，precache 9 entries / 2295.48 KiB） |
| 后端同环境 | 827 passed / 15 skipped / 0 failed（58.21s，AI key 置空，主仓 venv 的 python 3.12） |

三条迁移过的 spec 在切换 HEAD 前后**单独**跑过一遍（8.6s / 15.9s / 12.4s 全绿），全量再复跑一次，
不存在"只有单跑绿"的情况。

按文件聚合（同一 `fe_full_pass12_isolated.json`，pass/fail）：

| 文件 | pass | fail | | 文件 | pass | fail |
|---|---|---|---|---|---|---|
| `_qoderRealSeed.setup.ts` | 1 | 0 | | `qoder-mobile-overflow.spec.ts` | 1 | 0 |
| `product-v8.spec.ts` | 2 | 0 | | `qoder-today-hero.spec.ts` | 2 | 0 |
| `real-world-trip-operations-v9.spec.ts` | 1 | 0 | | `v10-accessibility.spec.ts` | 1 | 0 |
| `v10-live-execution.spec.ts` | 1 | 0 | | `v10-inbox.spec.ts` | 1 | 0 |
| `v10-quality-budget.spec.ts` | 1 | 0 | | `v13-5-fully-grounded.spec.ts` | 1 | 0 |
| `v13-authoritative-integrity.spec.ts` | 1 | 0 | | `qoder-ack-rendered.spec.ts` | 6 | 0 |
| `qoder-ack-resolution.spec.ts` | 1 | 0 | | `qoder-budget-evidence.spec.ts` | 2 | 0 |
| `qoder-budget-rendered.spec.ts` | 3 | 0 | | `qoder-contrast-audit.spec.ts` | 4 | 0 |
| `qoder-live-structure.spec.ts` | 9 | 0 | | **8 条 legacy** | 0 | **8** |

`golden`(1) + `live-autopilot-v5`(1) + `predictive-real-city-v6`(1) + `product-hardening`(5) = 8，
与 `docs/LEGACY_E2E_MIGRATION.md` 的清单逐条一致，没有第 9 条。

## 29. 截图复核里新看见、我没有动手的一处

*（pass-13 更正：这条的具体结论不成立，我先自己撤回。）*

原结论写的是"Copilot 悬浮胶囊压在 EVIDENCE 卡片首行，`Provider route, fres…` 被遮住"。
把 `reports/product-v9/ui/live-journey-mobile.png` 当证据看是错的：那是一张 390×2250 的
`fullPage: true` 拼接图，EVIDENCE 那一行在图里更靠下、文字是完整可读的，并没有被盖住。
`position: fixed` 的悬浮元素在整页拼接里会落在它当时所在的滚动位置附近，所以它能证明的只有：
**Live 页的固定 pill 与"Compare all modes"一带的内容空间发生了冲突**——这仍然值得查，
但不能拿它当作"EVIDENCE 首行被遮"的证据。方法错误本身记一条：不要根据长截图的拼接结果推断
遮挡关系，也不要去改 CSS。pass-13 改用在 390×844 真实视口下取 `getBoundingClientRect()` 相交判定，
结果见 §32。

## 30. 请判

1. 环境归属：是否授权我把"前端 e2e 必须跑在本仓代码自起的后端上"变成**可检查的约束**
   （最小做法：`playwright.config.ts` 在复用已有 server 前先核对 `/health` 里的构建标识，不匹配就 fail fast）。
   这属于你此前划的"Playwright 启动/数据库改造 NOT_AUTHORIZED"边界，所以我先问不动手。
2. `v13-5` 的 10s 预算：AI 打开时该端点确实要 15s+。这是产品性能问题（应给 discovery 一个
   可等待的进度态或后端超时降级），还是测试预算问题（`expect` 单独放宽到 30s）？我倾向前者，
   因为消费者真的会盯着"Composing city evidence…"不动。
3. pass-12 三条迁移是否解除 `CURRENT_E2E_CONTRACT_MIGRATION`（`BLOCKED_ON_E2E_EVIDENCE_CLOSEOUT`
   已由 pass-11 解除）；若解除，下一轮按 `docs/LEGACY_E2E_MIGRATION.md` 的 archive/port 判定执行，
   还是先做 §29 的 Live 遮挡与 Hero→replan 路线图。

---

# pass-13（2026-09-19 20:0x，门禁树 `5e84e29`）

按裁决只做 A（authoritative provenance 门）与 C（Live dock 先验证后修）两件事，
没碰 8 条 legacy，没开 OSM/Hero 路线图，没改 v13-5 的 10s 预算。

## 31. A：把"测的是不是自己"变成机器事实

`CITYNEXUS_E2E_AUTHORITATIVE=1` 下按顺序强制：

| 约束 | 落点 | 观察到的行为 |
|---|---|---|
| `CITYNEXUS_PYTHON` 必须显式给出且文件存在，禁止退系统 Python | `playwright.config.ts` | 缺失/路径不存在 → `authoritative mode refuses to start: CITYNEXUS_PYTHON="./nope.exe" does not exist` |
| 前端与后端端口必须显式且不相等 | 同上 | 缺 `CITYNEXUS_E2E_PORT` → 直接拒绝 |
| 独立 DB，且文件名必须含本次 `CITYNEXUS_E2E_RUN_ID`，必须是 `_*.db` | 同上 | `sqlite:///./citynexus.db` 被拒；命名含 run id 使"每次全新库"成为结构性质，而不是"跑之前偷偷删一下"（globalSetup 在 webServer 之后运行，那时文件已被本 run 的后端打开并锁住，Windows 上 `rmSync` 直接 EPERM——这条我踩过并改成了结构性方案） |
| 外部 AI 必须关闭 | 同上 | 环境里留着 `DEEPSEEK_API_KEY` 就拒绝启动，而不是静默走真模型 |
| 两个 webServer 全部 `reuseExistingServer: false` | 同上 | 端口被占时 Playwright 自己就拒绝：`http://127.0.0.1:8026/api/v1/health is already used, make sure that nothing is running on the port/url or set reuseExistingServer:true` |
| 通过**前端 origin** 读 `/health`，要求回显本次 run token、DB 路径、`ai=disabled` | `e2e/_qoderAuthoritativeSetup.ts` | `provenance ok: run=p13final1 frontend=:4202 -> backend=:8029 ai=disabled db=sqlite:///./_p13final1.db`；token 不匹配时报文直接指出"应答 :PORT 的后端不属于本次调用"并给出 netstat 查法 |

为什么要绕前端而不是直连后端：测试真正依赖的是 `vite → proxy → backend` 这条链，
只有从前端 origin 拿到正确 token，才能同时证明 dev server 也是本次起的。

`/health` 为此新增 `e2e_run_id` 与 `database_url` 两个字段（`backend/app/core/config.py`、
`app/main.py`），并由 `backend/tests/test_e2e_provenance.py` 钉住三条事实：
没被盖戳的服务器回显空串（所以借来的后端永远过不了断言）、被盖戳的回显自己的值、
以及它报的是自己打开的 DB。按裁决**没有**引入 Git SHA/哈希门。

provenance 打到 stderr（stdout 留给 `--reporter=json`，否则 JSON 会被首行污染——这个我第一版就踩了），
并落盘 `reports/e2e-provenance/authoritative.json` 随包交付。
workers / spec 顺序 / retry / DB schema / 产品语义一律未动。

## 32. C：Live dock 用真实视口重测，结论是我上一轮看错了

`e2e/qoder-dock-geometry.spec.ts` 在 390×844 下取 `.cn-copilot-dock` 与视口内所有可交互元素
（`button, a[href], input, select, textarea, [role=button]`）的 `getBoundingClientRect()`，
在 top/middle/bottom 三个滚动位各测一次并打印数字，截图为非 fullPage：

```
[dock-geometry] /v8/live   @top    dock=215,706 165x54 state=collapsed idle-compact idleCompact=true scrollY=0/1318    actionableInView=21 covered=0
[dock-geometry] /v8/live   @middle dock=215,706 165x54 ...                                            scrollY=659/1318  actionableInView=14 covered=0
[dock-geometry] /v8/live   @bottom dock=215,706 165x54 ...                                            scrollY=1318/1318 actionableInView=7  covered=0
[dock-geometry] /v8/hub    @top    ...                                                                actionableInView=21 covered=0
[dock-geometry] /v8/hub    @middle ...                                                                actionableInView=18 covered=1
      button "DAY 1FridayArrival · Check in · " rect=626..782 overlap=158x54px
[dock-geometry] /v8/hub    @bottom ...                                                                actionableInView=9  covered=0
```

结论：
1. **Live 页不成立**。真实视口里 dock 已经是 idle-compact 小胶囊（165×54，位于 215,706），
   三个滚动位都没有压住任何可交互元素；`reports/dock-geometry/live-390x844-bottom.png` 里
   `EVIDENCE / Provider route, freshness, cost and feasibility` 整行完整可读。
   pass-12 §29 那句"EVIDENCE 首行被遮"是 390×2250 fullPage 拼接图的产物，已按你的判定在 §29 就地撤回。
2. **没有做产品 CSS 改动**，因为不成立；这条归 `fullPage capture artifact`。
3. 顺带量到一件需要你定性的小事：Today 在**滚动到中间**时，DAY 1 卡片按钮与胶囊有
   158×54 的瞬时重叠（滚动停止后 covered=0）。这是 fixed 悬浮件经过滚动内容的固有现象，
   不是静止遮挡，所以我只把"静止时不得压住任何可交互元素"写成断言（已通过），
   瞬时相交只报数字不判对错。若你认为 pill 在滚动中也必须让位，那是产品规则，等你下令我再动。

## 33. 门禁数字（全部来自 HEAD `5e84e29` 上同一次 authoritative 运行）

| 门禁 | 结果 |
|---|---|
| 全量 Playwright（authoritative） | **40 expected / 8 unexpected / 0 flaky**（194.8s） |
| 8 条 unexpected | 恰为已分类 legacy：golden 1、live-autopilot-v5 1、predictive-real-city-v6 1、product-hardening 5 |
| 其中 `qoder-*` | 30 passed / 0 failed（含新增 dock-geometry 2 条；此前 28） |
| `v13-5-fully-grounded` | expected，测试自身 result duration **1298 ms**（10s 预算未动，也未改 30s） |
| 对比度 | `qoder-contrast-audit` 4 passed；8 屏 1740 节点 0 violations |
| `typecheck` / `typecheck:all` | 0 error |
| `vite build` | 成功（PWA precache 9 entries / 2295.48 KiB） |
| 后端同环境 | **830 passed / 15 skipped / 0 failed**（58.6s；= 827 + 新增 3 条 provenance 测试） |
| SQLite 争用告警 | 本次 authoritative 全量 0 次（此前单规格探测时出现过 1 次 `JourneyTwin cache write skipped ... database is locked`，未导致失败，仍记录在案） |

## 34. 请判

1. Today 滚动中途的瞬时相交（§32 第 3 点）：判"fixed 悬浮件经过内容属正常"结案，
   还是要求 pill 在滚动中也让位（那就是一次真实的 yield 规则改动）？
2. authoritative 模式目前只在我这条线强制。是否把它写进 `docs/` 的验收规约并作为
   所有 lane 出 E2E 证据的唯一口径（Sol/Astra 的只读输入约定我不清楚，需要你或负责人确认）？
3. 下一轮按你的排期是 pass-14：8 条 legacy 的 archive / port-first。
   要我现在就把 4 条 "Archive" 的入口改成 `/legacy` 并逐条记录能力不变量已被现行套件覆盖的证据，
   还是先只写归档 PR、把 port-first 的 4 条留到之后？
