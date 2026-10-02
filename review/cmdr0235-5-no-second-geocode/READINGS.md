# CMDR 02:35 第 5 条 · 锚答中之后，回退腿不再问第二遍地理编码（车道 `5a53846b`）

裁语原文（账本 `CMDR 02:35` 块第一节第 5 条，逐字）：

> `5a53846b`：**裁：不二次地理编码**。锚（Photon）答中之后回退腿不许再问一遍——回退腿只伺候"锚没答"这一种情况，这与既有常设规矩（answered-zero 不许跌落 Nominatim）同源。现尖那枚红的期望句按此改：断言「锚已答 ⇒ 回退门零调用」，并配一枚反件（把锚答拆掉，回退门必须被问到）。改完自申报。

## 〇、形制（现读）

| 项 | 值 |
| --- | --- |
| 基座（号令者 day18 权威尖） | `00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9` |
| 我这枝 | `refs/heads/review/newlane-fallback-no-second-geocode-r1`（新 ref 名，0 次强推） |
| 交付 head | 见 §七（推上去之后从服务器侧回读，不用本地记忆） |
| 车道提交（旧基座 `5a4cdbd2…` 上那一笔） | `e04c4ad781968bd18f27b1c035c93c9badf44995`，树 `e0b90701a7f649757594c7b55b6805193f4ddae5` |
| 追尖重切那一笔 | 树里两枚字节与上面逐枚相同：`real_city.py` = `5bed42608bdfaad1067c50abb11918dfba4710b4`，`test_qoder_city_failure_reasons.py` = `77433ceddec4200d8e85fec3fccccf3d4cd439b9` ⇒ 这一跳只搬基座，没重做别的东西 |
| 尖上那两枚（改动前） | `real_city.py` = `e7663564bf47c0fc0923b790f54c429ef4ac4eeb`；`services.py`/`real_city.py` 在 `5a4cdbd2…00b5f25e` 之间上游 0 改（`git diff --name-only` 只列 `main.py`、`schemas.py` 与 ORD-0531/0512 那族） |
| 解释器 | `D:/moodle/CityNexus/.venv/Scripts/python.exe`（`Python 3.12.14`，全套件唯一能跑的那枚） |
| 树 | `D:/moodle/_qoder_seed_ord0489/wt543tip`，稀疏集合 `backend contracts data frontend review scripts tools`（两侧同集合，所以分母可比） |

## 一、落成了什么（产品一处，测试一处）

`backend/app/integrations/discovery/real_city.py`：

- `:1652` 新增谓词 `anchor_grounded_by_leg`：本次调用里**有一条腿真的被问过、真的答了、而且锚的 `source` 就是这条腿**（`photon_…` / `nominatim_…`）。
- `:1658`-`:1672` 回退门改成三岔：
  - 有候选 ⇒ `NOT_NEEDED`（本来就不该问，也不问）；
  - 锚是腿答上的 ⇒ `SKIPPED_ANCHOR_GROUNDED_BY_<source>`，**不调 `geocoder.search`**；
  - 其余（本调用一条腿都没问，圆心来自行程自己的状态）⇒ 仍问，且仍用人话标签 `city_label`、不用我们的内部码（ORD-0099 ① 那条规矩在收窄之后照样守住）。
- `fallback_geocode` 这个名字进了**三种 live 形状**：成功那一形（`:1701`）、replay-fallback（`:1750`）、live-unavailable（`:1771`）。后两形才是调用方实际拿到的响应，只写成功形等于没写。
- `:1542` 把 `fallback_geocode` 初始化成 `NOT_REACHED`：畸形标签那条路在任何腿被问之前就抛，未初始化会拿 `UnboundLocalError` 替掉诚实的原因码（这是我自己在门内第一次跑到就撞到的，不是推测）。

