### SESSION=494abfd7 · 两份新契约已字节校验拉回并转成可执行派发；**我用六组入参探车道仪器，抓到一处判定顺序错**（B 轴本来红会被误判 COUPLED）@01:1x

`STATUS: CONTRACTS-PULLED-INSTRUMENT-FLAW-FOUND | 树 `git archive 14a5b64` → `v_14a5b64`（权威树 0 写）| 直接 import `tests/_qoder_mutation_receipts.cross_mutation_verdict` 六组调用，全 targeted（按 P5 未跑全量）|`

#### ① 两份新契约（仲裁分支尖端 `833d56acb`，我之前只跟到 `02d7d3f4`）
- `docs/pending_destination_identity_policy.md` @ **`833d56acb`**（+61，本地 16,653 B，blob sha 已核）：**mobility-gap 里程碑**定义 —— 允许停在 `HYDRATABLE + MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`，但必须交 **14 项 used-edge 收据**（`candidate_id / used_edge_count / used_edge_ids / per_edge_source_kind / per_edge_provider_or_fixture / per_edge_fact_quality / per_edge_hard_eligible / hard_eligible_count / frozen_fixture_count / synthetic_default_count / unknown_count / first_blocking_edge_or_edges / final_product_state / blocker_reason`）。
  六条硬规则里第 3 条**点名我的证成方式**：`184/240 = SYNTHETIC_DEFAULT` 这类聚合数**只能当背景**，blocker 必须由**该候选真正使用的 edge** 清点得出；第 4 条反向也管：**若真实 used edges 全 hard-eligible，就必须继续走 SELECTABLE**，不许拿宏观数据提前躺平。已原文转 B（ORD-0192）。
- `docs/test_execution_truth_policy.md` @ **`4b0792ede`**（+38/-1，本地 21,762 B，blob sha 已核）：**单次全量只能算 observation**，不得称基线 ⇒ 转给 F：下次全量标 `FINAL_SUITE_OBSERVATION_ONLY`，基线一律"交集+区间+具名轮换成员"。

#### ② 我自己探仪器，抓到一处**判定顺序**错（正是今晚反复出现的同一族）
```
真独立      GREEN/RED/GREEN/GREEN  -> INDEPENDENT            ✅
假独立(耦合) GREEN/RED/GREEN/RED   -> COUPLED                ✅
靶子本已红   RED/RED/GREEN/GREEN   -> INCONCLUSIVE           ✅
突变没撬动   GREEN/GREEN/GREEN/GREEN-> INCONCLUSIVE           ✅
非绿非红     …UNKNOWN…            -> INVALID_MUTATION_EVIDENCE✅
B 本来就红   GREEN/RED/RED/RED     -> COUPLED                ❌ 应为 INCONCLUSIVE
```
⇒ 成因：`axis_b_before != GREEN` 的检查排在 `axis_b_after == RED → COUPLED` **之后**，于是"B 在突变前就红"被归因成"我的突变把 B 带红了"——**把先存的红算成本次突变的后果**，与我自己今晚"184/240 当 blocker 依据"、"快照统计当候选结论"是同一形状。
⇒ 已要求：把 b_before 检查提到 COUPLED 之前，并把这第六组补进它的"双向自证"；**修完我重跑六组再升 REPRODUCED**（在此之前它的仪器继续记 SELF_REPORTED，我不会提前升档）。
⇒ 另提议 F 加一道元门：E2E 收据**不得引全仓聚合数**当 blocker 依据，只能引该候选的 `used_edge_ids`。

#### ③ 一条会把"工具问题"伪装成"产品结论"的现场风险（已入本地记忆，也转给 B）
**Photon 拒默认 httpx User-Agent ⇒ 403；换描述性 UA 就 200。**
⇒ 若冷链解析突然 `NO_MATCH`／解析失败，**先查 UA 再下结论**，并把 UA 固定写进适配器。"403 当 NO_MATCH"正是 R14 要禁的跨层误归因，而且是今晚最可能发生的一次（因为 B 正在真打 provider）。

status: 两份新契约（833d56acb / 4b0792ede）拉回并转派 B/F；六组入参探出仪器判定顺序错（B 本已红误判 COUPLED），修后方升 REPRODUCED；Photon UA 403 风险已提示 B
evidence: `v_14a5b64` 上六组 `cross_mutation_verdict` 原样返回值 · 两份 docs 的 blob sha 与磁盘一致 · 本地镜像 `arbiter_docs/`
