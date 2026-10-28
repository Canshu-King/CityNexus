# 本班后端整套证书（代次 `24a342198d`）

跑法（现读，不是沿用）：`cd backend && python -m pytest -q -p no:warnings --tb=no`，解释器 3.12.14 /
Windows 11。原始日志在本机 `trial/results/20261026_gozero/bt143-backend-full-24a342198d.log`，但仓库的 .gitignore 排除 `*.log`、它不入库 —— 所以能取回的两件是本证书里逐字抄下的末行，与入库的分组摘要 `trial/results/20261026_gozero/bt143-backend-digest.txt`。
先取分母：`python -m pytest -q --collect-only` 退出码 `0`、`2828 tests collected in 4.76s`。

整套结果（从日志末行原样取）：

    255 failed, 2545 passed, 15 skipped, 1 xfailed, 12 errors in 270.29s (0:04:30)

对账：`255 failed + 2545 passed + 15 skipped + 1 xfailed + 12 errors` 合计 2828，与分母 2828 相符。
耗时 270.29 秒。

## 一、这套红不是本班造出来的：写集零交集

`git diff --name-only 22106314c2..HEAD`（本班起点到现尖）共 57 个文件：.github 1 个、frontend 1 个、trial 55 个。
其中 `backend/` 改动 **0** 个、`contracts/` **0** 个 —— 后端与契约一行未动，
所以不需要对照重跑就能说清这套红与本班无关；本班唯一的产品文件改动是
`frontend/src/trial/mobile/WorkspaceActions.tsx`（净增二十七行、删零行）。

## 二、blocker 6 那十五枚：逐条对表（现读）

| 文件 | 交付件记的数 | 本次现读 | 结论 |
| --- | --- | --- | --- |
| `tests/test_sol_concurrency_and_remap.py` | 9 | 9 | 原样还在 |
| `tests/test_qoder_live_replans_endpoint.py` | 5 | 5 | 原样还在 |
| `tests/test_dsh_list_replans_bound.py` | 1 | 1 | 原样还在 |

三枚文件合计现读 15 枚，与 blocker 6 记的 9／5／1 逐条相符 —— 归属仍待裁，没有一条被本班上膛成产品缺陷。

## 三、整套在这台机器上的形状（只报总数，不判新红）

上一次同机整套记录是 2026-10-26 的 `261 failed / 2401 collected / 12 errors`（无逐条基线在册；那组数出自当日记录，本次没重跑那一代）。
本次 `255 failed / 2828 collected / 12 errors` —— 同一档位，errors 数一模一样。
**按口径，没有逐条基线就只报总数与聚焦范围，不判新红**；要判得先有一份逐条在册的红清单。

集中分布（本次现读，前六组）：

- `tests/test_r64_member_side_quest.py` 52 枚
- `tests/test_v13_integrity.py` 16 枚
- `tests/test_r57_group_presence_operator.py` 15 枚
- `tests/test_qoder_trip_shape_and_budget_reference.py` 10 枚
- `tests/stateful/test_journey_truth_state_machine.py` 10 枚
- `tests/test_sol_concurrency_and_remap.py` 9 枚

`tests/test_r64_member_side_quest.py` 一组就占 52 枚，是这套总数里最大的一块；它是否与 live provider /
外部依赖缺席有关，我没有测 —— 这条留作下一步，不当结论。

