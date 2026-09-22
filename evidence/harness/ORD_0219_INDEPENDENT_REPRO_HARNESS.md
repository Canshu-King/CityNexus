# ORD-0219 ③④⑤ · HARNESS 独立复现（缩减但具名）@`4d9ceae`

规格（commander 01:5x 复述、我记账本待触发的那三条）：**① 自己跑满 3 轮全套、报交集＋范围**（绝不重复
B 自认的"两轮当基线"）；**② 连击只从 9 个门里具名挑 2 个 × 10 进程**，报 `STREAK_MET(10)` 与每轮
`path_did_not_exist_before_this_run`，不冲 90 只库；**③ 跑完删自己临时库并报释放字节数**。
纪律：**B 的数只当对照，不进本报告当我的结果。**

## 0 · 坐标

| 项 | 值 |
| --- | --- |
| 权威 SHA | `4d9ceaee785e78fd25482f91d80e3f832aa3f684`（短 `4d9ceae`，B 的 ORD-0219 尖，未 push） |
| 我的导出树 | `D:/moodle/_qoder_harness_revival_20260921/lab/snap_4d9ceae/backend`<br>`git -C D:/moodle/_qoder_integration_20260919 archive 4d9ceae backend data contracts tools \| tar -x -C lab/snap_4d9ceae` |
| 解释器 | `D:\moodle\CityNexus\.venv\Scripts\python.exe`（3.12.14；全仓唯一跑得动本套件的口） |
| 连击量具 | commander 的尺 `D:/moodle/_qoder_cmdr_ref_20260921/live_checks/gate_streak.py`（薄适配器，判据全 import 共享模块） |
| 共享判据模块 | `tests/_qoder_streak_receipt.py` **sha256 `5528700cfbe71711…` / 50,316 B**，与你给的坐标逐字节相同 |
| 采集分母 | `collected 1193 items` = passed 1165~1167 + failed 10~12 + skipped 15 + **xfailed 1**（每轮 `rc=1`） |

**一处必须说的树改动**：`4d9ceae` 里**没有** `tests/_qoder_streak_receipt.py`（那是 F 的判据件，不在产品分支）。
尺 `load_shared()` 拒绝在没有它时猜判据，所以我把**你给定坐标那一枚**（sha256 前缀 `5528700cfbe71711`）
复制进我自己的导出树的 `tests/` 下。⇒ 本报告用的树 = `git archive(4d9ceae)` **+ 这一个量具文件**；
它不是 `def test_` 开头，采集数不变（1193），**没有碰任何产品文件**（权威树/`CityNexus\**` 全程未写）。

## 1 · ① 基线：6 轮全套（两批各 3 轮），报交集＋范围

| 批次 | 命令 | 每轮红数 | 范围 | 交集 | 具名泳者 | 每轮解析库路径 |
| --- | --- | --- | --- | --- | --- | --- |
| A（03:05 收据 `baseline_4d9ceae_3r_0305.json`） | `pytest tests --tb=line -p no:cacheprovider **-q**` | 10 / 11 / 11 | [10, 11] | 10 | 2 | **没抓到**（见下） |
| B（03:32 收据 `baseline_4d9ceae_3r_0332.json`） | `pytest tests --tb=line -p no:cacheprovider` | 11 / 12 / 10 | [10, 12] | 10 | 3 | 3 个互不相同、每轮 `fresh=True` |

**我自己的量具缺陷（已修，如实登记）**：A 批我带了 `-q`，而 ORD-0211 那行
`ORD-0211 test database: resolved=… \| exists=… \| declared_by=…` 是 **pytest report header**——`-q` 把它整块藏掉，
于是 A 批三轮的 `resolved_db_path` 全是 `None`、`distinct_db_paths=0`、`any_path_shared=True`。
**那是我没量到，不是库共用**（这个坑我 09-22 刚替别人指出来过，这次轮到自己踩）。已去掉 `-q` 重跑成 B 批，
B 批三轮：`declared_by=conftest`、`exists=False` ⇒ `path_did_not_exist_before_this_run = True` ×3、
3 个不同 `cnx_pytest_*` 目录。**A 批只作为"红集合观察"保留，其 freshness 一格为 NOT_MEASURED。**

