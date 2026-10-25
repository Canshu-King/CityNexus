# 随机城市池为何永远为零：城市身份的 adcode 在落库时丢了（给 Codex 与号令者的事实与切片）

关联 Issue #47、`docs/revolution/SIMULATION_RUN_API_20261025.md`。我只读了本树与 Codex 分支的代码、查了演示库副本，没有改任何后端树或库。

## 预检要什么

Codex 枝的 `app/simulation/preflight.py` 逐城要求：城市码匹配 `(?:CN-)?[0-9]{6}`、至少五处真来源 POI、至少三条真捕获路线。演示库在隔离栈上的读数是「可用 0 座、需要 3 座」，唯一城市缺「城市身份未核实」与「真捕获路线不足三条」。

## 身份为什么不是六位

- 建行程时前端直接给了一个随机身份：`frontend/src/trial/RevolutionFirstLook.tsx:407` 生成 `CN-RV-<12 位>`，注释说「目录解析器会补上正式身份」。
- 后端解析来源时把行程的身份原样复制到每个地点：`backend/app/integrations/discovery/real_city.py:1617`，没有写回真行政区划码的一步。
- 所以 `places.city_code`、`real_place_candidates.city_code` 全是同一个随机码。

## 关键事实：adcode 本来就有，只是没落库

- 研究任务侧一直在用六位 adcode：`backend/app/agent/goal_amap.py:119` 读取 `adcode` 并与任务 region 的 adcode 做前缀比对（`MATCHED`/`CONFLICT`/`UNKNOWN`）。
- 线索字段白名单里就有 `adcode`：`backend/app/agent/goal_tasks.py:831`；缓存事实也保留它：`backend/app/agent/goal_artifacts.py:131`。
- 但 `real_place_candidates` 表没有 `adcode` 列（列清单：`id/journey_id/provider_key/external_id/city_code/name/category/latitude/longitude/tags_json/opening_hours_json/metadata_json/captured_at/expires_at/distance_m/evidence_json/materialized_place_id/status`），一条真实样本的 `metadata_json` 只有 `cost_evidence / discovery_mode / location_type / public_address / region_status / source_urls`；`public_address` 是一个 Python 字典的字符串，里面没有 adcode。

结论：**adcode 在任务侧生成过，落成线索与地点时被丢掉了；行程身份又用了随机码，于是预检永远判「身份未核实」。** 这不是预检过严，是身份链少了两步。

## 三个切片（谁做、做什么、怎么验）

切片 A（研究落库；后端研究域）
- 给 `real_place_candidates` 增 `adcode TEXT` 列（schema + 迁移），研究 lead 落库时写任务 region 的六位 adcode；留空表示「任务没带」，不猜。
- 迁移前的老行保持空值，不回溯编造。

切片 B（身份写回；后端数据域）
- 一次性对账：当某趟行程的 live 线索里同一六位 adcode 达到阈值（建议五条）时，把 `journeys.city_code`、`places.city_code`、`real_place_candidates.city_code` 一并改写为该 adcode，并写一条审计事件（旧值、新值、依据的线索数与 adcode）。
- 幂等键用（journey_id, adcode）；已写回的行程再跑应判「无需改写」。
- 这一步之前，`places.city_code` 与行程身份必须同时改，否则预检里的「地点 city_code 等于线索 city_code」会失配。

切片 C（前端建行程；我的域，但需要裁语）
- `freshCityCode()` 不再造随机码；改为先用用户输入的地区，等来源解析出 adcode 后由切片 B 写回。
- 障碍：`journeys.city_code` 现在非空且参与多处相等判断，若允许「待解析」，后端要接受占位值并在写回时替换；这需要产品裁「DRAFT 行程允许无身份吗」，我不单方面改。

切片 D（路线门槛；数据或产品）
- 演示库北京只有两条真捕获路线，预检要三条。要么补一条真采集（高德步行/公交，走产品自己的抓取路径），要么改门槛（不建议为凑演示降门槛）。

## 验证口径

- 隔离栈 `GET /api/v1/journeys/{id}/simulation/cities?seed=17`：切片 A+B 之后，北京应从 `BLOCKED` 变成 `ELIGIBLE`（或至少只剩「路线不足」这一项，读 `missing` 现读）。
- 前端控制台那一行会从「可用 0 座 / 需要 3 座」变为「可用 N 座」，老师不必看到内部码。
- 任何写回都要能在审计里追到「凭哪几条线索把身份定成这个 adcode」。

## 边界

- 我没有改后端树、没有改演示库；切片 A/B/D 需要他们实施，切片 C 需要一句裁语。
- 即便身份修好，随机城市池仍要三座城都达标才 READY；演示库里另外三座城的真来源数量也没到门槛。
