# ORD-0526 追件 · 源上线后那四格到底有没有分母（现读尖 `514b397f…`，05:32）

CMDR 在账本里挂着一条依赖：「长图/地图/日历/足迹四格仍无分母；等 ORD-0526 登记源」。源现在在
权威线上（我上一件的 `dc86d1d0…` 是 `514b397f…` 的祖先，四枚产品 blob 逐枚等值）。这一发不是在
重证源，是拿现读回答那四格现在通没通——用产品自己的门，不数库。

私有后端 `:8801`，库 `run/_cells514b.db`，树头 `514b397f96f3b5165b24865f4a544ab6f8020084`。
三证随件（`four_cells__cells514b.json` 的 `ownership`）：P1 监听命令行含 `--app-dir …wt_cells_514b\backend`
与 `--port 8801`；P2 `GET /places` 行数 == 同文件计数、journey 在本文件、现造 uuid 回 404；P3 回追到启动 PID。

## 逐格读数

| 格 | 走的那扇门 | 现读 | 有没有分母 |
| --- | --- | --- | --- |
| 补水（源本身） | `POST /api/v1/catalog-hydrations` | op `f8bbc9a9-ceb1-4cc6-8b0c-7413f0b60193`，`ALREADY_CURRENT`，`places_held` 5，`pending` 0，`places_written` 5 | 通：源真给 5 枚地点 |
| 地点回读 | `GET /api/v1/places?city_code=CN-TIANJIN` | `http_status=200`，5 行 | 通 |
| 排程/长图/地图（要一份 active plan 的那三格） | `POST …/plans/generate` | `http_status=422` `CATALOG_INSUFFICIENT`，`places_in_catalog` 5、`city_services_in_catalog` 5、**`day_sequences_available` 0** | 不通：有地点、没有能成行的日序 |
| 日历 | `GET …/calendar.ics` | `http_status=409` `CALENDAR_SOURCE_UNREADABLE`，`reason=ACTIVE_PLAN_NOT_DECLARED` | 不通：没有 active plan 可导 |
| 足迹 | `GET …/checkins` | `http_status=200`，0 行 | 空集（门是活的，只是没打卡） |
| 分享 | `POST …/share-grants` `visibility=LINK_READ` | `http_status=201`，token 生成；`GET /api/v1/shared/journeys/{token}` `http_status=200`，`plan_state` 无 active plan | 通：分享收得回，但收回的是「没有方案的这趟」 |

一句话：源上线把「一座城一个地点都没有」这格解开了（`NO_REGISTERED_SOURCE` → `ALREADY_CURRENT`，地点 5 枚真落库），但 CMDR 要的「四格一次性补读」还差**日序**这一腿——`plans/generate` 明确报 `day_sequences_available` 0，于是长图/地图/日历三格仍拿不到分母。这一腿不在 ORD-0526 题面里（它只管登记供给源、让终态从「没源」变「有地点」），归 ORD-0521「非破坏供给」那一单，或一张新单。

探针 `probe_cells_after_0526_r1.py` 可重跑（`DB`/`PORT`/`TREE`/`JOURNEY_DAYS` 可用环境变量换）。第一炮分享门 422 是我探针**漏填 `visibility`**（必填枚举 `PRIVATE/LINK_READ/INVITEES_ONLY/PUBLIC`，`app/schemas.py:871`）——不是产品的拒绝，补齐后同一扇门 201，所以这里贴的是补齐后的读数，第一炮那枚作废、已具名说明。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
