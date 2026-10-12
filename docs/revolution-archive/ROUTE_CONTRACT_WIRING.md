# ORD-0603 承接面：`route_session_contract` 能不能接到一条真读路由上

世代钉死：本文每个数都出自权威尖 d79a857aee9fa8869d8f276d96898a03406d067a 的现读（2026-10-12 22:5x 本地钟点，
加闸工）。线往前走之后本文不改写，要更新就另开一份并在块头点名本文那一代——第五年要把 revolution 消解进主线语汇，
靠的是能对着旧世代复算，不是靠谁记性好。

## 一、这枚契约要什么输入

`fact_is_eligible_for_live_readiness` 只读一枚对象上的三样东西：时长（`duration_min`，或 `minutes`）、
出处档（`provenance`，或 `route_provenance`/`fact_quality`）、服务商键（`provider_key`，或 `provider`）——
判据本体在 `backend/app/execution/route_session_contract.py:88`，它把"合成/夹具/估算/模拟器"这一档
明确判成不合格（同文件 `:109` 与 `:111` 那两处黑名单）。也就是说：只有真的抓来的路线事实，才允许驱动一条
"你该几点出发"。另一枚函数 `classify_capture`（同文件 `:70`）要的是 explicit_fact + provider_failed +
provider_degraded 三个布尔形状，属于**抓取那一次**的判定，读路由手里没有这三个信号（见第四节）。

## 二、现尖 73 枚 GET 路由里，带这一族形状的只有 9 枚

逐枚判定（fact_payload 那枚投影在 `backend/app/stay_mobility.py:2041`，它一次就把三样都发出来）：

| 路由声明 | 路径 | 三样输入 | 现尖钉它键集的测试 |
|---|---|---|---|
| `backend/app/main.py:6104` | `/api/v1/journeys/{journey_id}/mobility` | 齐（逐条 MobilityFact） | `backend/tests/test_route_stub_验路工_0559b_r1.py:112` 与 `:124` |
| `backend/app/main.py:1829` | `/api/v1/journeys/{journey_id}/provider-mesh` | 不齐（只有服务商健康，不是一条边的时长） | 无 |
| `backend/app/main.py:10535` | `/api/v1/journeys/{journey_id}/route-evidence` | 不齐（properties 只有 provider/provider_backed/fallback/fallback_reason/plan_version_id，见 `backend/app/main.py:10471`） | 无 |
| `backend/app/main.py:2028` | `.../agent/runs/{run_id}` | 不齐（只有 provider_key 字样） | 无 |
| `backend/app/main.py:6703` | `.../web-observations` | 不齐（只有 provider_key 字样） | 无 |
| `backend/app/main.py:7052` | `/api/v1/providers/v9` | 不齐（服务商档，不是边） | 无 |
| `backend/app/main.py:9980` | `.../events` | 不齐（事件载荷里的 provider 字样） | 无 |
| `backend/app/main.py:10155` | `.../reflect` | 不齐（复盘文本里的 provider 字样） | 无 |
| `backend/app/main.py:14379` | `/api/v1/city-services/{service_id}/booking-slots` | 不齐（可约时段） | 无 |

结论只有一句：**唯一真能承接这枚判据的读路由是 `backend/app/main.py:6104` 那条 GET mobility。**

## 三、那条唯一的路上有一枚别人的钉，我不去撬

它逐条发出 MobilityFact 形状，三样输入都在（投影字段见 `backend/app/stay_mobility.py:2047`、`:2057`、`:2058`）。
但这条门被验路工的桩测按字段全集钉住：门级 `assert set(body) == DOOR_KEYS` 在
`backend/tests/test_route_stub_验路工_0559b_r1.py:112`，逐条 `assert set(item) == FACT_KEYS` 在同文件 `:124`。
我不是"读了一眼就下结论"，我把候选接线真打上、真跑了两遍（原始输出在 `review/加闸工-0603/`）：

| 哪一遍 | 结果 |
|---|---|
| 不接线，跑它那 4 条 | 4 条全过——这枚钉在现尖是活的，不是我推出来的（`review/加闸工-0603/stub_baseline.txt`） |
| 接上我这条候选，跑我的探针 | 门答出真值：同为 17 分钟的三条边里，只有真服务商捕获那条 `eligible=True`，合成出处与 mock 服务商两条 `False`（`review/加闸工-0603/probe_wired.txt`） |
| 接上我这条候选，再跑它那 4 条 | 1 失败 3 过，失败原文 `Extra items in the left set: 'live_readiness_eligible'`（`review/加闸工-0603/stub_wired.txt`） |

## 四、两条我考虑过、判定不做的走法（写出来免得下一位再走一遍）

1. 把判语塞进已有的 `evidence` 字段里（那条字段是自由 dict，加键不会撞任何键集钉）。不做：`evidence`
   在契约里指的是服务商给回来的证据袋（投影出处 `backend/app/stay_mobility.py:2061`），而我这枚是我方
   派生的判定；槽位装它没命名的东西，前端也照样读不到——等于把模块搬进另一个没人调的袋子，正是裁语点名的那种。
2. 接到 `/route-evidence` 或 `classify_capture`。不做：前者的 properties 里没有时长也没有出处档
   （`backend/app/main.py:10471` 那几行就是它的全部字段），接上去只会恒判 False，那是假调用点；
   后者要的 `provider_failed`/`provider_degraded` 只在抓取那一次成立，而抓取发生在写路径
   `backend/app/main.py:6134`（`capture_mobility_facts`），不是读路由，出本张单的范围。

## 五、要落地只需一步，但那一步不归我

候选补丁与打补丁的脚本都在枝上：`review/加闸工-0603/wiring_candidate_r1.patch`（38 行，已在临时树
`patch --dry-run` 过、`review/加闸工-0603/apply_wiring_r1.py` 带锚点唯一断言）。它只改两件事：加一行 import、
把那条门里 `fact_payload(item)` 就地多算一枚 `live_readiness_eligible`。要它上线需要下面任一裁决，我不自己动：

- 裁 A（最小）：请验路工把 `backend/tests/test_route_stub_验路工_0559b_r1.py:124` 那枚 `FACT_KEYS` 加上这个键
  ——那是他们的断言，按规矩由他们改或由号令者点名我改；我只把改动点写清楚。
- 裁 B：让判语走一个新增的门级键（例如 `route_truth_policy_version`，值就是
  `backend/app/execution/route_session_contract.py:9` 那枚策略版本串），同样要动 `:112` 那枚 `DOOR_KEYS`。
- 裁 C：先不接。那本文就是交付：现尖**除了** `backend/app/main.py:6104` 那一处，没有第二条路能承这枚判据。

本枝零产品字节：`backend/app/main.py` 在枝上与尖上同 blob（4cd1770924227257bad4d2e84ef0c2fc14441035），
候选接线只存在于补丁与临时树里；探针件刻意不放进 `backend/tests/`，否则它会以"断言一个还不存在的键"把整套测试拖红。
