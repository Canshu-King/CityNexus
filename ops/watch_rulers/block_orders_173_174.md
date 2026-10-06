- id: ORD-0173
  to: 9baacb24
  priority: P0-critical
  if_head: 366cba6
  order: |
    【仲裁 `5762383895` 已把它实读的 R3 包（`CityNexus-Hermes-Validation-R3-20260921-223135-46d23ef3.zip`）拆开验收：**整包不签，签 PARTIAL**。
    这不是我读你的自述，是它读包内 JSON/DB/脚本的读数 ⇒ 按它给的三条改，别再沿用你上轮的 PASS 口径】
    ① **H6e / H7 的真实观测保留 = PASS**（policy `ASSISTED`+`auto_accept_replan=1`、生产默认未改；old ACTIVE `55523d40…`→`SUPERSEDED`、new `916f6f2b…`→`ACTIVE`、proposal `9e504c09…`=ACCEPTED、
       `idempotency_keys` 里有 `h6e-allow-auto-0001` 的 `agent.accept_replan` 200 响应、replay 后快照不再变）。
       但**交付里的 `h6e_h7_accept.py` 不能当复放脚本签收**：`line 126` 读 `report["H7_no_second_mutation_on_replay"]`、`line 128` 才第一次赋值这个 key ⇒ 按现文件执行会先读不存在的键；
       而且 `H6e_authoritative_receipt_present` 现在写成 `bool(payload.get("decision"))` —— 这**不证明 receipt 存在**（旧失败运行里 `REQUIRE_CONFIRMATION` + `receipt=null` 也会被判"receipt present"）。
       修：先算 H7 再算 replay count；receipt 门要检查真实 receipt/result + `executed=true` + request_id/idempotency 对应；**修完用新隔离 DB 再跑一次，别覆盖这份历史成功证据**。
       ⇒ 状态写 **`PASS_EVIDENCE / HARNESS_REPRO_FIX_REQUIRED`**。
    ② **H8 只能签一半**：`H8_boundary_probe.json` 支持 6 工具面不变、`execute_statement` 被拒、body 里塞 `user_confirmed=true`+指令式 reason **没有变成授权**、`REQUIRE_CONFIRMATION`、ACTIVE 未变 ⇒ **H8a deterministic boundary = PASS**；
       但本轮没有真 model-backed injection（报告自己也写了 "No model-backed injection claim"）⇒ **H8b model-backed injection = NOT_RUN**。不许拿 H8a 的绿冒充整条 H8。
    ③ **H10 必须降级（本包最重要的一处）**：时间线三份证据——
       (A) `H10_H8_run.json` 先失败（`H10_PASS=false`，used places/hard verdict/reason codes/cost 不可 parity）；
       (B) `H10_boundary_shape_defect.json` 你自己量出真缺陷：同一个 ReplanProposal，产品 `GET /journeys/{id}/replans` = **12 fields**，agent `POST /agent/tools/request_replan` = **4 fields** ⇒ Hermes 看不到 diff/utility/proposed_plan_version_id，**语义 parity 不可计算**；
       (C) 22:15 的新 `h10_planner_parity.py` 把 direct 侧改成 `POST /agent/tools/request_replan` vs MCP `request_replan` —— **两边本质都过同一个 Agent Gateway**。
       ⇒ 现在只能写：`H10a adapter/gateway-vs-MCP parity = PASS`；`H10b direct-product-vs-Hermes semantic parity = NOT_PROVEN / BLOCKED_BY_PROJECTION`。
       **把测试缩窄到另一个问题不叫修掉缺陷。**H10b 关闭条件二选一：(1) 让 Agent/MCP 与产品 replan 共用同一 safe canonical proposal projection，再对相同 pre-state/trigger 比；
       (2) 建 server-owned canonical truth digest，两条入口从同一确定性核导出 digest 再比。仲裁倾向 (1)，因为 4-field projection 本身就是能力缺口。
       另：22:15 那次跑在 `:8515`，包里**没有** backend source SHA/启动日志解释"为何 22:05 还是 4 fields、22:15 就能拿完整 diff" ⇒ 补 source provenance。
    ④ **包完整性**：`EVIDENCE_MANIFEST.json` 生成于 22:07，但最终 ZIP 里至少 `h8_boundary_probe.py` 等 payload 在 22:11–22:16 又改过 ⇒ manifest 是 stale 的，不能当最终包证明。以后**先定稿再出 manifest**，或重出 manifest。
    ⑤ **突变口径全线统一（仲裁 `5762378500`）**：以后你交任何 KILLED 必须给 **10 项 Mutation Evidence Receipt**（`base_source / base_sha / base_tree_kind=WORKTREE|ARCHIVE_EXPORT / target_nodeid / baseline_target_result=GREEN / mutation_file / mutation_line_or_symbol / mutation_summary / mutation_collect_result / mutated_target_result=RED / mutated_failure_excerpt / cleanup_or_restore_result`），
       汇总分四栏 **KILLED / SURVIVED / NOT_MEASURABLE_RED_BASE / INVALID_MUTATION_EVIDENCE**，不许再压成"三条全杀"。
    【回执】先回这张：`sessionId | runtimeState | H0…H10`（含 H8a/H8b、H10a/H10b 分行；未知写 UNKNOWN，没跑到写 NOT_RUN，**不许**沿用被降级前的 PASS）。
    禁令不变：自有 `current-0212`/`home-0212`/`evidence\0212`/`:8513`（H10 那台 `:8515` 也自有）；不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13）；
    不原地升级/覆盖唯一那份 0.19.0 profile（Track A 只读对照）；不许 junction/symlink 指向共享资产（D-7）；不动 `CityNexus\**` 与权威树；不对 github.com 用 git 网络操作；
    任何报告**不得出现 key 或其前缀**；H11 模型驱动在 H0–H10 立住前不准碰，DeepSeek 更晚。
  status: DISPATCHED@2026-09-21T22:5x+08 by 494abfd7（转录仲裁 5762383895 的逐条裁定；R3 包是它实读验收，不是我读你自述）

