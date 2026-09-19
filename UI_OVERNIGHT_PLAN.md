# UI_OVERNIGHT_PLAN — CNX-CMD-002C-OVERNIGHT-PRODUCT-AND-UI

- 会话：UI Worker（Commander 按仲裁 Amendment C 新建，评论 5744696934）
- 基线：`D:\moodle\_qoder_integration_20260919` @ **`00dfd62`**（分支 `integration/frontend-apple-pass1`）
- 我的隔离树：`D:\moodle\_qoder_ui_overnight_20260920`，分支 `agent/ui-overnight-20260920`，工作区干净（`git status --porcelain` = 0 行）
- 稳定性判定：`frontend/src` + `backend/app` 全量 sha1sum 指纹，03:51:27 与 03:51:40 两次均为 `f80bffc889aea33915ff992fbd0ac83ae4397332` → 一致，才建树
- 账本写的 CURRENT_HEAD `13f1453` 已过期：其后落了 `4d2f0c8 / 4b1e829 / b31f331 / 3ae01e8 / 3a... / 00dfd62`。本设单以 `00dfd62` 实测为准
- 状态：**等待 Commander 批准**（未批不改任何文件）

---

## 1. 当前实际路由 / 屏幕清单

权威来源：`frontend/src/routes/v8Routes.ts`

### 移动端底部主导航（`mobileRoutes`，5 项）
| key | 标签 | 实际渲染者 | 定义位置 |
|---|---|---|---|
| `hub` | Today | `Hub()` | `V8Experience.tsx:1435` |
| `trips` | Trips | `TripsWorkspace()` 或 `Studio()` | `V8Experience.tsx:1248 / 1788` |
| `map` | Map | `MapPage()` | `V8Experience.tsx:2276` |
| `agent` | Copilot | `AgentComposer()` | `features/agent/AgentComposer.tsx` |
| `me` | Me | `Me()` | `V8Experience.tsx:2572` |

### 抽屉里的次级路由（`desktopRoutes` ∪ `mobileRoutes`，`V8Experience.tsx:205`）
`live`（Live，`V8Experience.tsx:2044`）、`studio`、`stay`、`discover`、**`bookings`（Travel Wallet，`V8Experience.tsx:2354`）**、`authoritative`、`intelligence`、`twin`。

### 首次进入 / Journey 创建
`JourneyTrialSetup`（`features/setup/JourneyTrialSetup.tsx:144`，592 行，36 个 `data-testid`）在 `V8Experience.tsx:820` 渲染，三步式：`trial-steps` → `trial-card` → `trial-review`，底部 `.trial-sticky-cta`。

### 关键结构事实（决定我能不能干活）
`Hub / Live / Bookings / Me / TripsWorkspace / Studio` 这六个屏幕的 **JSX 全部内联在 `V8Experience.tsx`（2785 行）里**，而该文件当前归 `8c66aa92`。屏幕内容组件（`features/**`、`components/v8/**`、三个 CSS）不在任何人名下。

### 已有的展示层分工（重要）
- `design-tokens.css`（927 行）= Apple pass-1 的打磨层：`cn-*` 组件类 + `@media (prefers-color-scheme: dark)` 下把 `--v8-*` 重绑到 `--cn-*`（`design-tokens.css:119-127`）。
- 已经过 pass-1 的界面：**Today**（`cn-now-next-hero` / `cn-hero-*` / `cn-attention-band`）、**Live**（`cn-live-toolbar` / `cn-live-secondary`）。
- **没经过 pass-1 的界面：Journey 创建、Wallet/Bookings、Me** —— 正是本次四个目标界面里的两个，加上首进门面。
- 引入顺序 `styles.css` → `design-tokens.css`（`main.tsx:39-40`），所以 token 层的 `!important` 覆盖是有意的、可用的。

