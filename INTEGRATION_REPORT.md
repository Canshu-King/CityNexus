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

---

# pass-13.1（2026-09-19 20:5x，门禁树见 COMMITS.txt）

按裁决只做三件：provenance 两处加固、Today dock 静止遮挡。8 条 legacy 一条没碰。

## 35. ① fresh-or-no-run：先说清楚为什么不能放在 config 里

裁决要求"webServer 启动前若目标库已存在就 fail fast，绝不自动删"。我先按字面实现在
`playwright.config.ts` 里，然后被自己的门拦下了：

```
authoritative mode refuses to start: the database for run "p131dock1" already exists at
D:\moodle\_qoder_integration_20260919\backend\_p131dock1.db
```

原因是 Playwright 会在主进程和 worker 进程里**各求值一次 config**，第一次求值后
后端已经建好文件，第二次求值自然"已存在"。也就是说 config 不是"启动前只问一次"的地方。

所以这条规则改放到**真正打开这个文件的那个进程**里：`backend/app/db/session.py` 的
`make_engine()` 在 `create_engine` 之前检查——只有被 `CITYNEXUS_E2E_RUN_ID` 盖过戳的进程
才受约束（普通 demo 服务与 pytest 完全不受影响），文件存在就抛错、绝不删除：

```
E2E run 'p131dock1' refuses to reopen an existing database at ...
An authoritative run must start from an empty file; issue a new CITYNEXUS_E2E_RUN_ID instead of deleting it here.
```

`_*.db` + 文件名必须含 run id 的命名规则保留，它正是让这条拒绝"可达"的前提。
三条行为由 `backend/tests/test_e2e_provenance.py` 钉住：盖戳进程拒绝重开、盖戳进程可以新建、
未盖戳进程不受影响。

## 36. ② /health 不再回显连接串

`database_url` 从 `/health` 移除，改为 `e2e_database_id`：只回显文件名（`_p131full1.db`），
且**只有被盖戳的 E2E 进程才回显**，其他进程一律空串。门与后端测试同步改了。
新增一条回归测试直接用最坏情况断言：把 `database_url` 换成
`postgresql://citynexus:s3cr3t@db.internal:5432/citynexus`，`/health` 里不得出现 `s3cr3t` 或 `db.internal`。

两条互相打架的注释也统一了：实测 Playwright 1.63 的 `globalSetup` 在 webServer **之后**运行
（第一版门在检查"端口是否空闲"时撞见自己刚起的 uvicorn，就是证据），
所以"必须在服务启动前完成"的检查留在 config 文件体内，"谁应答了这次运行"的检查留在 globalSetup。

## 37. ③ Today dock：你说得对，那是静止遮挡；另外这条规则还牵出导航栏

先认账：§32 里"静止时归零"是我的错误解释。middle 采样点确实是滚动停止、等了 450ms 之后测的，
重叠仍然存在；bottom 为 0 只是另一个位置的结果，我把它当成了"静止"的证据。

把门改成三个静止位都要 `coveredByDock == 0` 之后，我先加了一个**参照测量**（只报数不断言）：
同一规则套在底部导航栏上会怎样。

```
[v8/live @top   ] dock=215,706 165x54  coveredByDock=0  coveredByNav=2   nav=768..844
      (nav reference) button "mode-walk"    overlap=318x44px
      (nav reference) button "mode-bicycle" overlap=318x13px
[v8/hub  @middle] dock=215,706 165x54  coveredByDock=1  coveredByNav=2
      button "DAY 1FridayArrival · Check in ·" overlap=158x54px
      (nav reference) button "DAY 1..." overlap=356x14px  button "DAY 2..." overlap=356x36px
```

也就是说：`position: fixed` 的底部条带在任何静止位都会压住可交互内容，导航栏压得比 pill 更狠
（`mode-walk` 被盖 318×44，几乎整只按钮）。要按字面把这条规则贯彻到两者，唯一结构性做法是
把滚动视口截短到 pill 之上（导航 76px + pill 54px + 间隙 ≈ 138px），等于每台手机永久让出约 16% 高度，
而且会直接挤压首屏门。这个代价我判断不该由一次遮挡收口来付，所以按你允许的 yield 思路做：

**pill 在静止时若压住任何可交互元素，就自己让出内容列（向右滑出），带内一空就回来。**
`CopilotDock` 里 debounce 220ms 后按**布局盒**（不是 transform 后的矩形，否则会自激振荡）判定，
CSS 只加一条 `.idle-compact.yield-at-rest { transform: translateX(calc(100% + 16px)); opacity: 0; pointer-events: none }`，
带 `prefers-reduced-motion` 降级。没有保留 `idleCompact` 之外的行为改动，没有动导航，没有重开 Apple 视觉线。
入口不丢：底部导航本来就有 Copilot 项。

修后门里的数字（同一次 authoritative 运行）：

```
[v8/hub @middle] dock=396,706 165x54 state=collapsed idle-compact yield-at-rest yieldsAtRest=true coveredByDock=0
```

其余静止位 `yieldsAtRest=false`（本来就没压东西），`coveredByDock` 全为 0。
`yieldsAtRest` 与 `coveredByNav` 都打进日志，是为了让"绿"能区分"让位生效"与"根本没重叠"。
导航栏那两处重叠我没有修也没有断言——那是 shell 级布局策略，要不要为它让出 138px 由你定。

## 38. 门禁数字（同一次 authoritative 运行）

| 门禁 | 结果 |
|---|---|
| 全量 Playwright（authoritative） | **40 expected / 8 unexpected / 0 flaky**（195.7s） |
| 8 条 unexpected | 与 pass-13 完全相同的 8 条 legacy，一条没多一条没少 |
| `qoder-*` | 30 passed / 0 failed（含收紧后的 dock 门 2 条） |
| SQLite 争用告警 | 0 次 |
| `typecheck` / `typecheck:all` / `vite build` | 全部干净 |
| 后端同环境 | **834 passed / 15 skipped / 0 failed**（58.2s；= 827 基线 + 7 条 provenance/新鲜度测试） |
| 默认（非 authoritative）模式 | 回归通过：`authoritative=false ... reuseExistingServer=true` 照常工作，并把借用状态打印出来 |

一处随行为改变而变化的证据：`reports/contrast-audit/contrast-audit-mobile.json` 里
`live/mobile/light` 的 `borderWarnings` 从 4 变成 3（violations 仍为 0）。原因就是 §37 的让位——
静止时那个 pill 不再停在原处，被边界规则量到的元素少了一个。这是行为变化的正常后果，不是审计脚本被改。

## 39. 请判

1. 底部导航栏的静止遮挡（`mode-walk` 318×44、`DAY 2` 356×36）：与 pill 同规则处理（那就必须决定
   是否让出 138px 视口），还是明确豁免固定导航条、只把规则用于浮层？我给数据不给结论。
2. pill 让位用"滑出内容列"实现：可接受，还是你更希望它改为"上移到带内空隙"或直接不在移动端浮起？
3. authoritative 模式现已满足你要求的两点加固（fresh-or-no-run、连接串不外泄），
   是否正式定为 `AUTHORITATIVE_E2E_CANONICAL_GATE = REQUIRED`，并把它连同"非 authoritative 的 E2E 结果
   只能算本地诊断"写进 `docs/`？写的话我按你的措辞落文档，不改产品码。
4. 下一轮 pass-14 按 4 条 pure Archive 开工（移出默认 acceptance suite、保留源码、只针对 `/legacy`、
   不计入 merge 门、逐条留 capability→current test 映射），port-first 4 条留到 pass-15。

---

# pass-14（2026-09-19 21:4x）

按裁决四件事：canonical 规约落文档、yield 的 a11y 加固、导航终点可达性断言、4 条 pure Archive。
4 条 port-first 一条没动、一条没 skip。

## 40. A：验收口径写进 `docs/E2E_ACCEPTANCE_POLICY.md`

规约 8 条按你给的措辞落成表格，每条都标了"在哪强制"，包括第 6 条为什么必须绕前端 origin
（测试真正走的是 `vite → proxy → uvicorn`，只有从前端拿到正确 token 才能同时证明两个进程都属于本次调用）。
另外写明：非 authoritative 结果只能算本地诊断；Sol/Astra 只读别人工作树不受影响，
但任何 lane 声称"我这边 E2E 全绿"必须交 authoritative 证据；明确**不**引入 Git/SHA 哈希门。

顺带修掉两条过期注释（`_qoderAuthoritativeSetup.ts` 里"freshness 在 playwright.config.ts 强制"、
config 侧暗示存在性检查在本文件的措辞），并把端口/Python/DB/AI 的解析逻辑抽到
`frontend/playwrightEnv.ts` 共用。抽这个文件不是整洁癖：现在有两个 config，
同一套 authoritative 规则如果各写一份，下一次漂移只是时间问题——而"两份描述各说各话"正是你逐轮在抓的东西。

## 41. B：yield 的 ghost button 你抓得对

原来只有 `opacity: 0; pointer-events: none`，鼠标碰不到但键盘和无障碍树里还在。
改成同时 `visibility: hidden`（并给 visibility 一条 linear 过渡，让滑出动画仍然完整），
恢复时一切照旧。

新增窄断言 `a yielded pill is not a ghost control: hidden, unfocusable, and back again`：
先遍历若干滚动位**找到**让位状态（找不到就显式失败并提示"这条断言会空转"，而不是静默通过），
然后断言 `toBeHidden()`、JS 主动 `focus()` 也拿不到焦点、`checkVisibility()` 为 false；
最后再遍历回清晰位置，断言 pill 重新可见、可用、可键盘聚焦。
"让位后不再回来"等于删功能，所以返回路径也在断言里。

## 42. C：导航栏按你的两条规则分开处理

`coveredByNav` 从纯日志升格为**只在最大滚动位**断言 `== 0`（live 与 hub 各一条），
top/middle 继续只打印数字并在注释里写明"允许，但应该让读的人看得见"。
没有预留 138px 内容带。

## 43. D：4 条 pure Archive 是真的搬出去了

- `frontend/e2e/legacy/archived-product-hardening.spec.ts`：Control Tower evidence/authority、
  persisted NL mission、assisted acceptance、Proactive Guardian，入口改 `/legacy`，断言一字未改。
- `playwright.config.ts` 加 `testIgnore: /[\/]e2e[\/]legacy[\/]/`；`--list` 实测主套件里 legacy 目录 0 条。
- `playwright.legacy.config.ts`：显式调用才跑，打印 `NON-GATING` 横幅，
  且传 `CITYNEXUS_E2E_AUTHORITATIVE=1` 会被**报告并忽略**——归档结果不可能被误当成 merge 证据。
- 每条留下 capability invariant / 为何属 legacy / 当前 owner(API) / 当前覆盖测试 / 归档位置，
  写在 `docs/LEGACY_E2E_MIGRATION.md`；引用的 9 个测试文件与 4 条路由逐条核过存在，
  其中 twin 端点我一开始写成 traveler 级，已按实际 `GET /api/v1/journeys/{journey_id}/twin` 改正。

实测归档套件本身：`--config playwright.legacy.config.ts` → **4 passed (18.8s)**。
这条结果同时证实 pass-8 的判断：表面活着，它们在默认套件里红只是因为向根路径要了这个表面。
也因此在 legacy config 里它是绿的、在 acceptance 里不参与门，两件事不冲突。

保留在默认套件里继续红的 4 条 port-first：`golden`、`live-autopilot-v5`、
`predictive-real-city-v6`、`product-hardening`(autonomous envelope-safe)。没有 skip、没有软化。

## 44. 门禁数字（同一次 authoritative 运行）

| 门禁 | 结果 |
|---|---|
| authoritative 当前产品套件 | **41 expected / 4 unexpected / 0 flaky**（151.3s） |
| 4 条 unexpected | 精确是 golden、live-autopilot-v5、predictive-real-city-v6、product-hardening:172 |
| 与你预期 40/4 的差 | 多出的 1 条 expected 是 §41 新增的 ghost-control 断言；归档只减不加的话应为 40，我没有为了对上数字省掉这条测试 |
| `qoder-*` | 31 passed / 0 failed |
| 主套件是否发现 legacy | `--list` 22 文件 45 测试，legacy 目录 0 条 |
| 归档套件（非门） | 4 passed / 18.8s |
| SQLite 争用告警 | 0 次 |
| `typecheck` / `typecheck:all` / `vite build` | 全部干净 |
| 后端同环境 | 834 passed / 15 skipped / 0 failed（62.2s） |

## 45. 请判

1. 多出的第 41 条 expected（ghost-control 断言）是否接受为 pass-14 的正常产物，
   还是要求基线数字严格对齐 40/4。
2. `playwrightEnv.ts` 这次为共用规则做的抽取是否算越界改 harness——我判断它不改 workers/顺序/retry/DB，
   只是防止两个 config 漂移；如果你认为该留在 pass-14 之外，我可以把两文件回退成内联重复。
3. pass-15 四条 port-first 的顺序与目标断言：我建议先 `product-hardening:172`
   （envelope-safe autonomous recovery 与现行 Copilot/Guardian 面最接近），
   再 `live-autopilot-v5`（零触发）、`predictive-real-city-v6`（自主预防）、
   最后 `golden`（reload 持久化）。目标断言由你给还是我按现状提草案？

---

# pass-15（2026-09-19 22:1x）

按你定的顺序 golden → :172 → v5 → v6 做 port-first，四条都没有改指 `/legacy`、没有 skip、没有降成 API-only。

## 46. A golden：迁到当前 V8 Live，持久化用身份而不是文字

链条：closure 事件 → 当前 Live 呈现 proposal → 旅客按产品自己的 `live-accept` →
接受的 plan 身份是服务端事实（journey 与 twin 一致）→ reload 后仍渲染已解决状态 →
受保护承诺还在。断言落在 plan 身份与"不再重复询问"上，不是标题文字。

两处测量结果我没有藏：
1. **`/experience` 的 active_plan 里 6 个 activity 的 `place_id` 全是 null**，而
   `/plans/generate` 是填了 `place_id` 的。所以"同一个地点仍被保护"在当前消费者载荷里无法证明，
   我改成按旅客看得见的 title 匹配（`Nexus River Cruise Pier`），并由测试把这行差异打印出来。
   这是契约不一致，不是测试偏好。
2. 原本照 legacy 写"localStorage 键必须恰好等于三个"会因合法原因失败——Copilot dock 本来就把
   每个 journey 的对话历史存 localStorage。改成断言真正要紧的：没有任何 plan 形状的键，
   且任何存储值都不含被接受的 plan id，否则"reload 后还在"证明的是浏览器不是服务端。

setup 走产品自己的转换（demo/reset → plans/generate → select → `/start`），因为
`request_replan` 在未 ACTIVE 的 journey 上直接 409 `journey must be ACTIVE with an active plan`；
去改状态列等于测一个旅客到不了的状态。

## 47. B envelope-safe 自主恢复：数字与表面都断

legacy 用 Control Tower 的模式/成本/漂移输入。能力没消失，所以检查搬到当前表面：
gateway 在旅客自己的 policy 下 `ALLOW_AUTO`、真的 `executed`、执行出的子 plan 版本成为权威、
cost delta 与 drift 落在配置的 envelope 内、locked commitment 保住、
`/v8/authoritative` 渲染出 accepted 的子版本 id + `C4 commitments preserved` + provider 证据。
PUT 之后把 policy 读回来再断——"在 envelope 内"如果 envelope 根本没存进去就毫无意义。

实测一次：`cost delta -3000 of 5000, drift -5 of 120, plan 55523d40… -> a8f9bdc5…`。

## 48. C zero-touch：与 B 保持结构差异

