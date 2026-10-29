# 三种方案、选一份、刷新还在：真城市以外的第一整套实测（2026-10-22）

一句话：**接管令 P0 里「三种方案 → 刷新恢复」这一段，在 rescue 这枝的真后端上走通了；「改半天」那一格今天还没条件验。**

一趟 11 月 2 日出发的新行程（`POST /api/v1/journeys`，201，DRAFT），一次 `plans/generate` 要三版：服务器回 201，给了 `version_no` 1 / 2 / 3 三版 CANDIDATE，三版都 `selectable=true`。浏览器（只带凭据与身份，不带行程指针）从「我的旅程」→「继续这趟」进工作台，屏上出发块写着「等待正式计划 / 3 份正式候选方案」，方案卡标题按序是「方案 1 / 方案 2 / 方案 3」，各带一枚「选用这份方案」。

故意选**最后一版**：一次 `POST .../departure/commit`，带 `Idempotency-Key`，请求体只有 `plan_version_id`；屏上同一块变成「可以确认出发 / 6 项正式安排」。库里对得上：版本 3 = SELECTED，版本 1、2 仍是 CANDIDATE，审计只有 `plan.selected` 一行加一行 `plan.committed_by_traveler`（`actor_type=traveler`）——选一份不会把另外两份也搬走。

整页刷新之后：工作台还在（`rev-plan-workbench` 在 DOM 里），出发块仍是「可以确认出发 / 6 项正式安排」，不需要重新探索、也没有退回空态。截图：`20261022_V3_VARIANTS_BEFORE_PRESS_390.png`（选之前）、`20261022_V3_VARIANTS_AFTER_RELOAD_390.png`（刷新之后）。

自己的仪表错过一次，记下来：第一次跑时我在方案卡还在异步填充的那一瞬数按钮，读到 0，差点把「屏上没有三方案」当成结论写出去；第二次改成轮询到列表落地再数，才读到 3。教训是**读屏要等它长完**，不是产品的问题，但下一次谁再用这套脚本别踩。

这一整套**没有**证明的：

- 「在同一个 task 上改某半天」这一格没验——它走的是草案 + `prepare-plan` 那条 Agent 路，而这屏此刻写着「AI 暂未开启」（同一段文字里就有）。要先把助手那条口开起来。
- 这三版都来自演示库唯一有地点目录的城市码 `CNX-DEMO`；真城市的候选供给（来源线索 → 身份映射 → 媒体）还没接上，所以「换地点、补资料、比价」这类内容今天仍然算未验。
- 一次 `GET .../bootstrap-shortlist` 回 409 是设计里的具名拒绝（这趟行程不是从探索流建的），不是崩溃；屏上也没因此吓人。
- 手机真机仍未做，`USER_VERIFIED` 继续 PENDING；供应商一次没调，UNKNOWN 仍是 UNKNOWN。

原始读数一件没有加工，逐行落在这个目录里：`20261022_V3_VARIANTS_AND_RELOAD_PRESS_RECEIPT.txt`（`GENERATE` 那行是三版 CANDIDATE 的返回，`SELECT_BUTTONS`、`GATE_AFTER_COMMIT`、`AFTER_RELOAD_GATE`、`DB_PLANS_AFTER_PRESS` 各占一行）。