### 已有的现成前端门（我不得削弱，且要复用其 seed）
- `e2e/qoder-mobile-overflow.spec.ts` — 360/412/430 横向溢出，仅 **Today + Live**
- `e2e/qoder-today-hero.spec.ts` — hero 一个主 CTA、高度 ≤45% 视口、Now 不空
- `e2e/qoder-contrast-audit.spec.ts` — Today/Live 明+暗对比 + focus 3:1
- `e2e/qoder-dock-geometry.spec.ts`、`v10-accessibility.spec.ts`

**覆盖缺口**：Journey 创建与 Wallet 目前没有任何移动端溢出/对比/触控门。

---

## 2. 四个最高价值界面

按"手机上今晚能被看见的差别"排序：

1. **Journey 创建 / 首次进入**（`JourneyTrialSetup.tsx` + `styles.css:431-604`）
   唯一决定"用户看不看得下去"的界面；且整块 CSS 引用了不存在的 token（见 §3.1）。组件在我名下，可改。
2. **Wallet / 支付**（`bookings` 路由 = `Bookings()` 内联 + `BookingArtifactScanner` + `JourneyInboxWorkbench`）
   现在是一张 booking 卡列表 + 两个 `.v8-page` 堆叠。目标"不得是无解释的空面板"必须由 Inbox/Scanner 两个**我名下**的组件承担解释层。
3. **Today**（`Hub()`）
   pass-1 已给 hero；剩余问题是排版节奏与次级噪声（`v8-day-row` 三列在手机上塌成单列后每卡 120px 高、标签 9px）。
4. **Live**（`Live()`）
   现在 Now 卡 / mode-chooser / next-card / comparison 四块平铺，没有"现在最重要"的焦点区。

（`Me` 与 `Trips` 不在本轮四个界面内，但 `Me` 复用同一批 v8 类，会连带受益/受累 —— 见 §6 回归监控。）

---

## 3. 当前问题（每条都已在 `00dfd62` 实测，非推断）

### 3.1 【BLOCKER】两个 token 从未定义，18 处声明静默走 fallback
- `--v8-accent` **全仓无定义**（定义只有 `--v8-indigo: #4658d9`）。14 处 `var(--v8-accent, #0f766e)` 因此恒取 teal `#0f766e`：`styles.css:471,472,477,478,542,543,598,600,820,821,845,889,1007,1138,1139`。
- `--v8-surface` **同样无定义**，且**同一个 token 在三处写了不同 fallback**：`styles.css:592` → `#0b1f24`（近黑），`styles.css:922` 与 `:1019` → `#fff`。
- 直接后果：Journey 创建的主按钮 `.v8-primary-button`（`styles.css:597-603`）是**青色**，而全应用其它主按钮 `.v8-primary`（`styles.css:162`）是 Apple 蓝；`.trial-sticky-cta` 的渐变底（`styles.css:592`）是**近黑色 scrim 压在白页上**。首进门面自己打架。
- 修法：把两个 token 按**意图**拆开并真正定义 —— accent 归 `--cn-accent`；`#0b1f24` 那处改成 scrim 语义（`--cn-scrim-raised`），`#fff` 那两处归 `--cn-surface`。这是"统一 radius/elevation/border/surface token"的字面落点。

### 3.2 【BLOCKER】移动主导航没有 safe-area，且壳层留白是写死的魔数
- `.v8-mobile-nav` 在 680px 断点为 `padding: 8px 5px 7px`（`styles.css:173`）——**没有** `env(safe-area-inset-bottom)`。
- 全仓 `env(safe-area-inset-*)` 只出现 4 次：`design-tokens.css:812`、`styles.css:591,648,675`。**导航本体不在其中。**
- 同时 `.v8-product-shell { padding-bottom: 63px }`（`styles.css:173`）是写死的 63px，等于"nav 实测高度"的快照；nav 一旦因字号/触控目标变高，内容就被遮住。
- iPhone 安全区下现有实现：CTA 与列表末项会落在 home indicator 区域。