触发（一个 provider 形状的 CLOSURE 事件）之后测试不做任何点击/输入/accept。
plan 身份自己改变；与该事件关联的 proposal 是 `ACCEPTED` 且 `locked_commitments_preserved`；
审计日志把它记为 `replan_auto_accepted / AI_AGENT`；`/v8/authoritative` 显示 accepted 子版本，
`/v8/live` 不再就一次已经发生的恢复询问旅客；reload 后 plan id 不变。

第一版我把 feed 请求包在 `.catch()` 里并且猜错了路径（`/agent/feed`），结果 404 被吞成空列表，
"证明它是自动的"这条断言就静默变成了空转——正是这条工作线一直在抓的沉默削弱。
正确端点是 `/journeys/{id}/agent-feed`，返回 `{source, events}`，swallow 已去掉。

## 49. D 预测式自主预防：能力在，表面没有主人——留红

后端确实端到端做了预防：只喂一个 `RISK_FORECAST` fixture（journey 上没有任何 CLOSURE/CRITICAL 事件，
这条是被断言的而不是假设的），autopilot 自己产出
`decision=PREEMPTIVE_RECOVERY / trigger_kind=PREDICTIVE / action_status=EXECUTED`，
`evidence.observation.forecast_before_hard_failure=true`，plan 从 `55523d40…` 变成 `e8037cd1…`，
River Cruise 仍在，且 `scanRequests == 0`（测试自己没去要决策，否则就成 reactive）。

但渲染它的组件——`guardian-decision`、`guardian-predictive-resilience`、`guardian-provenance`、
`guardian-trace`、`guardian-standing-mission`、`guardian-provider-risk-forecast`——
**只存在于 `src/main.tsx`，即 `/legacy` 后面的旧表面**。V8 里没有任何面承接预防结果
（`api/citynexus.ts` 有 `PREEMPTIVE_RECOVERY` 与 `trigger_kind` 类型，组件层零引用）。

因此这条按裁决**留红**，失败信息直接写 `PRODUCT INTEGRATION GAP: …` 并给出修法方向
（给 V8 一个预防结果的 owner），同时写明两条禁止的捷径：不得改成 backend-only 断言变绿，
不得把 reactive recovery 改名冒充 prevention。

一个诚实的弱点：这条断言目前是"页面文本里出现 PREEMPTIVE/predictive/forecast 之一"。
它现在为假所以缺口成立；但如果将来有人在无关文案里写了 "forecast"，它会虚假变绿。
给 V8 补真 owner 时应把这条换成结构化断言（具体 testid + run 身份），我在 §51 请判里提出。

## 50. 门禁数字（同一次 authoritative 运行）

| 门禁 | 结果 |
|---|---|
| authoritative 当前产品套件 | **44 expected / 1 unexpected / 0 flaky**（122.2s） |
| 唯一 unexpected | `predictive-real-city-v6` —— §49 的产品缺口，故意留红 |
| 与你预期 45/0 的差 | 一换一成立（45 条总数不变），差的那 1 条正是 D：能力存在、表面没有主人 |
| 默认套件是否发现 legacy | 否（`--list` 与本次运行都不含 `e2e/legacy`） |
| `qoder-*` | 31 passed / 0 failed |
| SQLite 争用告警 | 0 次 |
| `typecheck` / `typecheck:all` / `vite build` | 全部干净 |
| 后端同环境 | 834 passed / 15 skipped / 0 failed（93.9s） |

## 51. 请判

1. D 的处置：批准"留红 + 报产品缺口"，并把它排成一次独立的产品补线（V8 需要一个预防结果 owner）？
   若批准，我按你的边界提最小方案：在 `/v8/authoritative` 的恢复面板上承接 guardian 预防run
   （decision + trigger_kind + 预测证据 + 为什么提前改），不改产品语义、不复活旧控件。
2. 那条文本级断言是否接受为过渡（现在为假，能证明缺口），还是要求我在补线时一并换成结构化断言？
3. `place_id` 在 `/experience` 里为 null 而 `/plans/generate` 有值——判为契约缺陷要我修，
   还是记为已知限制？它影响任何"同一地点仍被保护"的当前表面证明。
4. 四条 port-first 已清三条，剩 D。`INTEGRATION_CANDIDATE_READY_FOR_MAIN` 的签发条件现在是否可以
   定义为"authoritative current-product 0 unexpected + D 有 owner"，还是另有条件？

---

# pass-16（回应 §51 请判 1/2/3）：身份契约、真承诺、预防的表面主人

## 52. C `place_id`：先诊断到层，再修那一层

§51.3 那个"`/experience` 里 place_id 为 null"的问题判为契约缺陷并修掉。诊断是一次测量，
不是猜测：同一次运行里，canonical 子计划 `GET /api/v1/plans/{id}` 报 6/6 活动带 place_id，
同一个计划经 `GET /journeys/{id}/experience` 报 0/6。
所以身份没有丢在 solver 或 accept 里，是丢在**投影层**。

修在 `backend/app/stay_mobility.py::_active_plan_payload`：把 `place_id` 和 `city_service_id`
放进活动投影。回归不是"字段存在"这种断言，而是整条链
（generate → select → start → closure → request_replan → accept）跑完后比较两个投影的
place_id 集合，`backend/tests/test_qoder_activity_identity_contract.py`，2 passed。
第二条测试防的是反向偷懒：替代活动也必须带真 place_id，不能靠 null 蒙过比较。

前端四条 spec 里所有 `/river cruise/i` 之类的标题匹配全部换成 place_id + protected。
标题可翻译、可改名，不是键。

## 53. A/B 承诺：fixture 里原本没有可保护的东西

写 §48 时我用了 `locked_commitments_preserved`。测量结果说明那三个案例都是空转：
demo 计划上的游船活动是 `locked: true` 而 `protected: false`——`protected` 由 ACTIVE
Commitment 行推导，必须有 booking 且付款已 CAPTURE。也就是说"受保护承诺被保住了"
在一个根本没有受保护承诺的 fixture 上恒真。

现在三条（golden / envelope / zero-touch）加上预防案例，都通过公开端点先建真承诺：
`POST /bookings` → `POST /transactions` CAPTURE（带 `Idempotency-Key`），
而且必须在 `/start` 之前——行程中预订活动会被 422 拒绝（这也是测出来的）。
共享 helper `protectCommitment()` 放在 `frontend/e2e/_qoderFreshJourney.ts`，
它建完会回读 `/experience`，若 `protected` 没落地就抛错——四个各写一份、
各自漂移成"大概受保护"正是仲裁要我避免的事。

## 54. 一条我没能证明的主张，如实撤回

预防案例里我加了"预防后的计划必须含 `real-place-*` 活动"，想证明预防 grounded 在真实城市。
**跑出来是假的**：`place-tech-art → place-city-park`，六个活动仍是 demo 命名空间。
原因也是查出来的：pytest 版 `test_v6_predictive_real_city.py` 之所以有 real-place，
是因为它用 `seed_explicit_mobility` 把特定 leg 声明成显式 replay 事实，改变了 solver
认为可负担的替代集；不带那层种子的真实 mobility 下，预防买到的是时间余量而不是换点。
在这里硬断言就是在测 fixture，不是测产品。所以删掉该断言，改成两条可证的：
`/provider-mesh` 必须含 `openstreetmap-replay` 的真城市候选，
以及把 recomposition 前后 (place_id, start_at) 指纹打进运行日志。
`v13-5-fully-grounded` 才是"真地点被选进计划"的所有者，这条不抢它的活。

## 55. D/E 预防的表面主人（§51.1、§51.2 的处置）

新增 `frontend/src/features/recovery/V14PreventivePanel.tsx`，挂在 `/v8/authoritative`
的反应式恢复面板之上。它读的是 `GuardianRun` 本身而不是计划 diff，这样就不可能把
reactive recovery 换个标签冒充 prevention：TRIGGER 行是 run 的 `trigger_kind`，
TIMING 行是 `evidence.observation.forecast_before_hard_failure`，FORECAST 行是 run
据以行动的那张快照，PLAN 行带 before/after 两个计划 id 的 data 属性，
并显式写明"反应式结果由下面的面板负责"。

§49 承认的那个可被无关文案骗过的文本哨兵已删除，换成按 testid + `data-run-id === run.id`
的结构化断言。案例同时要求：跑动前无 CLOSURE/CRITICAL、真实 forecast payload 的
`components.forecast_risk === 88`、`solver.kind === ORTOOLS_CP_SAT_V2`、承诺按身份仍在且
仍 protected、`scanRequests === 0`。

两个只有真跑才暴露的事实：
1. 韧性**总分饱和**——提交 forecast 88 渲染成 `risk 100`，所以面板和测试都看
   `forecast_risk` 分量，不看总分；
2. `GuardianRun` 行先以 `status=RUNNING / action_status=PLANNING` 落库，重排完才变 EXECUTED。
   只 poll"行出现"就会读到半成品并按 PLANNING 失败——补了一条按同一 run id 等终态的
   poll，两条失败信息各自准确（从未出现 vs 出现但没完成）。
3. 面板发现 run 后停止轮询：run 是持久证据，继续 3 秒一次只是和 autopilot 的写抢 SQLite。
4. 裁决明确"不能只凭 `trigger_kind=PREDICTIVE` 认定 grounded real-city 预测"，所以案例直接读
   run 自己的证据：`evidence.prediction.evidence_provenance` 必须非空、**每一条**都是
   `provenance == "REPLAY"`（不是被洗成硬事实的 mock 默认值）、且至少一条来自 replay provider。
   实测这张 journey 上是 `open-meteo-replay`(CITY_SIGNAL) 与 `city-signal-fixture`(MOBILITY)，
   两条都 REPLAY，mesh 里 3 个真城市候选；这些数字随运行日志一起打印，主张和数据同处一地。
   另需说明一个未消除的现象：单独反复跑这条案例时出现过 2 次
   `JourneyTwin cache write skipped … database is locked`（后端显式捕获的容错路径，不影响断言），
   而三次全量 authoritative 运行都是 0 次。我没有把它"修成 0"，只是如实报两种观察。

## 56. 归档套件的一个真实不确定性（新发现，非门禁）

legacy 套件带 host `DEEPSEEK_API_KEY` 跑：3 passed / 1 failed，
`Proactive Guardian …` 得到 `action_status=MODEL_NO_MUTATION`。
同一棵树关掉 AI 开关跑：4 passed / 21.2s。
所以那一条依赖外部模型回合，不是本轮改动引入。归档套件不签门禁，
但它的数字以后必须连着 AI 开关状态一起报——已写进 `docs/LEGACY_E2E_MIGRATION.md`。

## 57. 文档与事实对齐

`docs/E2E_ACCEPTANCE_POLICY.md` 的 "Known-red by design" 列着四条现在已绿的案例，
`docs/LEGACY_E2E_MIGRATION.md` 结尾还说它们"still red, deliberately"。两处按现状改写，
并保留原则（红测试命名缺口 > 绿测试掩盖缺口）与将来留红时的写法要求。

## 58. 证据卫生：一张"通过却空白"的截图（本轮自查发现）

第一次 authoritative 全量跑（`p16full1`，tree `6311382`）是 45/0，但我按惯例去比对
门禁重截的 PNG 时，`reports/product-v13.5/fully-grounded-discovery.png` 从 133910 字节
掉到 91550 字节。看图：页面只剩发现表单，结果卡片整块不见。
而这条 spec 是 **passed** 的——`v13-discovery-result`、`FULLY GROUNDED`、`valhalla`、
`SELECTED` 全部断言过。

原因不是功能退化，是**截图时机**：结果卡片淡入，而 `toBeVisible()` 在 opacity 0 就已经为真。
上一轮恰好截在半透明（图上能看见卡片但发灰），这一轮截在淡入之前（完全空白）。
一张在过渡中拍的图不是"已稳定表面"的证据——这正是 §29 那次 fullPage 假证据的同类错误，
只是这次藏在通过状态里。

修法（`1d922ef`）：截图前等该子树的动画进入终态，作用域限定在结果卡片，
因为应用别处有无限循环的 pulse 点，文档级等待永远不收敛。修完这张图 178816 字节，
内容比历史上任何一版都完整（候选列表含 `天津文化中心 · Eligible · openstreetmap-replay`、
证据面板、`FULLY GROUNDED`、`SELECTED`）。

其余 8 张 PNG 我做了像素级 diff 而不是只看字节：`mobility-sheet-desktop` 37.6% 变化
但内容同构（同一模态、同一横幅、同一五种模式数据），差异是 fullPage 画布上模态的
垂直锚点 + 时间戳 + 地图节点位置；其余在 0.02%–3.8%。没有一张变成空白。

最终一次运行（`p16full3`）又重截了一遍，所以引用那次的包里的图按同一方法再对比
（相对 `5de880b`）：bottom 0.02%、fully-grounded 0.03%、journey-hub 3.65%、
mobility-desktop 0.56%、mobility-mobile 37.14%、stay-explorer 1.72%、
trip-studio 2.60%、v9 live 0.01%、v9 offline 0.01%。
`journey-hub-desktop` 字节从 96643 掉到 67129 看着吓人，但像素只差 3.65%、
平均亮度 244.4 → 246.3，是 PNG 对文本栅格化的敏感性而不是内容消失；
空白页会是接近 100% 的差异，不是这个量级。

## 59. 门禁数字（同一次 authoritative 运行 `p16full3`，tree `967e2b2`）

| 门禁 | 结果 |
|---|---|
| authoritative 当前产品套件 | **45 expected / 0 unexpected / 0 flaky / 0 skipped**（115.6s） |
| 为什么不是更早那两次 | `p16full1`（tree 6311382）也是 45/0，但它产出的截图证据不合格（§58）；`p16full2`（tree 1d922ef）之后又加了 §55.4 的 provenance 断言，树变了。本轮只引用最后一次运行 `p16full3` |
| 与 §50 的 44/1 之差 | D 从红转绿：不是删断言，是补了表面主人；总数 45 不变 |
| `qoder-*`（视觉/对比/几何/无障碍预算） | 31 results / 0 failed（对比 4、dock 几何 3、live 结构 9、移动溢出 1、today hero 2、ack 7、budget 5） |
| SQLite 争用告警 | 0 次 |
| `typecheck` / `typecheck:all` / `vite build` | 全部干净（build 4.70s） |
| 后端套件（同环境，单跑） | 836 passed / 15 skipped / 0 failed（56.7s；比 §50 多 2 条 = 身份契约回归） |
| legacy 非门禁套件 | AI 关闭 4 passed（21.2s）；继承 host `DEEPSEEK_API_KEY` 时 3 passed / 1 failed（§56） |

## 60. 请判

pass-15 的裁决已经把 final integration gate 定义成三组条件，并把 pass-17 排成
Integration Freeze / Clean-checkout Reproducibility。所以本轮**不请求**签发
`INTEGRATION_CANDIDATE_READY_FOR_MAIN`——那条按你的定义要等 pass-17 从干净 checkout
复现之后。这里要的是 pass-16 的关闭判定与 pass-17 的验收形式。

1. D 的关闭五条件按裁决逐条自陈：real-city deterministic/replay 证据恢复（discover 在
   RISK_FORECAST 之前，`provenance == REPLAY`，mesh 有 `openstreetmap-replay` 候选，
   run 的每条 prediction 证据都是 REPLAY）；genuine C4 fixture（booking + CAPTURE，
   建完回读断言 `protected` 落地）；V8 有 preventive owner；结构化断言（七个
   `v14-preventive-*` testid + `data-run-id` / `data-plan-before-id` /
   `data-plan-after-id`，并断言页面显示的 run id 就是刚执行的那一个）；
   authoritative 0 unexpected / 0 flaky。identity contract 一侧：`/experience` 不再丢
   `place_id`，Golden 不再用 title 认亲。是否判 D = CLOSED？
2. §54 那条撤回是否接受：真实 mobility 下预防买到的是时间余量而不是换点，
   "真地点进入计划"的所有者仍是 v13-5。若你要求预防本身必须引入 real-place，
   那是产品语义线，需要另开实现而不是测试里断言——请明确是否开。
