# ORD-0392 · 面板挂载改成注册表（行为逐字不变）

车道：Q · 分支：`review/Q-ord0392-panel-registry` · 基线：`db6a04cb1d734963b673351973329c08bb264ef3`
数据仍是车道自己的导出副本 `D:/moodle/_qoder_q_ord0369_wk/q0386.db`；没跑 `demo/reset`，没碰
`_preview.db`，没依赖 `:8000`。

## 做了什么

一张表：`frontend/src/app/v8PanelRegistry.tsx`，三个面（`route` / `trips-tab` / `authoritative`），
每条声明 `id` + `surface` + `testId` + `when` + `render`。外壳只遍历表：
`{renderPanels(routePanels, routeScope)}`（`frontend/src/app/V8Experience.tsx:1829`）、
trips 四个子页 `{renderPanels(tripsTabPanels, tripsTabScope)}`（`:2100`）、
权威屏 `{renderPanels(authoritativePanels, {...})}`（`:3316`）。

页壳（`Hub` / `Studio` / `Live` / `MapPage` / `TripsWorkspace` / `Bookings` / `Me` /
`AuthoritativeExecution` / `WalletCommitments`）留在定义它们的文件里，通过 `slots` 交给表——
它们不是面板，且把它们搬走就会连带搬动布局，本单的验收是"屏不变"。
**新增一个面板 = 在表里加一条**，不再打开 4 494 行的外壳文件。

`testId` 一律读自组件源码或实测屏（不是编的）：初稿我编了 9 枚（`hub`、`stay-explorer`、
`destination-preparation`、`control-tower`、`twin-panel`、`agent-composer`、`recovery-required`、
`v12-authoritative-journey`、`v14-preventive` 里只有 2 枚是真的），逐条对着 390 屏的
`[data-testid]` 实测列表回验后改成真值；面板本身不渲染任何 testid 的（`TwinPanel`）与页壳（`hub`）
写成 `null`，字段不许省略。

## 行为不变的证据（不是"我看了一下"）

仪表 `screens_0392.mjs`：13 条路由 × 4 个宽度（320/360/390/412）+ trips 四个子页 = 68 屏，
每屏记 8 项：`body.innerText` 全文、字符数、有序 `[data-testid]` 列表、有序可交互控件列表
（tag|testid|aria-label|role|文字）、版本面板计数、`<details>` 开合串、抽屉是否存在、URL。
基线在 `db6a04cb` 的构建产物上取，改动后在同一仪表上再取：

- 原始差异 4 项，全部是 live 屏上的一分钟时钟（`15:54` → `16:04`）；
- **同一份代码连跑两次（after vs after2）也在同样这 4 项上差一分钟** ⇒ 这是仪表的时钟敏感，不是改动；
- 把时钟串归一后：**68 屏 × 8 项差异 = 0**（`screen_diff_summary.json`）。

窄屏四形（验收 D）：`geometry_base.json` 与 `geometry_registry.json` 各 52 条（13 路由 × 4 宽度），
逐条比 `documentElement.scrollWidth - clientWidth` 与越过右缘的元素集合 —— **差异 0**，
两侧都是 0 条横向滚动、83 个越界元素。那 83 个是 `.cn-copilot-edge` 一族在基线代就存在的越界，
不是本单带来的（同一仪表第一次量基线时报 0，是因为我起 `:4193` 时漏了 `CITYNEXUS_BACKEND_PORT`，
那一轮量的是没启动的壳；补上开关后两侧一致）。这条教训记在这儿，不删第一次的读数。

## 门禁

`frontend/e2e/qoder-ord0392-panel-registry.spec.ts` 四条臂，与 ORD-0386 的七条臂一起跑：
`stats: expected=11 unexpected=0`（`gate_run_stdout.txt`）。
`tsc --noEmit` rc=0，`vite build` rc=0。

变异（`mutant_kill_table.json`）：删掉表里一条 → R1 红（`条目数变了，实读=6`）；
把两条的顺序换掉 → R2 红；把外壳里一次遍历改坏 → R4 红（`遍历次数不是 3，实读=2`）。
每次还原后与还原前逐字节相同。第一条 R4 变异是我瞄错了（它加回的是 R4 没点名的那一屏），
第二条是我漏传 `CITYNEXUS_ORD0386_MATCH` 导致 0 条测试被跑——两次都不算 R4 的功劳，
所以换成 R4c 重做并记在表里。R3（谓词真的管用）没有对应变异，**未证明它会咬**。

## 还没解决 / 没改善的部分

1. `route` 面 14 条里只有 6 条是"纯面板"，其余 8 条整块交给 `slots`。对这些屏而言，表决定了
   **它出现在哪一屏**，但屏内部的顺序仍由页壳自己决定——这一层没拆，拆了就会动布局。
2. `Hub` 内部那三块（`JourneyLinkAction` / `SimulationEntry` / `MapPanel`，`V8Experience.tsx` 的
   `Hub` 组件里）仍是硬编码在长 JSX 中间；要给"今天"屏加一块，还是要动外壳。要拆得先把 `Hub`
   搬出这个文件，那是另一单。
3. `renderPanels` 的 key 用 `entry.id`：改 id 会重挂载面板（丢内部状态）。表里加了注释说明，
   但没有门禁守着 id 不被改——R1 只查同代内不重复。
4. R3 没有被变异杀过（见上）。
5. 本单没碰任何文案、样式、面板内部逻辑；`LocaleContext.tsx` 一行没动。
