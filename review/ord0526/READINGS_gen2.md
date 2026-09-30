# ORD-0526 · 追尖后的那一代读数（交付所指的一代）

基座换了，字没换。这一枚是交付时应当被引用的一代；`READINGS.md` 里那张表量在旧基座
`6d10cf8059a94e9aa027437e2b55ad61059c01bb` 上，件仍随包（`evidence/door__final0526.json` 等），
两代同名格逐格等值，见下面「跨代携载」。

- 现尖（两路一致，开切时读）：`7862c6de5565c02c20ec2dccaa9da18960603e06`
- 我的两笔：产品 `e506524eb2da49ea3a951e2a4e617eb742c16008`（父位即上面那枚现尖），
  量具换行符 `f66c9d3010fe9fd200b1b9f2d592b4a6d6b9fc30`
- 私有后端 `:8798`（正常与三证）/ `:8799`（反件 M1），库 `run/_gen2_0526.db` / `run/_gen2m1.db`

## 门读数（`evidence/door__gen2_0526.json`）

```
operation_id  f68cb970-7bf7-48b8-9258-dab722c87532
status        COMPLETED        outcome  ALREADY_CURRENT
survey        city_code CN-TIANJIN | places_held 5 | pending_materialisations 0
applied       in_effect true | claim(candidate_count) 5 | candidates_captured 5
              places_before 0 | places_after 5 | places_written 5 | reason null
              provider_key openstreetmap-replay | source_kind OFFLINE_SNAPSHOT
              city_code_inside_file TSN | city_equivalence_predicate real_city._is_tianjin_replay_city
source_kinds  ["OFFLINE_SNAPSHOT"]   registry 长度 1
places 门     GET /api/v1/places?city_code=CN-TIANJIN -> 5 行
plans/generate 422 CATALOG_INSUFFICIENT | places_in_catalog 5 | day_sequences_available 0
```

## 反件 M1（`evidence/door__gen2m1.json`，只多加一枚 `CITYNEXUS_CATALOG_OFFLINE_SOURCES=off`）

```
operation_id  269223bc-a515-419e-989a-4a4d6cb716c4
status        UNAVAILABLE      outcome  NO_REGISTERED_SOURCE
survey        city_code CN-TIANJIN | places_held 0 | pending_materialisations 0
applied       in_effect false  reason   NO_REGISTERED_OFFLINE_SOURCE
registry      []               source_kinds []      places 门 0 行
plans/generate 422 CATALOG_EMPTY | places_in_catalog 0
```

## 反件 M2（`evidence/mutant_M2_row_count_wt526.json`，三趟连跑）

1. `3 passed in 2.79s` —— 诚实基座先绿；
2. `1 failed, 2 passed in 2.15s` —— 注册表那一行改指一枚自报 5 行、实含 3 个不同
   `external_id` 的快照之后，臂红并且点名两枚数：
   `OFFLINE_SOURCE_ROW_COUNT: 5 rows were captured and the store gained 3`，
   失败格 `test_every_registered_offline_source_claims_only_rows_that_land`；
3. `3 passed in 1.86s` —— 还原后 `catalog_sources.py` 字节回到改前（本机字节 sha1
   `1a2843660dae0f57ab3ef0ea4330ab59d5cf2e7d`，改前改后同值），谎报文件删净，
   `git status --porcelain` 为空。

## 三证归属（`evidence/ownership__gen2_0526.json`）

- P1 监听 PID 命令行同时含 `--app-dir D:\moodle\_qoder_seed_ord0489\wt526\backend` 与 `--port 8798`；
- P2 我库里的 journey `61602f1b-ac8a-444a-9eb0-bd17d8f069be` 被路由回读 200，一枚造的 uuid 回 404，
  `GET /places` 行数 == 同文件 `select count(*)` == 5，且
  `every_row_marked_offline_snapshot = true`（五行 `provider_key` 与
  `metadata_json.provenance` 逐行都是 `openstreetmap-replay` / `OFFLINE_SNAPSHOT`）；
- P3 监听进程向上回追到我记录的启动 PID（`listener_reaches_launcher = true`）。

## 集合与红集

`pytest backend/tests -k "catalog or hydration or real_city or discover or offline_source or place or
provenance or source_kind" --ignore=backend/tests/test_v18_hermes_r20_transport_reliability_probe.py`
→ **4 failed, 130 passed, 1 skipped, 1497 deselected**。

那四枚红不是我这一代带上去的，两代对照在包里：干净现尖 `7862c6de…` 上同一组也红这四枚
（`wt526base`，detached、无我的改动）；ORD-0519 之前那一代 `8dd6905dec515b49b7713ea487806fe4f069d92a`
（`wt526pre`）只红 `test_g10_...` 与 `test_G4_...`，`test_g16a_...` / `test_g16b_...` 是绿的
⇒ g16a/g16b 归 ORD-0519 的锚腿次序，机制与另开一单的建议都写在 `READINGS.md` 第 5 节。
`test_v18_hermes_r20_transport_reliability_probe.py` 在本树是
`ModuleNotFoundError: No module named 'citynexus_mcp'`，属稀疏检出的环境限制，具名 NOT_REACHED_BY_LANE。

## 跨代携载（"只搬基座没改字"的三件证明）

1. `git merge-tree --write-tree 7862c6de… f52f056d…` 退出 0，预测树
   `03d827192acd520708f7deda069d831f7951f35d`，冲突段为空；
2. 五枚被量文件在预测树里逐枚等于我写下的 blob：
   `catalog_sources.py f72e4c908faa535b7ace60ead8b28b0ba6cfce90`、
   `catalog_hydration_operations.py a15856d1b72c345dbe4b96ea2f5d9893fb355cd7`、
   `real_city.py ab10aded1b1b25d37c29c773a686d5fa268fb6e7`、
   测试模块 `a9a8d47c6c652ec13aedaa82721cefd95bbbda39`、
   `READINGS.md 92eb77db6adcaf73361334ce3a177cba8e77a292`；
3. 产品那一笔 `git show <commit> | git patch-id --stable` 两代相等：
   `87aca0c70125d1b6d2477d242d5f84184d25b3c5`（`f52f056d…` 父位 `6d10cf80…` vs
   `e506524e…` 父位 `7862c6de…`）——只是换了父位。