3. `V14PreventivePanel` 只挂在 `/v8/authoritative`（你批准的最小 owner 位置）。
   是否还需要在 `/v8/live` 出现，还是 live 只需要渲染被预防后的权威计划本身（案例里
   已用 `live-journey-current` 与 `/experience` 的活动身份对齐）？
4. `locked_commitments_preserved` 这个 proposal 级 flag 现在被四条案例的身份断言架空，
   后端仍产出它。是否降级为信息字段（以 plan 身份为准），还是保留为权威字段并要求
   后端也加契约测试？
5. pass-17 的验收形式请定：我理解为在临时目录 `git clone` 本分支 → `npm ci`（lockfile 驱动）
   → `vite build` → 一次 authoritative E2E（不借任何现有 server、独立端口与一次性 DB）→
   后端套件 → `git status` 干净，并把每步命令与输出打进包。若如此，pass-17 期间发现需要
   改源码才能复现的问题，按你的规则应当回炉为 pass-16.1 而不是在 freeze 里修，确认这一点。
6. §58 的 settled-before-capture 我只修了暴露出来的那张。其余 8 张做了像素 diff 确认未退化，
   但它们的 spec 没有同样的等待。是否推广为截图门通用前置（我倾向推广，但那属于宽泛视觉线，
   你两次让我不要重开，所以先问）。

---

# Sol Truth Convergence Integration（外部 handoff：Codex GPT-5.6 Sol V2）

## 61. 基线冲突怎么处理的（先说清楚，免得审计重新推导）

handoff 写的基线是 `HEAD = 0af1905`，并且"Do not work on the pass-15 /experience
place_id contract defect / predictive V8 ownership"。但同一份 handoff 又要求
"Preserve all current pass-15 behavior"，而 pass-15 的 GPT 裁决把那两项判为 main
前必修并已派给我——我在收到 handoff 之前已经做完、打包、送仲裁。

所以我的处置是：**不回退、不 cherry-pick、叠加在 `fec2204` 之上**。
理由是可核实的：Sol 那四项缺陷（cursor 语义、同 proposal 竞态、竞争 proposal、
CAPTURE vs ACCEPT）我逐条读过代码定位，我的五个 pass-16 提交完全没碰
cursor 解析 / accept / CAPTURE / serialization 路径，四项缺陷在 `fec2204` 上依然
全部成立。回退到 0af1905 只会把已交付的仲裁项丢掉，不会让 convergence 更好做。

Sol 的两个 verification commit（`c19daa54`、`776be4e9`）在本仓与主仓都不可读，
只在 `D:/moodle/_codex_sol_extreme_v2_20260919/snapshot/citynexus/.git` 里可读。
我只把它们当行为参考读，**没有 fetch、没有 cherry-pick**；本 pass 的实现是自己写的
（`concurrency_guards.py`、`commitment_remap.py`、`_execution_truth` 的三分支、
前端 `liveActivityWindow`），命名、注释、边界都按本线的情况写。

## 62. A / CX-SOL-001：cursor 从"提示"变成"断言"

改前 `_execution_truth`（`backend/app/operations/v9.py:129-138`）只有一条分支：
`current_index is None` 就回退到首个非终态活动。也就是说"cursor 为空"和"cursor
指向一个不在本计划里的活动"走同一条路，后者会凭空造出 Now / Next / NextLeg。

现在是三态：`VALID`（精确指向该活动）/ `ABSENT_FALLBACK`（合法前置执行态，允许回退）
/ `STALE`（present-but-unresolvable，Now/Next/leg 全为空，`now_state=STALE_CURSOR`）。
`cursor_status` 随每条投影输出：offline snapshot、Edge journey-snapshot、`/experience`。

写测试时测到的事实（不是我推测的）：`journeys.current_activity_id` 和
`activities.place_id` 都是外键，所以随机 uuid 和编造地点在 SQLite 层就被拒——
"unknown cursor" 的真实形态是**指向另一个计划上确实存在的活动**，它满足外键却对
当前计划不可解析，测试因此改成那个形状。

Edge 侧原来在 cursor 不可解析时说 `"Journey complete"`；这是假话（旅程在进行，是记录
自相矛盾），现在说 `Execution position unresolved` / `Next step unavailable`。
前端 Live 与 LiveSecondary 原来直接读 `activities[0]/[1]/legs[0]`，完全不看 cursor；
现在统一走 `liveActivityWindow`，STALE 时不再显示"Awaiting plan"（那会把旅客推去
选计划，而问题不在旅客那边），并加 `data-cursor-status` 让断言不依赖文案。
`/experience` 的活动投影补 `status`，否则客户端只能靠顺序判断"做完没有"。

## 63. B：Journey 级串行化，以及它不是什么

`backend/app/concurrency_guards.py` 新增 `journey_write_lock(journey_id)`
（RLock 注册表 + WeakValueDictionary）。边界覆盖**完整** read/validate/mutate/commit：
锁在第一次读之前拿、在 commit 之后放，并且拿锁后 `session.expire_all()`，
因为定位 journey_id 的那次读发生在锁外、不能信。接的三个写入点：
replan accept（`_accept_replan_impl` 变成 wrapper，真身在
`_accept_replan_serialized_impl`，agent gateway 走同一条实现所以自动受益）、
payment transaction 端点（commit 与 rollback 都在锁内）、以及 accept 内部的
commitment 升级。

披露按 handoff 要求做在三个地方：常量 `PROCESS_LOCAL_ONLY = True`、模块 docstring
明写"不是多 worker 安全、不是分布式安全"、以及"参考部署是单进程 SQLite 且
SQLite 不支持 SELECT … FOR UPDATE，所以没有数据库层兜底"。
以后换成分布式锁只需替换这一个函数，业务不变量不动。

## 64. C / D：接受竞态断言的是最终全局真值

`_final_truth()` 直接从行里读，不看端点：ACTIVE PlanVersion 集合、Journey 指向、
ACCEPTED proposal 集合、其 proposed_plan_version_id、锚在active plan 之外的 active
commitment、cursor 是否还能解析。每条 schedule 都过 `_assert_one_winner`。

四种 schedule（barrier 同步释放，没有 sleep 当正确性机制）：
同 proposal / 同 proposal（不同幂等键）→ 恰好一个 200 一个 409；
同 proposal 同幂等键并发 → 两个都 200 且只发生一次转换；
竞争 proposal A / B（同一 base plan）→ 恰好一个 ACTIVE，输家落在既有领域状态
`INVALIDATED`（没有为测试新增状态），其 plan 不为 ACTIVE；
replan accept / booking CAPTURE → 见 §65。

## 65. E / CX-EXT-004：CAPTURE 不再盲目升级指针

改前 `service_impl.create_transaction` 的 CAPTURE 分支全程不读 Journey、不读
`active_plan_version_id`、不重跑 gate，直接把 `commitment.activity_id` 指向的行升到
C4。并发放行后，承诺就留在被替换的计划上——旅客被告知他持有一个受保护承诺，
而没有任何权威计划包含它。

现在 CAPTURE 先解析锚点：指向的行仍在 active plan 上就直接通过；否则按结构身份
重绑，0 个匹配或 >1 个匹配一律 `CommerceConflict` → 409。
另外 accept 的重绑范围从"只有 C4"扩到"所有 active commitment"：C4 解析不了就
fail closed（拒绝整次接受），非 C4 解析不了就跳过（它不是承诺，不该因为它把旅客
需要的恢复也挡掉）。

## 66. F：三个重绑点共用一条计数规则

`backend/app/replanning/commitment_remap.py` 是唯一实现：0 → fail closed，
1 → 重绑，>1 → AMBIGUOUS fail closed。身份只比精确相等的集合
（policy 的 semantic key + 锚点活动的 metadata semantic key 为强身份；
`place_id` / `city_service_id` 为弱身份，且只在候选方没有更强语义身份时才用），
再加拉锚时刻（比较瞬时而不是字符串，因为计划按城市偏移归一化而承诺可能是 UTC）。

被替换掉的两处：accept 里的 `candidate.endswith(term)`（字符串相似度冒充身份，
短的键能声称任何共享后缀的长键）；`operations/v9.py` 激活路径的
`by_semantic.get(...) or by_place.get(...)`——匹配不到就**静默跳过**，把承诺留在
被替换的计划上，而且字典推导让 sequence 更大的活动覆盖更小的，重复身份会解析成
"最后写入的那个"。现在两处都走同一 resolver，激活路径解析不了直接 raise。

Sol 的物理身份实现**没有**移植：`compare_physical_venue()`、
`HARD_FEASIBLE_QUALITIES`、mobility provenance 与 fact-quality 规则全部保持本线现状，
`grep` 可验证它们未被本次改动触碰。

## 67. G/H：测试强度是用 mutation 检查挑出来的，不是自评

`_sc_mutation_check.py` 逐个施加破坏、跑收敛套件、还原文件。结果 **8 个破坏，7 个被杀，
1 个存活**：

| 破坏 | 结果 | 被哪些用例抓到 |
|---|---|---|
| B 锁变空操作 | KILLED | 5 条（含锁本身的对照用例） |
| E CAPTURE 不再重锚 | KILLED | 2 条 |
| A 陈旧 cursor 回退成"首个活动" | KILLED | 4 条（含投影 oracle） |
| F accept 的 C4 冲突分支被跳过 | **SURVIVED** | 见下 |
| F1 多个匹配取第一个 | KILLED | resolver 计数用例 |
| F2 零匹配返回 None | KILLED | 3 条 |
| F3 身份退回后缀相似度 | KILLED | 后缀用例 |
| F4 锚定时刻不参与匹配 | KILLED | 2 条 |

存活那一个不是我没测出来，是**它通过公开端点不可达**：把受保护地点从子计划里删掉
会被 feasibility gate 以 `LOCKED_COMMITMENT_LOST` 拒掉，复制一份会被
`ACTIVITY_OVERLAP` 拒掉，两者都发生在 remap 之前。所以该分支是纵深防御，
它的计数行为由 resolver 的直接用例覆盖。我没有为了"杀光"去伪造一个产品到不了的状态，
而是把这条写进用例 docstring 和这份报告。

mutation 检查还抓出我自己写的一条空转用例：第一版 CAPTURE-vs-ACCEPT 竞态用了
**已经 capture 过的 booking**，第二次 capture 必然 409，永远不可能留下悬挂承诺，
把锁拆掉它照样绿。改成未 capture 的 booking（accept 只重绑 C4，看不见它）之后，
它才真的能 stranded。这条也写进了提交信息。

投影差分 oracle（H）在 `test_sol_execution_cursor.py`：参考投影直接从
Activity / JourneyLeg 行重算，比较 `cursor_status`、`now_activity_id`、
`next_activity_id`、`next_leg_id`、`next_mode`、`next_eta_min`，覆盖五种 cursor
状态 + accepted replan 之后一轮；有权威事实的字段不允许任何分歧，没有权威事实时
必须 fail closed 而不是产出外观等价值。为此 `_execution_truth` 补了 `next_leg_id`
（两条 leg 可以有相同 mode 和相同 eta 却是不同承诺）。

浏览器侧新增 `qoder-stale-cursor.spec.ts`：拦截 `/experience` 注入不可解析 cursor，
断言 Live 说"未解决"而不是任何计划里的步骤，并跑同一路径的真实 cursor 作对照。
handler 里那个 `catch` 只用于页面放弃的请求，所以我加了 `served >= 2` 断言，
防止"handler 一直失败"变成静默通过。

## 68. 门禁数字（authoritative 一次运行 `scfull3`，tree `faaa4a8`）

| 门禁 | 结果 |
|---|---|
| authoritative 当前产品套件 | **47 expected / 0 unexpected / 0 flaky / 0 skipped**（127.7s） |
| 与 pass-16 的 45 之差 | +2 = `qoder-stale-cursor`（A/H）与 `qoder-preventive-lifecycle`（C0）；没有用例被删，pass-15 的四条 port 与 D 全部保留且仍绿 |
| 后端全量 | 865 passed / 15 skipped / 0 failed（62.0s；pass-16 是 836，+29 = 本 pass 收敛用例） |
| Qoder/Sol truth contracts 子集 | 175 passed / 0 failed（14.8s） |
| SQLite 争用告警 | 0 次 |
| `typecheck` / `typecheck:all` / `vite build` | 干净（build 5.86s） |
| legacy 非门禁套件（AI 关闭） | 4 passed（20.1s） |
| mutation 检查 | 8 破坏 / 7 killed / 1 survived（原因见 §67，非"全绿"） |
| 数据库不变量探针 | 带索引 REFUSED（1 个 ACTIVE 留下）/ 去掉该索引 ACCEPTED（2 个 ACTIVE）|

## 69. 没有做的，以及请裁

1. **Sol 的 stateful fuzz（60×30）与 catastrophic mutation campaign（17/17）没有复现**。
   本仓不存在任何 property-based / stateful / fuzz 测试（`grep hypothesis|RuleBasedStateMachine`
   零命中），Sol 的 `real_api_state_machine.py`、`mutation_runner.py`、
   `concurrency_harness.py`、`projection_oracle.py` 都在仓库之外的快照目录里。
   按 handoff"不强行凑数、行为与不变量优先"，我交了确定性并发 schedule + 差分 oracle +
   上面那 8 个破坏的 mutation 结果。是否要求把 fuzz/mutation harness 正式移植进本仓
   成为常驻门禁，请裁定——那是新增基础设施，不是本 pass 的范围。
2. CX-SOL-001 / CX-EXT-002 / CX-EXT-003 / CX-EXT-004 我的自评为
   **CLOSED / CLOSED / CLOSED / CLOSED**，证据分别是 §62+用例、§64 三条 schedule、
   §64 竞争 schedule、§65+§67；F 的物理身份按 §66 保持本线更强模型。
   请独立复核而不是接受我的自评。
3. 基线问题（§61）请确认：convergence 叠加在 pass-16 之后是否可接受；
   若要求必须从 0af1905 起算，请给出处置已交付 pass-16 的方式，我不会自行回退。
4. 与 GPT 仲裁那条线（pass-16 §60 的 5 个问题）仍未回复，两条线的裁决顺序请定。

## 70. C0：仲裁抓到的面板 lifecycle 缺陷（我自己没发现）

pass-16 的裁决确认 D 的后端能力与证据都关闭，但指出 `V14PreventivePanel` 有一个窄
blocker，而且正好和同一轮报告 §55 里我自己写下的事实互相打脸：

> GuardianRun 先以 `status=RUNNING / action_status=PLANNING` 落库，之后才变 EXECUTED

我在 API 层为此加了"等同一 run id 到 COMPLETED"的 poll，却在面板里写着"看到任何
preventive run 就停止轮询"。所以旅客如果在动作进行中间打开 `/v8/authoritative`，
面板会永久停在 PLANNING，直到手动刷新。测试没抓到，是因为它自己在 API 层先把 run
poll 到 COMPLETED 才打开页面。

修法按裁决收窄到两点：只有 `status === "COMPLETED"` 才停轮询（RUNNING 与
FAILED_RETRYABLE 继续，因为重试会改变面板正在断言的内容）；不再靠 `runs[0]` 猜
"这是最新一条"，改按 `created_at` 选最新。顺带把裁决要求的排序契约钉成后端测试：
`/guardian/status` 确实按 `created_at desc, id desc` 返回，所以那是一条契约而不是一
个巧合，面板同时也自己排序，将来排序变了不会让它去描述一条旧 run。

新增 `qoder-preventive-lifecycle.spec.ts`：先让 autopilot 真跑出 COMPLETED/EXECUTED
的预防 run（`/guardian/scan` 是反应式控制器，永远不产出预防，这点是测出来的），停掉
autopilot，再把 `/guardian/status` 的第一次响应改成同一 run 的 PLANNING 形态。页面
先渲染 PLANNING，随后**不 reload、不点击**自动变 EXECUTED。
`_sc_c0_sensitivity.py` 把面板改回"见到 run 就停"，这条用例即失败——它不是摆设。