### 3.3 【HIGH】主控件不足 44px
- `.v8-primary { min-height: 42px }`、`.v8-outline-button / .v8-rain-button { min-height: 40px }`（`styles.css:162`）。
- `styles.css:260` 已在 680px 下把 nav button 抬到 48px、并把 `.v8-mode-chips button / .v8-compare-button / .v8-page-intro button` 抬到 44px —— **但覆盖不到 `.v8-primary` 与 `.v8-outline-button`**。
- `.v8-primary` 字号 12px，`.v8-mobile-nav button` 字号 9px（`:173`，`:260` 抬到 10px）。10px 文字在手机上是不可读的。

### 3.4 【HIGH】明暗对比：v8 层只有局部补丁，且导航栏硬写白色
- `.v8-mobile-nav { background: #fffffff2 }` 是**字面量白色**（`styles.css:173`），dark 下必然刺眼。
- `--v8-*` 整套定义在 `.v8-product-shell` 上且是**仅亮色字面量**（`styles.css:125`）；dark 支持靠 `design-tokens.css:119-127` 的重绑 + `:437 / :546` 两段手工 `!important` 补丁，注释里自己写明"off-path panels are intentionally left as declared debt this pass"。
- `styles.css` 内含 **562 处字面 hex，其中 60 处 `#fff`**；`design-tokens.css` 63 处、`v10.css` 59 处。凡是未被 `--v8-*` 重绑覆盖到的字面量，dark 下都是漏的。
- 现有 `qoder-contrast-audit.spec.ts` 只扫 Today/Live —— 与 `styles.css:260` 之外的大量白底声明同时存在，说明**暗色门是覆盖面不足的门，不是已经干净的证据**。

### 3.5 【MEDIUM】嵌套卡片与噪声
- `Bookings` 路由把 `Bookings()` + `BookingArtifactScanner` + `JourneyInboxWorkbench` 三段各包一层 `.v8-page`（`V8Experience.tsx:1113-1134`），形成卡中卡；Wallet 无"这页管什么、我该做什么"的说明面。
- `Live` 的 `.v8-live-side > .v8-next-card` 与 `.v8-comparison` 与 `.v8-mode-chooser` 三块同权重（`styles.css:168`），无主次。

### 3.6 【MEDIUM】断点粒度不匹配验收口径
- 实际断点只有 `960 / 680 / 560 / 480 / 380`（`styles.css:118-121,172-173,258-260,275-276,1170,1223,1243` 与 `design-tokens.css:404`、`v10.css:6,15,32`）。
- `390` 与 `412` 落在 680 单一分支里，没有任何针对性处理；`360` 与 `380` 才有尾部规则。三档验收口径（360×800 / 390×844 / 412×915）目前是"一套 680 规则打天下"。

### 3.7 【BASELINE，不算我引入】既有 TypeScript 错误
在 `00dfd62` 干净树实测（`node_modules` junction → `D:\moodle\CityNexus\frontend\node_modules`，未 npm install）：
- `npm run typecheck`（`tsconfig.check.json`）：exit **2**，**1** 条错误 —— `features/studio/SortableActivityList.tsx(47,59) TS2322`
- `npm run typecheck:all`（`tsconfig.typecheck.json`）：exit **2**，**5** 条错误 —— 上条 + `components/ProductErrorBoundary.tsx(46,10 / 49,30 / 63,29) TS2339` + `stories/V12ExecutionStates.stories.tsx(62,13) TS2322`

（第一次跑我用 `| tail` 导致退出码取自 tail 而误显示 0；以上是直接取 tsc 退出码的复测。）
**我的门是"不超过 1 / 不超过 5"。** 这 5 条不在我 write-set 里，本轮不顺手修，除非 Commander 另外授权。

---

## 4. 精确 write-set