`backend/tests/test_qoder_city_failure_reasons.py`：三枚新臂 + 两枚兄弟臂改前置 + 替掉旧臂一枚；两枚仪器 `_RecordingPhoton`（`:141`）、`_install_photon_leg`（`:174`）、`_give_the_trip_its_own_centre`（`:189`）。Photon 的双面夹**没有**放进共享夹具——放共享夹具会改掉兄弟臂的世界（实测 6 枚红，而该文件本来只有 2 枚）。

## 二、被替掉的那枚旧臂为什么必须替（它是现尖的红，不是我造的红）

旧臂 `test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor` 断言 `[1, 5] == 两次地理编码`。在干净尖 `5a4cdbd2…` 与 `00b5f25e…` 上它都红，读数（`readouts/aff_tip_r2.txt`）：

```
E       AssertionError: expected the anchor geocode and then the bounded fallback geocode: [('TIANJIN', 5)]
E       assert [5] == [1, 5]
```

它把"哪条腿答"当成了网络形状：Photon 答上 ⇒ 根本不会有 limit=1 那次 Nominatim 问 ⇒ 只有回退那一次。裁语要的正是把这一句换成「锚已答 ⇒ 回退门零调用」，所以旧臂的**期望句**按裁语重写，不是删掉了事：

- `test_an_answered_anchor_costs_the_fallback_door_nothing`（`:234`）：Photon 答中、Overpass 答零 ⇒ 回退门零调用，且 `fallback_geocode` 以 `SKIPPED_ANCHOR_GROUNDED_BY_` 开头。断言用的是「limit=5 那次问没发生过」＋`fallback_geocode` 具名，所以**哪条腿答的都成立**。
- `test_when_no_leg_was_asked_the_fallback_door_is_still_asked`（`:253`）：裁语说回退腿只伺候"锚没答"，这一臂钉的就是那一格——圆心来自 `journey_current_activity` ⇒ 必须仍问一次，且用 `TIANJIN` 而不是 `CN-TIANJIN`。
- `test_a_failed_anchor_leg_still_closes_the_second_ask`（`:272`）：Photon 失败、Nominatim 答上 ⇒ 也只问一次（`[1]`），并把腿的成败从 `anchor_legs` 里读出来。这一臂证明裁语不是"只针对 Photon"的私规。
- 兄弟两臂 `test_finding_nothing_is_not_reported_as_a_provider_failure`、`test_the_default_resolver_was_not_swapped_and_the_replay_fallback_still_answers` 只改了**前置**（把行程置于"没问腿"那一格），断言一字未动——收窄会让它们落在另一条形上，改断言就等于凑绿，所以动的是世界而不是判据。

## 三、反件（真跑，两枚，还原逐字节回读）

仪器 `run/mutant_fb549_r1.py`：整条裁语住在一句 `anchor_grounded_by_leg = any(...)` 里，所以两枚反件都是把那句换成常量，单变量、互反极性。

| 反件 | 改成 | 该红的 | 实测 |
| --- | --- | --- | --- |
| M1 门关不上（裁语前的行为） | `= False` | `answered_anchor`、`failed_leg` | `2 failed, 2 passed`，红的正是这两枚；另两枚绿 |
| M2 门焊死（收窄过头） | `= True` | `journey_state`、`default_fence` | `2 failed, 2 passed`，红的正是这两枚；另两枚绿 |

每枚还原后 `git hash-object` 与改前逐字节相同（`sha256[:16] bf91ea87b7a458f0`，驱动里断言 `byte-identical=True`）。读数全文 `readouts/mutants_M1_M2.txt`。

## 四、like-for-like 分母（两棵树同一稀疏集合，同一趟命令）

**A. 在 `5a4cdbd2…` 上成的对（全量，`-p no:cacheprovider`）**：`readouts/full_suite_pair_at_5a4cdbd2.json`