## 71. 把"一个 Journey 只有一个 ACTIVE 计划"交给数据库

裁决给的硬边界是：进程内锁可以是第二道保护，不能成为 CX-EXT-002/003/004 的唯一
closure 依据，否则判 MITIGATED_SINGLE_PROCESS 而不是 CLOSED。我上一轮的提交正好踩在
这条线上，所以改成持久层决定：

1. `ux_plan_versions_single_active` —— `plan_versions(journey_id) WHERE status='ACTIVE'`
   的 partial unique index。两个 ACTIVE 计划在数据库里不可表示，任何进程都一样。
   `_collapse_duplicate_active_plans` 在建索引前清理历史违规（保留最新一条，其余转
   `SUPERSEDED`），否则老库根本建不起来。
2. 接受路径的两次状态翻转改成**条件 UPDATE**：base 必须仍是 ACTIVE、candidate 必须
   仍是 CANDIDATE，谓词由数据库对当前行求值，rowcount 不为 1 就回滚 + 409；commit 时
   的 IntegrityError 翻译成同一个 409，而不是 500。
3. Trip Studio 被新索引当场拦下，而且它报的是真问题：它把子计划以 `status='ACTIVE'`
   插入、之后才把 base 转 SUPERSEDED，于是同一事务里存在过一瞬的两个答案。现在顺序
   由产品决定而不是由 flush 调度决定：建为 CANDIDATE → 退休 base 并 flush → 再晋升。
4. `locked_commitments_preserved` 按裁决定位成 **DERIVED_GUARD_ASSERTION,
   NOT SOURCE_OF_TRUTH**：字段保留（UI/日志/审计有价值），但接受前用**当下**的
   Commitment 行、booking/payment 状态与两个计划的规范活动身份重新推导；若期间新
   CAPTURE 出的受保护承诺会被候选计划破坏，接受被拒。这正是裁决要求并入 CX-EXT-004
   的那件事。

证据不是自述，是两条独立可跑的探针：

- `test_two_sessions_without_the_lock_still_cannot_produce_two_active_plans`：绕开
  `journey_write_lock`，两个独立 Session 直接调 serialized 实现（等价于两个后端进程），
  结果仍是恰好一个 ACTIVE、一个 accepted、一个 409，且零悬挂承诺。
- `_sc_db_invariant_probe.py`：同一份 schema 建两个临时库，用裸 SQL 写两个 ACTIVE，
  带索引那个 `REFUSED (UNIQUE constraint failed: plan_versions.journey_id)` 且只留
  1 个；把那一行索引去掉，同一写入 `ACCEPTED 2 ACTIVE plans`。所以保证在索引里。

副作用值得记一笔：把锁改成空操作后，收敛套件从"5 条失败"变成"3 条失败"——不是因为
变弱了，而是那两条竞态用例现在由数据库兜住，不再依赖锁。这正是裁决要的分工。

## 72. 接受的仲裁更正

- **记账错误**：交付消息里把 pass-16 包写成"21 payload + MANIFEST"，实际是
  22 payload + MANIFEST = 23 entries（MANIFEST 自身也列 22 条）。数字来自包体，
  我写消息时手数错了条目。包不改（改了就换 SHA），在此更正。
- **D 的 owner 位置**：完整 preventive owner 只放 `/v8/authoritative`，不复制进
  `/v8/live`；Live 的责任是渲染预防后的当前权威旅程、且不重复询问已完成的动作——
  这一点已由 `predictive-real-city-v6` 用活动身份对齐证明。
