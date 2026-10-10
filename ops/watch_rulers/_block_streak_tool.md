## commander 工具 @2026-09-22T16:1x+08 —— **`gate_streak.py`：把仲裁冻结的 GATE_ACCEPTANCE_STREAK 做成可跑的量具**（两向自检过，F / C / HARNESS 直接用它交收据，别再手写循环）

`D:\moodle\_qoder_cmdr_ref_20260921\live_checks\gate_streak.py`。它只做仲裁那八条里**能被机器判的那几条**：每 run 一个独立进程、捕 `ORD-0211 test database: resolved=…` 那行、跑前跑后各读一次行数、**两次落在同一个临时库就判无效**、没捕到解析路径就判 `HARNESS_INVALID`、有 `_live.db`/`_preview.db` 就直接 `ABORT_FORBIDDEN_TARGET`；它**不删任何库**。

用法（在导出树的 `backend` 上跑）：

```text
python gate_streak.py --tree <export>/backend --node <nodeid> --sha <exact SHA> --runs 10 --out streak_<门>.json
```

**两向自检（16:12，`0a4cb23` 钉住树，各 2 个进程，证明它两种结局都真判）**：

| 靶子 | exit | 判定 | 关键读数 |
|---|---|---|---|
| `test_g3_five_concurrent_hydrations…` | 1 / 1 | `STREAK_NOT_MET(0/2_green)` | 两个不同 `cnx_pytest_*` 路径、`duplicate_db_paths=[]`、`row_counts_recorded=true` |
| `test_g1_destination_capability…` | 0 / 0 | `STREAK_MET(2/2)` | 同形收据、`table_count=55`、跑前/跑后行数分别落 JSON |

收据里我特意留了一句不可机器判的话：**第 6 条（不许 sleep／重试／降并发／放宽断言）本工具证明不了**——交单的车道必须自己写一句"我用什么手段达成 streak"，我按 diff 复核；**并且按你 15:58 加的反向要求，streak 全绿本身不等于根因结案**（只到 `STREAK_GREEN`，能破坏保护点并打断 streak 才叫门咬住了）。
⚠ 现场：`56d20ec` 仍是 working tip；16:02 的 cold/静默名单我已逐条叫醒（含 C 的 ORD-0213 未 CLAIMED）；总线已回 `5773181951`，敲门 #60 已送达（页面回读 `第六十次敲门` 命中 1 次、输入框已空）。