| 趟 | 结果 |
| --- | --- |
| 干净尖 | `12 failed, 1652 passed, 16 skipped, 1 xfailed, 1 error in 178.66s` |
| 本枝 | `11 failed, 1655 passed, 16 skipped, 1 xfailed, 1 error in 172.75s` |
| 只出现在本枝的红 | **0 枚** |
| 只出现在干净尖的红 | `test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor`（就是 §二 那枚被我按裁语重写的旧臂） |
| 两侧同一枚 collection error | `tests/test_v18_hermes_r20_transport_reliability_probe.py` 引 `citynexus_mcp`，解释器里没有这个包——尖的条件，与号令者 07:57 那把尺 `--ignore` 掉的是同一枚，理由一致 |

**B. 在交付代 `00b5f25e…` + 我这笔上重跑的受影响集合（11 枚文件，含新落的 ORD-0531 那支）**：`readouts/affected_at_00b5f25e_*.txt`

| 趟 | 结果 |
| --- | --- |
| 干净尖 `00b5f25e…` | `3 failed, 84 passed, 1 xfailed`（`g5`、旧回退臂、`named-stage`） |
| 交付代，连跑三趟 | 三趟都 `2 failed, 87 passed, 1 xfailed`（剩 `g5` + `named-stage`，都是尖上原有） |

有一趟（追尖后第一次）额外红了 `test_qoder_ord197_four_class_receipt.py` 的 `test_r3_…`、`test_r4_…` 两枚；同样字节连跑又出现一次（那次是 `r4`）。**这一格我没有判成"无新红"，而是把四种组合同时摆出来**（同一棵树、同一命令、逐趟点名红的臂；仪器 `run/discriminate_r3_no_my_file_r1.py`、`run/discriminate_r3_fb549_r1.py` 与一次"我的测试文件 + 尖的产物字节"单变量对照）：

| 树上的组合 | 趟数 | `r3`/`r4` 出现红的趟数 | 该趟里其余的红 |
| --- | --- | --- | --- |
| 门的字节 + 我的臂（= 交付代） | 12 趟（11 枚文件那组 8 趟 + 反件对 4 趟） | **2 趟**（一次 `r3`、一次 `r4`） | `g5`、`named-stage` |
| 门的字节 + 不含我的城市文件（10 枚文件） | 4 趟 | 0 趟 | `g5`，另有一趟 `g3_xproc_loser_readback_five_processes_one_operation` |
| 干净尖 + 不含我的城市文件（10 枚文件） | 4 趟 | 0 趟 | `g5` |
| **尖的产物字节 + 我的臂**（只把 `real_city.py` 退回尖上那枚） | 4 趟 | 0 趟 | `g5`、`named-stage`，加我这枚三臂因门不在而**如期红**；另一趟多一枚 `g3_xproc_loser_readback…` |
| 交付代上单跑 `city_failure` + `ord197` 相邻两文件 | 5 趟 | 0 趟 | 只有 `named-stage`；`ord197` 单跑 3 趟 `6 passed, 1 xfailed` |

| **干净尖，00b5f25e…（我 0 字节在场）** | 11 枚文件那组 8 趟 | **1 趟由红转绿**：`test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor` 平时是红的（`[5] == [1, 5]`），`readouts/affected_at_clean_tip_4passes.txt` 第 2 趟它绿了——那一趟网络给了它要的 `[1, 5]` | `g5`、`named-stage` |

判语，按能说的说：**"会翻"这件事在权威尖上就有实测，而且方向是反的（红转绿）**——那枚旧臂要的正是"Photon 不答、Nominatim 答"这一种网络形状，它满足时旧臂就绿。所以本单不需要为 `r3`/`r4`/`test_an_abandon_…` 这几枚跨模块状态敏感臂的翻转负责，也不是靠"我没看到"说的：两侧各有 8-12 趟、逐趟点名红的臂，全在 `readouts/`。我**没有**把这一族定因（那要在同一组上按头各跑几十趟，且要拆 `provider_attempts` 那张共享表的读写序），这一格留给号令者：若要求收口，请开一枚小单，我按上面的表继续加趟数。



