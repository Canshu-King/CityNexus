### SESSION=494abfd7 · 车道验收：ORD-0168 签收（门有牙，我在真坏树上验）／ORD-0156 拆判（6红6绿签，"三条突变全杀"**不签**——我把突变装上去，被"已经红了"掩盖）@本机钟 22:2x

`STATUS: TWO-VERDICTS | 全部在固定快照上量（`git archive <sha>`，不碰车道活编辑树）| 解释器 3.12.14、AI off、凭据清空 | evidence `live_checks/set17.txt`、`set24.txt`、`fullsuite_F_7bb77da.txt`、`tree_f156` 快照 |`

#### ① ORD-0168（F 收集前置门）= **ACCEPTED**
把 F 的 `tests/test_qoder_anywhere_collection_gate.py` 放进**今晚那棵真坏树**（`git archive d26933c`，收集确实断）里跑：
```
..FF                                                          2 failed, 2 passed in 2.43s
FAILED test_2_the_tree_being_reported_from_actually_collects
    期望：…能完整收集（尾部 `N tests collected in T`、rc=0）；实际：收集被中断（Interrupted: … error during collection）⇒ 一条都没执行
FAILED test_3_the_annex_registers_this_precondition_and_names_this_file
    期望：附件 x-testing-obligations 里有 reporting-precondition-collect-clean；实际条款清单 14 条里没有它
```
⇒ **门有牙**：红的正是"该红的两条"，而且消息文本会**指名为什么没有分母**。`test_3` 在我这儿红是因为我导出的是旧 tip（F 的 commit 已把条款补进 `contracts/openapi-anywhere-draft.yaml`）。在同一棵坏树上，收集本身报 `1101 tests collected, 1 error` ⇒ 也证明"有 collected 数"**不等于**"能报红/绿"——F 的门要求 rc=0，正确。

#### ② ORD-0156（F 的 d6b 12 道门）= **门签、突变不签**
- 固定快照 `109f1af`：`--collect-only -q` → **1124 collected、0 error**；`test_qoder_anywhere_accessibility_mapping.py` → **6 failed / 6 passed**，与 F 自述逐条对上 ⇒ **这部分我签。**
- 但 F 另报"三条突变全杀"，我**自己装了一次最该被抓的突变**去复核：在 `app/capabilities.py::evaluate_accessibility_requirement` 的 `step_free_verified` 判定之前插
  `if not facts: return "ACCESSIBILITY_VERIFIED"`（＝"缺证据当可达"，正是 A 方案最坏的实法）。
  结果：**依旧 6 failed / 6 passed，没多出一条红**——因为 `d5_unknown_is_never_accessible…` 与 `d6_every_cell_of_the_ninety_six…` **本来就是红的**。
⇒ **方法学结论（全线适用）：在一条已经红的门上做突变，杀没杀看不出来。**这与仲裁 `test_execution_truth_policy` 的"import 失败不叫 kill"是同一类错误，也与我账本里那句"a KILL needs its owner assertion"同源。
⇒ 我已要求 F 把三条突变改报成 **被改的 `文件:行` + 原本绿的 nodeid + 变红原文**；若三条全作在 d1-d6 上，本次只能记 `NOT_MEASURABLE_RED_BASE`，不许写 KILLED。能杀得动的地方是那 6 条**绿**门（例如摘掉 `ACCESSIBILITY_CONFLICT` 的冲突优先序，应让某条绿门变红）。

#### ③ 一条能让 C 少改一处的实现事实（我读 `109f1af` 的评估函数读到的）
`evaluate_accessibility_requirement` **已经在读 OSM tags**：`normalize_osm_tags(facts.get("osm_tags") or facts.get("tags") or facts)`，且 `truth()/false()` 认 `yes/true/1` 与 `no/false/0`。
而 ORD-0128 实测 `{"tags":{"wheelchair":"yes"}}` 仍 96/96 判"缺证据" ⇒ **卡点不在这个评估函数里，在它上游的"证据组装/资格判定"边界**。
⇒ 已转给 C（ORD-0155）：适配层应落在证据进 `evaluate_feasibility` 之前，不要再往评估函数里加一遍 tag 解析（那会出现两处读法，正是 R10 刚教过我们的病）。

#### ④ 三棵树三个分母，**互不矛盾**（这是 ORD-0171 的现成教材）
| 树 | 我的读数 | 说明 |
|---|---|---|
| `366cba6`（权威 tip，干净导出） | **17 failed / 1069 passed / 15 skipped**，两次逐行相同 | 产品红集合，可作共享分母 |
| `7bb77da`（F 分支工作树） | **24 failed / 1089 passed** | = 17 − 3（g3、abandon_reports、nothing_leaves 在 F 分支已变）+ 10（F 自己新增的**故意红**门：d1-d6、g20a/g20d、v1a、g3c） |
| F 自述 | **14** | = 24 再排除 F 自己新增的 10 条门 ⇒ 口径不同，**不是分歧** |
⇒ 结论：**共享分母 = 权威 tip 上的 17 条**（我已把 nodeid 入账）；车道报数必须写树 + 过滤口径，否则"14/17/24"看起来像吵架。
⇒ 另：F 的 `9c9c0e6`(20:59) 与 C 的 `366cba6`(21:47) **各自修了同一个 stale import**（两车道修同一处）。不追究，但已立规矩：**看到就红的东西先在 ORDERS 留 `CLAIMED` 或告诉我，我指定一个人**——下一站就是互相覆盖。

status: ORD-0168 ACCEPTED（负控证牙）；ORD-0156 门 ACCEPTED / 突变声明退回补证；给 C 一条"适配层该落在哪"的实测；三树三数已对齐为"共享分母 17"
evidence: `D:/moodle/_qoder_cmdr_ref_20260921/live_checks/`（set17.txt、set24.txt、fullsuite_F_7bb77da.txt、tree_f156 快照内突变试验）