- **real-place 撤回**：接受。预防的语义是"real-city 证据影响了风险与可行性判断并促成
  提前重规划"，不要求最终方案必须塞进一个 `real-place-*` POI；`place-tech-art →
  place-city-park` 用时间余量吸收风险是合法的 preventive response。两个测试不互相
  吞职责，"真实地点进入计划"仍由 v13-5 负责。
- **locked_commitments_preserved**：不降级为装饰字段，也不当最高权威，定位成
  derived guard assertion；已在 §71.4 落成"生成时算一次、接受前按当下承诺真值再验证"
  的后端契约。
- **基线**：确认 convergence 叠加在 `fec2204` 之上、不回退 `0af1905`；Sol 两个
  commit 只作行为/测试参考，不整体 cherry-pick。§61 的处置与之一致。
- **PROCESS_LOCAL_ONLY**：披露措辞采纳，硬边界（不能单独关闭 002/003/004）按 §71
  落到数据库层，不再依赖锁。
- **pass-17**：暂缓。顺序为 fec2204 → C0（已完成）→ Sol convergence A–H（已完成）→
  外部复核 → PASS-17 clean-checkout freeze。pass-17 的两条新增要求已记下：后端也必须
  由 clone 自己声明的环境建立（不得借 `D:\moodle\CityNexus\.venv`），以及运行后
  `git status --short` 必须为空、任何源码/config/test 变化都算 freeze failure，且
  freeze 期间需要改源码即当场 FAIL。

---

# PASS-16.1 — 分布式幂等、迁移真值、freeze 前置

仲裁对 Sol convergence 包的裁决不接受我"四个 CLOSED"的自评，签的是
CX-SOL-001 = CLOSED、CX-EXT-002 = PARTIAL_CROSS_PROCESS_IDEMPOTENCY_OPEN、
CX-EXT-003 = RUNTIME_CLOSED_MIGRATION_TRUTH_OPEN、
CX-EXT-004 = CLOSED_CURRENT_SINGLE_DB_TOPOLOGY，并派下四项 freeze 前收尾。
下面是逐项处置。

## 73. A 同 Idempotency-Key 的跨进程重放语义

我上一轮把 CX-EXT-002 整体判 CLOSED 是过头的：我自己的 mutation log 已经招供——把
`journey_write_lock` 改成空操作后，
`test_replaying_the_same_idempotency_key_never_transitions_twice` 仍然失败。
也就是"同键重放得到同一个成功"这件事，靠的是恰好两个请求落在同一个 Python 进程里。

修法不是再加一层锁。`IdempotencyKey` 行本来就与计划转换在同一个事务里写入，
所以**它的存在就是转换已提交的证明**——这是可复用的既有 durable 记录，不需要新表。
缺的是另一半：冲突时没有人去读它。现在 `_accept_replan_serialized_impl`
执行前先读 durable receipt，执行若以 409 或 IntegrityError 结束，再读一次并回放胜者
留下的规范响应。两个进程、同 proposal、同 key 的结果是：一次转换、一个 ACTIVE、
Journey 指向它、一个 ACCEPTED、零悬挂 C4，两个调用者拿到同一份响应。

有界等待不是时序假设，写进注释里了：恰好一次转换由条件 UPDATE 与唯一索引保证，
与等待无关；如果胜者的 receipt 始终没落，调用者拿到确定的 409，数据库状态仍然正确。
新增 `test_one_idempotency_key_across_two_sessions_replays_without_the_lock`
完全绕开锁调用 serialized 层；mutation A1（把冲突回放拆掉）被杀。

## 74. B duplicate-ACTIVE 的迁移真值

`_collapse_duplicate_active_plans` 原来按 created_at/version_no 选"最新"，
却不看 `journeys.active_plan_version_id`。仲裁指出这会把"两个答案"迁移成
"唯一 ACTIVE 但 Journey 指向被 SUPERSEDED 的那条"——数据库工程非常有创造力。

现在指针优先：Journey 指向的那条 ACTIVE 是幸存者，其余转 SUPERSEDED；
指针不指向其中任何一条时 **fail closed**，抛明确的迁移完整性错误，绝不按时间猜。
两条回归用真实的历史库形状（把当前 schema 里那一行索引去掉建库、植入两个 ACTIVE、
再跑真的 `ensure_schema`）：
指针指向较旧的一条 → 迁移后 ACTIVE 只有它、指针==它、且此后裸写第三条 ACTIVE 被索引拒绝；
指针两条都不指向 → 迁移拒绝，且不许它"顺手"先选一个赢家。mutation G1 被杀。

## 75. C 验证不再改写 tracked 文件

PASS-17 要求跑完 `git status --short` 为空，而这不能靠"跑完 git restore"。
新增 `frontend/e2e/_qoderEvidence.ts`：15 处截图与 provenance 记录都经
`evidencePath(...)` 解析。`CITYNEXUS_EVIDENCE_DIR` 未设时基座仍是 tracked
`reports/`（开发者行为不变），设了就整体落到该目录，且两侧都过 `resolve()`
再比较前缀，防止 `..` 或正斜杠环境变量把文件写出根外。

两种模式都实测过，不是推断：默认模式跑 `qoder-dock-geometry` 确实改动
`reports/dock-geometry/...`；外部模式跑完 `git status --porcelain` 里 reports 一条没有，
而 17 个产物（截图、对比审计 JSON、provenance）都落在仓库外目录里。

## 76. D 仓库自有的扩展真值验证

不搬 Sol 的一次性快照。本仓现在有两件自己的东西：

- `backend/tests/stateful/test_journey_truth_state_machine.py`：确定性 PRNG + 打印 seed
  的有状态机器（venv 里没有 hypothesis，也不为此新增依赖），每步之后都断言七条灾难
  不变量。默认 12×12 随普通套件跑；`CITYNEXUS_STATEFUL_CASES/STEPS` 可调到 60×30。
- `tools/verification/mutation_campaign.py`：11 个破坏，跑收敛套件 + stateful，
  逐条还原。未申报的存活 = 失败；申报为不可达却已被杀 = 也失败（allowlist 不能变成
  让真缺口安度晚年的地方）。

这台机器第一次跑 60×30 就抓到两件事，都值得记：

1. **一个真缺陷**：`select_plan` 只退休其他 SELECTED 计划。在旅程 ACTIVE 时选择另一个
   计划（这是 hard recovery 的既定解决路径，v19.2.3/v19.2.4 两条 gate 就在用），会把
   正在执行的计划丢在 ACTIVE 状态、无人指向——唯一索引看不见它，因为始终只有一行
   ACTIVE。我先试的是禁止这种切换，结果打断了两条合法的恢复流程，说明我判错了对象：
   问题不是切换，是切换时不退休。现在按 `abandoned_id` 条件退休并同步把 cursor 移到新
   计划的首个未完成步骤（否则就留下一个 STALE cursor 去考验投影契约）。
   mutation G2 覆盖它。
2. **我自己写错的两条不变量**：一是"Journey 指针必须落在 ACTIVE 集合里"——PLANNED
   阶段指针指向 SELECTED 计划是合法的，`/start` 才晋升；二是"ACCEPTED 胜者的计划必须
   仍是 ACTIVE"——接受是某一刻的事实，旅客之后换计划会把它 SUPERSEDE，这不代表接受
   没生效。收紧成真正不许的形状：接受过的计划只能是 ACTIVE 或 SUPERSEDED，
   不能还是 CANDIDATE/REJECTED。写错的断言比没有断言更坏，因为它会在对的时候沉默、
   错的时候报警。

---

# RX 吸收与最终数字

## 77. Mission 002 B 节：RX-1/2/3 进权威测试树

基线先量再动手：HEAD `4d2f0c8`，全量 **881 passed / 15 skipped / 0 failed**（88.50s）。

吸收方式是按字节拷贝，不是"照着重写一遍"：三个文件在 `backend/tests/` 下的 SHA-1 前缀与
`_qoder_recovery_20260919/tests/` 里一致（`dd3d0cb92f` / `0a0d679001` / `470516cd59`）。
这样仲裁在 recovery 线上量到的 9 个节点，在这里是同一批 9 个，而不是一批长得像它们的用例。

计数：RX 专集 **9 passed / 0 failed**（1.68s）；全量 **889 passed / 15 skipped / 0 failed**
（88.10s）。889 = 881 + 9 − 1。

精确 test-node 对应表。这里要同时纠正 `4b1e829` 提交信息里的一处误计：RX-2 是 **+2**，
我在那里写成 +3，于是那张表自己加起来是 +9，而实际净增是 +8。表格以下面这份为准。

| 节点 | 变化 | 归属 |
| --- | --- | --- |
| `tests/test_rx1_cross_journey_trigger_gate.py::test_foreign_trigger_is_refused_by_the_journey_scope_guard` | +1 | RX-1 |
| `tests/test_rx1_cross_journey_trigger_gate.py::test_existing_status_code_assertion_would_pass_for_the_wrong_reason` | +1 | RX-1 |
| `tests/test_rx2_mock_hard_laundering_gate.py::test_hard_capture_has_no_mock_fallback_for_an_explicit_fixture_leg` | +1 | RX-2 |
| `tests/test_rx2_mock_hard_laundering_gate.py::test_soft_capture_may_still_degrade_to_the_explicit_fixture_leg` | +1 | RX-2 |
| `tests/test_rx3_stale_cursor_fails_closed.py::test_absent_cursor_may_project_the_first_pending_activity` | +1 | RX-3 |
| `tests/test_rx3_stale_cursor_fails_closed.py::test_matching_cursor_projects_that_activity_and_its_successor` | +1 | RX-3 |
| `tests/test_rx3_stale_cursor_fails_closed.py::test_final_activity_has_no_fabricated_next` | +1 | RX-3 |
| `tests/test_rx3_stale_cursor_fails_closed.py::test_stale_cursor_fails_closed_instead_of_resuming_from_the_first_activity` | +1 | RX-3 |
| `tests/test_rx3_stale_cursor_fails_closed.py::test_completed_prefix_does_not_hide_a_stale_cursor` | +1 | RX-3 |
| `tests/test_wp05_integrity_next.py::test_replan_trigger_event_must_belong_to_same_journey` | −1 | 空转节点退役 |

被删的那条不是"弱"而是"空转"：它给一个不带 affected activity 的 WEATHER 事件断言
`status_code == 422`，而这条请求在守卫存在与否两种情况下都会因为
`REPLAN_TARGET_UNRESOLVED` 得到 422——删掉归属校验它照样绿。RX-1 用真正的 CLOSURE 事件
走到守卫、断言守卫自己的 message、检查没有 proposal 泄漏，再加一条"同一事件在自己的旅程上
可用"的对照；保留旧节点等于复制 RX-1 的第一个用例且证明得更少。退役理由写在了它原来所在的
文件里（`test_wp05_integrity_next.py` 第 77 行起）。

RX-3 与既有 cursor gate 的差别是层次而不是重复：它钉的是 `_execution_truth` 本身——
Today、Live、Edge 共用的那一个真值来源——既有 gate 证明的是服务端投影出来的契约。
`completed-prefix` 那条在两个层次上都是新的。

吸收没有为老 fixture 动冻结区：提交只含 5 个文件（3 个新测试、1 个退役节点、
`tools/verification/mutation_campaign.py` 增加 RX1/RX2 两个破坏），
`HARD_FEASIBLE_QUALITIES`、mobility provenance 与 `fact_quality` 传播、
`MOBILITY_DATA_UNAVAILABLE`、`compare_physical_venue()`、provider-scoped 物理身份、
权威 E2E 策略、单一 ACTIVE 不变式、幂等语义、Live 陈旧游标 fail-closed、
domain/requirements baseline 一行未改。UI 未重构，无清理性改动。

一处诚实的边角：RX-2 文件自带的"前提守卫"函数
`_fixture_pair_is_what_this_gate_assumes` 因为下划线前缀不会被 pytest 收集，所以我吸收
过来的 9 个节点里不含它（若把它算作 +1，RX-2 就变成 +3、净增变成 +9）。我没有为了凑数改名。
它看守的前提也不是没有落点：模块级 `next(...)` 在 mock 矩阵里找不到显式边时直接
`StopIteration`，整个文件在收集阶段就报错，不会悄悄退化成一个恒真断言。


---

## 78. ORD-0008：RX-4 门吸收进权威测试树，并在权威树上正式跑一轮矩阵

### 78.1 吸收与节点对应表

两份门按字节从 `_qoder_rx4_20260920/delivery/` 拷进 `backend/tests/`（SHA-1 一致：
`37b45e3b10`、`f7fb3a93c4`），单独跑 **10 passed / 0 failed**（2.18s）。

计数是 +8，不是 +10，对应表如下：

| 节点 | 变化 |
| --- | --- |
| `tests/test_rx4_c4_generate_gate.py`（7 条） | +7 |
| `tests/test_rx4_c4_protection_surface_gate.py`（3 条） | +3 |
| `tests/test_qoder_generate_anchor_gate.py`（本线一小时前写的临时门，2 条） | −2 |

删我自己那条门的原因不是风格：`test_unresolvable_paid_anchor_refuses_generation_instead_of_omitting_it`
断言的是同一个 422、同一个 `C4_ANCHOR_UNRESOLVED:<key>`，而且还带两个我没有的场景（只有约束能materialise
的确认 ARRIVAL + 它的未确认对照，以及"demo 巡航根本不具备区分力"这条哨兵）。Mission 002 B 不许吸收进
重复语义，反方向也一样。有一条断言没跟着活下来，写在 §78.4。

全量：**907 passed / 15 skipped / 0 failed**（86.97s，解释器 `D:\moodle\CityNexus\.venv`，
`DEEPSEEK_API_KEY` / `CITYNEXUS_AI_API_KEY` 置空）。算术：899 − 2 + 10 = 907。

### 78.2 为什么这一步是阻塞项

Commander 上一轮给 `SUITES` 加了 `tests/test_rx4_c4_generate_gate.py`，而权威树里还没有这个文件。
在这个量具的判定规则下（收集不到 = HARNESS_INVALID，不是跳过），文件缺失会让整轮矩阵作废，
而不是少测一条门。吸收之后权威树 baseline `ran=137`。

### 78.3 权威树上的 17 行矩阵（Commander 的量具，一次未改）

`python tools/verification/mutation_campaign.py --python D:\moodle\CityNexus\.venv\Scripts\python.exe`
工作目录 `D:\moodle\_qoder_integration_20260919`；evidence 落在仓库外
（`CITYNEXUS_EVIDENCE_DIR=%TEMP%\cnx-authoritative-ev`）。每行 ran=137，无一例外；
判定来自 `FAILED` 行而非退出码。

| # | id | 语义破坏 | ran / passed / failed | 杀掉它的测试（首条） | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | A | 陈旧游标像缺省游标一样回退 | 137 / 130 / 7 | `test_completed_prefix_does_not_hide_a_stale_cursor` | KILLED |
| 2 | B | Journey 写锁变空操作 | 137 / 135 / 2 | `test_the_guard_actually_serialises_two_threads_for_one_journey` | KILLED |
| 3 | E | 捕获不再重锚承诺 | 137 / 135 / 2 | `test_capture_reanchors_a_commitment_that_arrived_stale` | KILLED |
| 4 | A1 | 同键冲突不再回放 durable receipt | 137 / 136 / 1 | `test_one_idempotency_key_across_two_sessions_replays_without_the_lock` | KILLED |
| 5 | G1 | 重复 ACTIVE 迁移又按"最新"猜 | 137 / 136 / 1 | `test_migration_refuses_to_guess_when_the_pointer_matches_neither` | KILLED |
| 6 | G2 | 选新计划不退休被抛弃的计划 | 137 / 112 / 25 | `test_journey_truth_invariants_survive_random_operation_orders[…]`（stateful 60×30） | KILLED |
| 7 | F1 | 多候选时取第一条而不是 AMBIGUOUS | 137 / 136 / 1 | `test_two_candidates_for_one_commitment_are_ambiguous_and_fail_closed` | KILLED |
| 8 | F2 | 零候选时返回 None 而不是失败 | 137 / 134 / 3 | `test_a_different_instant_is_not_the_same_commitment` | KILLED |
| 9 | F3 | 身份退化到后缀相似 | 137 / 136 / 1 | `test_a_suffix_of_a_semantic_key_is_not_an_identity_match` | KILLED |
| 10 | F4 | 计划时刻不再是锚的一部分 | 137 / 135 / 2 | `test_a_different_instant_is_not_the_same_commitment` | KILLED |
| 11 | RX1 | 触发事件不再检查 Journey 归属 | 137 / 136 / 1 | `test_foreign_trigger_is_refused_by_the_journey_scope_guard` | KILLED |
| 12 | RX2 | 硬捕获允许退回 mock | 137 / 136 / 1 | `test_hard_capture_has_no_mock_fallback_for_an_explicit_fixture_leg` | KILLED |
| 13 | PROV | 任意 provenance 标签都能洗成实时捕获 | 137 / 130 / 7 | `test_sealed_legacy_synthetic_fixture_without_quality_fails_closed` | KILLED |
| 14 | C4G | 生成候选时付费 C4 不再是硬约束 | 137 / 136 / 1 | `test_unresolvable_paid_anchor_refuses_generation_instead_of_omitting_it` | KILLED |
| 15 | C4A | anchor schedule 不再钉住 ACTIVE C4 | 137 / 135 / 2 | `test_confirmed_external_arrival_is_built_into_every_candidate` | KILLED |
| 16 | RX3NEXT | 陈旧游标从第一个活动继续投影 | 137 / 131 / 6 | `test_stale_cursor_fails_closed_instead_of_resuming_from_the_first_activity` | KILLED |
| 17 | F | 不可解析 C4 被跳过而不是让接受失败 | 137 / 137 / 0 | —（公开端点走不到该分支，理由随 EXPECTED_SURVIVORS 打印） | EQUIVALENT_OR_NON_ACTIONABLE |

汇总（工具自己算的）：`actionable=16 killed=16 survived=0 harness_invalid=0 equivalent=1`，
`campaign: 16 killed / 0 survived / 17 attempted`，`CAMPAIGN PASSED`。跑完 `git status --porcelain`
里 `backend/app` 一条没有 —— 十处被突变过的源文件全部按字节还原（本树这些文件都是 LF，
Commander 那版 `finally` 写回 LF 文本的缺陷在这里没有暴露，但对 CRLF 树是真实的，已随 diff 说明）。

第 17 行的口径冲突仍然待仲裁：Mission 002 C 的字面要求是 `0 SURVIVED / 16 KILLED`，
本表把 F 记为"声明不可达"而非 KILLED。要么按字面砍掉这一行（分母变 16 attempted），
要么接受"16 actionable + 1 equivalent"这个口径 —— 我没有为了让表好看而改它的分母。

### 78.4 一条没跟着活下来的断言，和一次独立交叉验证

本线那条临时门里还有一句：不可解析锚所在 ACTIVE 计划里没有任何 Activity 带着那个 place id，
也就是"确实只有约束在守"。吸收进来的门断言的是承诺 `activity_id is None`，接近但不等价。
它应该补进 RX-4 自己的文件（那是他们的所有权），我没有改一个字节。

交叉验证在一份 disposable worktree（同 `00dfd62`）用我自己的量具跑过：mandate 轨后端可行
13 行全 KILLED（三条前端行因 worktree 无 `node_modules` 未测），扩展轨 12 KILLED + 1 声明不可达；
其中 `anchor_schedule.py:90` 那个站点用整条 `tests` 作门时 `collected=962` 且 KILLED，
"已被现有门覆盖"这句话在我这边也是量出来的，不是转述。

---

## 79. 这一轮的量具边界与一条新发现（不是任务，记下来免得下次重新发现）

### 79.1 `/twin` 不参与"游标是否可信"这件事

`cursor_status` 目前只有两个消费者会算：`operations/v9.py::_execution_truth`（`STALE` /
`VALID` / `ABSENT_FALLBACK`）和 `stay_mobility.py::_active_plan_payload`（`/experience` 用的那份，
三态判据与前者一致，逐条对过）。`GET /api/v1/journeys/{id}/twin` 走
`_twin_snapshot`，它把游标按 ACTIVE 计划解析：

```python
current = next((item for item in activities if item.id == current_id), None)
```

这一步本身是对的（游标落在被替换掉的计划上时不会认错活动），但它把"游标不可解析"和"还没有游标"
压成同一个 `None`，而且 `JourneyTwinSchema` 里没有任何字段能表达这个区别。
结果是一个只读 twin 的消费者看见 `derived_now = journey.start_at`：那既不是旅行者的位置，
也不是计划的真相，而是一个填补出来的默认值。这属于 ORD-0007 同一族的问题（两个消费者对
"现在在哪"必须给同一个答案），但形态不同——那里是互相矛盾，这里是**沉默**。

我没有擅自改它：给 schema 加字段是契约变更，超出 ORD-0006/0007 的字面范围。
最小改法是 `_twin_snapshot` 复用同一条三态判据（活动列表已经在手上了）并在 schema 上暴露
`cursor_status`；要动的话我一次做完，连带一条 `/twin` 与 `_execution_truth` 的差分回归。

### 79.2 `len(legs) > len(activities)` 不是这棵树能自然长出来的形状

ORD-0006 要的权威回归必须先有这个形状才可能失败。三处写腿的产品代码
（`operations/v9.py:664`、`main.py:4620`、`planning/authoritative_v12.py:1383`）都按"相邻活动成对"
写，恒等于 `len(activities) - 1`；demo 生成的计划一条腿都不写。所以权威回归里那条腿是我按 schema
直接持久化的（腿的 `from_activity_id` / `to_activity_id` 可空是设计如此，一条只连两个 place key
的 provider 事实本身是完整事实）。

这意味着 ORD-0001/0006 的修法性质上是**契约加固**，不是"复现了一个正在发生的错误"。
但 Commander 的指纹（`next_mode="AUTO"`、`next_eta_min=29`）来自一份真的多出一条腿的计划——
如果那不是手摆的，那么"谁写了第 N+1 条腿"本身是另一条缺陷，值得单独开一单，我不想把它顺手吸进
这条已经收口的修复里。

### 79.3 矩阵现在有两份实现，只应该有一份数字

Commander 按仲裁 Amendment B 直接修了 `tools/verification/mutation_campaign.py`（ORD-0002），
我不再碰那个文件；我把带 canonical `J-*` 行、逐行 declared gate + `--collect-only` 前置、
模糊 anchor 拒绝、按原行尾字节还原 + SHA-256 校验、journal/`--recover`、evidence JSON 出仓、
以及三条前端行的版本作为 diff 交付在 `_qoder_recovery_20260919/patches/CNX-002C-mandate16-*`。
两份的分母不同：Commander 那版是 16 actionable + 1 equivalent（键名 `A/B/E/A1/G1/G2/F1-F4/RX1/RX2/PROV/C4G/C4A/RX3NEXT/F`），
我这版是 16 条 mandated（`J-*` + `RX4-C4-GENERATE-ANCHOR`）外加 13 条本线自有缺陷单列。
外部仲裁拿到的表需要能对上 `mutation_manifest.json` 的 15 个 id，这一点只有后一种键名能直接对上。

我在一份 disposable worktree（同 `00dfd62`）里跑过自己那版的后端可行部分，数字独立可查：
mandate 13/13 KILLED（三条前端行因 worktree 无 `node_modules` 未测），扩展轨 12 KILLED + 1 声明不可达，
`Q-ANCHOR-SCHEDULE-C4` 用整条 `tests` 作门时 `collected=962` 且 KILLED —— 这就是"anchor_schedule.py:90
已被现有门覆盖"这句话在我这边的测法，不是转述。


---

## 80. Mission 002 E：本轮全门禁数字（权威树、HEAD `21cbf22`，全部为实测）

解释器统一是 `D:\moodle\CityNexus\.venv\Scripts\python.exe`（含 ortools），
后端命令都清空 `DEEPSEEK_API_KEY` / `CITYNEXUS_AI_API_KEY` 并置 `CITYNEXUS_AI_ENABLED=false`。

| 门禁 | 命令要点 | 结果 |
| --- | --- | --- |
| 后端全量（集成门） | `pytest -q` in `backend/` | **907 passed / 15 skipped / 0 failed**（86.97s） |
| 权威突变矩阵 | Commander 那版 `tools/verification/mutation_campaign.py`，未改一字 | baseline `ran=137`；**17 attempted / 16 KILLED / 0 SURVIVED / 0 HARNESS_INVALID / 1 EQUIVALENT**；`CAMPAIGN PASSED` |
| 扩展 stateful 门 | `CITYNEXUS_STATEFUL_CASES=60 CITYNEXUS_STATEFUL_STEPS=30`，`tests/stateful tests/test_qoder_next_leg_binding.py tests/test_sol_execution_cursor.py tests/test_rx4_c4_generate_gate.py tests/test_rx4_c4_protection_surface_gate.py` | **86 passed / 0 failed**（31.62s；60 + 4 + 12 + 7 + 3 = 86） |
| 前端类型门 | `npm run typecheck` / `npm run typecheck:all` | 各自退出码 **0**，无新增 TypeScript 错误 |
| 前端构建 | `npm run build` | 退出码 **0**（generateSW，9 entries / 2301.56 KiB） |
| 权威 E2E | `CITYNEXUS_E2E_AUTHORITATIVE=1`，run `ord08-20260920a`，前端 :3153 / 后端 :8153，`CITYNEXUS_DATABASE_URL=sqlite:///./_ord08-20260920a.db`，`reuseExistingServer=false`，`--reporter=json` | **47 expected / 0 unexpected / 0 flaky / 0 skipped** |

权威 E2E 的来源指纹（stderr，逐条核对过）：

```
[citynexus e2e] suite=current-product authoritative=true python=D:\moodle\CityNexus\.venv\Scripts\python.exe
                frontend=:3153 backend=:8153 db=sqlite:///./_ord08-20260920a.db ai=disabled reuseExistingServer=false
[citynexus e2e] provenance ok: run=ord08-20260920a frontend=:3153 -> backend=:8153 ai=disabled db=_ord08-20260920a.db
```

也就是说这两次跑的数字属于这一棵树、这一次调用：自己的解释器、自己的端口、自己的一次性库，
AI 关闭，且 `/health` 的回显是经前端 origin 拿回来并核对过 run token 的。

### 80.1 “验证不改写 checkout”这一条是怎么核的

矩阵与 E2E 都跑完之后 `git status --porcelain` 只剩两条：
`tools/verification/mutation_campaign.py`（Commander 的量具，我不写）与
`qoder-handoff/qoder_xiaomi_truth_hardening_v6.patch`（另一条线的交接补丁）。**两者都不是本层的改动**，
并且本轮开始前就已经在那里。除此以外没有一条 backend/、frontend/、reports/ 的改动，
截图与 provenance 全部落在 `CITYNEXUS_EVIDENCE_DIR`（仓库外）。

十处被突变的源文件逐一按字节还原：矩阵自身只在 `finally` 里写回原字节，
本层跑完后另用 `git status` 复核，不依赖工具自报。

### 80.2 一项已裁（口径如下），一项仍等令

1. **已裁** —— 真总线 `Canshu-King/CityNexus-Workspace` Issue #1（评论 5745031386 / 5745135961）：
   口径是 **16 actionable + 1 equivalent，且 equivalent 那一行在分母之外**。
   所以本表保持 17 行、`F` 仍记 `EQUIVALENT_OR_NON_ACTIONABLE` 并带不可达理由：
   **没有删行，也没有把它伪造成 KILLED**。"0 SURVIVED / 16 KILLED"与这张表不再冲突——
   那句约束的是 16 个 actionable，等流行本来就不在它里面。
