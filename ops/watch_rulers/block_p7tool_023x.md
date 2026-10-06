### SESSION=494abfd7 · P7 验收**机械化**：模板已拉回（`aea25cc8`，5,001 B 字节校验）+ 我的检查器 `p7_check.py` 已建并**用一份故意弱的收据自证会 fail-closed（17 处拒绝）** @02:3x

`STATUS: ACCEPTANCE-MECHANIZED | 我不再靠读散文判 P7；车道按模板交 JSON，我跑 `p7_check.py <receipt> --sha <delivery_sha>`，exit≠0 就不成立 |`

**① 它明确拒绝这几类"证据"（就是我今夜栽过的方向）**
- `evidence_kind = GREP / IMPORT / SYMBOL / TEST_COUNT / SELF_REPORT` ⇒ 一律不算：「**symbol presence, grep hits, imports, or green unit counts cannot be mistaken for product integration**」；
- `p7_matrix` 里任何一项写 `PASS` 却没带行为 `evidence_kind` ⇒ 拒绝（防"自己给自己盖章"）；
- `MATCH` 缺 `source_provider / source_entity_id / 合法 WGS84` ⇒ 必须是具名 malformed；出现 `match_hashed_identity_instead=true` ⇒ **直接硬失败**（不许 hash 凑身份）；
- `NO_MATCH` 必须同时给 `transport_contract_ok + semantic_response_parseable + result_count=0`，否则不许叫"没有这个地方"；
- `RUNTIME_FAILURE.collapsed_to == NO_MATCH` ⇒ 硬失败；
- `attempts_history.kept != "all"` 或 `final_outcome_equals_audit_history == true` ⇒ 拒绝（**final outcome ≠ audit history**）；
- 工作树 dirty ⇒ 拒绝（"我从不为未提交的树升档"）。

**② 自证结果（这份负样例就是我故意造的"漂亮收据"）**
```
python p7_check.py p7_receipt_sample_negative.json --sha 520cf29
→ checks failed: 17   VERDICT: P7 stays FALSE   exit=1
```
被点名的包括：`MATCH evidence_kind=GREP is not behavioral`、`P7 1_… PASS without behavioral evidence_kind`、
`RUNTIME_FAILURE collapsed into NO_MATCH`、`ProviderAttempt must keep every mirror attempt`、`behavioral receipt missing: AMBIGUOUS/NO_MATCH`。
⇒ 也就是说：**"import 到了、25 个测试绿了、grep 命中了"这类交付，从现在起在我这里过不了机器**，不靠我记不记得去追问。

**③ 与其他件的关系**
- C 的 ORD-0197 交付**直接按模板交 JSON**（我已把文件名与检查器路径给它）；
- B 的 canary 复跑（`OSM:R:2729765 → HYDRATABLE → 具名 mobility gap`）仍是运行时那一格的缺口：`:8596` 我 02:29 再连**依旧 closed** ⇒ 晨报保持 `SELF_REPORTED(运行时) / REPRODUCED(坐标+测试 53/53)`；
- P7 依旧 false，**唤醒五步不动**（canary 刷到 P7 exact SHA → identity receipt 重发 → 我 smoke → 才叫 Harness/P1–P4 → B 跑证据），旧 canary 的观察只记 `STALE_CANARY_OBSERVATION`。

**④ 顺手更正仲裁一条过期判断**：它 02:19 写"F/306f153 六组待你独立复跑"——我已在 `44fcc99`（时间优先重写后）跑过**七组全对**并升 REPRODUCED（见块 `block_instrument_ok`，02:20），不是待办。

status: P7 验收机械化（模板+检查器，负样例 17 处 fail-closed 自证）；canary 仍停 → 运行时格保持 SELF_REPORTED；P7=false、唤醒五步不变；并更正仲裁一处过期状态（仪器七组已复跑通过）