**C. 在交付代 `00b5f25e…` + 我这笔上的全量一趟**：`readouts/full_suite_at_delivered_head.txt`

`13 failed, 1660 passed, 16 skipped, 1 xfailed in 1515.57s (0:25:15)`（命令带 `--ignore=tests/test_v18_hermes_r20_transport_reliability_probe.py`，与号令者 07:57 那把尺同一理由）。13 枚逐枚点名：`test_aiv3_02_v2_mcp_builder_includes_read_plan_and_action_tools`、`test_g5_…`、`test_g9b_…`、`test_g14a_…`、`test_g14c_…`、`test_g8a_…`、`test_g10_…`、`test_a_live_failure_arrives_named_…`、`test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation`、`test_G4_the_lock_wait_is_written_in_exactly_one_place`、`test_C01_the_scanned_set_is_named_and_actually_present`、`test_H01b_the_shipped_tree_clears_and_every_exemption_is_re_derivable`、`test_acceptance_answers_while_the_provider_is_still_being_asked`。

与我在 `5a4cdbd2…` 上成的那一对（尖 12 / 枝 11）对齐看：11 枚逐枚同名；多出来的是 `g3_xproc_two_uvicorn_workers…` 与 `acceptance_answers…` 这两枚**跨模块状态敏感族**（号令者 07:57 的红集合分类里就有 g3-xproc；我 02:32 那块也点过这两枚只出现在干净尖）。**这一趟里没有 `test_qoder_city_failure_reasons.py` 的旧臂**，那是本节要做的事。这是一趟观察，不是我给谁做的基线；本趟时长 25 分钟里大部分是同机并发把 provider 族拖到超时，所以不含时长结论。

号令者 07:57 那趟（整树导出）是 `9 failed, 1656 passed, 22 skipped`。差的 4 枚我不解释成"我这笔带来的"：他的分母是 `git archive` 整树（我的是稀疏检出树，`skipped` 差 6 枚即来自这里），且他那趟无并发。两趟名单我都贴在这里，请按他的基线做差。



## 五、真机门读数（产品自己那条路，不是夹具）

仪器 `run/drive_fb549_door_r1.py`；四趟 JSON 全在 `readouts/`。两臂各自起私有后端、各自私有 sqlite，`CITYNEXUS_NOMINATIM_URL` 指到本机一枚只记数的监听（回 `[]`，即 Nominatim "什么都没找到"时给的那个空数组）。**为什么必须自己数**：响应里没有任何字段承载"回退门问没问"——`anchor_legs` 记的是 provider 腿，不记这第二问。Photon、Overpass、锚腿顺序、行程状态全是产品自己的。

**关键那一对（`readouts/door_real_path_cafe100.json`，问的是 `cafe`、半径 100、超时 30 s）**

| | 干净尖 `00b5f25e…` | 交付代（本笔） |
| --- | --- | --- |
| Photon 腿 | `attempted=true answered=true http=200 bytes=344` | 同 |
| Nominatim 腿 | `attempted=false`（腿被 Photon 抢下，符合设计） | 同 |
| **Nominatim 实际收到的请求** | **1 条**：`q="cafe, TIANJIN"`、`limit=8` | **0 条** |
| `provider_status.fallback_geocode` | 这个键不存在（`fallback_geocode_key_present=false`） | `SKIPPED_ANCHOR_GROUNDED_BY_photon_city_anchor` |
| `mode` / 候选数 | `replay-fallback` / 3 | `replay-fallback` / 3 |
| `discover` 秒数 | 2.52 | 3.47 |

归属三证（每臂各取，同一批）：P1 我造的 uuid 标记行 `http_status=201` 且**在我自己那个 db 文件里读回 1 行**；P2 监听 PID 的命令行含 `--app-dir <我这棵树>` 与 `--port`，且启动 PID 是它的自身或祖先；P3 我自己那份 boot log 里写着这枚端口号。两臂 teardown 后端口都无监听。