2. §79.1 的 `/twin`：它按 ACTIVE 计划解析游标（正确），但 `JourneyTwinSchema` 里没有任何字段
   能表达"游标存在但不可解析"，消费者只能看见 `derived_now = journey.start_at` 这个被填出来的时间。
   这是 ORD-0007 同族但形态不同（那里是互相矛盾，这里是沉默）。改它要动 schema，属契约变更，
   等令再动；连带一条 `/twin` 与 `_execution_truth` 的差分回归。
   （这与 ORD-0011(3) 冻结的是同一件事：Mission 002 期间 `/twin` 顶层 `projection_status`
   保持 `READY|DEGRADED`，执行新鲜度只走嵌套 `cursor_status`。未动。）


---

## 81. ORD-0010：recovery 卡的幽灵键，以及用另一把量具把 mandated 16 行重测一遍

### 81.1 修的是什么，以及它今天有没有伤到旅客

`LiveRecovery` 读的是 `context.execution.current_activity_id`。这个键不存在——那份 dict 是
`_execution_truth()` 的返回，键是 `now_activity_id / next_activity_id / cursor_status /
persisted_cursor`；twin 在**上一层**确实有一个叫 `current_activity_id` 的字段，两边混了。
于是读出来永远是 null，紧跟的 `?? activities[0]` 就把首站永久钉成"现在"。

但必须说清楚严重性的真实边界：`design-tokens.css:389` 把 `.live-shell` 下这张卡的 intro
整块 `display: none`（注释原话是 Live 已经显示唯一当前状态、把重复标题留在 DOM 里）。
所以今天旅客在 `/v8/live` 上并没有读到那个错步骤——谎言被算出来、被渲染进 DOM，屏幕阅读器跳过它，
但任何别的 markup 消费者不会。这也决定了门的形状：两头都断言（卡解析出的身份 + 可见 Live 标题同意），
这样 Amendment C 那一路重新排这一屏时，卡不会把一个假 Now 抬到可见区。

门：`frontend/e2e/qoder-live-recovery-cursor.spec.ts`，3 collected。

* 用例 1 完全不加拦截：走产品自己的 `/complete` 两次，要求卡与可见标题都指向第三个活动；
* 用例 2 把"游标存在但不可解析"同时喂给 `/twin` 与 `/experience`（只改一个等于测试自己造出两个
  消费者的分歧，什么也测不到）；
* 用例 3 是这一轮新发现的无主守卫（见 81.2）。

突变验证：把修法退回 phantom key + 索引零兜底 → 3 个节点里 2 个失败，实测
`data-now-activity-id` 打出 `3a58c470`（activities[0]）而 twin 给的是 `61e3096d`（activities[2]），
不可解析态打出 `"Next: Old Town Gate"`（首活动标题）；源文件跑完字节还原 sha256 一致。
干净态 4 passed / 0 failed（run `ord10-c` / `ord10-d`，backend :8163 / :8398，一次性库，`ai=disabled`）。

顺带把 Live 自己的第三态补齐：有 ACTIVE 计划但没有待执行步骤时，标题与副行原本说
`Awaiting plan` / `Select a plan to calculate your route`——都是对"已经有计划"的不实陈述。
新增一个 locale 键 `live.nothingDue`（en + zh），卡与 Live 共用，避免同一状态两种说法。

按令未动：`main.py:5220` 的 twin `projection_status` 仍只在 READY/DEGRADED 之间取值（等仲裁裁 schema）。
同一族还剩第三处：`V10LiveExecutionPanel.tsx:53` 只要游标存在就说 `In progress`（含陈旧游标），
诚实的修法是把解析后的窗口传进去，而不是继续读原始 `current_activity_id`——这条我没有擅自扩。

### 81.2 一条"有守卫、没主人"的前端缺陷

`liveActivityWindow` 里"Now 必须非终结态"的守卫，删掉之后整套验收门全绿。
这是突变矩阵要抓的那一类缺陷（守卫无人认领），只是层次在浏览器里。
补了用例 3：通过产品自己的完成动作把游标留在一个 COMPLETED 活动上，要求可见标题
说"现在没有待进行的步骤"而不是复述那个已完成的步骤标题。

这条直接改变了矩阵的结论：`J-LIVE-FIXED-INDEX` 原本报 `SURVIVED`（collected=2，门选错了文件——
`live-autopilot-v5.spec.ts` 从不构造这个状态），把门加宽到真正持有断言的 spec 之后变成
`KILLED`（collected=6）。也就是说：一次"存活"其实是量具指错了地方，不是产品没有守卫。

### 81.3 用另一把量具把 mandated 16 行重测一遍（同一棵树，内容即 `a75ba7a`）

命令（权威树，仓库外 evidence）：

```
python <candidate matrix> --repo D:/moodle/_qoder_integration_20260919 \
  --lane M --full --e2e-backend-port 8405 --e2e-web-port 3405
```

结果：`mandate: attempted=16 killed=16 survived=0 harness_invalid=0 declared_unreachable=0
rows_with_zero_collected=0`，`CAMPAIGN PASSED`。逐行 collected：

| 行 | collected | 行 | collected |
| --- | --- | --- | --- |
| J-ACK-RESOLVED | 2 | J-AMBIGUOUS-ADMITTED | 23 |
| J-CROSS-JOURNEY-TRIGGER | 1 | J-PROTECTED-C4-DROPPED | 7 |
| J-ACK-CLOSES-UNRELATED | 3 | J-PARTIAL-BUDGET-FULL | 3 |
| J-PROVENANCE-LAUNDER | 24 | J-LIVE-FIXED-INDEX | 6 |
| J-NONE-QUALITY-HARD | 24 | J-STALE-CURSOR-FALLBACK | 5 |
| J-MOCK-HARD-FALLBACK | 1 | J-MATERIALITY-DIFF | 1 |
| J-NONE-NONE-PHYSICAL | 23 | RX4-C4-GENERATE-ANCHOR | 1 |
| J-COORDINATE-ONLY-SAME | 23 | J-CROSS-PROVIDER-NUMERIC | 23 |

同一次调用尾部的集成门（Mission 002 E）：`ran=970 / 955 passed / 15 skipped / 0 failed`。
**970 与 §80 的 922 不矛盾**：这把量具的 ENV 固定 `CITYNEXUS_STATEFUL_CASES=60`（§80 那次是默认 12），
60×30 的有状态机比 12×12 多 48 个参数化节点，907 + 48 = 955 passed，922 + 48 = 970。

这也顺手解掉 §80.2 第 1 条那个分母冲突：mandated 16 行全部 KILLED，而那条"公开端点走不到"的
`Q-ACCEPT-PROTECTED-SKIP` 放在另一轨并带理由打印，于是 "16 attempted / 16 KILLED / 0 SURVIVED /
0 HARNESS_INVALID" 字面成立，不需要把任何一个行改名或删掉。Commander 那版量具仍是权威，
这一版是候选与交叉验证（`patches/CNX-002C-mandate16-*`）。

### 81.4 前端门必须自带来源指纹

这轮我自己踩了三次，都值得写下来给下一个量具作者：

1. Playwright 门不带 authoritative 环境跑，就会连到别的 lane 已经开着的 :8000——一行"绿"
   测的是别人的树；候选现在拒绝在没有 run id / 端口 / 一次性库时运行前端门。
2. 一整行共用一个 run id：干净态那次创建 `_mut<stamp>.db`，突变那次想重开同一个文件，
   fresh-or-no-run 守卫直接拒启——现象是"突变下 0 条执行"。现在每次调用一个 token。
   这条恰恰证明那道守卫是对的：它宁可不开，也不让两次测量共用一份库。
3. 汇总行的取法：Playwright 的 line reporter 把 `N failed` 单独成行、后面才是
   `M passed (Xs)`，只取最后一条匹配行会把"有失败"读成"全通过"。现在两种计数都进表。


---

## 82. ORD-0011 / ORD-0017 / ORD-0024：结构不变式、四例门、两句文案与一个"别再来修"的注释

### 82.1 ORD-0011 (1)：只补真正没人守的那件事

Commander 的 05:36 更正我接受，而且它说得很具体：精确缺席元组**已经有权威看守**——
`backend/tests/test_sol_execution_cursor.py:499-515` 用整字典相等钉住九项，512-515 行连 Edge 视图
一起钉。所以把四项断言抄进 `test_rx3_stale_cursor_fails_closed.py` 是零新增覆盖，我没抄。

补的是那条结构不变式，而且必须跨形状成立：

```
next_leg_id is None  <=>  (next_mode, next_eta_min) == ("NONE", 0)
```

`tests/test_qoder_next_leg_binding.py` 新增 4 collected（3 个参数化形状 + 1 条正向陈述），
形状是 `0 腿计划 / 每跳一腿 / activities=9·legs=10`（后者正是 `journey_legs`
ON DELETE SET NULL 的合法持久态），每个形状里再扫三种完成模式 × 去重后的游标状态，
`checked >= 8` 保证参数化不是摆设。正向那条要求：只要给出了 mode/eta，就必须给出腿的身份，
而且那个身份必须真在本计划的腿列表里——一个没有 id 的时长没法刷新、复核或向旅客解释。

鉴别力实测（一次性突变，字节还原 + sha256 校验，两文件共 21 collected）：

| 突变 | 结果 | 杀掉它的节点 |
| --- | --- | --- |
| `next_eta_min` 在腿为 null 时仍给 17（混合缺席编码） | 11 failed / 10 passed | 三条结构参数化节点、Edge 结构节点，以及原有 STALE/完成态/差分 oracle 各条 |
| Edge 的 `mode` 不再读共享投影（写死 "WALK"） | 5 failed / 16 passed | `test_the_edge_copy_honours_the_same_leg_rule_as_the_projection` 与 ORD-0007 两条跨消费者门 |

### 82.2 ORD-0011 (4)：Edge 那份副本也要守同一条规则

`v9.py` 的 Edge 快照现在与离线快照共用一次投影判断（这是 ORD-0007 的修法）。
光"两处相等"还不够：一份一致地错着的响应照样能让手表显示一段没人承诺的路。
所以新增 `test_the_edge_copy_honours_the_same_leg_rule_as_the_projection`，
对 5 个游标状态各断两件事——两侧各自满足 `null <=> ("NONE", 0)`，以及两侧彼此相等。

### 82.3 ORD-0011 (2)：LiveRecovery 的四例门，以及哪一例负责击杀

`frontend/e2e/qoder-live-recovery-cursor.spec.ts` 现在 4 collected，覆盖仲裁点名的三例
（VALID 解析出精确 id / STALE 不回退首项 / 空活动列表不凭空造 current），加上一例
"游标落在已完成步骤"（82.4）。一次性把 `?? activities[0]` 加回去之后：

```
Running 5 tests … 3 failed / 2 passed
  case 1  期望 data-now-activity-id 61e3096d（activities[2]），实到 3a58c470（activities[0]）
  case 3  期望 "Execution position unresolved"，实到 "Next: Old Town Gate"
  case 4  失败在拦截计数上，不是失败在契约断言上
```

**所以击杀由 case 1 与 case 3 承担，case 4 不是鉴别器**：在突变下它的契约断言没有变红，
只有记账断言变红。我先把结论按测量写下来，再把那条会误报的记账断言删掉——它依赖
`/plans` 这条 route 真的被命中，而这个 PWA 的 service worker 可以从缓存回答计划列表，
于是"门没跑"和"产品出错"在报表里长成同一个样子。删掉它不减少覆盖，因为被保证的东西
在前面那行断言里。这也把我一开始写进注释的预测推翻了一次：我原以为空列表那一例
无论如何都不会变红，实测它变红了、但红在错误的地方——那正是更值得修的东西。

`seen.experience` / `seen.twin` 的计数保留：那两条 route 是断言成立的前提，不是装饰。

### 82.4 顺带发现：一个前端守卫没有人守

`liveActivityWindow` 里"Now 必须非终结态"的判断，删掉之后整套验收门全绿。
补了 case（游标停在一个已完成、后面还有未完成活动的步骤），要求可见的 Live 标题说
"现在没有待进行的步骤"，而不是复述那个已经做完的步骤标题。

### 82.5 ORD-0017 (1) 与 ORD-0024：两句措辞

1. Wallet 的 `Bookings()` 面板里，标题写"导入预订"，正文却让旅客"去 行程 · 预订 粘贴确认单"，
   并声明"这个页面只用于结构化数据"——**旅客此刻就在 Bookings 里**，而这句话把人支使自己站着的地方。
   改为：`结构化导入在这里：展开下方「高级」粘贴 JSON 确认单。确认单文本与截图走行程收件箱。`
   不再撒谎的那句是第二句的否定形式：它不再声称"这里只能结构化 / 别处才能粘贴"，而是说出这个面板实际有的
   入口（Advanced → JSON），并把确认单文本、截图两类输入指给行程收件箱——那边确实有 paste 与
   screenshot（`accept="image/*"`）两个 tab，这句我是读了 `JourneyInboxWorkbench.tsx:466/587/595`
   才写的。逻辑与结构未动，纯文本替换（en/zh 同步）。
2. Journey 创建那处的提前 return 保持原样，只补了注释：Amendment F 裁定它是刻意的
   focused pre-Journey onboarding，首进门不给全局底部主导航；下一辆车道（含 UI 车道的 onboarding
   wrapper）不要再把它"顺手修好"——为一块屏幕去迁移壳层，比它换来的措辞代价大得多。
   注释归我，wrapper 归它，没有互相伸手。

### 82.6 这一轮收口时的门禁数字

| 门禁 | 结果 |
| --- | --- |
| 后端全量（默认 12×12 stateful） | **912 passed / 15 skipped / 0 failed**（67.23s） |
| `npm run typecheck` / `typecheck:all` / `build` | 退出码 0 / 0 / 0 |
| 权威 E2E（全 current-product 套件） | **51 expected / 0 unexpected / 0 flaky / 0 skipped**（provenance：web :3419 → backend :8419，一次性库 `_ord11-e2e2.db`，ai=disabled，reuseExistingServer=false） |
| 本门 4 collected 的干净复跑 | 5 passed / 0 failed（含 real-seed setup 1 条） |

算术：§80 的 907 + 结构不变式 4 + Edge 结构门 1 = 912；
E2E 从 §80 的 47 加到 51（本 spec 从 2 例增到 4 例）。

那一次 51 之前还有一次全量：`50 expected / 1 unexpected`，红的是
`product-v8.spec.ts :: completes the multi-day stay and autonomous recovery journey`，
状态 `timedOut`（60s 上限），同一时刻后端全量与别的车道正在同一台机器上抢 SQLite
（webserver 日志里能看到 `JourneyTwin cache write skipped … database is locked`）。
把它单独重跑是 **3 passed / 16.0s**。结论：不是产品缺陷，也不假装它没发生——这条门在满负载下
会自己超时，属于验收稳定性欠账，和 §80 那次 7 failed/1 error 的噪声同源；我没有为它放宽
任何断言，也没有把负载下的红擦掉，只是补了一次可复现的隔离复跑作为证据。


---

## 83. ORD-0028 与 ORD-0026：一支更宽的门进树，游标家族的第三处结案

### 83.1 ORD-0028：RX-4 更正版 generate 门吸收（8 节点）

`backend/tests/test_rx4_c4_generate_gate.py` 换成 delivery 版，逐字节一致（24,513 B，LF，SHA-256 相符）。
拷贝前逐行核过 diff 只有两处：`from app.db.models import` 一行扩成 `Activity, Commitment, Journey`，
以及追加的 `_import_unresolvable_reservation` + 新节点
`test_nothing_outside_the_commitment_pins_the_unreachable_anchor`。没有夹带别的。

跑（命令原文）：

```
cd D:\moodle\_qoder_integration_20260919\backend
DEEPSEEK_API_KEY= CITYNEXUS_AI_API_KEY= CITYNEXUS_AI_ENABLED=false \
  D:\moodle\CityNexus\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --no-header tests/test_rx4_c4_generate_gate.py
-> 8 collected, 8 passed, 2 warnings in 1.53s
```

全量后端 **913 passed / 15 skipped / 0 failed**（912 + 1）。

