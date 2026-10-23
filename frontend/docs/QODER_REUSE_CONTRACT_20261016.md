# QODER 复用契约 · 2026-10-16（Issue #22 交付）

**读的是哪一棵树**：`mirror/integration-frontend-apple-pass1` @ `f27c3dfe11f9b80fac478fba353192abf7c31d7c`（本文每一行坐标都是这棵树上现读的）。
**没做的**：没读也没改 Codex 的 `design/revolution-mobile-first-v1`（含 `RevolutionFirstLook.tsx` / `AgentWorkStatus.tsx`），没开融合，没动 Qoder 主线，没起新一轮产品监管工程。下面凡是关于 Revolution 侧的话，都是"主产品有 X，你可直接用 X"，不是对它实现的判断。

---

## 一、真可复用的（按优先级，五件）

**P1 · 事件与运行态的类型 = 你要的"工具轨迹 + 耗时 + 待审批"，已经定好了**
`frontend/src/api/citynexus.ts:345` `export interface NativeRuntimeEvent`：`event_type` / `run_id` / `sequence` / `tool_name` / `friendly_label` / `status` / `timestamp` / `duration_ms` / `result_summary` / `policy_decision` / `source` / `approval_id` / `approval_status` / `approval_method` / `proposal_id` / `mission_id`。
复用方式：**共享 import，零复制**（`import type { NativeRuntimeEvent } from "…/api/citynexus"`）。依赖：无 React 依赖。
去重键与合并已在 `features/agent/CopilotDock.tsx:68`（`eventKey`，十字段拼键）与 `:92`（`mergeEvents`，Set 去重）。这两枚建议提到 `lib/` 后双方共用，别各写一份。

**P2 · "Hermes 到底有没有真跑工具"的判据，主产品已经有一枚可执行的**
`features/agent/CopilotDock.tsx:288`：`executed = events.some(e => e.source === "HERMES_NATIVE" && (e.event_type === "run.started" || e.event_type.startsWith("tool.")))`，并通过 `onExecutionChange` 往外报（`:294`）。
这一枚就是"不许拿 WATCHING 冒充在跑"的实现形状：**它只认事件，不认状态字**。手机侧若另写一套"看起来在跑"，透明度页面就会自相矛盾。
配套的服务器词表：`api/citynexus.ts:377` `AiStateWord`（`CONFIGURED_UNVERIFIED` / `NOT_CONFIGURED` / `DISABLED_BY_OPS` / `PROVIDER_REFUSED`，来源 `backend/app/agent/ai_availability.py`，别处不产）；`api/citynexus.ts:383` `AgentRuntimeStatus`（含 `native_binary_detected`、`native_mcp_proven`、`hermes_native_gateway.{configured,reachable,ready?,runs,events,approval,profile?}`）。
唯一允许的"词→态"映射是 `features/planning/PlanWithAiSheet.tsx:316` `aiStateFromServer()`；端点是 `/api/v1/agent/runtime-status`（调用处 `app/V8Experience.tsx:837`）。渲染先例：`features/intelligence/ControlTowerPanel.tsx:14`。

**P3 · 轨迹条组件与它的五档语义**
`features/agent/AgentRunRail.tsx:3` `AgentRailStep`，`status: "pending" | "active" | "done" | "approval" | "failed"`；`:13` `AgentRunRail({steps})`，`<ol aria-live="polite">`。
注意 `:6-10` 的注释：字段原名 `detail`，改成 `runMeta` 是因为"按上游字段名渲染的槽位，无法区分是它自己的话还是转发上游的话"——手机侧新增字段时请沿用这条命名纪律。
样式 `frontend/src/styles.css:465-472`（`.cn-agent-rail` / `.cn-agent-step.{done,active,approval,failed}`）。**形状可直接用，颜色别抄**：那几行是未令牌化的十六进制字面量，暗色下不过契约；换成 `--cn-elev-*` / `--cn-on-elev-*` 成对令牌（`design-tokens.css:96` 与 `:212` 的 `--cn-control-border` 是同一族）。
另有一条现成纪律可借：`CopilotDock.tsx:297-300` —— 默认轨迹**永不打印裸 MCP 工具名**（snake_case 是工程词汇），只印 `friendly_label`，裸名收在 Advanced 里。

