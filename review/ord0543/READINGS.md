# ORD-0543 · 日序供给腿（裁语选 1：加宽模板腿）——车道 5a53846b

基座：开切现读 `dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5`，追尖落定 `0c061d9eb74b21f0b0b297a068778479b08658b4`
（两路一致：`git ls-remote origin` 与本地 remote-tracking ref）。
题面是号令者 15:30 裁语第 8 条①「开新单 ORD-0543（日序供给腿），归你，不在 0526/0521 里塞」+
重启令里那句「裁语选 1（加宽模板腿）」。我按这个形状做，没自造别的方向。

## 1. 这格原先卡在哪（现读，不是推断）

同一枚驱动（`drive0543_door_r1.py`，私有后端、三证随件）打在**没有我这改的干净树**上：

```
plans/generate  http_status=422  CATALOG_INSUFFICIENT
details         places_in_catalog 5 | city_services_in_catalog 5 | day_sequences_available 0
                candidate_rejections []
calendar.ics    http_status=409  ACTIVE_PLAN_NOT_DECLARED
```

`day_sequences_available` 是 `backend/app/services.py:1978` 那句 `len(raw_templates)`；`raw_templates`
在没有 fixture 模板时由 `_catalogue_templates`（`backend/app/services.py:883`）现排，而它旧代码只收
`_place_window(place)` 为真的地点（`backend/app/services.py:843`：open/close 缺一或倒置就算没说）。
我这枚离线源落的五行里 **1 行说营业时间、4 行是 `{"intervals": [], "status": "UNKNOWN"}`**
（现读自私有库 `run/_dayseq543c.db`，逐行值在 `readouts/door__dayseq543c.json`）。
一行有窗口 ⇒ 任何日序至少要两站 ⇒ 排不出 ⇒ `day_sequences_available` 0 ⇒ 长图/地图/日历一起没分母。

## 2. 改了什么（一处腿、两处上报，共一笔产品改动）

`backend/app/services.py`：

- `_catalogue_templates` 新增具名参数 `day_end_minutes: int = 18 * 60`，与既有 `day_start_minutes`
  合成**产品自己的工作时段** `band`；带子若倒置（`end <= start`）就置为 `None`，此时无窗口地点一律不排
  ——宁可不排，也不把一个不存在的区间当成一站的落地时间。
- 无窗口的地点现在排在**所有有窗口的地点之后**（`unsourced` 接在 `ordered` 尾巴上，按 id 定序可复现），
  所以真实窗口不会被一个猜测顶掉；它们只能落在 `band` 内，超出带子的站照旧被丢（原「drop not squeeze」
  规则没动）。
- 每站落地时在 `Activity.metadata_json` 上写 `hours_basis`：
  `STATED_OPENING_HOURS` 或 `PRODUCT_WORKING_BAND`（锚站 `anchor_role` 不为空时不贴，保留自己的来源）。
  这一枚是关键：加宽之后「排出方案了」绝不能被读成「方案有来源」。
- 短路回答的 `details` 里新增 `day_sequences_unsourced_hours`（`backend/app/services.py:1982`），
  由 `_templates_resting_on_unsourced_hours` **从 `places` 里数出来**，不是写死的句子。
- 模板元组契约 `(place_id, title, start HH:MM, end HH:MM)` 一字未改；终态词表、`CATALOG_EMPTY` /
  `CATALOG_INSUFFICIENT` 的判法都没动。

## 3. 改完之后（同一枚驱动、同一枚库形状，两棵树各跑）

| | 干净树（无加宽） | 本枝（加宽） |
| --- | --- | --- |
| `plans/generate` | `http_status=422`，reason `CATALOG_INSUFFICIENT` | `http_status=201`，候选 3 枚 |
| `day_sequences_available` | 0 | 非零（3 枚候选由它排出） |
| `plans/{id}/select` | 无候选可选 | `http_status=200`，`active_plan_version_id` 落上 |
| `calendar.ics` | `http_status=409` | `http_status=200`，整正文 1669 B，`BEGIN:VEVENT` 5 条，SUMMARY 逐条是这五个地点名 |
| `share-grants` | `http_status=201`（旅程级） | `http_status=201` |
| 每站 `hours_basis` | — | 1 站 `STATED_OPENING_HOURS`、其余 `PRODUCT_WORKING_BAND`（库里 stated 1 / unstated 4 / total 5） |

一次自纠：第一版驱动把 `.ics` 交回时被我自己的 `call()` 截到 200 字符，于是报出「200 B、1 个 VEVENT」
——那是仪器的产物不是产品的。改成整段取回再数，读数是 1669 B / 5 条；两版都在包里（`readouts/`）。