顺带把 §78.4 我认下来的那条缺口销掉：那个"ACTIVE 计划里不得有任何 Activity 钉住不可解析锚点"的前提，
现在由 RX-4 自己的新节点守（还多了未确认对照 201+3 候选、以及全库 `strays == 0`）。
它自我修正的那一步（上一版报 "C4G owners 2/2"、更正后实测 1 failed / 7 passed、owner 一个）
也该记一笔：**收窄的断言才是能被突变检验的断言**。

给 Commander 的连带后果要更正一个数：SUITES 的 collect 现在默认 12×12 下是 **91**，
按 60×30 换算即 **139**，不是 138。原因是那 11 个路径里有两处进了新节点——
RX-4 这支 +1，以及 `test_sol_execution_cursor.py::test_the_edge_copy_honours_the_same_leg_rule_as_the_projection`
（`7f9bb69`，ORD-0011 (4)）+1。除这两处外我没再动 SUITES 里的文件，可以一次跑完整场矩阵再引用 C 节。

### 83.2 ORD-0026：游标家族的第三处，结案

`V10LiveExecutionPanel` 用 `clock.data.current_activity_id` 判断"是否在进行中"——那是**持久指针的存在性**，
不是执行位置。一个字段给出两个错答：陈旧游标 → "in progress"（人根本不在那一步）；
旅程已完成 → "awaiting plan"（有计划，只是走完了）。现在它解析窗口后四态回答：
解析出步骤 → in progress；游标不可解析 → Execution position unresolved；
有计划但无待执行 → Nothing is due right now；无计划 → Awaiting plan。

解析器被**移**到 `src/lib/executionWindow.ts`（不是再抄一份）并带上 `cursorStatus`：
这一夜三次分歧（Live、recovery 卡、这个面板）根因都是"同一个三态规则有多个实现"，
第四份拷贝只会看起来一致到有人突变它为止。文案没有新造：unresolved / nothing-due 复用
Live 与卡已经在读的同两个 locale 键，所以可见文案改动只涉及既有标签——这就是订单里说的
"不需要 UI 车道配合的那一半"。Story 被迫显式写 `plan: null`：窗口由 props 解析之后，
"这块故事里没有计划"必须是故事自己下的判断，而不是组件替它猜。

实测（指标加了 `data-testid="v10-current-step"` 让断言点名字段而不是猜文本）：

| 状态 | 结果 |
| --- | --- |
| 干净态本 spec 4 collected | 5 passed / 0 failed（12.7s，run `ord26-b`，backend :8423，一次性库，ai=disabled） |
| 把旧的"存在性判断"塞回去 | 2 failed / 3 passed：已完成步骤那例期望 "Nothing is due right now" 实到 "in progress"；STALE 那例期望 "Execution position unresolved" 实到 "in progress"；源文件字节还原 sha256 相符 |
| 门 | typecheck / typecheck:all 退出码 0 |

### 83.3 本轮收口数字

| 门禁 | 结果 |
| --- | --- |
| 后端全量 | **913 passed / 15 skipped / 0 failed**（62.28s，在 `d322547` 上重跑） |
| typecheck / typecheck:all / build | 0 / 0 / 0 |
| 权威 E2E（current-product 全套） | **51 expected / 0 unexpected / 0 flaky / 0 skipped**（run `ord26-e2e`，web :3427 → backend :8427，一次性库 `_ord26-e2e.db`，ai=disabled，reuseExistingServer=false） |
| 本线 HEAD | ``d322547`` |


---

## 84. ORD-0029：一个键名只该有一套词表，以及"门自己把自己跑红"的那类断言

`data-cursor-status` 之前同时存在两种取值域：后端契约是
`VALID | STALE | ABSENT_FALLBACK`，而 `V8Experience.tsx` 的前端派生值是
`VALID | STALE | ABSENT`。两边各自都说得通，但同名不同域，下一个读测试的人会拿
`"ABSENT"` 去推后端枚举——今晚反复在防的正是这种误读。

订单给了两条路：(a) 改名成前端展示态的名字，或 (b) 保留名字加注释说明对应关系。
两条都没选，因为都留下两套词表。共享解析器（`src/lib/executionWindow.ts`，ORD-0026 建）本来
就产出与后端**同一域**的 `cursorStatus`，标题直接发布它即可：

```
before:  STALE | VALID | ABSENT                 ← ABSENT 在后端从不出现
after:   STALE | VALID | ABSENT_FALLBACK | UNKNOWN   ← UNKNOWN 是"还没拿到计划"，取数态不是执行态
```

原来断言 `ABSENT` 的两处，现在各自说出它真正构造了哪个事实：没有游标 = `ABSENT_FALLBACK`；
游标指向一个已完成活动 = `VALID` 且无 Now。后者正是 `ABSENT` 抹掉的区别，方向和 ORD-0007、
ORD-0026 一致。

同一次改动里删掉了所有"拦截计数"断言，理由是测量而不是洁癖：配对跑出现过一次
`Expected: >= 1 / Received: 0`，同一条命令再跑就过——最脆的那行是"route handler 命中了几次"。
service worker 可以从缓存回答请求，而那些例子里每一条实质断言都只有注入状态真的到达页面才可能成立，
所以"拦截没生效"本来就会让真断言变红；计数只多提供了一种**为错误的理由变红**的方式。

实测：`typecheck:all` 退出码 0；受影响两份 spec 连跑两次各 6 passed / 0 failed
（run `ord29-c` / `ord29-d`，各自端口与一次性库）。收口复跑在 `94295e5`：
后端 **913 passed / 15 skipped / 0 failed**（64.94s）、build 0、权威 E2E
**51 expected / 0 unexpected / 0 flaky / 0 skipped**（run `ord29-full`，web :3437 → backend :8437）。

## 85. ORD-0030：UI 过夜车道合进权威树，以及一次"我自己把门跑红"的记录

合并本身没有戏剧性：Commander 已用一次性 worktree 试过合（"Automatic merge went well"、
零 unmerged 文件），我在真树上做同一件事——`git merge --no-ff --no-commit agent/ui-overnight-20260920`
→ 零冲突 → 提交为 **`5a33eaf`**。`git show --stat`：**11 个文件、+1628 / −25**，
其中 **零个 `backend/` 路径**：

```
UI_OVERNIGHT_PLAN.md · frontend/index.html · frontend/src/design-tokens.css
frontend/src/styles.css · frontend/src/v10.css · frontend/src/features/setup/JourneyTrialSetup.tsx
frontend/e2e/_qoderMobileScan.ts · frontend/e2e/qoder-mobile-ui-overnight.spec.ts
frontend/e2e/qoder-ui-overnight-shots.spec.ts · review/UI_OVERNIGHT_{BASELINE,EVIDENCE}.md
```

也就是说这一笔确实"只动前端"，Commander 预登记的那个判断条件（Amendment E 1b：只有 `source=`
目标文件或 owner 节点被碰到才重跑矩阵）不成立，矩阵不必因为我重跑。

### 85.1 合并前后：同一命令、同一口径

| 门 | 合并前 `a98babb` | 合并后 `5a33eaf` |
| --- | --- | --- |
| 全量后端 `pytest -q -p no:cacheprovider --no-header`（AI 关） | 913 passed / 15 skipped / 0 failed（64.94s） | **913 passed / 15 skipped / 0 failed（66.40s）** |
| 权威 E2E `--reporter=json`（自有端口、一次性库、ai=disabled、reuseExistingServer=false） | 51 expected / 0 unexpected / 0 flaky / 0 skipped | **54 expected / 0 unexpected / 0 flaky / 5 skipped**（152.5s） |
| `npm run build` | 退出码 0 | **退出码 0** |
| `npm run typecheck` / `typecheck:all`（不接管道，`> file 2>&1` 后读 `$?`） | 0 / 0，`error TS` 0 条 | **0 / 0，`error TS` 0 条** |
| UI 车道三道门（同一套件内的逐条） | 不在本树 | **contrast-audit 4/4、mobile-overflow 1/1、today-hero 2/2** |
| 新 12 点门（3 视口 × 4 界面 = 12 个测量点） | 不在本树 | **3 passed；溢出 0 / <44px 0 / 截断 0 / chrome 重叠 0 / CTA 被遮 0 / 找不到 CTA 0** |

后端总数一字未动，符合"只动前端则不应变"的预期，所以这一轮没有需要压的意外。
E2E 的 +3 expected 正是 12 点门；**5 skipped 全部来自 `qoder-ui-overnight-shots.spec.ts`**——
它按设计在没有显式 `CITYNEXUS_SHOT_LABEL` 时跳过，理由是防"整套跑悄悄把 before 基线刷成改后像素"，
所以 skip 是这道门的正确行为，不是漏跑。我另外单独按标签跑了一次以证明这份文件在合并树上可用：
`CITYNEXUS_SHOT_LABEL=after` → **6 passed（30.3s）**、20 张 412x915 明/暗截图（5 场景 × 明暗 × 整页/首屏），
落在仓库外的证据目录，`git status` 未新增任何跟踪文件。

12 点门的逐条数字是从门自己写的原始测量里数出来的（`ui-overnight/geometry-*.json`：seeded 9 行
+ setup 3 行 = 12 个测量点），不是复述车道自报；触控分层对照也在同一份产物里：
桌面 30px 紧凑、移动 44px 达标。

### 85.2 我第一次的全量后端跑是红的，红在我的调用方式

第一次 `pytest -q`（同一棵合并树）：**9 failed / 902 passed / 16 skipped / 1 error（307.32s）**。
我没有把它当成"合并引入的回归"报上去，先查了机制：

- 那一次我**没有清 `DEEPSEEK_API_KEY`**（这条会话的 shell 里它是设着的），
  而门要求的正是"AI 必须关"。权威 E2E 的 `playwrightEnv.ts` 会因这个键直接拒绝启动；
  pytest 侧**没有对应的守卫**，于是它带着真键跑了 AI 路径。
- 9 条失败的族谱支持这个归因：`test_guardian_v4`(3)、`test_v13_integrity`(gateway)、
  `test_v15_copilot`（用例名本身就是"without deepseek configuration"）、`test_v5_autopilot`、
  `test_v6_predictive_real_city`、`test_v7_traveler_twin`、`test_v8_stay_mobility`（自然语言 mission）。
  全是依赖"没有配置外部 agent"的测试。
- 那条 ERROR 更具体，而且**是一条真缺陷**：`tests/test_v16_integration.py:111` 写的是
  `@pytest.mark.skipif(settings.ai_api_key, reason="…")`。pytest 对**字符串形式**的 skipif 参数
  会当作表达式去 `eval`，所以一旦键存在（值形如 `sk-…`）这个"该跳过"的守卫就不是跳过而是
  `SyntaxError: invalid decimal literal (<skipif condition>, line 1)` → 收集期 ERROR。
  换句话说这条守卫**在它想防的那个场景里永远失效**——和今晚反复在修的"守卫从不触发"同一族。
  最小修法是 `bool(settings.ai_api_key)`；该文件不在 campaign 的 `SUITES` 里，改了不动矩阵分母。
  我**没有动它**：不在本单写域，且这类一行修该由 Commander 派单落名。

清键重跑（`DEEPSEEK_API_KEY= CITYNEXUS_AI_API_KEY= CITYNEXUS_AI_ENABLED=false`）→
**913 passed / 15 skipped / 0 failed（66.40s）**，与合并前逐项相同。
教训值得留在账上：这台机器上"全量后端绿"必须显式带三个 AI 环境变量，否则数字根本不可比；
两次跑相差 4.6 倍时长（307s vs 66s）也说明当时还有别的车道在抢 CPU。

### 85.3 合并产物里我发现、但没顺手改的一件事

`frontend/e2e/qoder-mobile-ui-overnight.spec.ts` 的三处写盘（200 / 269 / 328 行）把
`generatedBy: "e345b9d6"` 和 `head: "00dfd62"` **写成了字面量**。在车道自己的树上它恰好为真；
合到 `5a33eaf` 之后，它产出的 JSON 会声称自己是 `00dfd62` 生成的——而我这一轮拿到的三份
几何产物（时间戳确实是本次的 07:01）里 `head` 全是 `00dfd62`。这正是我们刚在 ORD-0029 里
消灭的那类东西：一个字段说"我是谁"，但它不来自这次运行。建议改成从 `git rev-parse HEAD`
或 `CITYNEXUS_E2E_RUN_ID` 取值，等 Commander 派单，我不在合并的同一轮里改刚合进来的别人家文件。

### 85.4 一个仍然悬着的口径问题（不因为我跑绿就消失）

ORD-0031 的结论是 **`package-lock.json` 是权威**，而两棵 `node_modules` 都有同一处偏移
（`@types/react` 19.3.0、`@types/react-dom` 19.3.0、`csstype` 3.2.3，lock 里都没有条目）。
所以上面那两个 `typecheck = 0 errors` **只与同一依赖集上的历史数字可比**，不能拿去覆盖任何人的基线，
也不能当作"合并把类型问题清理干净了"的证据——它只是"在这台机器当前的 node_modules 下不报错"。
在依赖问题结清之前，我报的每个 tsc 数字都自带这条脚注。

### 85.5 一次性：把散落的一次性脚本移出权威树（以及我自己踩的一次空）

