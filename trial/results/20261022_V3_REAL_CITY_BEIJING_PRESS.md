# 北京这一趟：三方案、选最后一版、出发、刷新还在（2026-10-22）

一句话：**接管令 P0 的「三方案 → 改半天 → 刷新恢复」里，除了「改半天」，其余每一环今天都在一个真城市（`CN-BEIJING`）上走通了，屏上读回来的是北京的地名，不是占位符。**

## 走的是什么路

1. `POST /api/v1/demo/reset`（带具名 token，只打在为本轮新建的金丝雀库上）之后，库里的地点目录是两座城市：`CN-BEIJING` 八处、`CNX-DEMO` 八处。
2. `POST /api/v1/journeys` 建一趟 2026-11-02 出发的北京行程（`http_status=201`，`city_code` 由服务端回的是 `CN-BEIJING`）。
3. `POST /api/v1/journeys/{id}/plans/generate` 要三版：`http_status=201`，三版都是 `CANDIDATE`，三版 `selectable` 都为真。
4. 浏览器（390×844，只带凭据与身份，不带任何本地行程指针）从「我的旅程」→「继续这趟」进工作台，屏上「选用这份方案」按钮数与三版一致，出发块写着「等待正式计划 / 3 份正式候选方案」。
5. 故意按**最后一版**：一次 `POST .../departure/commit`（带 `Idempotency-Key`，请求体只有方案版本一个字段），出发块变成「可以确认出发 / 5 项正式安排」。
6. 整页刷新：工作台还在，出发块仍是同一句，屏上北京地名没有掉。
7. 按「确认方案，开始行程」：`POST .../start`，屏上「旅程已开始 / 5 项正式安排」，库里 `journeys.status=ACTIVE`。

## 屏上读回来的地名（不是截图里的形容词，是 DOM 文本）

方案卡与在途屏里出现的目录地名：**后海、护国寺、南锣鼓巷、前门大栅栏、全聚德、故宫、天安门**（中英两种写法都在），截图里能看见「17:00—18:30 Houhai Lake Bar Street (后海酒吧街) ¥80.00 转场预留 20 分钟」和「18:45—19:30 Huguo Temple Snacks (护国寺小吃) ¥40.00 转场预留 15 分钟」。

库里对得上：三版方案的活动数分别是 6 / 4 / 5，被提交的第三版是 `ACTIVE`，前两版仍是 `CANDIDATE`；这些活动的 `place_id` 指向的地点行 `city_code` 全是 `CN-BEIJING`。审计里旅客亲手那一笔是 `plan.committed_by_traveler`，`actor_type=traveler`。

## 先更正我自己写错的那句

前两份实测（`20261022_V3_FUTURE_DEPARTURE_PRESS.md`、`20261022_V3_VARIANTS_AND_RELOAD_PRESS.md`）里写过「演示库唯一有地点目录的城市码是 `CNX-DEMO`」。**这句是错的**：随件发布的离线目录 `data/mock/places.json` 里 `CN-BEIJING` 同样有八处地点，本轮现读为证。写错的原因是我只看了自己那趟行程用到的城市，没有把目录按城市数一遍。这条更正影响的是「还差多少供给」的判断——真城市的点击路径今天就能走，缺的不是城市，是**真来源的事实与图**。

## 这一套没有证明的，写在明处

- 这八处北京的地点来自随件发布的离线目录，`provider_key` 是 `mock-city`：营业时间、票价、转场时长是目录里带的，不是本轮向任何供应商问来的。本轮一次供应商调用都没有，`UNKNOWN` 仍是 `UNKNOWN`，没有被改写成 verified。
- 「在同一份草案上改某半天」这一格仍未验：它走草案 + `prepare-plan` 那条助手路，屏上此刻写着「AI 暂未开启」（服务端 `CITYNEXUS_AI_ENABLED` 默认关，见 `backend/app/core/config.py:17`），下一棒把这条口开起来再量。
- 两次 `GET .../bootstrap-shortlist` 回 409 是设计里的具名拒绝（这趟行程不是从探索流建的），不是崩溃，屏上也没因此吓人。
- 屏幕是本机 Chromium 的 390 宽视口，不是手机在手里的点击，所以 `USER_VERIFIED` 继续 PENDING。
- 多人那一面没动：这枝只给发起座位 `JOURNEY_UPDATE`（`backend/app/db/session.py:241`），裁语未下来之前不扩权。

原始读数一件没加工，逐行落在同目录：`20261022_V3_REAL_CITY_BEIJING_PRESS_RECEIPT.txt`（`PLACE_CATALOGUE_AFTER_RESET` 一行、`GENERATE` 一行、`NAMES_ON_SCREEN_*` 三行、`DB_PLAN_VERSIONS` 一行、`DB_ACTIVITY_TITLES` 一行）。截图：`20261022_V3_REAL_CITY_BEIJING_CARDS_390.png`（选之前）、`20261022_V3_REAL_CITY_BEIJING_STARTED_390.png`（出发之后，能看见北京地名与时间、票价、转场）。
