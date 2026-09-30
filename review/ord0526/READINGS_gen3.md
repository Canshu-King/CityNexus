# ORD-0526 · 第三代读数（基座 `2f0568e05fb2540266b8e4fdbafb1e03d25a29c7`，交付所指的一代）

`READINGS.md` 量在 `6d10cf80…`、`READINGS_gen2.md` 量在 `7862c6de…`；本文件是最新的一代，
账块引用的就是这一代。三代同名格逐格等值（下面把值都写全，读者不必回翻）。

- 现尖（两路一致：`git ls-remote origin` 与本地 remote-tracking ref）：
  `2f0568e05fb2540266b8e4fdbafb1e03d25a29c7`
- 交付链（四笔线性坐在那枚现尖上）：`589d6a5787f4d654928c71ef39022a990914a95a`（产品）→
  `8ef4a49e…`（量具换行符）→ `65ad0df8…`（上一代收据）→ 本笔。head 以账块为准。
- 私有后端 `:8798`（正常与三证）/ `:8799`（反件 M1）；库 `run/_gen3_0526.db` / `run/_gen3m1.db`

## 门读数（件 `receipts/door__gen3_0526.json`）

```
operation_id  0a81d27b-4a68-44e1-b9ff-40e0e3e7a734
status COMPLETED   outcome ALREADY_CURRENT   canonical CN-TIANJIN
survey  city_code CN-TIANJIN | places_held 5 | pending_materialisations 0
applied in_effect true | candidate_count 5 | candidates_captured 5
        places_before 0 | places_after 5 | places_written 5 | reason null
        provider_key openstreetmap-replay | source_kind OFFLINE_SNAPSHOT
        city_code_inside_file TSN | city_equivalence_predicate real_city._is_tianjin_replay_city
source_kinds ["OFFLINE_SNAPSHOT"] | registry 长度 1 | places 门 5 行
plans/generate http_status=422 CATALOG_INSUFFICIENT | places_in_catalog 5 | day_sequences_available 0
```

## 反件 M1（件 `receipts/door__gen3m1.json`）

```
operation_id  066a7bc4-80a6-4b55-97c5-c54e46b65849
status UNAVAILABLE   outcome NO_REGISTERED_SOURCE
survey places_held 0 | pending_materialisations 0
applied in_effect false | reason NO_REGISTERED_OFFLINE_SOURCE | places_written 0
registry [] | source_kinds [] | places 门 0 行
plans/generate http_status=422 CATALOG_EMPTY | places_in_catalog 0
```

## 反件 M2（件 `receipts/mutant_M2_row_count_wt526.json`，一趟连跑三趟）

`3 passed in 1.45s` ⇒ 把注册表那一行改指自报 5 行、实含 3 个不同 `external_id` 的快照 ⇒
`1 failed, 2 passed in 1.21s`，判语点名两枚数
`OFFLINE_SOURCE_ROW_COUNT: 5 rows were captured and the store gained 3` ⇒
还原后 `3 passed in 1.46s`，`catalog_sources.py` 的**本机字节 sha1**（对文件字节重算的
sha1，不是 git blob）改前改后同值，谎报文件删净，`git status --porcelain` 为空。

## 三证归属（件 `receipts/ownership__gen3_0526.json`）

P1 监听进程命令行同时含 `--app-dir` 指向我这棵树的 `backend` 与 `--port 8798`；P2 我库里的
journey 被路由回读 `http_status=200`、一枚现造 uuid 回 `http_status=404`、`GET /places` 行数与同文件
`select count(*)` 相等（都是 5），且 `every_row_marked_offline_snapshot` = true；
P3 监听进程向上回追到我记录的启动 PID。

## 为什么这一代必须重跑，以及 ORD-0522 撞同一枚文件的结果

新基座里 `backend/app/catalog_hydration_operations.py` 被 ORD-0522 加过一段只读看板
（`catalog_hydration_operations.py:265` 的 `OUTCOMES_WITH_SUPPLY`、`:280` 的 `leg_states`），
所以我那枚 blob 在预测树里被自动合并**改写**（`a15856d1…` → `d7d8d587…`，行号整体下移：
`_survey` 现在在 `:752`、`apply_registered_offline_source` 在 `:791`、worker 的调用点在 `:985`）。
`git merge-tree --write-tree` 退出码 0、无冲突标记，但「不冲突」不等于「没被改写」——
这一步只有把路径在预测树里打开回读才看得见。合并后的 PERSISTING 段仍然只有一处供给调用
（我的 `:985`），没有第二次写；而他们那句 `OUTCOMES_WITH_SUPPLY = (CATALOG_PREPARED, ALREADY_CURRENT)`
正好把我这单挣来的终态认成「留下了能排的物质」的结尾，两单在这一格上不打架。

集合（`-k "catalog or hydration or real_city or discover or offline_source or place or provenance or source_kind"`，
`--ignore` 掉稀疏树里 `ModuleNotFoundError: citynexus_mcp` 那一枚）：
`4 failed, 130 passed, 1 skipped, 1505 deselected`。四枚红与上一代同一组、同一批名字，
归因见 `READINGS_gen2.md` 的红集那一节（两代干净检出对照：现尖红这四枚，ORD-0519 之前只红
`test_g10_…` 与 `test_G4_…` ⇒ `test_g16a_…` / `test_g16b_…` 归 ORD-0519）。
