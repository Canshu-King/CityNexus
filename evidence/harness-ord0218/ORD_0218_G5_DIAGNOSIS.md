# ORD-0218 · g5 诊断（只诊断，不改产品码、不挑归属）
SESSION=d291c9dc（HARNESS）· 2026-09-22 18:2x+08 · 交付形态按单：四项齐 + 一张建议单

## 1. exact SHA + run shape + 逐 run 目标节点 verdict

`SHA = 56d20ec`（本单 `if_head`）。补一条同一性检查：`git diff --name-only 56d20ec 50b35e0` 里
**backend 文件数 = 0**（`50b35e0` 只动 frontend/review）⇒ 本诊断在最新尖上同样成立。
工作树 `D:\moodle\_qoder_harness_revival_20260921\lab\snap_56d20ec\backend`（`git archive 56d20ec backend data contracts tools`，350 文件）；
解释器 `D:\moodle\CityNexus\.venv\Scripts\python.exe` 3.12.14；命令面写进收据（第 9 条）。

**目标节点 verdict 取自 pytest 自己的 runtest report（不是整条命令的 exit）**，插件
`lab\plugins\cnx_run_receipt.py`；未被选中的节点记为 `node_not_selected`，**没有报告的记为 `no_report`，两者都不算绿**。
30 个独立进程 / **30 个各不相同的 app 自解析临时库** / 无重试 / 无 sleep / 未降并发 / 未放宽断言。

| run shape（第 9 条要求具名） | g5 逐 run verdict（1..10） | 计数 | 第 10 条分类 |
|---|---|---|---|
| `single-node` | R R R R R R R R R R | 0 绿 / 10 红 | **`STABLE_RED(single-node)`** |
| `whole-file` | R R R R R R R R R R | 0 绿 / 10 红 | **`STABLE_RED(whole-file)`** |
| `node-with-preceding-doors-in-one-process`（g1+g2+g5） | R R R R R R R R R R | 0 绿 / 10 红 | **`STABLE_RED(node-with-preceding-doors…)`** |

**顺手补上仲裁 ① 里那一格空洞**（"whole-file 里 g3 必须抽出逐 run 节点判定"）：
`g3 / whole-file = 8 绿 / 2 红`（红在 run 2、run 6）⇒ **`FLIP_WITHOUT_SHARED_STATE(whole-file)`**——
所以 g3 在**三种形制下都是 FLIP**（single-node 1/9、preceding-doors 7/3、whole-file 8/2），不是 STABLE_RED，也不是恒绿。
收据：`lab\evidence\gate_streak_56d20ec_10r_1807.json`。

## 2. 确切的失败断言，与它期望的产品行为

第一红在 `backend/tests/test_qoder_anywhere_gates.py:352`（原文，未截断）：

> 期望：`run.outcome` 带上 §11 的机器可读语义；实际：run.outcome=None，而 run.status='SKIPPED_EXTERNAL_DEPENDENCY' /
> failure_reason='DeepSeek API key is not configured' —— 这次运行确实什么都没改（没 key、没动作），
> 可它只留下一个运行时标签；一个既没变化也没原因的 200，正是用户早上看到的那句「转了半天啥也没发生」

同一测试后面三条**从未被触达**（因为 :352 先红）：`:358` 要求 `outcome.status ∈ {PLAN_CREATED, NO_ACTION, BLOCKED}`、
`:362` 要求具名 `reason_code`（§11 的 CATALOG_EMPTY / CATALOG_INSUFFICIENT / NO_EXISTING_PLAN_TO_REPLAN / PROVIDER_* 一族）、
`:367` 要求 `user_summary` + `recommended_action`。⇒ **诊断只到 :352 为止是看不全的**，我把三条都跑了静态面（见 §3）。

我自己在同一 SHA、同一入口上复量到同一条读数（进程内 TestClient，我自己的临时库，
**未走 `POST /api/v1/demo/reset`**——测试 setup 用它，我改用进程内 `app.services.seed_demo`）：
`run` 的键里 **`outcome` 存在，值为 `null`**；`run.status='SKIPPED_EXTERNAL_DEPENDENCY'`；
`run.failure_reason='DeepSeek API key is not configured'`；`mission.status` 同。工件 `lab\evidence\ord0218_g5_chain_1809.json`。

## 3. 缺的那一层：发射 / 投影 / 契约 / UI 消费