三证归属随每份读数：P1 监听进程命令行同时含 `--app-dir` 指向我这棵树的 `backend` 与 `--port 8803`；
P2 journey 被路由回读 `http_status=201`、一枚现造 uuid 回 `http_status=404`；P3 监听进程向上回追到
我记录的启动 PID（第一版我把 P3 写成了从启动器往**上**走，永远碰不到子进程，已改成从监听进程往上回追）。

## 4. 六枚臂与两枚反件

`backend/tests/test_ord0543_day_sequence_leg_r1.py`，`--collect-only` 分母 6、6 passed：
无窗口城市能排出日序且每站落在带子里；真实窗口仍绑住自己那一站且带子不许把它挪前；
单站不成日、空目录仍空；加宽只读不写（`opening_hours_json` 前后相同）；带子倒置一律不排且有正对照;
`day_sequences_unsourced_hours` 两个方向都量（全有窗口 ⇒ 0，混合 ⇒ >0，全无 ⇒ 等于总数）。

反件（`readouts/mutants_M1_M2.json`，一趟连跑）：M1 把带子回退去掉（无窗口站点重新被跳过）⇒
`4 failed, 2 passed`，点名那句 `the widened leg still returned nothing for a city with no stated hours`；
M2 把带子用到**所有**站点（即无视声明过的营业时间）⇒ **恰好 1 failed**，
`test_a_stated_window_still_bounds_its_own_stop`，判语 `assert 540 >= 840`（09:00 对 14:00）。
两枚还原后 `services.py` 的 blob 与改前相同（`564bb4a9cfb6…`，本机 `git hash-object`），重跑 6 passed。

## 5. 全量：三遍配对，红名逐枚对

同一形状的两棵树（稀疏集合都含 `backend contracts data tools scripts review`）各跑整套，我这树再跑第二遍：

| 跑 | 读数 |
| --- | --- |
| 干净树 `dc9dc10f` | `35 failed, 1608 passed, 16 skipped, 1 xfailed` |
| 本枝 第一遍 | `36 failed, 1612 passed, 16 skipped, 1 xfailed` |
| 本枝 第二遍 | `36 failed, 1612 passed, 16 skipped, 1 xfailed` |

红名**不重合**：本枝两遍都是 36 枚但名字换了两枚（第一遍多
`test_R4_the_seed_reads_the_call_itself_not_the_moment` 与 `test_guardian_status_lists_runs_newest_first`，
第二遍多 `test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation` 与
`test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match`），干净树也少同一枚 g3。
四枚单跑全部绿（各 `1 passed`）⇒ 同字节两趟红名不同、单跑绿 ⇒ 这是跨模块状态敏感那一族
（账本里已点名 guardian / ord0332 R4 / g3 xproc），**不是我带的红，我也不认领它绿**。
**三遍都红的稳定集合 = 34 枚**，与干净树完全一致 ⇒ 加宽在整套里没引入确定性新红。

一处过程自纠：第一次配对时干净树少红了那枚日历导出
（`test_an_activity_without_a_usable_clock_is_skipped_and_counted_never_silently_lost`），我差点报成
「我这改把它修好了」。读它才发现第 641-642 行断言 `review/ord0496/…` 那枚文件存在，而我的干净树稀疏集合里
没有 `review` ——是**我树的形状造的假红**。补 `review` 后两棵树红名一致（各 2 failed / 229 passed）。

## 6. 我没做的两件事（具名）

- **没**给 `day_sequences_available` 或 `hours_basis` 加任何前端文案/屏幕改动：本单题面是腿，
  上屏那格在别的单里。
- **没**动 `candidate_rejections`、预算门、mobility 证据这些同一条流水线上的其他判据；
  `mobility` 在补水代答里仍是 `MISSING`，出行时间在带子里仍按 0/冻结值算——那是 0521/新单的格，不塞进这单。

## 7. 复现

```
cd D:/moodle/_qoder_seed_ord0489/wt543
D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest backend/tests/test_ord0543_day_sequence_leg_r1.py -q
cd D:/moodle/_qoder_seed_ord0489
TREE=D:/moodle/_qoder_seed_ord0489/wt543  PORT=8803 DB=_dayseq543c python run/drive0543_door_r1.py   # 改后
TREE=D:/moodle/_qoder_seed_ord0489/wt543ctl PORT=8804 DB=_ctl543  python run/drive0543_door_r1.py   # 对照
python run/mutant0543_r1.py                                                                          # 两枚反件
```
