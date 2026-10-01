# ORD-0544 · 锚腿形状与 `ALREADY_CURRENT` 的具名副词（车道 5a53846b）

基座 = 权威线现尖 `c874b1d6bac6735d4ad164379a76db7b73398bd8`（两路现读：`git ls-remote origin`
与本地 remote-tracking ref 同值）。题面只有号令者 15:30 裁语那一句（`cmdr_1530.md` 第 8 条②③），
本文件把「做了什么、没做什么、为什么不做」都落字。

## 1. 根因是量出来的，两代对照各跑一次

同一具仪器（MockTransport 计数外呼）、同一枚私有库，冷一趟暖一趟，只换树：

| | 现尖 `c874b1d6` | ORD-0519 之前 `8dd6905d` |
| --- | --- | --- |
| 冷趟外呼路径 | `/api/`（Photon 先问） | `/search` + `/api/interpreter` |
| 冷趟 `provenance` / `mode` | `REPLAY` / `replay-fallback` | `LIVE_PROVIDER` / `live` |
| 冷趟 `failure_stage` | `anchor_geocode`，`fallback_reason=PROVIDER_BAD_RESPONSE` | 无 |
| 落库候选的 `provider_key` | `openstreetmap-replay`（3 行） | `overpass`（1 行） |
| **暖趟外呼** | **1 次（`/api/`）** | **0 次，`mode=live-cache-hit`** |

件：`readouts/diag_c874b1d6.json`、`readouts/diag_8dd6905d.json`（驱动器 `diag0544_r1.py`，可重跑）。

链条是这一句：Photon 那一腿的正文若不是 GeoJSON 对象，`response.json().get("features")` 抛
`AttributeError`，而解析处的 `except` 元组里只有 `(ValueError, KeyError, TypeError)`——没有
`AttributeError`。异常逃出整趟编排，被判成 `PROVIDER_BAD_RESPONSE at anchor_geocode`，于是**整趟
live 降级成 REPLAY**；落库行的 `provider_key` 因此是 `openstreetmap-replay`，而 TTL 闸门
`_unexpired_cached_candidates`（定义 `backend/app/integrations/discovery/real_city.py:1379`，那一行判据 `backend/app/integrations/discovery/real_city.py:1404`）只把
`provider_key == "overpass"` 的行认成可用缓存 ⇒ 暖趟永远不命中 ⇒ 每次重复请求都再出一次网。
g16a 同一条链：暖冷两趟都没走到 Overpass，仪器的 `/interpreter` 判据自然抓不到查询文本。

## 2. 修法（两处，都不放松判据）

`backend/app/integrations/discovery/real_city.py`：
- `PhotonCityAnchor.search` 先取 `payload = response.json()`，**显式**判形状；不是对象就返回
  `([], reading)`，reading 具名 `outcome = "ANSWERED_NOT_GEOJSON"`、`answered = True`、带
  `http_status` / `bytes` / `elapsed_ms`。语义是「这条腿答了、但答的东西读不懂」，记在一腿上，
  不是整趟失败——于是腿循环继续走到能答的那条腿（Nominatim），Overpass 被正常问到。
- 解析 feature 的 `except` 元组补 `AttributeError, IndexError`，把「读到一半形状不对」也关在同一腿内。

没做的两件，具名说明为什么不做：
- **没有**放宽 TTL 闸门去接受 `openstreetmap-replay` 的行。REPLAY 不算供给是 ORD-0519 自己立的判据，
  放松它就是那道判据禁止的方向。
- **没有**改 `test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor` 或它守着的产品行为。
  那枚见下面第 4 条，它需要的是一个决定，不是一个默认值。

## 3. ③ 具名副词（同一枝）

`backend/app/catalog_hydration_operations.py` 新增两个名字与一个字段：
`OUTCOME_QUALIFIER_OFFLINE_SOURCE = "OFFLINE_SOURCE_SUPPLIED"`、
`OUTCOME_QUALIFIER_ALREADY_HELD = "ALREADY_HELD_IN_STORE"`，结果体里
`"outcome_qualifier"` 由**这一趟自己写进库的行数**决定：`applied.places_written > 0` ⇒
`OFFLINE_SOURCE_SUPPLIED`；否则终态是 `ALREADY_CURRENT` ⇒ `ALREADY_HELD_IN_STORE`；
**其它任何终态 ⇒ `null`**（给拒绝造一个副词就是把零打扮成事）。终态词本身一个没改。

## 4. 臂与两枚反件