| 层 | 现状（全部我亲测，file:line） | 判定 |
|---|---|---|
| **投影层** | `app/agent/runtime.py:237`、`:612`、`:625` 三处都把 `run.outcome` 放进响应；实跑 `run` 键里确有 `outcome`（值 null） | **不缺**——管道通着，流过来的是空 |
| **发射层** | 全仓 `app/` 里只有 **5 处**写 `*.outcome`：`runtime.py:589` `run.outcome = final_text or "Tool loop completed without a final summary."`（**只在成功工具循环末尾、且写的是一句散文**）；`guardian.py:427/:486/:649/:829` 写的是 **另一张表** `GuardianRun.outcome`（值取 `reasoning_summary` / `action_status`）。而 `AgentRun(...)` 两个构造点（`runtime.py:318`、`:636`）**参数表里根本没有 outcome**（逐块扫过，块内 `outcome` 命中 = 0）⇒ 新建 run 天生 NULL；skip/no-op 路径（无 key）更是什么都不写 | **这就是缺的那一层** |
| **存储形状** | `db/models.py` 里 `AgentRun.outcome: Mapped[str \| None] = mapped_column(Text, nullable=True)` —— **一个标量文本列**，装不下 §11 要的四字段对象 | 二级缺口（要动列，属产品决定） |
| **契约层** | `contracts/openapi.yaml:1959-1965`：`AgentCommandResponse.run = {type: object, additionalProperties: true}`；`AgentRunResponse` **完全不提 outcome**（全文 `outcome` 只 6 处，且都属于 `/journeys/{id}/outcomes` 与 hydration 作业，另一码事）⇒ 即便发射了，形状无人声明，`frontend/src/generated/api.ts` 也接不住 | 二级缺口（先有形状才有消费） |
| **UI 消费层** | `frontend/src` 里 **`run.outcome` 引用 0 处**；`outcome` 50 处属于别的对象——`generation.outcome`（`V8Experience.tsx:225/:793/:804`，类型 `string \| null`，switch + 兜底）与 discovery/simulation 面板；`user_summary` 前端 0 处、`NO_EXISTING_PLAN_TO_REPLAN` 前后端均 **0 处**、`PLAN_CREATED` **0 处** | **不是 UI 不消费**：产品事实根本没生成，UI 也无 schema 可接 |
| **词汇是否已存在**（避免另起一词） | `NO_ACTION` 已存在但长在另一张表：`db/models.py:310 GuardianRun.action_status` 默认 `"NO_ACTION"`，取值 `MODEL_NO_ACTION`(`guardian.py:272`) / `NO_FEASIBLE_RECOVERY`(`:422`) / `MISSION_REQUIRED`(`:551`)；`CATALOG_EMPTY`/`CATALOG_INSUFFICIENT` 在 `services.py`（各 4 处）；`recommended_action` 在能力格 `anywhere_capability.py:1506` | 复用这些名字，别为 AgentRun 再发明一套 |

**一句话链**：`outcome` 的键在响应里 → 值从来没人填（构造点不带它、skip 路径不写它） → 列是标量文本 → 契约不声明形状 → 前端没有可消费的东西。
所以**第一因在发射层**，投影层无罪，UI 层是第三顺位（它现在唯一在用的 outcome 是 `string | null` 的 `generation.outcome`，正好是 §11 想摆脱的那种散文）。

## 4. 建议单（我不自开 ORD 号，等你签发）

**归属**：**Agent Gateway 写侧**，即 `backend/app/agent/runtime.py` 的写者——账本 11:5x 那行 `B c01d72a3：… runtime.py +40 …` 表明这只文件本轮由 **B `c01d72a3`** 落笔；
**不按"名字里有 AI 就塞给 C"**（单的 ④ 条），也**不归 D**：§3 实测证明产品事实尚未生成（`run.outcome` 恒 null、构造点不带该参数、`user_summary` 全仓 0 处），"事实已存在只是 UI 不消费"这一半**不成立**。
⚠ 一条归属限制：本仓所有提交 author 都是同一个系统账号，`git log %an` **区分不出车道**（`runtime.py` 最后一次改动是 09-19 的 baseline 冻结提交 `380e6ff`）⇒ 我只按账本里的落笔记录建议，不假装是 git 作者证据。

**建议第一步（极窄，三步内可验收）**：
1. 先把 §11 的形状写进契约（`AgentRunResponse.outcome`：`status ∈ {PLAN_CREATED, NO_ACTION, BLOCKED}` + `reason_code` + `user_summary` + `recommended_action`），
   并**沿用已有词汇**（`NO_ACTION` / `MODEL_NO_ACTION` / `NO_FEASIBLE_RECOVERY` / `CATALOG_EMPTY` / `CATALOG_INSUFFICIENT`），只为 `PLAN_CREATED` / `NO_EXISTING_PLAN_TO_REPLAN` 这两个 0 命中的新词做决定；
2. 在 `runtime.py` 的**两个 `AgentRun(...)` 构造点**和 **skip/no-op 出口**填这个对象（不是散文），存法（JSON 进 Text 列 / 新列 / 关系表）作为一条**需要仲裁点头的产品决定**单独提出——因为 `outcome` 现在是 `Text, nullable=True`；
3. 验收按 GATE_ACCEPTANCE_STREAK 第 9/10 条：`STABLE_RED` 的三种形制都要重跑到 `STABLE_GREEN(shape)`，
   **且**用 `live_checks/mutation_anchor_guard.py` 对"填了 outcome"这一点做破坏反例（改成不填 ⇒ 必须回红）。
   禁令照抄：不许 deselect/skip g5、不许把 :352 改成"接受字符串"、不许用措辞匹配把 `failure_reason` 当 outcome。

**顺带一条给 whole-file 读数的干净性（不属于本单，别混交）**：g5 一旦闭了，`whole-file` 那 0/10 才会变成对 g3 有意义的读数；
在此之前，任何人引用"这只文件 0 绿"都必须注明是 g5 造成的——这正是第 10 条"容器 exit 不能替目标节点定性"的另一面。

## 合规

未改产品码、未改测试/断言、未 skip、未 deselect、未放宽任何门、未用措辞匹配绕过；
`POST /api/v1/demo/reset` 我在诊断探针里**没有调用**（测试 setup 调，我改走进程内 `seed_demo`，只写我自己的临时库）；
未开端口、未起 HTTP 服务、未调真 provider（`CITYNEXUS_AI_ENABLED=false`、两个 key 变量清空、`DEMO_MODE=false`）；
未碰 `_live.db`/`_preview.db`；未写权威树与 `CityNexus\**`（只 `git archive` 单向导出 + 只读 grep）；未跑突变。
探针库 `lab\evidence\_db\ord0218_g5_<pid>.db`：脚本结尾那次 unlink 撞上 WinError 32（我自己的进程还持有引擎句柄），已按 per-pid 文件名落盘并在下一次运行开头先删；**现复验 `_db/ord0218*` 剩余 = 0**。
