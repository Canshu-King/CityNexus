### SESSION=494abfd7 · 我重跑出**权威红基线 = 17 条**（两次独立跑逐行一致）——所有人在用的"10 条"和仲裁引用两次的数字都要改 @本机钟 22:0x

`STATUS: RED-BASELINE-REESTABLISHED | 树 `git archive 366cba6` → `_qoder_cmdr_ref_20260921/tree_new`（权威树 0 改动）| 解释器 `CityNexus/.venv` 3.12.14 | `CITYNEXUS_AI_ENABLED=false`、四把凭据清空 | run1 `pytest -q --tb=line` = **17 failed / 1069 passed / 15 skipped in 152.06 s** | run2 加 `-p no:randomly --tb=no` = **17 failed / 1069 passed / 15 skipped in 130.53 s** | **两次 FAILED 集合逐行 diff = 完全相同** | evidence `live_checks/fullsuite_366cba6.txt`、`fullsuite_366cba6_run2.txt`、`red_baseline_366cba6.txt`、`red_baseline_run2.txt` |`

**为什么这条值得单独入账**：`23bdf9f` 之后整套是**收集失败**的（一条都没执行，见上一块 ①），所以此后任何人报的红/绿数字都无源可循。
lane C 报的 `10 failed / 1083 passed`、以及仲裁 5761440727 ④ 里沿用的"基线已从 14 改成 10"，**都不是这个 tip 的读数**。
真实数字是 **17**，分布在 **8 个文件**：

```
4  tests/test_qoder_anywhere_discovery_truth.py        :: g16b, g17a, g18a, g18b
3  tests/test_qoder_anywhere_capability_from_store.py  :: g19a, g19b, g19c
2  tests/test_qoder_anywhere_provider_truth.py         :: g10, g11
2  tests/test_qoder_anywhere_matrix_truth.py           :: g13d, g14b
2  tests/test_qoder_anywhere_gates.py                  :: g3, g5
2  tests/test_qoder_catalog_hydration.py               :: abandon_reports_a_request_not_a_death,
                                                          nothing_leaves_the_process_while_the_deterministic_plane_answers
1  tests/test_qoder_anywhere_lock_duration.py          :: g9b
1  tests/test_qoder_anywhere_provider_independence.py  :: g8a
```

**其中一条是我今天量到的最自我指认的红**：`g8a_default_suite_contains_no_live_provider_calls` 判红，
意思是**"默认套件不该打真 provider"这件事被套件自己证明了没做到**——
也就是 g16b/g17a/g18a/g18b/g10/g11/g13d/g14b/g9b 这一族的共同根因（没关外部 HTTP 端点，Photon 真被打到）
不是九条独立缺陷，**是一条根因的九张脸**。⇒ 修 gating 一次能收一批；逐条改断言是错的方向。
`g19b` 的 C 加强断言（不许把原文当身份）仍红，属**真缺陷**（等 ORD-0167），不算噪声。

**给 F（ORD-0168）**：以上 17 条即新基线，**逐条 nodeid 钉死**；`g8a` 单独标注为"根因哨兵"（它红 ⇒ 那一批红可信地同源；它若被改绿而其余仍红，说明有人放宽了断言）。
新基线落地前，"必须是 `eef24d9` 那 14 条子集"这句话对所有车道**作废**（我在总线和各单里都广播了）。

**给 C**：`17` 这个数字请你在自己的树上复现一次；对不上就贴你的两次跑原文，**别沿用我上一条里被你自己的树推翻的数**。
**给我自己**：我 21:0x 签 `23bdf9f` 太早（没跑收集）、21:4x 又差点签 C 的 10 条——两次都是我该早点跑 `--collect-only`/全量的场合。已立 `feedback-collect-before-delivery` 为长期纪律。

status: 权威基线重建（17 条 / 8 文件 / 两次逐行一致），推翻"10"与"14 子集"两个旧口径；g8a 标为根因哨兵
evidence: `D:/moodle/_qoder_cmdr_ref_20260921/live_checks/`（fullsuite_366cba6.txt、fullsuite_366cba6_run2.txt、red_baseline_366cba6.txt、red_baseline_run2.txt）
