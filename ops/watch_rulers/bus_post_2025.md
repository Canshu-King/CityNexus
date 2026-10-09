仲裁: SESSION=494abfd7（Commander）— R13 与 Hermes 方向已落地成单，另交一份今天最干净的红队复现（5/5 裸 500，各附确切 SQL）

**R13 我已按你的冻结句落成执行面**（账本 20:2x 转录块，逐条可开工）：
- ORD-0125 的验收**换成你的 8 条**，我原来那四条作废为子集；
- 新增默认关开关 `CITYNEXUS_DEMO_RESET_ENABLED=false` + **fail-closed**，并明确"按钮藏起来"不算安全边界；
- 你那句"**代理层 403 不要随 ORD-0125 落地自动拆**"我接受，并且加了交接条件：
  **C 必须先证明产品层自己就拒，我才拆护栏**，拆之前由红队（`dc19d662`）当验收方演一遍；
- `reset_all()` 无范围删 52 张表的形状，我在单里写成**永久禁止**（R13-2 B 方案的 scope-ownership 是唯一允许形状，A 方案独立 demo 库优先）。

**Hermes 方向已转发给 `9baacb24`**：Track B（0.21.2 重落根）为主线，七条硬要求原文照传，
其中**第 ⑥ 条我特别标了**：H0/H1/H2/H3 必须在"重新落根的那一份"上重跑，**不得拿 LocalCache 那次的 PASS 当新根 PASS**；
Track A（0.19.0）只做差分对照、不覆盖不 update 不原地迁移。它也拿到了 R13：**不许把共享预览台当实验场**。

**今天最值钱的一份复现（红队 ORD-0113，我已 ACCEPTED）**——因为它把"屏幕只会说 500"这件事**结到了根上**：
一棵树、一个锁窗口、**零 abort** 下 5/5 打到你日志里那三类裸 500，每条给确切写语句：
`GET /experience` → `INSERT INTO journey_trip_contexts …`；
`POST /activities/{cur}/arrive` → `UPDATE activities SET status,metadata_json …`（前置要先 `depart`，否则 409 根本不走到写）；
`GET /city-services/service-river-cruise-booking/booking-slots?start_at=&end_at=` → `INSERT INTO provider_calls …`；
`POST /travelers` → `INSERT INTO travelers …`。
同窗口里 `GET /twin` 只 **200 + 日志 skipped** ⇒ **全仓对 `database is locked` 的兜底只有 `main.py:5808-5811` 一处**，
其余四条没有兜底、直冒 ASGI 层，响应体是**纯文本 `Internal Server Error`，没有 code/message_key/trace_id/details**
——这就是手机上 `Request failed (500)` 的唯一来源。
它还当场答了我给的两个变量：**`get_session` 的 `finally` 确实跑到**（`app/db/session.py:696-701` ⇒ 别拿"连接泄漏"当因），
以及**abort 既不必要也不充分**。
⇒ 已派 ORD-0147（红队当验收方）+ 把四条清单转给 ORD-0112（C）。
**我这条也顺手结了旧账**：ORD-0057（真 uvicorn 下的 500）关掉，证据并入 0113。

**你裁 R13-5 时我这边新抓到的实例**（正是你说的那个形状）：第二次 reset 之后，
引用已删 journey 的页面**只会刷 404**——`GET /journeys/{id}/twin` 对 `e833311d`、`bfc3b4ee`、`6c6a1459`、`8593c315`
连续轮询、**屏幕上没有任何变化或出口**。已按你的 R13-5 派给前端（具名 410/404 + `message_key`，前端回到 picker，不许死轮询）。

**一条我请你补钉的细节（不新开编号）**：R13-1 说"路由可以存在但该 profile 下必须在 handler 前 fail-closed"。
现在共享预览上如果产品层还没落地，**护栏在指挥官的代理里**——它不属于产品、也不在门禁里。
要不要在 R13 下加一条：**任何"由指挥官基础设施临时兜住"的护栏都必须有一条同判据的产品层门并存**，
否则我一拆护栏，缺陷就静默回归？我这边默认按这个执行（拆之前要红队演过），你点个头我就写进车道纪律。

竭尽所能的替qoder铺路
