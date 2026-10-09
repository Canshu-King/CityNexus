**S1-q64sweep → ORD-0326 再切已执行：范围收成两枚 agent 文件、我造的第二套 helper 已撤；r5 双向证通（28→25，装回 cause.message 就重新被旗）；ORD-0332 的字段实到清单也量好了 —— 六个允许字段只有 2 枚真到得了**

**开枝与清单**：开枝 sha = 0f8b925facabc9df57bab600b86d999dd515bf94（`merge-base --is-ancestor` 验过）；候选 `agent/S1-q64sweep-candidates-r3` = commit 08a651e7fc25cf1ccaa0617e97a313b45aad3066（`ls-remote` 回验同值）。**只碰 2 枚**：`frontend/src/features/agent/AgentComposer.tsx`、`frontend/src/features/agent/CopilotDock.tsx`。**没有新建任何 `lib/` 或 `components/` 文件**（件里 `no_new_lib_module=True`）：我上一版的 `lib/serverReason.ts` 与 `components/ServerReasonDetail.tsx` 在这枝上不存在，职责交回既有通道 `lib/failureAttribution.ts:150` 的 `classifyReadFailure` + `copyFor`，其语义一处未改。让出的六枚文件逐枚验过相对开枝 diff=0：`JourneyInboxWorkbench.tsx`、`ProductErrorBoundary.tsx`、`HotelsPanel.tsx`、`V8Experience.tsx`、`PlanWithAiSheet.tsx`、`PlanComparison.tsx`。

**改法**：四处 catch（`AgentComposer.tsx:98`、`CopilotDock.tsx:345`、`:363`、`:617`）不再把 `cause.message` 写进被渲染的字符串，改为 `classifyReadFailure(cause)` → 屏上 `copyFor(attribution, zh).body`，并把该 Attribution 自带的 `telemetry` 挂成同元素的 `data-attribution` —— 机器字段落属性、不落正文。

**双向证明用已发布的 r5，不用我自写的断言**：尺 `evidence/ord0331-ast-crossfile-S4/ui_exposure_taint_ast_r2.cjs` = blob ff98091cf3accb0d836ae25ba49820170b92d932（自测 SELFTEST_PASS、n_fixtures 20），跑法 `git archive <sha> frontend/src` 后 `--tree`（逐文件 `--ref` 会复现 r4 旧答案，弃用）。开枝代次 28 枚 → 本枝 **25 枚**，移除的正是派给我的 `AgentComposer.tsx:185`、`CopilotDock.tsx:450`、`CopilotDock.tsx:770`，新增 0 枚；反方向在 scratch 拷贝里把 `cause.message` 装回 `:617`，r5 立刻重新旗出 `CopilotDock.tsx:783|UPSTREAM_EXCEPTION_TO_DOM`（25→26）。突变只落在拷贝，枝从未被改。`tsc --noEmit` exit=0；未改既有断言、0 skip、0 推权威线。

**ORD-0332 的字段实到清单**（路由实名是复数：`POST /api/v1/journeys/{journey_id}/copilot/messages`，见 backend/app/main.py:11046 —— 你令里的单数找不到代码）。六枚允许字段在这条路上 **2 到、4 不到**，每条带机器抽取的 `path:line`：

- `http_status` **EMITTED**：main.py:492 → 客户端 api/citynexus.ts:681/:689 → 通道 lib/failureAttribution.ts:57/:123 → 上屏 :358 与 telemetry :133。
- `content_type` **EMITTED 但只有一条腿读**：头由 main.py:492 隐含带出，客户端只在 api/citynexus.ts:686 守卫内于 :687 读 —— 正常 4xx 的 JSON 回答走不到那行，于是 `Attribution.content_type` 留空、telemetry 省略该键（不会显示空值）。
- `body_bytes` **NOT-EMITTED（两端皆无）**：唯一可能的地方是 api/citynexus.ts:663（整段 body 读成 text 后把长度丢掉），服务端从不发。**要求它上屏＝要求产品编一个没量过的数。**
- `response_received` **NOT-EMITTED，但既有通道已用别名覆盖**：`evidence_kind=HTTP_RESPONSE|TRANSPORT`（lib/failureAttribution.ts:42，telemetry :132）。再加一个布尔是重复信息、且属语义改动 —— 按你条件① 只报不做。
- `elapsed_ms` **NOT-EMITTED（这条路上）**：同名字段 api/citynexus.ts:730 属执行时钟负载，且 :757 注释记着后端拒编该分母；copilot 请求今天无计时。
- `request_id` **NOT-EMITTED**：B 的量我复现了 —— main.py 全文 **0 命中**（扫 11446 行），且无 X-Request-Id 头、无中间件（同类 0 命中）。但服务端每次拒绝都铸了号：`error.trace_id`（main.py:456 定义、:487 进信封），客户端从不读、通道无槽。**所以 ORD-0332 的真问题不是"要不要发 request_id"，而是"已存在的 trace_id 以什么名字暴露"。** 顺带自纠：我上一版 spec 把 trace_id 当 request_id 断言，那是我起的键名，别据此以为服务端有 `request_id`。

**坐标**：件 `commander/control:evidence/ord0326-server-reason-S1/agent_fields_r1.json` = blob c80f6f61bff8d574dc529a27ba21dd9cbc5cb328（commit d2af065f2987c6c86968f8f80308cdecb1f096c3，`rev-parse` 与本地 `hash-object` 全等）。旧件不动：`channel_r1.json` = baa3f4f902997f3f1a54873628e12fe558969ac1、`channel_r2.json` = 86fc78a7540535ee2898d7129449428fbe6bb7ad、`channel_r3.json` = 94de764e50019d8c76c7cb09fadf68e534cdab64（其中 r3 记录的 helper 方案自本令起作废，以本帖与 `agent_fields_r1.json` 为准）。**账本块** `D:\moodle\_qoder_ledger_inbox\S1-q64sweep_0531.md` 取代已入账的 `0524` 那块范围（旧块一字未改；自跑 `_hex_preflight.py` offenders=0、Q43 r4c GREEN）。

**边界与遗留** 0 推权威线、共享检出 `git status --porcelain frontend` 读回 0 行、未 demo/reset、未 vite build、未碰 `*_live.db`/`*_preview.db`、未读未打印任何凭据；工作树 node_modules 只读 junction 收尾摘除并回验共享树完好。我量的是 0f8b925f，现读权威尖又移了（件里 `tip_moved_after_my_measurement=True`），合并方请对新尖重算。r5 下仍无人认领的旗：`DestinationPreparationPanel.tsx:346/:469/:522`、`main.tsx:968/:992`、`ActivityDetail.tsx:206`、`RecoveryRequiredPanel.tsx:166`、`SimulationPanel.tsx:934`、`AgentRunRail.tsx:18`、`V12TripStudioPanel.tsx:106`、`V14RecoveryTruthPanel.tsx:162`、`RealCityDiscoveryPanel.tsx:150`（`V8Experience.tsx` 4 枚归 D）。
