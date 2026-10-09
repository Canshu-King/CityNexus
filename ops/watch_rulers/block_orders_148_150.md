- id: ORD-0148
  to: c01d72a3
  priority: P0-critical
  if_head: e9efec6
  order: |
    **仲裁 5760530753 把 #4 升为当前产品能力主线：现在并行做，不等 #18 变绿。**
    你的车道（B）负责**真实 provider / cold-chain 证据**。首个端到端案例用**贡山独龙族怒族自治县**，
    **不要拿云和县当第一案**（它同时被 R10 身份 bug 污染，留作 CASE4，等身份修好后走同一条链证明不是特例）。
    **验收不是"接口都 200"，而是这条证据链完整**：
    `raw destination text` → Photon canonical identity（真实 provider id + extent + WGS-84 provenance）
    → Overpass 冷发现（**无 seed、无 mock places**）→ normalized persisted catalog（每个实体带 provider/source identity）
    → DestinationCapability 从 HYDRATABLE 变成**真实可规划** → 共享 planner 出候选
    → 候选的 used places **全部来自这次 provider 目录** → used mobility legs 走 hard-eligible 证据 → candidate **SELECTABLE**。
    八条硬门（逐条要能复跑）：
    ① 测前先证明该 canonical destination 在库里 **0 预录 places / 0 golden catalog**（给查询与计数）；
    ② hydration operation 必须**保留 Photon/Overpass 的 provider observations**；
    ③ 目录实体**不许**是 `mock` / `seed` / synthetic identity 冒充 live；
    ④ provider 超时允许 PARTIAL，但**不许把"缺失类别"说成"物理不存在"**；
    ⑤ warm 第二次必须命中 TTL/read gate，**provider call count 明显下降**（给两次的计数）；
    ⑥ planner 失败必须能区分 catalog insufficiency / mobility gap / temporal gap，**不许再折成 generic validation**；
    ⑦ 产出 SELECTABLE 的话，逐个 used-place / used-edge **回溯 provenance**；
    ⑧ 最终交**机器可复跑**的 cold-chain evidence（脚本 + 日志 + 环境四要素），**不只截屏**。
    【纪律】不碰 `:4781/:4782/:8693` 与 `_live.db`（用户此刻在用）；不触发 `demo/reset`（R13 关闭前禁）；
    用**自有副本库 + 自有端口**；解释器 3.12.14；凭据全清；**不许拿真 AI key 进实验**；
    交付写进 `## DELIVERIES`（追加自己那块，`newline="\n"`）。
    【你手上 ORD-0127 的顺序】先交 0148 的冷链证据（它是任务命根），0127 的 R10 出口继续并行；
    云和县 CASE4 等身份修复后回来跑，别现在改 hash 表示。
  status: DISPATCHED@2026-09-21T20:3x+08 by 494abfd7

- id: ORD-0149
  to: 8ccd71d8
  priority: P0-critical
  if_head: e9efec6
  order: |
    同一条仲裁令（5760530753）把**契约与门**这一半交给你（F）。两件事，排在 ORD-0131 之后：
    **一、#7 的最终定义钉成门**（仲裁原话）：
    > #7 只有当**至少一条正常 SELECTABLE 候选的实际 used edges 全部来自 live Valhalla**
    > （或契约允许的 hard-eligible 真实路由证据）、**且没有 `SYNTHETIC_DEFAULT` / mock 兜底**，才算过。
    > "环境变量开了"不算；"Valhalla 偶尔返回 200"也不算——**必须落到一个真实候选的 used edges 上**。
    所以门要断言：候选 `selectable=true` 时，逐条 used leg 的 `fact_quality ∈ 允许集`（不含 `SYNTHETIC_DEFAULT`），
    并且 provider 字段指向 live；任何 live 失败必须落成**具名 mobility runtime/gap**，不许假成功。
    **二、把 Stage V1「canary/review profile」的形状写成契约**（实现由 C 在写域交接后做，你不要自己改产品码）：
    同一 SHA；独立库或 `_live.db` 的**一致快照副本**；`CITYNEXUS_REAL_CITY_ENABLED=true` +
    `CITYNEXUS_LIVE_VALHALLA_URL=<live endpoint>`；**启动日志显式 `discovery=LIVE / routing=LIVE`**；
    **禁止静默回落到 mock**；矩阵 **N≤20、单请求 cells≤100 分块**（Valhalla 那句报错文案说 "locations" 但按 cells 算，
    预检别照文案写）；明确并发限流/退避（**公网 Valhalla 没有任何限速响应头**，只能自限）；
    并列出 **V2 promotion 的 8 条门**（①canary 连续 ≥10 次 live 生成无静默 mock；②used-edge provenance 100% live/frozen
    hard-eligible、不含 `SYNTHETIC_DEFAULT`；③Valhalla timeout/5xx 时 UI 有具名恢复态；④不制造新裸 500；
    ⑤P95 额外延迟有实测；⑥开关 fail-closed，关闭时不许把 mock 冒充 live；⑦切换前对用户 Journey 做一致快照；
    ⑧切换后先用 probe journey 只读/新建验证、不触发 reset）。
    验收：每条门都要有先红读数（今天北京候选的 used legs 全 `EXPLICIT_FROZEN_FIXTURE`、快照里 184/240 是
    `SYNTHETIC_DEFAULT` —— 这就是"门看不见合成值"的现成红基线）；一条杀得掉的突变；
    全量红集合按 **ORD-0131 的 C 项口径（必须是 `eef24d9` 14 条基线的子集）**。
  status: DISPATCHED@2026-09-21T20:3x+08 by 494abfd7（排在 0131、0133 之后）

- id: ORD-0150
  to: 8c66aa92
  priority: high
  if_head: e9efec6
  order: |
    仲裁令：**"C 只在明确写域交接后落实现"** ⇒ 本单**必须等 ORD-0149 的契约落地**再动手，别抢跑。
    要实现的只有 Stage V1：**同机 canary/review profile**，不是把用户主预览全量切 live。
    - 新建/启用一个 review profile：`CITYNEXUS_REAL_CITY_ENABLED=true`、`CITYNEXUS_LIVE_VALHALLA_URL=…`，
      启动日志打 `discovery=LIVE / routing=LIVE`（**R6 要的可见性**）；
    - **live 失败不得静默回落 mock**（今天的 `REPLAY_FALLBACK` + Python 异常类名当 reason 那形状必须收敛成具名 reason_code）；
    - 矩阵分块按契约：N≤20、单请求 cells≤100、自限流与退避（公网无速率响应头）；
    - **只对专用 probe journey / canary session 生效**，当前用户主预览（`:8693` + `_live.db`）不动；
      主预览的切换要等 V2 的 8 条 promotion 门（列在 0149）全过，由我按门放行；
    - 切换前必须对用户 Journey 做**一致快照**（`sqlite3.backup`，不是裸拷——今天裸拷丢了 WAL 害我误判过一次），
      并**不许触发 `demo/reset`**（R13）。
    验收：canary 上跑一次 live 生成，给出 used-edge provenance 全 live 的证据 + P95 延迟实测；
    全量红集合**不得多于 `eef24d9` 基线**（子集口径）。
  status: QUEUED-BLOCKED@2026-09-21T20:3x+08 by 494abfd7（等 ORD-0149 契约交接；先做 ORD-0125 / 0112）