门跑完后树里还剩 **38 个未跟踪的 `_*.py`**——本轮之前几轮的补丁/探针脚本（`_sc_*`、`_p161_*`、
`_build_pkg_*` 等）。它们不影响任何门的数字，但 PASS-17 要的是"`git status --short` 为空"，
靠事后清理不算达成，所以挪去了 `D:\moodle\_qoder_scratch_20260920\scripts\`。

用 `mv _*.py` 一把梭的时候踩了一次空：仓库根里另有**两个是被跟踪的**产品文件
（`_autopilot_flow.py`、`_demo_flow.py`，自基线 `380e6ff` 就在树里），glob 不认识"未跟踪"这件事。
已经 `git checkout --` 还原，并按 SHA-256 逐文件比对确认与 HEAD **逐字节相同**
（`af3c8a05…` / `2812a6fc…`），`git diff --name-only HEAD` 对这两个路径为 0 行。
记在这里是因为这类错的形状很典型：**"我以为这堆文件都是我刚生成的"**，而判别依据（未跟踪列表）
我手上本来就有——先按 `git status --porcelain` 的 `??` 过滤再动，就不会有这一步。

现在权威树的 `git status --porcelain` 只剩两份别人家的修改（`tools/verification/mutation_campaign.py`
由 Commander 持有、`qoder-handoff/qoder_xiaomi_truth_hardening_v6.patch` 属另一车道），未跟踪文件为 0。

## 86. ORD-0011 被重放了一次：没有重做，改成在合并树上重新证明它有鉴别力

07:2x 收到的转达写的是"账本新增 **ORD-0011（urgent，if_head 21cbf22）**"。账本里 ORD-0011 是
第 288 行那一条，状态 `DONE@20260920-061922`，而且带 Commander 06:40 的 `commander_check`；
最后一笔订单是 ORD-0031，没有 ORD-0032/0033。所以这是一次**重放**，不是新工作。
另外转达要点 (1) 要求"把四项断言补进 `test_rx3_stale_cursor_fails_closed.py`"，
而账本原文里同一件事有 **05:36 的更正**：精确缺席元组已由 `test_sol_execution_cursor.py:499-510`
用整字典相等钉住九项，抄进 rx3 是**零新增覆盖**，本条收缩为"只剩多形状结构不变式"。
按长期协议（聊天只作提醒、正式指令以 ORDERS 为准），我按账本收缩版复核，不按转达原文动手。

要重验的理由是实的：ORD-0026 把游标解析收进共享 `src/lib/executionWindow.ts`，ORD-0029 又换掉了
`"ABSENT"` 词表 —— 这两笔都动在 ORD-0011 鉴别力断言的正下方。所以在合并树 `bf0869b` 上重测。

### 86.1 静态与 collected 复核

`tests/test_sol_execution_cursor.py:499-510` 的整字典钉仍在（九项 + 511 行"游标确实不在活动里"），
`now_state == "STALE_CURSOR"`、哨兵对 `("NONE", 0)` 都在其中；行号与订单引用一致，未漂移。
`grep -rn "activities\[0\]" frontend/src` 在 `LiveRecovery.tsx` 只剩注释一处（第 131 行解释为什么不要它）。

| 套件 | collected | 合并树结果 |
| --- | --- | --- |
| `tests/test_qoder_next_leg_binding.py` | 8 | 全绿 |
| `tests/test_rx3_stale_cursor_fails_closed.py` | 5 | 全绿 |
| `tests/test_sol_execution_cursor.py` | 13 | 全绿 |
| 三文件连跑（AI 关） | **26** | **26 passed / 0 failed（2.58s）** |
| `e2e/qoder-live-recovery-cursor.spec.ts` + `qoder-stale-cursor.spec.ts` | 4 + 1 | 全绿（含在 `ord30-full` 的 54 expected 内） |

### 86.2 突变归属表：一次"变红"不等于一份鉴别力

订单要的是"把 `?? activities[0]` 加回去必须变红"。今天这句话有两种读法，我分别测了，
因为它们的击杀集合**不一样**（一次性、唯一 anchor、读回校验、字节还原 + SHA-256，`tsc --noEmit` 均 exit 0 证明突变体本身可编译）：

| 突变 | 位置 | 红了几条 | 红在什么断言上 |
| --- | --- | --- | --- |
| M1 纯列表回退（游标仍读对） | `LiveRecovery.tsx:217` | **1 / 5** | `spec:267`（`toHaveText`） |
| M2 历史缺陷原样（幽灵键 `current_activity_id` ⇒ 游标恒 null ⇒ 回退首项） | `LiveRecovery.tsx:213-217` | **2 / 5** | `spec:96`（`data-now-activity-id` 期望 `61e3096d…`=activities[2]，实到 `3a58c470…`=activities[0]）、`spec:267`（期望 "Execution position unresolved"，实到 "Next: Old Town Gate"） |
| M3 共享解析器允许陈旧游标按列表顺序造 Now | `src/lib/executionWindow.ts` STALE 分支 | **2 / 5** | `spec:267` 与 `qoder-stale-cursor.spec.ts:36`，都红在标题 `live-journey-current`："Old Town Gate" 而不是 "Execution position unresolved" |
| M4 撤掉后端 trustworthy-Now 守卫（退回 `legs[current_index]`） | `backend/app/operations/v9.py:169-173` | **6 / 26** | 结构不变式 `[more legs than activities]`、`[one leg per hop]`、`test_no_trustworthy_now_projects_no_next_leg` 两例、权威层整元组与"完成旅程多出出发腿"两例 |
| M5 把"空计划"当成"还没拿到计划" | `src/lib/executionWindow.ts` 的 `if (!plan)` → `if (!plan \|\| plan.activities.length === 0)` | **1 / 5** | `spec:138`（标题 `data-cursor-status` 期望 `ABSENT_FALLBACK`，实到 `UNKNOWN`） |

**仲裁点名的三例，现在各自都有能杀它的突变体**：VALID 例 ← M2（`spec:96`）、STALE 例 ← M1/M2/M3
（`spec:267`）、空列表例 ← M5（`spec:138`）。同时要说清 M5 为什么必须另找：**索引回退那具突变体杀不到
空列表例**——空数组的 `activities[0]` 本来就是 `undefined`，回退也是空。所以"给空计划配一条鉴别力"
不能靠重复 M1，只能针对这个形状自己的失效方式，也就是把"计划存在但零步"与"还没有计划"混成一态；
这正是 `UNKNOWN`（取数态）与 `ABSENT_FALLBACK`（执行态）两个值存在的理由，M5 一混就红。
M5 同样 `tsc --noEmit` exit 0、字节还原后 `executionWindow.ts` 与 HEAD 相同（`4280bbe8…`）。

三点要记的口径：

- **M1 只杀 1 条不是门变钝**：游标解析成功时列表回退分支根本不可达，`spec:96` 不可能为它变红；
  `spec:138`（空计划）也不可能——空数组的 `activities[0]` 本来就是 undefined。
  这解释了"为什么 ORD-0011 当年报的是 3 failed 而如今同样一句话只有 2/1 failed"：
  当年那第三条红是 `spec:134` 的**拦截计数**断言（我在结案时已写明"契约断言没红，击杀由前两例承担"，
  并在 ORD-0029 把那条计数删掉）。计数没了，红也就没了 —— 少的那条本来就不该算。
- **一条畸形突变体会伪造鉴别力**：我第一版 M2 写成 `(context?.execution as X).current_activity_id`
  （漏了可选链），组件渲染当场抛错，`live-next` 整个消失，**4/5 齐红且全部红在 `openLive()` 的
  `toBeAttached()` 上**。如果只看"红了几条"，这具突变体看起来比正确的更强。加上 `?.` 之后真实答案是 2 条。
  这与 Commander 在量具里加的 `KILLED_UNVERIFIED` 是同一件事：**击杀必须点名拥有它的那条契约断言**。
- **一个我怀疑错、查过就撤销的"缺口"**：我原以为 M3 之下 V10 面板（`v10-current-step`）说"进行中"
  没人管。实际 `qoder-live-recovery-cursor.spec.ts:331-334` 就断言了 STALE 时它是
  "Execution position unresolved" 且不得为 "in progress"，只是同一例子里标题（328 行）先失败所以没跑到。
  写在这里是为了下一辆车道不必再查一遍：**同一测试内多条断言时，报表上的击杀只反映最先红的那条**。

### 86.3 一处同类问题：不是新发现，是复核它还在

账本里它本来就有名字——`KNOWN_FAILURES` 第 2 条 / `INTEGRATION_QUEUE` 第 3 条：
"前端仍有一处墙上时间推断：`V8Experience.tsx` 约 1501 行
`activities.find(end_at >= nowMs) ?? activities[0]`，与后端 docstring 相冲，是否纳入本轮需裁决"。
我在合并树上重定位了一遍，三处新信息：

```
const nextStop = activities.find((item) => Date.parse(item.end_at) >= nowMs) ?? activities[0] ?? null;
```

- **行号已漂**：表达式现在在 `1479-1480`（账本写的"约 1501"是 `nextUp` 那一行，1501-1503）。
- **它确实进旅客眼睛**：`nextStop` → `nextUp`（1501-1503）→ 1590 行的标签 `"Next" / "接下来"`
  与 1593 行的 `${heroClock} ${nextUp.title}`。所以当**所有活动都早于 now**
  （旅程已完成，或旅程日期落在过去）时，Today 会把早已结束的第一站显示成"接下来"并配上它的起始钟点。
- **注释与代码相反**：1495-1496 行写 "No empty current slot is ever fabricated" ——
  那句对 `currentStop`（1497-1500，确实无回退）成立，对 `nextUp` 这一侧不成立。

按本次的规矩标注：**静态读到，未做端到端实测**。`qoder-today-hero.spec.ts` 现有 2 例覆盖的是
单一 CTA / 高度 / 无空 Now / 无溢出，不含"全部已结束"这个态。要修该由 Commander 派单，
并配一条"全部活动已结束时 Today 不得说 Next"的门；我没有在重放复核这一轮里顺手改它。

## 87. ORD-0025 又作为 urgent 回来了：先测，再决定做不做

账本里 ORD-0025 是 `VOID@20260920-061500 by commander —— 我的测量伪果`，并附完整 `void_reason`；
这次转达把它当新单发来（urgent，`if_head 9e66d1e`）。这种"作者已自否证、又以原样重发"的情况，
我按当前树重测一遍再回答，不引用任何一方的文本。

### 87.1 三条命令的实测（`ee6a93e`，Node v24 / Playwright 1.63，`node node_modules/@playwright/test/cli.js`）

| 命令 | 启动方式 | 退出码 | stdout | stderr |
| --- | --- | --- | --- | --- |
| A) 不加 `CITYNEXUS_E2E_AUTHORITATIVE`，`--list` | bash 原生 | 0 | 641 B（列出节点） | 183 B（announce 行） |
| B) **只加这一个变量** | **bash 原生赋值** | **1** | 0 B | **1505 B** |
| C) 与 B 完全同一条命令 | **`env VAR=1 node …`** | **0** | 0 B | 0 B |

B 的 stderr 第一行就是要求 (1) 要的东⻄：

```
Error: [citynexus e2e] authoritative mode refuses to start:
       CITYNEXUS_E2E_PORT must be set explicitly (the frontend must not be borrowed)
[citynexus e2e] fix the invocation, not the assertion.  See docs/E2E_ACCEPTANCE_POLICY.md.
    at refuse (…/playwrightEnv.ts:30:9)
    at requiredEnv (…/playwrightEnv.ts:38:15)
```

⇒ **求值期的拒绝本来就响亮且非零，`playwrightEnv.ts` / `playwright.config.ts` 一行未改**（要求 (1) 无需施工）。

### 87.2 要求 (3)："命令看起来很完整，还缺什么" —— 什么也不缺，那具启动器什么都不做

这条我能答了，而且答案比"只是吞输出"更糟：**`env` 前缀下的 Playwright 根本没运行**。
把变量给齐（RUN_ID、`_ord25-envtest.db`、:3465/:8465、存在的 venv、AI 关）再走 `env(1)`：

```
exit=0   stdout=0 B   stderr=0 B   backend/_ord25-envtest.db 不存在
```

服务器没起、库没建、一条测试没跑 —— 却回报"成功"。这一次观测同时解释了留档里那四组对照
（`auth.out` 0/0、`run2.out` 0/0、`refuse_*` 0/0、"`_cmd01.db` 至今不存在"），
不需要假设 config 有任何缺陷。UI 那棵树也不是反例：同一棵树的同一模式在两处行为一致，
差异只在**哪条命令带了 `env` 前缀**——"指一个不存在的 config 会大声报错"那组对照，
唯一的自变量也是启动器。要求 (3) 因此有解，但解不在产品侧：

> 本机规矩（对所有车道）：跑门只用 `VAR=value prog`，永远不要用 `env VAR=value prog`；
> 看到"0 输出 + exit 0"时先换启动器复现，再谈缺陷。

### 87.3 要求 (2) 仍然做了：这条回归此前确实不存在

`FILE_OWNERSHIP` 对我这两个文件写着"**改它必须带回归：缺必需变量时必须非零退出并打印缺哪个**"，
而今天没有这样一条测试 —— 一个已经响亮的守卫，如果哪天被改成不响亮，没人会知道。
新增 `frontend/e2e/qoder-e2e-config-guard.spec.ts`（4 条）：用 `process.execPath` 起真 CLI、
只跑 `--list`（强制求值 config 而不启动 webServer，所以它不会 Adopt 任何人的 :8000），
断言子进程的退出码与 stderr：

- 逐个缺一个必需变量（`CITYNEXUS_E2E_PORT` / `_BACKEND_PORT` / `_PYTHON` / `_DATABASE_URL`）时，
  **既**非零退出**又**在输出里点名那个变量，还带 "fix the invocation, not the assertion"；
  两个条件都断，正是为了不被"非零但静默"糊过去；
- 不给解释器时拒绝，并说明理由"falling back to system Python"（Pass-12 那一幕）；
- 带着活的 `DEEPSEEK_API_KEY` 时拒绝（既为确定性也为额度）；
- 变量给齐时**接受**，且 announce 行含 `suite=` / `authoritative=true` / 端口 / `ai=disabled` /
  `reuseExistingServer=false`，并断言 `--list` 的 stdout 里真有节点 —— 防"门自己没测到东西"。

**鉴别力实测（M-G2）**：把 `refuse()` 换成 `return process.exit(2) as never;`（=静默但非零，
正是要求 (2) 点名的形状）→ **3 failed / 2 passed**；其中"完整环境被接受"那条**仍然绿**，
所以红的是"沉默"本身而不是文件加载失败。一次性、唯一 anchor、字节还原 `577561705393609c…` 与 HEAD 相同。

**这条门的分母要写清**（"collected 4" 与 "3+2=5" 看着像矛盾，Commander 08:3x 就抓了这一点）：
本文件自己声明 **4** 条，但 `playwright.config.ts` 的 `chromium` 项目写着 `dependencies: ["real-seed"]`，
所以**只选这一个文件也会带上 `_qoderRealSeed.setup.ts:110` 那 1 条**，任何一次跑的 summary 都是 5。
"collected 4" 说的是声明数，"3 failed / 2 passed" 说的是运行数，两者不冲突——但我不该让读者自己做这个加法。
三个可复现读数（日志都在 `D:\moodle\_qoder_ord30_evidence_20260920\`）：

```
node node_modules/@playwright/test/cli.js test e2e/qoder-e2e-config-guard.spec.ts --list
  → Total: 5 tests in 2 files          （chromium 4 + real-seed 1；exit 0；ord25-guard-list.txt）
干净态  run ord25-guard3  :3469→:8469  _ord25-guard3.db
  → Running 5 tests … 5 passed (12.4s)                                          exit 0
M-G2    run ord25-mg2     :3461→:8461  _ord25-mg2.db
  → Running 5 tests … 3 failed / 2 passed (12.4s)                               exit 1
     ok 1 [real-seed] seed a real journey | x 2 :85 缺变量点名 | x 3 :121 系统 Python
     x 4 :132 活键必须拒 | ok 5 :149 完整环境被接受（这条在突变下仍绿 = 红的是沉默）
```

顺带记一条我自己写门时踩的：第一版用 `__dirname`，收集期就
`ReferenceError: __dirname is not defined in ES module scope`（这套 spec 是 ESM 加载），
整跑 exit 1；改成 `fileURLToPath(import.meta.url)`。这类错的形状是"门没测任何东西却像被测过"，
所以文件里留了一句 CLI 不存在就抛 —— 门起不来要说自己起不来。

### 87.4 数字与一条可直接照抄的权威命令

新增门后同口径复跑：`typecheck` 0（`error TS` 0 条）、`typecheck:all` 0（0 条）、`npm run build` 0；
`guard + qoder-live-recovery-cursor + qoder-stale-cursor` = **10 passed / 15.7s**（run `ord25-guard2`）；
**全套 58 expected / 0 unexpected / 0 flaky / 5 skipped（157.5s）**（run `ord25-full`，:3467→:8467）
—— 54 + 4，正是这份新门，别的车道一条没动。

给 Commander 复跑 LiveRecovery 那扇门（也是 ORD-0011(2) 要的那件）的完整命令：

```
cd /d/moodle/_qoder_integration_20260919/frontend
CITYNEXUS_E2E_AUTHORITATIVE=1 CITYNEXUS_E2E_PORT=3459 CITYNEXUS_BACKEND_PORT=8459 \
CITYNEXUS_PYTHON='D:\moodle\CityNexus\.venv\Scripts\python.exe' \
CITYNEXUS_DATABASE_URL='sqlite:///D:/moodle/_qoder_integration_20260919/backend/_ord25-guard2.db' \
CITYNEXUS_E2E_RUN_ID=ord25-guard2 CITYNEXUS_AI_ENABLED=false DEEPSEEK_API_KEY= CITYNEXUS_AI_API_KEY= \
CITYNEXUS_EVIDENCE_DIR='D:\moodle\_qoder_ord30_evidence_20260920\guard2' \
./node_modules/.bin/playwright.cmd test e2e/qoder-e2e-config-guard.spec.ts \
  e2e/qoder-live-recovery-cursor.spec.ts e2e/qoder-stale-cursor.spec.ts --reporter=list
```

一次跑只换一个 `RUN_ID` 与同名 `_*.db`（fresh-or-no-run 会拒第二个调用复用同一个库），
且**不要**在这条命令前加 `env`。