`backend/tests/test_ord0544_anchor_leg_shape_r1.py`（`--collect-only` 分母 4，4 passed）：
1. `test_unreadable_anchor_answer_costs_one_leg_not_the_capture`：不可读正文 ⇒ `provenance` 仍是
   `LIVE_PROVIDER`、`failure_stage != anchor_geocode`、候选 `provider_key` 集合 == {`overpass`}、
   腿读数里 photon 记 `ANSWERED_NOT_GEOJSON`（`answered True`、`bytes > 0`）而 nominatim 记
   `ANSWERED`、`anchor.source == nominatim_city_anchor`，**暖趟外呼路径列表 == []** 且
   `mode == live-cache-hit`。
2. `test_geojson_anchor_answer_is_the_leg_credited`：Photon 真答时功劳仍归它、nominatim 记 `SKIPPED`
   ——ORD-0519 的具名记腿契约不许被这次修改冲掉。
3. `test_already_current_says_which_fact_made_it_current`：跑两趟真补水作业，第一趟
   `OFFLINE_SOURCE_SUPPLIED`，第二趟 `ALREADY_HELD_IN_STORE` 且 `offline_source_applied is null`。
4. `test_a_refusal_gets_no_invented_sub_word`：`NO_REGISTERED_SOURCE` 的副词必须是 `null`。

反件（`readouts/mutants_M1_M2.json`，一趟连跑，逐枚带还原校验）：
- M1 把守卫改成 `if payload is None:` 并把 `except` 元组退回三类 ⇒ 臂 1 红，判语点名
  `assert 'REPLAY' == 'LIVE_PROVIDER'`，日志里就是那句
  `PROVIDER_BAD_RESPONSE at anchor_geocode: AttributeError: 'list' object has no attribute 'get'`；
  还原后 `real_city.py` 的 blob 与改前逐字节相同。
- M2 把副词钉成 `None` ⇒ 臂 3 红（而臂 4 仍绿，说明咬的是值不是字段存在性）；还原后
  `catalog_hydration_operations.py` blob 同改前。
- 两次还原后重跑：模块 `4 passed`，`test_qoder_anywhere_discovery_truth.py` `7 passed`。

## 5. 集合：与干净现尖同分母对两遍

同一选择 `-k "catalog or hydration or real_city or discover or offline_source or place or provenance
or source_kind or anchor"`，同一 `--ignore`（`test_v18_hermes_r20_transport_reliability_probe.py`，
`ModuleNotFoundError: citynexus_mcp`，稀疏树环境限制，具名 NOT_REACHED_BY_LANE）：

| 树 | 读数 |
| --- | --- |
| 干净现尖 `c874b1d6`（`wt544ctl`，第二遍） | `5 failed, 168 passed, 1 skipped, 1482 deselected` |
| 本枝（第二遍） | `3 failed, 174 passed, 1 skipped, 1482 deselected` —— 选中总数 178 对 174，差 4 枚正是我新增的那一个模块 |

红的名字逐枚对上：本枝红 `{g10, bounded_fallback, G4}`，现尖红 `{g16a, g16b} ∪ 同这三枚` ⇒
**差集正好是题面点名的 g16a/g16b**。第一遍现尖多报了一枚
`test_qoder_catalog_hydration.py::test_abandon_reports_a_request_not_a_death`：它在两棵树单跑都绿、
整模块单跑也绿、第二遍宽选择里也没再红 ⇒ 记为跨模块状态敏感的偶发，**不归因、不认领**。

## 6. 同一根因族的第三枚红，我不擅自动它

`test_qoder_city_failure_reasons.py::test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor`
在 `8dd6905d` 是**绿的**，在现尖是红的，判语 `assert [5] == [1, 5]`
（"expected the anchor geocode and then the bounded fallback geocode"）。它和 g16a/g16b 同源
（锚腿次序），但它的断言要求「受限回退仍然按同一 label 再地理编码一次」——Photon 答中锚之后是否
还该发这一次，是一个产品决定，裁语里没写，题面只给了「g16a/g16b 回归」六个字。按「不够你动手的那一格
具名报缺，不要自造默认值」，我把它**报在这里，不动**：要么命令者裁「回退腿照旧再问一次」（那我就把
锚腿次序改成只在回退之后取 Photon），要么裁「这枚断言的形状已被 0519 换掉」（那它该重写判据）。

`test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at`（判语
`assert 'PROVIDER_SERVER_ERROR' == 'PROVIDER_BAD_RESPONSE'`）在 `8dd6905d` 就已经红，与本单无关。
`test_g10_...` 与 `test_G4_...` 也在 `8dd6905d` 红，属既有债。

## 7. 复现

```
cd D:/moodle/_qoder_seed_ord0489/wt544
D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest backend/tests/test_ord0544_anchor_leg_shape_r1.py -q
D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest backend/tests/test_qoder_anywhere_discovery_truth.py -q
cd D:/moodle/_qoder_seed_ord0489
TREE=<tree> HEAD=<sha> D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0544/diag0544_r1.py   # 两代对照
D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0544/mutant0544_r1.py                          # 两枚反件
```
