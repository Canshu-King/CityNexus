# ORD-0526 · 供给适配器盘清、离线源登记、门读数与两枚反件

车道 `5a53846b`。基座 = 权威线 `mirror/integration-frontend-apple-pass1`，开切时现读尖
`6d10cf8059a94e9aa027437e2b55ad61059c01bb`（父位；交付那一代的尖见账块）。
解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`，工作目录 `<tree>/backend`。
树 = `D:/moodle/_qoder_seed_ord0489/wt526`（稀疏集合 backend contracts data tools scripts review）。

## 1. 谁注册、注册在哪、什么条件算「已登记」（我改动之前的事实，逐枚打开回读）

| 腿 | 入口 | 「注册」在哪 | 谁读它 | 会不会写 `places` |
| --- | --- | --- | --- | --- |
| A 旅程实时发现 | `POST /api/v1/journeys/{journey_id}/real-city/discover`（`backend/app/main.py:1786`） | 没有注册表：调用即腿 | 旅客打开一趟旅程时的编排 `capture_real_city_candidates`（`backend/app/integrations/discovery/real_city.py:1423`），内部两处落地 `real_city.py:1481`、`real_city.py:1779` | 会，经 `materialize_candidates`（`real_city.py:1137`） |
| B 密封回放 | 同 A 的编排，`mode=replay`/`captured_replay` | 一个磁盘路径函数 `_replay_snapshot_path`（`real_city.py:241`）+ `_load_replay_snapshot`（`real_city.py:247`） | 只有 A；`_captured_replay_candidates`（`real_city.py:1045`） | 会（同一落地腿） |
| C Photon 身份腿 | 环境变量 `CITYNEXUS_PHOTON_ENABLED` / `CITYNEXUS_PHOTON_BASE_URL`（`backend/app/integrations/provider_config.py:22`、`:23`，import 时冻结） | 配置，不是目录源 | `resolve_destination`（`backend/app/anywhere_capability.py:944`） | 不会：只给身份 |
| D CNX-DEMO 夹具 | 无路由 | `seed_demo`（`backend/app/services.py:241`），其第一行就是 `reset_all(session)`（`services.py:242`） | 只有 `demo/reset` 那条破坏路 | 模板在 `services.py:780` `_templates()`；行不带 canonical 城市号（CMDR 23:20 现读：演示/CNX-DEMO/demo 三发 `canonical_destination_id` 均为 null） |
| E 来源分类词表 | 无 | `SOURCE_KINDS`（`anywhere_capability.py:79`，五种含 `OFFLINE_SNAPSHOT`） | `_classify_source`（`anywhere_capability.py:1065`）读 `provider_key` + `metadata_json.provenance` | 不写，只分类；不认识的最弱处理 |

改动前「已登记」的准确含义就是：**没有登记这回事**。补水 worker 只做一次计数
`_survey`（`backend/app/catalog_hydration_operations.py:630`），判据是同文件 `:862` 与 `:870`
两行的 `places_held == 0 and pending_materialisations == 0`，成立即
`OUTCOME_NO_REGISTERED_SOURCE`。CMDR 22:58 ①是对的：身份不可解析走的是另一具名分支
（`catalog_hydration_operations.py:820`，写在 `:829`），两者不是同一格。

## 2. 这一单登记了什么（产品字节）

新文件 `backend/app/catalog_sources.py`：注册表是字面量表（`catalog_sources.py:63`），
一枚源 = 城市号 + 树内相对路径 + `provider_key` + `source_kind`。

一条源算「已登记」的四个条件全在 `inspect_source`（`catalog_sources.py:91`），每条都不满足就
具名返回原因，绝不静默：

1. 路径不出树（`SOURCE_PATH_OUTSIDE_TREE`）；
2. 解析成带 `candidates` 的 JSON 对象（`SOURCE_UNREADABLE` / `SOURCE_HAS_NO_CANDIDATES`）；
3. 文件里**自报**的 `city_code` 与登记的城市号同城 —— 这枚快照文件自报 `TSN` 而不是
   `CN-TIANJIN`，等价关系借用产品自己已有的谓词 `real_city._is_tianjin_replay_city`，
   我在事实里把它写名（`city_equivalence_predicate`），不在这里新造一张别名表；谓词不认就
   `SOURCE_CITY_MISMATCH`（`test_a_source_about_another_city_is_never_credited_here` 用
   `CN-BEIJING` 走同一形制验到了这条）；
4. 每行候选有 `external_id` / `name` / 数值经纬（`SOURCE_CANDIDATES_UNUSABLE`）。

worker 侧（`catalog_hydration_operations.py`）：两计数皆零时，先叫一次
`apply_registered_offline_source`（定义 `:669`，调用 `:863`），写完**重新** `_survey` 再定
outcome（`:870` 起），所以终态属于库不属于意图；`places_written` 是改前后两次库内计数之差，
不是循环里数的。开关 `CITYNEXUS_CATALOG_OFFLINE_SOURCES=off`（`catalog_sources.py:42`）
是反件用的那扇门，`registry_facts()` 也尊重它。

行级来源标记：`materialize_candidates` 在 `mode=offline_snapshot` 时给
`Place.metadata_json` 写 `provenance = "OFFLINE_SNAPSHOT"`（`real_city.py:71`）。只这一形——
live/replay 行的分类一个字节没动，因为给它们补标记等于**加强**类别，正是词表反着做的方向。
没这条时，离线行也报 `OFFLINE_SNAPSHOT`，但那是 `_classify_source` 的兜底分支
（`anywhere_capability.py:1065`）在起作用，等于「没人能解释的行按最弱处理」，不是具名。

地点名一条也不曾凭空造：五行全部来自 `data/replay/tianjin_real_snapshot.json` 里 OSM 自己的
`way/73422999`、`way/1228981599`、`way/1464199917`、`node/5172762221`、`node/5172662927`，
文件自报 `city_code=TSN`、`city_name=Tianjin`、`captured_at=2026-09-12T03:15:03.659327+00:00`。
按 CMDR 23:20 的裁语，这单**没有**去让解析器认 `CNX-DEMO`，也没有把 D 那半格折进来。

## 3. 门读数（私有后端 `:8798`，三证见 `receipts/ownership__final0526.json`）

逐枚四值（`city_code` / `places_held` / `pending_materialisations` / 终态 `outcome`，带 `operation_id`）：

| 源 | city_code | places_held | pending_materialisations | status | outcome | operation_id |
| --- | --- | --- | --- | --- | --- | --- |
| 登记生效（正常一代） | CN-TIANJIN | 5 | 0 | COMPLETED | ALREADY_CURRENT | `8846c1e1-ea72-4d12-bcd9-2ea4d96edd5d` |
| 源未登记（反件 M1） | CN-TIANJIN | 0 | 0 | UNAVAILABLE | NO_REGISTERED_SOURCE | `ad118535-f609-4fc6-989b-4dd3f65c0be6` |

正常一代 `result.offline_source_applied` 全文（`receipts/door__final0526.json`）：
`in_effect=true`、`candidate_count=5`（文件自报可用行）、`candidates_captured=5`、
`places_before=0`、`places_after=5`、`places_written=5`、`reason=null`、
`source_kind=OFFLINE_SNAPSHOT`、`provider_key=openstreetmap-replay`、`bytes` 见件。
同一代 `source_kinds=["OFFLINE_SNAPSHOT"]`、`registry` 长度 1、
`capability_after=HYDRATABLE`、`coverage_after.attractions=READY`（food/nightlife/lodging/mobility/booking 仍 MISSING，这单没碰）。

紧接着的排程门（同一趟 journey，`POST /api/v1/journeys/{id}/plans/generate`）：
`http_status=422`、`reason_code=CATALOG_INSUFFICIENT`、**`places_in_catalog=5`**、
`day_sequences_available=0`。M1 那一代同一格是 `CATALOG_EMPTY` / `places_in_catalog=0`。
也就是说目录计数现在由这扇门自己报，不再是我数库。

三证归属：P1 监听 PID 的命令行同时含 `--app-dir <tree>\backend` 与 `--port 8798`；
P2 我这库里的 journey id 被路由回读 200、一枚造的 uuid 回 404、`GET /places` 行数 5 ==
同文件 `select count(*)` 5、五行 `provider_key` 全 `openstreetmap-replay` 且
`metadata_json.provenance` 全 `OFFLINE_SNAPSHOT`（`every_row_marked_offline_snapshot=true`）；
P3 监听进程向上回追到我记录的启动 PID。

## 4. 两枚反件，真跑

**M1 源未登记时终态仍是 `NO_REGISTERED_SOURCE`。** 同一扇门、同一 query、同一台私有后端
（`:8799`，另一枚库），只加 `CITYNEXUS_CATALOG_OFFLINE_SOURCES=off`：终态
`NO_REGISTERED_SOURCE` / `UNAVAILABLE`，`places_held=0`，`offline_source_applied.in_effect=false`
`reason=NO_REGISTERED_OFFLINE_SOURCE`，`registry=[]`，`places` 门 0 行，排程门
`CATALOG_EMPTY`。判据没被改松成假成功。件：`receipts/door__finalm1.json`。

**M2 夹具行数被谎报时臂必红。** `receipts/mutant_M2_row_count.json` 三趟连跑：

1. 诚实基座：`3 passed`（先证明它本来就绿，否则「红」不是证据）；
2. 谎报：把注册表那一行改指一枚自报 5 行、实际只有 3 个不同 `external_id` 的快照（重复 id 由
   落地腿按 `(城市, provider_key, external_id)` 收敛，库里真只长 3 行），跑同一枚臂 →
   `1 failed, 2 passed`，红话点名两枚数：`OFFLINE_SOURCE_ROW_COUNT: 5 rows were captured and
   the store gained 3`，失败格
   `tests/test_ord0526_offline_source_row_count_r1.py::test_every_registered_offline_source_claims_only_rows_that_land`；
3. 还原：注册表字节回到改前（本机字节 sha1 `1a2843660dae0f57ab3ef0ea4330ab59d5cf2e7d` 改前改后相同），
   谎报文件删净，重跑 `3 passed`。

臂本体就在交付的测试模块里，对**每一枚**已登记的源生效（不是只对今天这一枚）。

## 5. 三条我在做这单时量到的、需要落字的事实

1. **「落地写路根本不存在」这句不准。** 写路一直有：`materialize_candidates`
   （`real_city.py:1137`）创建 `Place` 行并把 `row.materialized_place_id = place.id` 钉上；
   缺的是补水 worker 从来没有人叫它。这单的改动就是把「叫它」这一步接上，而不是新建一条写路。
2. **我自己 ORD-0519 带上去的一枚回归，具名报。** 同一枚 `plans` 无关、只关乎发现腿：
   `test_qoder_anywhere_discovery_truth.py::test_g16b_an_unexpired_candidate_set_must_answer_without_going_outside`
   期望未过期候选集的暖趟 0 次外呼，现在实际 1 次、路径 `/api/`（Photon），
   同族的 `test_g16a_...` 也因外呼归因换了形而红。两代对照：
   干净现尖 `7862c6de5565c02c20ec2dccaa9da18960603e06` 四枚红（g16a/g16b/g10/G4），
   而 ORD-0519 之前那一代 `8dd6905dec515b49b7713ea487806fe4f069d92a` 只红 g10/G4、
   g16a/g16b 是绿的 ⇒ g16a/g16b 归我那一单，机制是锚腿在 TTL 闸门**之前**被问。
   这单没有顺手改它（不在题面里，且会第二次动同一扇解析/锚门）。要修就另开一单：
   先读未过期库存，再决定要不要出网问锚。
3. **`.gitattributes` 落地后有三枚 CRLF 的 `.py` 在每个新检出里假脏。**
   `git diff --numstat` 在干净检出的现尖上给出 `backend/app/commerce/strengths_generated.py 13/13`、
   `backend/app/stay_mobility.py 2056/2056`、`backend/tests/test_v1922_six_fix_regressions.py 525/525`，
   而我逐枚量过：工作树文件的 CR 字节数与 HEAD blob 完全相同（13 / 2056 / 525），
   即内容 0 处不同、纯换行符申报差。任何车道用 `git status` 数量当「谁没提交」的尺都会被抓一次。

## 6. 形制选择：甲

选了**甲**（捕获腿 + 已有落地写路 ⇒ `places_held > 0`），不是乙（只捕获、新增一枚
`pending_materialisations > 0` 的具名终态）。理由两条：落地腿本来就存在并已把
`materialized_place_id` 钉上（第 5 节 1），乙会造出一个「知道自己有货却不给货」的终态，
而旅客在一趟旅程里走 A 腿时得到的正是甲的形状 —— 两条形制若不同，屏幕上就是两套事实。
`OUTCOME_PENDING_UNAPPLIED` 仍留在原位（`catalog_hydration_operations.py:874` 那段），
没有被这单改名或删除。

## 7. 没动的东西（按令）

`demo/reset` 与 `seed_demo` 一字未动；`prepare-scenario` 那句 "call demo/reset first" 措辞未改，
等 CMDR 判；解析器（`resolve_destination`）与 `CNX-DEMO` 可解析性未动；共享预览库
`_preview.db` 未写；`:8000` `:4781` `:4782` `:4783` `:4785` `:4786` `:8693` 未碰，本单只用
`:8798` `:8799`（两枚都属本车道，P1/P3 已证）。

## 8. 复现命令（逐字可跑）

```
cd D:/moodle/_qoder_seed_ord0489
D:/moodle/CityNexus/.venv/Scripts/python.exe run/drive0526_door_r1.py            # PORT/DB 可换
PORT=8799 DB=_finalm1 EXTRA_ENV='{"CITYNEXUS_CATALOG_OFFLINE_SOURCES":"off"}' \
  D:/moodle/CityNexus/.venv/Scripts/python.exe run/drive0526_door_r1.py           # M1
JOURNEY_ID=<door 里的 journey.id> D:/moodle/CityNexus/.venv/Scripts/python.exe run/prove0526_r1.py
D:/moodle/CityNexus/.venv/Scripts/python.exe run/mutant0526_M2_r1.py              # M2 三趟连跑
cd D:/moodle/_qoder_seed_ord0489/wt526
D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest backend/tests/test_ord0526_offline_source_row_count_r1.py -q
```
