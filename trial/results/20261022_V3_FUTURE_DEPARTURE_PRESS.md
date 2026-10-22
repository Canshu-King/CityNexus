# 从一句话到「行程执行中」：一趟未来日期的行程，本机浏览器走通（2026-10-22）

第一句：**能走通。** 一个签名旅客在干净浏览器里，从「我的旅程」列表进来，按两次钮，就看到自己在途的行程。

走的路径（每一环都是这枝自己的门，没有桩件）：

1. `POST /api/v1/journeys` 造一趟未来的行程（`start_at` 2026-11-02，回执 201，`status` DRAFT；这扇门要 256 位十六进制的写回执键，普通字符串会被 422 具名拒掉——这本身是对的）。
2. `POST /api/v1/journeys/{id}/plans/generate` 出一版候选（201，`selectable=true`）。
3. 浏览器只带凭据与身份（不带任何本地行程指针）→ 「我的旅程」列出可继续的行程 → 按「继续这趟」。
4. 工作台读 `GET .../departure`：屏上「等待正式计划 / 1 份正式候选方案」。
5. 按「选用这份方案」→ 一次 `POST .../departure/commit`，带 `Idempotency-Key`，请求体只有 `plan_version_id`；屏上变成「可以确认出发 / 6 项正式安排」。
6. 按「确认方案，开始行程」→ `POST .../start`；屏上「旅程已开始 / 6 项正式安排」，并进入在途首屏：「行程执行中」「下一站：Old Town Gate」。

服务端账（同一趟行程，事后从库里读）：`journeys.status` = ACTIVE，`active_plan_version_id` 指向被提交的那版，`current_activity_id` 已落；`plan_versions.status` = ACTIVE；`audit_logs` 依次有 `plan.selected`、`plan.committed_by_traveler`（`actor_type=traveler`）、`journey.started`。截图 `20261022_V3_FUTURE_DEPARTURE_ACTIVE_390.png`。

这不算什么，写在明处：

- 本机 Chromium，不是手机在手里的点击，所以 `USER_VERIFIED` 仍 PENDING（接管令 D 段）。
- 地点的营业时间、票价、转场仍是 `UNKNOWN` / `PARTIAL_UNKNOWN`：这三棒没有调任何供应商，也没有把这些改写成 verified。
- 造这趟行程用的是演示库里唯一有地点目录的城市码（`CNX-DEMO`），所以「三方案、按半天改、局部刷新」这类真内容还没验；换真城市要先把候选侧的地点供给接上。
- 多人：这枝只给 OWNER 发 `JOURNEY_UPDATE`，非发起人座位按这一按仍被方案门原话挡回；2/3、3/3 的裁语没下来之前，确认轮在真库里凑不出第二个应答者。
- 上一棒在这屏控制台看到过一次 409 的读取，这一棒没再抓到，仍未查名，留给下一棒。

原始读数一件没有加工，逐行落在这个目录里：`20261022_V3_FUTURE_DEPARTURE_PRESS_RECEIPT.txt`（`JOURNEY_CREATED`、`GENERATE`、`BROWSER :: HTTP_WRITES`、`DB_JOURNEY_AFTER_PRESS`、`DB_AUDITS_AFTER_PRESS` 各占一行）。
