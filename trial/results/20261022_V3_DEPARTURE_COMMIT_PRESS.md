# 出发提交：一次真实点击（2026-10-22）

结论：**一个真人能走通「把我已有的行程定下来」了**——在同一台机器上开一个全新的浏览器上下文
（只有签名凭据，没有任何本地行程指针）也能走通。

- 入口：`/revolution` → 「我的旅程」。这一屏现在会向服务器问一次
  `GET /api/v1/journeys/session/recent-drafts`，把属于这个签名旅客的行程列出来，
  每行一个「继续这趟」。以前这一屏在干净设备上只会说「开始探索一个地区后…」。
- 中间：行程打开后是 `MobilePlanWorkbench`，出发状态读自 `GET .../departure`，
  当时是「等待正式计划 / 1 份正式候选方案」。
- 那一按：「选用这份方案」发出 `POST /api/v1/journeys/{id}/departure/commit`，
  带 `Idempotency-Key`，请求体只有 `plan_version_id`（不许前端塞地点名和价格）。
- 屏上读回：出发块变成「可以确认出发 / 6 项正式安排」；截图见同目录
  `20261022_V3_DEPARTURE_COMMIT_AFTER_PRESS_390.png`。
- 服务端凭据：`audit_logs` 里一行 `plan.committed_by_traveler`，`actor_type=traveler`，
  `plan_versions.status` = SELECTED，`GET .../departure` 的 `gate` = READY_TO_DEPART。

未做到的部分，写在明处：

1. 这是本机 Chromium 的点击，**不是手机真机**，所以 `USER_VERIFIED` 仍是 PENDING。
2. 这趟行程是服务端演示库那趟（城市码 `CNX-DEMO`），日期已过；它证明的是**这一按走得通**，
   不是 10 月 22 日可以出发。下一次出发验收要用未来日期的新行程。
3. 打开行程时浏览器控制台出现过一次 409 的读取（读的是这屏自己的某枚 intent/ready 门），
   没有拦住上面的路径，但还没查清是哪一枚，留给下一棒。
4. 多人：这枝的能力表只给 OWNER 发 `JOURNEY_UPDATE`，所以非发起人的座位按这一按会被
   方案门原话挡回；2/3 与 3/3 的确认轮要等裁语扩权后才可能真的出现。
