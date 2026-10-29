# 合并 PR #54 之后的全量后端观察（2026-10-26 04:00）

## 怎么跑的

- 目录 `D:/moodle/_cmdr_rescue_v3_1022/backend`，解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`（3.12.14）。
- 命令：`python -m pytest -q --tb=no -p no:cacheprovider`（全量 `tests/`，不跑 e2e/Playwright）。
- 代码：rescue 分支，含 merge `cedeaf2800`（PR #54）与之后的笔记/探针提交（产品前端改动不影响 pytest）。
- 结果：**261 failed, 2401 passed, 15 skipped, 1 xfailed, 12 errors in 291.20s (0:04:51)**。
- 日志：`C:/Users/仓鼠王/AppData/Local/Temp/full54.log`；摘要工具 `trial/human_walk/_full_suite_digest_r1.py`。

## 能判什么、不能判什么

- **能判**：PR #54 的 CI 范围在这次全量里 **0 红**——`tests/test_issue49_*`、`tests/test_issue47_simulation.py`、`tests/test_wp01_wp03.py`、`tests/test_day_rhythm.py`、`tests/test_goal_draft_patch.py` 的 FAILED/ERROR 计数为 0（合入前 wp01 是 7 红，合入后 0）。
- **不能判**：合并前的记录只有汇总数（266 failed / 2374 passed），**没有逐条红清单**，因此这次不能逐条断言「哪些是新红」。总数从 266 failed（旧）到 261 failed + 12 errors（新）也不等值：两次的收集面与错误分类不保证相同。
- 需要逐条判新红时，应先在同一个尖上再跑一次作为当代基线；本次只作为观察。

## 红集中在哪些文件（按 FAILED/ERROR 行分组）

| 计数 | 文件 |
|---|---|
| 52 | `tests/test_r64_member_side_quest.py` |
| 16 | `tests/test_v13_integrity.py` |
| 15 | `tests/test_r57_group_presence_operator.py` |
| 10 | `tests/stateful/test_journey_truth_state_machine.py` |
| 10 | `tests/test_qoder_trip_shape_and_budget_reference.py` |
| 9 | `tests/test_sol_concurrency_and_remap.py` |
| 7 | `tests/test_qoder_ord0402_recycle_bin.py` |
| 7 | `tests/test_qoder_ord0434_share_grants.py` |
| 7 | `tests/test_r63_planned_separation.py` |
| 7（ERROR） | `tests/test_qoder_mobility_evidence_sources.py` |
| 6 | `tests/test_v1923_final_code_gate.py` |
| 5 | `tests/test_qoder_anywhere_matrix_truth.py` |
| 5 | `tests/test_qoder_live_replans_endpoint.py` |
| 5 | `tests/test_qoder_simulation_mode.py` |
| 5（ERROR） | `tests/test_qoder_current_plan_is_named.py` |

其余文件各 1–4 条，完整分组见摘要工具输出。

## 结论

- PR #54 在其声明的范围内没有引入红；课堂相关的聚焦回归仍是 82 passed（另一次单跑）。
- 全量仍有大量既有红，不能当作「课堂栈已坏」的证据，也不能当作「已全绿」的证据。
- 这台机器 C 盘只剩约 1.4 GiB（D 盘约 2.0 GiB）；本次测试的临时目录已删旧三份（`pytest-553/554/555`），当前 `pytest-556` 约 128 MiB 留作复查。清盘前先读引用链，不删工作树与库。