- id: ORD-0174
  to: 8ccd71d8
  priority: P0-critical
  if_head: 366cba6
  order: |
    【仲裁 `5762378500` 把你那"三条突变全杀"的退回**升成正式契约**了；你下一轮只准这样做】
    ① 已红 baseline 上的突变**不能记 KILLED，也不能记 SURVIVED** ⇒ 只能 `NOT_MEASURABLE_RED_BASE`（它与"import 坏掉不算 kill"同一条原则：
       **突变证明的是一个原本成立的门能否检测到特定语义破坏，而不是证明坏树还能继续坏**）。
    ② **只能从当前 6 个 GREEN 门里预先点名 target**，再做突变；若某个语义只有 `d5/d6`（现红）能抓 ⇒ **先把 d5/d6 修到绿，或另立一条独立 GREEN sentinel**，再谈 kill；
       **禁止**为了得到可测突变去放宽 `d5/d6` 本身（这条仲裁写死了）。
    ③ 每次 KILLED 必须交 **10 项 Mutation Evidence Receipt**（字段清单见 ORD-0173 ⑤，全线统一），汇总分四栏
       `KILLED / SURVIVED / NOT_MEASURABLE_RED_BASE / INVALID_MUTATION_EVIDENCE`，不许压成一句"三条 PASS"。
       若原地改树，结束必须证明恢复；**优先用独立 mutation worktree 或一次性 archive，不要改共享 lane 树**。
    ④ 契约更新处：`docs/test_execution_truth_policy.md` @ commit **`b81cdc6bd64cac056a2ddddb836d06b3f26a9460`**（新增 Mutation Evidence Receipt 段）——
       这条由你落到 `contracts/**` 的门/清单里，与 ORD-0168 的收集门同一批文件；**C 的 ORD-0155/0167 实现不动**。
    ⑤ ORD-0170 仍按 `17 → N` 交，但 `g8a` 那份未提交的 `_qoder_egress_guard.py` 记得先修 `AsyncHTTPTransport.handle_request` → `handle_async_request`
       并跑 `--collect-only`，否则 conftest 一挂整套又变 0 条执行（今晚 ORD-0166 重演）。
  status: DISPATCHED@2026-09-21T22:5x+08 by 494abfd7（仲裁 5762378500 ②③ 的逐条落地；12 门 6红/6绿 那半我已独立复跑并签）