**合并 6 轮（同一 SHA、同一导出树）的基线口径**：

- 红数范围 **[10, 12]**；**交集 10 条具名**（这 10 条 **6/6 全红**）；并集 13 条。
- 稳定红 10 条：`test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at`、
  `test_aiv3_02_v2_mcp_builder_includes_read_plan_and_action_tools`、
  `test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes`、
  `test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts`、
  `test_g14c_the_verdict_must_not_depend_on_the_providers_wording`、
  `test_g5_an_ai_run_that_changed_must_say_which_it_was`、`test_g8a_default_suite_contains_no_live_provider_calls`、
  `test_g9a_the_instrument_actually_sees_write_transactions_and_provider_calls`、
  `test_g9b_provider_http_never_runs_inside_an_open_write_transaction`、
  `test_release_metadata_and_map_entrypoint_are_converged`
- 具名泳者 3 条（**这才是要报的**）：`test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation`
  **2/6**、`test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match` **2/6**、
  `test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage` **1/6**
  ⇒ 三条都是**并发/时序族**，红不是恒定的；任何拿单轮数当基线的说法在这三条上都会翻。
  每轮起跑时我记录了本机其它 python 进程（`lane_backend.py`、8693/8424 上的 uvicorn 等仍在跑）——
  **机器是共享的**，这三条的抖动至少与负载同向，我不把它写成产品根因。
- **B 的 9 道门（`test_qoder_demo_accessibility_evidence.py`）在 6 轮里一条都没进过红集合**（0/6），
  这一点与我量到的 1152 格矩阵一致（见 `EXP_HARNESS_012_PRODUCER_BITE.md`）。

## 2 · ② 连击：具名 2 门 × 10 进程

从 9 道门里挑这两道（一道生产者、一道消费/守卫，都是我自己那两件实验的靶）：

| # | target nodeid（具名） | 形制 | 逐 run 判定 | verdict | closure |
| --- | --- | --- | --- | --- | --- |
| 1 | `tests/test_qoder_demo_accessibility_evidence.py::test_demo_producer_lands_every_claimed_fact_with_demo_provenance` | single-node（已 `run_shape_verified=True`） | 10 × GREEN（`pytest_counts.passed==1` 逐轮佐证，无 SKIPPED 冒充） | **`STREAK_MET(10)`** | `STREAK_GREEN` |
| 2 | `tests/test_qoder_demo_accessibility_evidence.py::test_generation_never_persists_a_candidate_that_conflicts_with_a_hard_capability` | single-node | 10 × GREEN（同上） | **`STREAK_MET(10)`** | `STREAK_GREEN` |

两门的共同读数（逐字段从收据 `runs[]` 再算，不抄字面量）：

```
rounds=10 | green=10 red=0 not_observed=0
freshness path_did_not_exist_before_this_run = True 10/10     ← 每条令要的字段
distinct resolved db paths                    = 10/10          duplicate_db_paths=[]
path_source                                   = app_printed_receipt_line（不是我拼的）
final_row_counts                              = table_count 55 ×10
problems=[] | clause6_command_surface_clean=True | forbidden_targets=[]
```

收据：`lab/evidence/streak_door1_demo_producer_4d9ceae.json`、`streak_door2_generate_conflict_guard_4d9ceae.json`。
复算脚本 `lab/tools/show_streak.py`。

**判级边界（我自己划，不等你纠正）**：两次都停在 `STREAK_GREEN` 而不是 `CLOSED`，因为尺要求
`clause6_declared` 与**独立的反向突变证据**——**交付方是 B，不是我**，我不替它声明第 6 条，
也不拿我这 20 个进程冒充产品反向突变。⇒ 这两格的意义只有：**门在 exact SHA + single-node 形制下可复跑、
每进程独立、每库新鲜、路径来自应用自己打印的收据行**。

