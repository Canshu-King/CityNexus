# ORD-0272 同代复验（一条命令，只读）

lane F `8ccd71d8` · 生成于 2026-09-24T20:17:29+08:00

## 为什么有这一件

本单不闭的最后一环是「**同一代落地后复跑**」：落地方（commander）与 verifier（HJ-P3）都要能在
交付方不在场时把八格门与反突变载体归属复量一遍。所以它是一个**脚本**，不是一段说明。

## 用法

```bash
python o272_reverify.py --tree <落地后的工作树根> [--gen <换代 bundle 名>] \
                        [--python <解释器>] [--json <输出文件>]
python o272_reverify.py --selftest --tree <有门的树> --absent-tree <没门的树>
```

* `--tree` 要**仓库根**（含 `backend/tests`）。传错（例如传 backend 本身）会答
  `NOT-PRESENT` 并说明"这不是绿，是没验"，不会假绿。
* 解释器依次找 `--python` → `<tree>/.venv` → `<tree>/backend/.venv` → 本机已知 venv。
* 退出码：`0` 八格全绿且无警报；`1` 有格红；`3` 树里没门；`4` 八格收集不全（改名/删过）；`5` 自测失败。

## 只读声明（脚本自己印在报告里）

1. 只在被测树里跑 pytest：`-p no:cacheprovider` + `PYTHONDONTWRITEBYTECODE=1` ⇒ 不落
   `.pytest_cache` / `__pycache__`（若跑前没有、跑后出现就报警）；
2. 不部署、不起服务、不发网络请求；
3. 不写任何数据库：套件按 ORD-0211 用一次性临时库，报告**原样贴出**那行解析后的绝对路径，
   并断言其中不含 `_live.db` / `_preview.db`；
4. 跑前跑后对被验文件算 sha256，任何差异判 FAIL。

## 本次读数（写这一件的当天现取）

| 场景 | 树 | verdict | 八格 | 库路径行 | 警报 |
|---|---|---|---|---|---|
| 工作树（git，尖 aa29612c8） | `D:\moodle\_qoder_f_ord253_20260923` | **GATE-GREEN** |  | `ORD-0211 test database: resolved=C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_0gcny_ot\suite.db | exists=False | declared_by=conftest temp dir` | 无 |
| 非 git 导出树（`git archive` 解开的一棵） | `D:\moodle\_qoder_f_run\e_272ab_candidate_aa29612` | **GATE-GREEN** |  | `ORD-0211 test database: resolved=C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_4w9wo0b4\suite.db | exists=False | declared_by=conftest temp dir` | 无 |

双向自测（命令自己跑的）：

```text
[selftest] 有门的树 -> GATE-GREEN（八格 8/8 绿）
[selftest] 没门的树 -> NOT-PRESENT
SELFTEST_PASS
```

三处刻意踩过的坑（都留在脚本注释里）：`-q` 会把 pytest 报告头整块吞掉（那行库路径就在头里）；
`--no-header` 同理；`.pytest_cache` 常常是**更早的跑**留下的，所以只在"跑前没有、跑后出现"时才报警。

## 反突变载体归属（本命令打印的那张表）

| 臂 | 它该带走的 nodeid（已核对在落地树里仍可收集） | 收集 | K8 的跨进程归属 |
|---|---|---|---|
| `K1_claim_stops_committing_before_generation` | tests/test_qoder_ord0272_continuation.py::test_G1_one_mission_generates_once_and_a_plain_resend_replays_the_same_plans, tests/test_qoder_ord0272_continuation.py::test_G2_the_two_states_of_one_claim_answer_differently_and_neither_reruns_generation, tests/test_qoder_ord0272_continuation.py::test_G3_second_device_with_no_client_header_still_gets_the_same_answer, tests/test_qoder_ord0272_continuation.py::test_G4_two_identities_stay_two_doors_and_both_use_the_canonical_409, tests/test_qoder_ord0272_continuation.py::test_G6_no_second_failure_vocabulary_is_introduced, tests/test_qoder_ord0272_continuation.py::test_G7_the_feed_projection_names_the_mission_and_the_plans_it_produced | 6/6 |  |
| `K2_two_identities_merged_into_one` | backend/tests/test_qoder_ord0272_continuation.py::test_G3_second_device_with_no_client_header_still_gets_the_same_answer | 1/1 |  |
| `K3_mission_ownership_door_removed` | backend/tests/test_qoder_ord0272_continuation.py::test_G8_a_mission_that_is_not_this_journeys_is_not_an_identity | 1/1 |  |
| `K4_link_event_stops_naming_the_plans` | backend/tests/test_qoder_ord0272_continuation.py::test_G7_the_feed_projection_names_the_mission_and_the_plans_it_produced | 1/1 |  |
| `K5_both_replay_doors_removed` | tests/test_qoder_ord0272_continuation.py::test_G1_one_mission_generates_once_and_a_plain_resend_replays_the_same_plans, tests/test_qoder_ord0272_continuation.py::test_G2_the_two_states_of_one_claim_answer_differently_and_neither_reruns_generation, tests/test_qoder_ord0272_continuation.py::test_G3_second_device_with_no_client_header_still_gets_the_same_answer, tests/test_qoder_ord0272_continuation.py::test_G4_two_identities_stay_two_doors_and_both_use_the_canonical_409, tests/test_qoder_ord0272_continuation.py::test_G6_no_second_failure_vocabulary_is_introduced | 5/5 |  |
| `K6_unowned_path_laundered_into_a_bare_500` | backend/tests/test_qoder_ord0272_continuation.py::test_G6_no_second_failure_vocabulary_is_introduced, tests/test_v1923_final_code_gate.py::test_v1923_acknowledge_does_not_make_infeasible_plan_selectable, tests/test_v1923_final_code_gate.py::test_v1923_arrival_after_departure_is_a_precise_conflict, tests/test_v1923_final_code_gate.py::test_v1923_zero_alternatives_persists_explicit_no_alternative, tests/test_v1924_final_truth_gate.py::test_v1924_replan_validated_candidates_are_advertised | 5/5 |  |
| `K7_refusal_stops_persisting_the_durable_fact` | tests/test_v1923_final_code_gate.py::test_v1923_zero_alternatives_persists_explicit_no_alternative, tests/test_v1924_final_truth_gate.py::test_v1924_replan_validated_candidates_are_advertised | 2/2 |  |
| `K8_receipt_overwrite_guard_removed` | （空集） | 0/0 | 单进程里占位与回填是同一发 ⇒ 本臂在**本门内没有载体**；『覆盖别人已填的回执』要两个进程才观测得到 ⇒ 归属 verifier（HJ-P3）的跨进程门。本命令不宣称这一面已验。 |

K8 的期望红**本来就是空集**：单进程里占位与回填是同一发，"覆盖别人已填的回执"要两个进程才观测得到 ⇒
归属 HJ-P3 的跨进程门。**本命令不宣称这一面已验**，它只把归属写清。

## 顺带跑（不改变本单判据）

本单回归的两枚既存载体也跑一遍：`tests/test_qoder_current_plan_is_named.py` +
`tests/test_qoder_simulation_mode.py` ⇒ 本次 。

## 与判级的关系

本命令的 verdict 只由八格门推导（外加只读警报）；载体表是**归属说明**，不是把存活说成击杀。
`derived_result` 仍归 verifier。