### A 组：CSS / token 层（无所有权冲突，本轮主力）
| 文件 | 改动范围 | 目的 |
|---|---|---|
| `frontend/src/design-tokens.css` | 新增 `--v8-accent`、`--v8-surface`、`--cn-scrim-raised` 定义；新增 mobile 排版/间距/触控/navi 高度 token；扩 dark 段 | 统一 token；修 3.1/3.4 |
| `frontend/src/styles.css` | `.v8-product-shell`、`.v8-mobile-nav`、`.v8-primary/.v8-outline-button/.v8-rain-button`、`.trial-*`、`.v8-booking-*`、`.v8-live-*`、`.v8-day-*`；新增 360/390/412 三档断点段 | 3.2/3.3/3.6 + 排版节奏 |
| `frontend/src/v10.css` | `.v10-execution-*`、`.v10-inbox-*` 移动端 | Live/Wallet 焦点区 |

### B 组：不在任何人名下的 feature 组件（我有所有权）
| 文件 | 目的 |
|---|---|
| `frontend/src/features/setup/JourneyTrialSetup.tsx` | Journey 创建：一视图一主行动、明确下一步、`trial-review` 渐进披露 |
| `frontend/src/features/inbox/JourneyInboxWorkbench.tsx` | Wallet 解释层：这页管什么 / 已确认与待确认 / 空态说明 |
| `frontend/src/components/v8/StateBlocks.tsx`（**新建**） | 共享 empty / loading / error 三态原语，供 B 组与任何 features 复用 |