**P4 · 流式与兜底：一条已经收口的实现**
`CopilotDock.tsx:219-262`：`new EventSource(run.events_url)`（URL 由服务端给，不由前端拼）→ 收到 `run.completed|run.failed|run.stopped` 就 `ended=true; source.close()`（`:237`）；`onerror` 最多重连三次、指数退避 `min(5000, 500*2^(n-1))`，第三次之后落到**可见状态** `copilot.stream.unavailable`（`:246-253`）；解析失败也是状态不是沉默（`:243`）。另有 3 秒轮询兜底跑状态（`:265-283`）。
→ 无穷 spinner 的解法就在这段里：**终止即关流、重连有上限、上限之后必须出声**。建议共享同一套状态词（`copilot.stream.*` 在字典里）。
→ 一处要提醒的鉴权形状：`EventSource` 不能带自定义 header，现在靠同源 Cookie。若后端把 agent 事件挪到 bearer token 之后，这条流会**静默失败**（`onerror` 会响，但内容永远为空）。手机侧若打算换 fetch-stream，请同时保留"终止关闭 + 上限重连 + 可见降级"三件事。

**P5 · 移动壳与安全区：借令牌，不借 markup**
`design-tokens.css:260` `--cn-touch-min: 44px`；`:263` `--cn-nav-item-h: max(48px, var(--cn-touch-min))`；`:282` `--cn-nav-clearance: calc(var(--cn-nav-h) + env(safe-area-inset-bottom, 0px))`；`:283` `--cn-safe-top: env(safe-area-inset-top, 0px)`。底栏实例在 `styles.css:185` 的 `.v8-mobile-nav`（5 列 grid + `backdrop-filter` + 固定 bottom）。
现读确认：主产品**没有** `visualViewport` / `interactive-widget=resizes-content` 的处理，所以键盘遮挡这块 Codex 是新写的，无得可复用；能借的只有上面那四条 `env()` 组合。
`.v8-mobile-nav` 的 markup 与路由表绑死，建议只借令牌与"底部留白 = 栏高 + 安全区"这一条算式。

---

## 二、`styles.css` 全局 button 冲突的最小隔离

事实：`frontend/src/styles.css:47` 是**元素选择器** `button { display:block; width:100%; margin-top:12px; border:0; border-radius:12px; padding:12px 14px; background:#4259d8; color:white; font-weight:700 }`。任何新写的 `<button>` 默认就是"整块蓝底白字"，这就是 Revolution 那边开始叠 `!important` 的源头。

三个选项（按我的建议排序）：

1. **建议：不动 `:47`，Revolution 只用带类的既有控件** —— `v8-primary` / `v8-outline-button` / `v8-quiet-button`（定义同在 `styles.css:174` 一族）。这三个已经被暗色契约与对比度门覆盖，新增零个元素选择器，`!important` 归零。代价：按钮外观受主产品约束。
2. 作用域重置（一处、影响面小）：在 Revolution 自己的根类下写 `#root button { display:inline-block; width:auto; margin-top:0 }`。代价：要把 padding / radius 重新给一遍，且它自己也会变成下一个人的靶子。
3. 最干净但影响全仓：把 `:47` 改成 `:where(button) { … }`（零特异度，任何 class 天然盖过，全仓不再需要为按钮写 `!important`）。**这条必须由号令者走落地门做两臂对表**，不属于本次审查范围，我不在这里改。

---

## 三、对 Codex 分支的具体破坏风险（都带具名引用）