## 3 · ③ 删自己的临时库（按具名清单删，不做形状清扫）

`lab/tools/harness_tempdb_sweep.py` 只删**出现在我自己收据字段里**的那 23 个 `cnx_pytest_*` 目录
（`%TEMP%` 是共享的，按名字形状清扫会毁掉别的车道的证据——我犯过一次）：

```
named db paths from my receipts: 23 | temp dirs they live in: 23
removed 23/23 dirs, bytes freed: 32,567,296        复跑同一清单：全部 exists=False，bytes=0
今天我自己建的其它库：evidence_gate_4d9ceae_post0219.db 741,376 B（删）
                       tagscan_<pid>.db + sidecars 774,144 B ×2（工具跑完自删，收据里逐条具名）
本会话合计释放：34,857,104 B ≈ 33.24 MiB
```

**留着没删的**（具名理由，不是忘）：`lab/evidence/_db/` 里 09-21/09-22 的 59 个库
（`promotion_killtest_*`、`evidence_gate_dfdc5d5*`、`simprod_*` 等，合计 ≈ 46 MB）——它们是已发布收据
（EXP-008/009/010）的存储侧对照，删了就得重跑才能对表；你要清我就清，一句话。

## 4 · 顺手量的两件（不在规格里，所以单独列，不混进上面判级）

1. **仲裁第 (c) 项 `tags_json` 迁移清单**：结论 **0**（真实路径下该通道为空），两存储一致，附分母 ⇒
   `EXP_HARNESS_011_TAGS_CHANNEL.md`。**不开 producer-normalization 票；没改 evaluator 去吃 `tags_json`。**
2. **`EXP-HARNESS-012` 生产者咬合回填**：我那把 1152 格常驻门从 `dfdc5d5` 的 320 挡 → `4d9ceae` 的 **354 挡**，
   **34 格新挡全部落在 `stroller_infant`(17) + `large_luggage`(17)**，其余 11 族逐格相同；
   两族的 `constraint_rows 0 → 1`、`severities STRONG → HARD`。⇒ 009 那次"模拟注入"的预言成真，这次是真产品。

## 5 · 我要请 commander 办的一件事（坐标可复推）

逐笔 4 个 patch blob 我全部对上（`git format-patch -1 --stdout` 逐笔 sha1 = 你给的
`1c4d4f14bbed06cb / 308aa9added037fb / f0a562b015c5e0c1 / 1ce909c1ee9a1351`，4/4 精确一致）。
但**累积那一枚 `0d97dfc6b0393ded` (19,924 B) 我用 5 种配方都推不出来**：
`git diff bce7269 4d9ceae`(36,653 B `0be887ef404f437d`)、path-limited 同形、`-- backend/app`(9,268 B)、
`format-patch --stdout bce7269..4d9ceae`(46,959 B)、`git log -p`(46,945 B)。
⇒ 请把**生成那一枚的确切命令**记进账本（或改挂逐笔四枚）；否则"累积 patch"这一坐标在审计侧不可复推，
我不拿一个自己复现不出来的 blob 当已验证坐标。

## 6 · 本件没有做、也不声称做到的

- 没有 push 任何东西；`4d9ceae` 在 GitHub 上仍不可解析 ⇒ **本报告的外部可读坐标是发布后的 git blob sha1**，清单记在账本我那一块里。
- 没有跑真 provider / 真 AI；没有 `demo/reset`；没有写权威树、活库、用户库（活库只 `mode=ro` 扫，
  三条写探针全被拒为 readonly，size+mtime 前后逐字节相同——见 `EXP_HARNESS_011_TAGS_CHANNEL.md` §4）。
- **10 连绿不产生语义正确性**：B 那 9 道门断言的产品语义我没复审（按新口径深度审计归你/仲裁），
  我只证了形制与可复跑。
- 那 3 条时序泳者的**根因不在这份报告里**——我只给出"它们 6 轮里红 1~2 次"这一观察。

— HARNESS `d291c9dc`，2026-09-23（时间戳由 Python 生成为 +08）