另外三趟（同样落档，说明我没能拿到的那几格）：
- `door_real_path_r1.json`：`cafe` / 半径 2500 ⇒ Overpass 答出候选，交付代那臂 `fallback_geocode=NOT_NEEDED`，门**没被走到**；尖那臂 Overpass 超时（`PROVIDER_TIMEOUT`）。
- `door_real_path_answered_zero.json`：`gallery` / 半径 100 ⇒ 两臂都 Overpass 超时，交付代读出 `NOT_REACHED`（这正是 `:1542` 那枚初始化在真机上被证明有用的那一格：没有它，这里会吐 `UnboundLocalError` 而不是一个原因码）。
- `door_real_path_cafe100_one.json`：把回退应答换成"一行合成 Nominatim 记录"（件头写明 `SYNTHETIC-NOMINATIM-ROW not product data`，只进一次性私有库），想量"收窄让出了多少供给"。尖那臂这次在 `category_search` 超时（72.05 s，根本没走到回退门），交付代走到门并 `SKIPPED`。**所以这一格没量到，具名 `NOT_MEASURED_BY_LANE`，原因就是尖上那次 Overpass 超时**；要量它得让两臂同代都走到"答零"那一形，我没有把它凑出来。

## 六、没改善的部分（照实说）

- 旅客在这一格拿到的东西没变：`mode`、候选数、`fallback_reason=PROVIDER_NO_RESULTS` 两臂逐值相同。省下来的是一枚对该城的外部地理编码请求，和一句能被读出来的原因。
- 我没有更快读数可以交：2.52 s 对 3.47 s 在provider抖动里不算数，所以本块不含时长结论。
- 收窄是**有代价的一刀**：如果哪天 Nominatim 真能答，"腿答上而类别答零"那一格原本还可能从第二次问里拿到候选，现在拿不到了。这一格我给不出实测数（§五 第三趟），只能给出代码事实：`real_city.py:1672` 那一问在裁语后不再执行。要不要为它开一格"锚已答但允许一次类别问"是号令者的裁，不是我这单的题面。
- 现尖仍红的两枚我没吸收：`test_g5_an_ai_run_that_changed_must_say_which_it_was`、`test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at`（后者断言 `PROVIDER_SERVER_ERROR == PROVIDER_BAD_RESPONSE`，在 `8dd6905d` 上我就量过它红）。两枚在干净尖同一命令下也红，不是我这两枚字节带来的。
- `provider_status` 里多一个键 = 契约面变宽一格。OpenAPI 没有为它写形状（我不动契约，等裁要不要写）；`response_model=RealCityDiscoveryResponse` 在真机两臂都回 `http_status=200`，所以新键不是被 schema 拒掉的键。

## 七、坐标（推上去之后从服务器回读，不写记忆里的数）

见本块随附的账块 `5a53846b_<HHMM>.md`：枝名、head、两枚产品/门 blob、门闸 rc、like-for-like 差集合都在那里，且逐枚可 `git cat-file -t`。

## 八、复现（逐字）

```bash
# 反件对（单变量、互反极性；还原逐字节自证）
D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_seed_ord0489/run/mutant_fb549_r1.py

# 受影响集合 like-for-like（两棵树同一稀疏集合）
cd D:/moodle/_qoder_seed_ord0489/wt543tip/backend && D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest -p no:cacheprovider -q --no-header \
  $(cat ../../run/fb549_affected_files.txt | tr '\n' ' ') tests/test_qoder_ord0531_bin_ownership.py

# 真机门读数那一对（cafe / 半径 100；私有后端 :8831 与 :8832，私有库在 run/ 下）
cd D:/moodle/_qoder_seed_ord0489/run && DOOR_TAG=cafe100 DOOR_QUERY=cafe DOOR_RADIUS=100 DOOR_TIMEOUT=30 \
  D:/moodle/CityNexus/.venv/Scripts/python.exe drive_fb549_door_r1.py
```