1. **跨成员数据泄露（最该先看的一条）**：行程引用存在 `localStorage` 的 `citynexus.v8.journey_id`（`features/access/accessDoors.ts:215`，读法 `:217` `readJourneyReference()`），**不带属主绑定**。同文件 `:203-213` 的注释已经写明"这个值只是引用，调用方必须在 list door 的答案里找到它，陈旧 id 正是那处记录的风险"。若 `AgentWorkStatus` 直接拿它 GET 监测/审批状态，切换签名用户后会渲染上一位成员的行程动态。窄补丁建议：照 `features/planning/PlanRankingPanel.tsx` 的先例，先 `readMembers`（`accessDoors.ts:202`）/行程列表再匹配，匹配不到就退回选择器——**不报错也不静默**。
2. **事件缓存没有用户维度**：`citynexus.native-hermes.timeline.<journeyId>.<runId>`（`CopilotDock.tsx:83`，尾部 250 条上限 `:86`）。键里有 journey 与 run，但没有 traveler；同机换人若命中同一 journeyId，就会把上一位的 `result_summary` 一起渲染出来。窄补丁建议：键里加当前 traveler 前缀，或在切换/登出时清 `citynexus.native-hermes.timeline.*`。
3. **权限按钮误导**：主产品的审批动作**守卫先于动作**——离线（`CopilotDock.tsx:372`）与缺 id（`:376`）各自给状态词，之后才 `recording → recorded`（`:379`、`:382`），审批块在 `:459-465`，文案全走 `copilot.approval.*`。手机侧若在离线时仍让"批准"可点、或点完只给绿字，就是误导。复用这四条状态词即可，别新增第五种。
4. **LIVE / TEST 来源**：`lib/executionWindow.ts:5` `ExecutionCursorStatus = "VALID" | "STALE" | "ABSENT_FALLBACK"` 与 `:3` `TERMINAL_ACTIVITY_STATES`。`ABSENT_FALLBACK` 就是"我在展示兜底、不是实时"的具名出口；渲染先例是 `features/simulation/SimulationPanel.css:48-64` 的 `cn-sim-ball-dot[data-state]`（`STAGE_LIVE` / `CHECKING` / `UNREADABLE` / `NO_STAGE`）。透明度页若要标 LIVE/TEST，请复用这套四态，不要再造"绿色=正常"。
5. **错误可读性**：`lib/errorReceipt.ts:25` `RECEIPT_SHAPE = /^CNX-[23456789ABCDEFGHJKMNPQRSTVWXYZ]{8}$/`、`:26` `RECEIPT_MISSING = "NOT-EMITTED"`、`:48` `readErrorReceipt()`；渲染先例 `components/CnxMeasuredFacts.tsx:27`。手机侧显示"错误"时带上这枚回执（或明说服务器没发），比红字有用。归属判定在 `lib/failureAttribution.ts:33/55/57/60/70`（`AttributionReason` / `EvidenceKind` / `SourceLayer = RESOURCE_STATE|TRANSPORT|RUNTIME` / `RecoveryAction` / `Attribution`）。

---

## 四、正式融合时保留哪一套（≤5 条建议）

1. **Agent 轨迹的唯一规范是 `AgentRunRail`（列表 + `aria-live="polite"`）**，不是对话流。DSH 手机版只作交互参考（AGPL-3.0，不复制代码；assistant-ui 是 MIT 但仍需先核对文件与来源）。
2. **导航以主产品的 `--cn-nav-*` 令牌家族为规范**，Tab 数量交给路由表；Revolution 的三 Tab 可以作为它的一个子集，不建议反向改主产品导航。
3. **主题只认一个根：`<html data-theme="light|dark">` + 成对令牌**（`--cn-elev-N` 与 `--cn-on-elev-N` 同移）。不接受第二套 `@media (prefers-color-scheme)` 分支——主产品现读零处。
4. **新样式层的规矩**：零 `!important`，靠 `main.tsx` 的 import 顺序赢（现读五层：`styles.css` → `design-tokens.css` → `cn-pulse.css` → `cn-pulse-actions.css` → `cn-pulse-chrome.css`）；新领域新建 `cn-pulse-<domain>.css`，不往别人那枚里加。
5. **交付判据统一**：任何视觉改动带两臂对表（同一把尺、同一台机、按**选择器集合**判、新开红必须零枚），并跑八档相位 × 主题。按 `required` 跨阈值判位移，别按 `selector|ratio|text` 行身份——后者会把"同一格从 1.00 涨到 4.10"记成"修好一格 + 新开一格"。