### C 组：证据（**不进生产目录**）
`D:\moodle\_qoder_ui_overnight_20260920\review\` —— `before/`、`after/`、`geometry/*.json`、`gates/*.log`、`UI_OVERNIGHT_EVIDENCE.md`

### 明确不在 write-set
- `frontend/src/app/V8Experience.tsx` —— 归 `8c66aa92`，**只读**
- `frontend/src/main.tsx` —— 暂不动（不在我 A/B 组即可完成本轮）
- `backend/**`、`src/api/**`、`src/contracts/**`、`src/generated/**`、`src/state/**`、`src/lib/**`、`e2e/**` —— 真值/契约/验收策略，本轮禁止
- `tools/verification/mutation_campaign.py` —— `8c66aa92` 正在写（权威树未提交修改）

### 若必须改 `V8Experience.tsx` 才能推进的情形
只有一种：Today/Live 的"焦点区"或 Wallet 标题无法用 CSS + 现有类名达成。届时我会先在 ORDERS 提**anchor-only diff**（只加 `className` / `data-*`，零逻辑、零 JSX 结构变化），列出行号，等释放；不抢改。

---

## 5. 要拍的截图清单

口径 `412×915`，每屏 before/after；Today / Live 各加一对 `412×915` 暗色。

| # | 界面 | 状态 | 明 | 暗 |
|---|---|---|---|---|
| 1 | Journey 创建 step 1（首次进入） | before/after | ✓ | — |
| 2 | Journey 创建 step 3 `trial-review` | before/after | ✓ | — |
| 3 | Today（`hub`） | before/after | ✓ | ✓ |
| 4 | Live（`live`） | before/after | ✓ | ✓ |
| 5 | Wallet（`bookings`） | before/after | ✓ | — |

= **14 张**（7 对）。

补充几何证据（非截图，JSON）：`360×800 / 390×844 / 412×915` 三档 × {Today, Live, Wallet, Journey 创建} = 12 组，记录
`documentElement.scrollWidth vs clientWidth`、每个主 CTA 的 `getBoundingClientRect()` 与 `min-height`、`.v8-mobile-nav` 是否遮挡 CTA、以及 `scrollWidth > clientWidth` 的元素选择器。

跑法：`playwright.config.ts` 的 `real-seed → chromium` 两 project，**`CITYNEXUS_E2E_AUTHORITATIVE=1`**，显式给 `CITYNEXUS_PYTHON=D:\moodle\CityNexus\.venv\Scripts\python.exe` + 独立 `backendPort/frontendPort/DB`，并清空 `DEEPSEEK_API_KEY` / `CITYNEXUS_AI_API_KEY`。
理由：本项目已实测过 clone 的 e2e 会静默测到邻道的 `:8000` 后端；数字必须知道自己来自哪棵树。

---

## 6. 与真值线的所有权 / 语义冲突

| 冲突 | 说明 | 处置 |
|---|---|---|
| **四个目标界面的 JSX 都在 `V8Experience.tsx`** | 该文件归 `8c66aa92`，我只读 | A 组走 CSS + `cn-*` 层；B 组走我名下组件。需要改 TSX 时按 §4 提 anchor-only diff 等释放 |
| **`tools/verification/mutation_campaign.py` 权威树有未提交修改** | `8c66aa92` 正在写 | 我不碰；我的树是 `00dfd62` 干净快照，取数字前复测指纹 |
| **Wallet 的"解释"不得变成编造真值** | `Bookings()` 显示 `v8-booking-state` / `role-alert` / `v8-no-payment` | 我只改这些既有事实的**呈现**，不新增任何 provider 数据，不把 degraded/unknown 藏起来 |
| **Live 的游标语义** | `V8Experience.tsx:254 liveActivityWindow()` / `:280 nextActivityOf()` 是真值消费者；已知 KNOWN_FAILURES §2 指 `:1501` 墙上时间推断待裁决 | 一行 JS 都不改。CSS 层不得改变 Now/Next/STALE 的可见性：STALE 时后端给 null，前端就该显示空/降级，不做漂亮化掩盖 |
| **暗色门已有但覆盖窄** | `qoder-contrast-audit.spec.ts` 只扫 Today/Live | 我扩扫描范围属**加强**门，不放宽任何阈值；若扩门后暴露新违规，如实报数、不静默修数值过关 |
| **`mobileRoutes` 刻意不含 Wallet** | `v8Routes.ts:15-17` 注释：Wallet 已移出 golden path，住在 Trips/Me 下 | 本轮按 Mission 要求做 Wallet 界面，但**不改导航拓扑**（那是产品真值决定，不是样式决定），并在验收里标出这条口径分歧 |

---

## 7. 验收口径（自证方式）

- 360×800 / 390×844 / 412×915：`scrollWidth ≤ clientWidth`，无元素越过视口边（复用并加强 `qoder-mobile-overflow.spec.ts` 的选择器逻辑）
- 主 CTA 完整可见、不被 `.v8-mobile-nav` / safe-area 遮挡；nav 与其它 fixed 元素不互相重叠
- 关键文案不截断（尤其 `.v8-anchor-row small`、`.v8-day-card small`、`.step-result` 这些现在写了 `text-overflow: ellipsis` 的地方）
- 所有主控件 `min-height ≥ 44px`（含 `.v8-primary`、`.v8-outline-button`）
- 暗色：Today/Live 无字面白底泄漏
- `prefers-reduced-motion: reduce` 下动效关闭（`design-tokens.css:182/908`、`styles.css:274/412` 已存在，我新增的动效必须进同一 guard）
- 前端生产门：`npm run typecheck`（**≤1**）、`npm run typecheck:all`（**≤5**）、`npm run build`、`npx playwright test`（报 collected / passed / failed / skipped 条数，且**注明解释器与端口**）

---

## 8. 请 Commander 批准的事项

1. 批准本 write-set（A 组 3 个 CSS + B 组 2 个改 + 1 个新建 + C 组 `review/`）。
2. 确认 `frontend/src/features/**` 与 `frontend/src/components/v8/**` 确实无人持有（账本 FILE_OWNERSHIP 未列，但请显式认可，避免与 `8c66aa92` 撞车）。
3. 裁定第 6 节最后一条：Wallet 在移动端刻意不在主导航内 —— 本轮是"打磨 Wallet 界面"而非"把 Wallet 放回 golden path"，是否接受这个边界。
4. §3.7 的 5 条既有 TS 错误：本轮**不修**（避免混入无关改动），除非要求我清账。
5. 是否需要我在开工前先落一次 `before` 截图（不需要批准改动，纯只读渲染）；若需要，请给我可用端口区间与是否允许我起本地 backend。

**未看到 `APPROVED` 之前，我只继续只读调查，不改任何文件。**
