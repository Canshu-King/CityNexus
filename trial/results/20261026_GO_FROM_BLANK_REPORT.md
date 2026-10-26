# 从空白到 GO：真实 Chrome 走查报告（2026-10-26）

派单：`trial/tasks/20261026_QODER_GO_FROM_BLANK_AND_AGENT_VISIBILITY.md`（基线 `a8a53d41f9…`）。
本文件只写**现读**：每条结论后面是屏幕读数、HTTP 状态或库里的行。产品 SHA 与同号收据在 §5。

## 0. 一句话

隔离试玩栈（`60361/14461`，库 `citynexus_v3_gozero_1026.db`，`db_kept=true`）上，真 Chrome（Playwright `channel:"chrome"`，390×844）从冷首屏输入真实句子，一路走到 **ACTIVE**（journey `693a693a…`，同一任务 `49a999d6…`，方案 `4cab4148…`）。**修掉的第一个真实阻塞**是「讨论问答看不到去研究的门」——修前 8 趟旅程全部卡在 `DISCUSS`，每趟只有 `ask_traveler/inspect_journey`、0 个 Slot；修后一次真人点击「不选了，直接按现在的方向开始研究」，同一 `journey/task` 产出 56–64 个真实地点、冻结的移动证据，并在合并 PR #55 后的隔离栈上走到 `CANDIDATE → SELECTED → ACTIVE`。

## 1. 修前的读数（不是推断）

DB 回执 `before-fix-db.txt`（八趟旅程，全部同一形状）：

| journey | mission 状态 | 模型轮/工具 | 工具 | 草案 Slot | 待问 |
|---|---|---|---|---|---|
| 72e18fb9 | NEEDS_DECISION | 7 / 6 | ask_traveler 6、inspect_journey 1 | 0 | 有 |
| 49ada5ce | NEEDS_DECISION | 8 / 7 | ask_traveler 6、inspect_journey 2 | 0 | 有（第 6 问） |
| d62fc603 | FAILED_RECOVERABLE `MODEL_HTTP_429` | 12 / 9 | ask_traveler 7、inspect_journey 4 | 0 | 无 |
| 其余五趟 | NEEDS_DECISION | 1 / 1 | ask_traveler 1 | 0 | 有 |

屏幕侧：`390-round4-after.png`（修前 UI，390×844）只有四个选项 + 「也可以在下方直接说你的想法」，**没有**任何开始研究的入口；待问问题存在时 `按讨论的方向开始研究` 按钮被 `!pending_question` 条件隐藏（`frontend/src/trial/mobile/WorkspaceActions.tsx:595` 旧代码）。

后端侧：`interaction_mode=DISCUSS` 时工具白名单只有 `{ask_traveler, inspect_journey}`（`backend/app/agent/goal_tasks.py:1333`），所以讨论轮在结构上不可能产出草案——不是模型懒。

## 2. 修了什么

1. **前端多一扇门**（`WorkspaceActions.tsx`）：待问问题旁边新增 `data-testid="rev-agent-skip-questions"`「不选了，直接按现在的方向开始研究」，发送一条 RESEARCH 消息（明说「不用再问我；缺的资料按未知处理」）。
2. **后端认这句话**（`goal_dialogue.py` 新增 `asks_to_end_questions`；`goal_tasks.py`）：旅客说「不用再问/直接开始研究」时，
   - `DISCUSS → RESEARCH`（空旅程没有 Slot，旧的条件分支永远打不到）；
   - 这一轮的工具白名单**去掉 `ask_traveler`**，并追加一条系统说明：不要再问，用已定方向去研究并保存草案，未核实的票价/营业/步行距离保持未知。

## 3. 修后的真机路径（390×844，真 Chrome，隔离库）

一次会话内完成（重开浏览器会丢令牌，见 §6）：

| 步 | 动作 | 屏幕/HTTP 读数 | 截图 |
|---|---|---|---|
| 1 | 冷首屏填真实句子 | 目的地北京、12-03～12-04、2 人自动解析 | `390-go-cold.png` |
| 2 | 继续规划 → 对话 → 对话设置勾两权限 → 发送 | `POST 201 /journeys`、`POST 201 /agent/goal-tasks`、`POST 200 /run` | — |
| 3 | Agent 第一问 + 真点「不选了，直接开始研究」 | `HIT skip-questions true`，待问问题在屏 | `390-go-pending-question.png` |
| 4 | 研究轮（同一 journey/task） | 12 模型轮 / 11 工具：`discover_places×7`、`route_public_places×2`、`save_draft_itinerary×1`；`research_places=56` | — |
| 5 | 草案保存 | `draft_revision 0→1`、7 项安排、2 天；屏幕「已整理 2 天 · 7 项安排」 | `390-go-after-research.png` |
| 6 | 我的旅程 → 勾「按以上时间准备方案」→ 保存 | `POST 200 .../prepare-plan`，得到 PlanVersion `71973500…`（CANDIDATE，mobility snapshot 已冻） | `390-go-saved-*.png` |
| 7 | 生成正式候选 | `POST 422 /plans/generate`（`CATALOG_INSUFFICIENT`：56 个真实地点，缺开放时间/票价来源），屏幕如实说明 | `390-go-saved-*.png` |
| 8 | 核实并冻结转场 | `POST 200 .../freeze-routes`；屏幕「转场已核实 5/5（1 段跨夜、5 段按公共交通、5 段超 1 公里已换公共交通）· 已冻结进这版方案」 | — |

DB 回执：`r12-receipt.txt`（journey `e8f81207…`、mission `e99b4180…`、plan `71973500…`，7 条未决事实 = 6 条票价「旅客承担」+ 1 条「具体地点」）。

## 4. 两个仍未过的门（同一个旅程上的读数）

1. **一格没有地点**：草案第 2 天晚上「晚餐+夜宵现场挑」没有 `place_id`，`PLACE_REQUIRED`，正式方案因此 `selectable=false`；卡片上对应的门是「和 Agent 补齐出发资料」（`rev-v3-ask-agent`）。
2. **票价未知**：6 条 `ADMISSION_PRICE / UNKNOWN / PRICE_HELD_BY_TRAVELLER`；卡片上的门是「确认费用先不计入预算」（`rev-v3-accept-price`）。

这两门由 r13 的同一会话按顺序真点（先补地点、再确认费用、再选用、再出发），结果追加在本文件 §7。

## 5. 收据

- PRODUCT_SHA：`baf4d9421e`（本报告 §2 的三处产品改动；`git cat-file -t baf4d9421e` = commit）
- 同一趟旅程（r12，走到 CANDIDATE）：
  - JOURNEY_ID `e8f81207-2070-4360-aeee-4090d2979c85`
  - TASK_ID `e99b4180-3754-43ee-a1d5-4433d136f1f5`
  - CANDIDATE_ID `71973500-e058-42af-9c51-003c9b6870ba`（`status=CANDIDATE`、`mobility_snapshot=cd61bdb7…`）
  - SELECTED_PLAN_VERSION：**无**（未选中）
  - ACTIVE：**未达**
- ACTIVE 收据（同一 journey/task 的终点）：
  - JOURNEY_ID `693a693a-6289-422c-9ca4-b2a860db5ef5` → `status=ACTIVE`
  - TASK_ID `49a999d6-dcf5-4c98-85a8-9055be068a18`
  - CANDIDATE_ID / SELECTED_PLAN_VERSION / 当前方案：`4cab4148-3295-4a27-8ca9-699d62b59d87`（`status=ACTIVE`）
  - CURRENT_ACTIVITY_ID `789f2183-46c0-4a29-b9bf-b7d96b56bf25`
- 另两趟同流程：`f1685791…/72d031ab…`（plan `e569d15f…`，commit 422）、`b49cfe49…/07527975…`（plan `3e3c55cc…`，9 条未决）
- 脱敏：以上均为库内 id 与状态，不含令牌、密钥或请求头。

## 6. 已知阻塞（如实写）

- **模型网关会超时/限流**：`MODEL_HTTP_429`（d62fc603）与 `MODEL_TIMEOUT`（2a07aa70、r12 之前一趟）；同一网关小请求实测 200/1.8–6.1 秒，说明是长补全偶发超时，不是断网。产品侧表现为「这次有一部分还没完成」；重按「开始研究」可续（r12 就是这样起来的）。
- **重开浏览器找不回这趟行程**：同一 Chrome profile 重开，屏上写「这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到进度」（`390-cont-journeys.png`）。令牌在会话里，不在磁盘上；所以本报告所有 GO 证据都来自**一次会话内**。
- **正式候选生成仍 422**：56 个真实地点没有一处同时具备开放时间与票价来源；界面已如实说明并指向草案候选路径，这是数据供给问题，不是本轮产品改动能消掉的。

## 7. 结果（2026-10-26 12:46 本地）

**达到 ACTIVE。** 合并 PR #55（真实高德路线几何等）后重启隔离栈，同一流程在 390×844 真 Chrome 上一次走通：

| 步 | 读数 |
|---|---|
| 旅程 | `693a693a-6289-422c-9ca4-b2a860db5ef5`（04:38:42Z 建） |
| 任务 | `49a999d6-dcf5-4c98-85a8-9055be068a18`；RESEARCH，15 模型轮 / 13 工具（discover_places 6、discover_nearby 2、route 1、save 1、replace 2、ask 1）；64 个真实地点；草案 rev 3 / 6 项 |
| 正式方案 | `4cab4148-3295-4a27-8ca9-699d62b59d87`，**status=ACTIVE**，mobility snapshot `f092b552…`，6 条未决 |
| 选用 | `POST /departure/commit` → **200**（无拒绝句） |
| 出发 | `POST /start` → **200**；journey `status=ACTIVE`、`active_plan_version_id=4cab4148…`、`current_activity_id=789f2183…` |
| 屏幕 | 「行程执行中」「行程已开始」「第一站：故宫博物院（午门进、神武门出） · 12月3日 09:00」；执行与待办页显示课堂时空模拟 12/03 09:00（`390-g4-final.png`） |

同一趟旅程、同一任务，从「研究」一路到 `CANDIDATE → SELECTED → ACTIVE`，没有换预置行程。收据见 §5，DB 回执 `active-receipt.txt`。

**为什么这次能过、之前三次不能**：
- 前三次都停在 `CANDIDATE`：草案里先后出现「无地点的一餐」「营业时间未知」两类未决事实，正式计划门要求逐格有地点；其中一次真点「选用」得到 422（`f1685791…`）。
- 这次 Agent 的两次 `replace_draft_slots` 把无地点的格子补成了真实地点；合并后的写入侧按真实高德几何冻结转场（snapshot `f092b552…`），出发门没有再拒绝，commit/start 都是 200。
- 讨论门（§2）仍是这段路的入口：一次真点 `rev-agent-skip-questions`，任务从 DISCUSS 转 RESEARCH，才有后面的研究。

**仍要如实记的**：这次 `unresolved` 还有 6 条（票价未知，已按「旅客承担」处理），journey 的 `current_activity_id` 指向第一站；能不能一路演到完，属课堂线（§11 的同一代码）下一班的事。

## 10. 第 2 刀：Agent 可见性（状态：时间线有屏证；接受旁差异 = 代码已落、屏证未取）

**做了的**：

1. **工具时间线**（`WorkspaceActions.tsx`，`data-testid="rev-agent-tool-timeline"`）：把原来「工具结果 · N 次」换成「Agent 工具时间线 · N 步」，每一步给出序号、工具名、状态徽标（完成 / 被拦下 / 失败 / 进行中）、公开结果一行、**本地时间**与耗时；末尾一行「下一步」由任务自己的状态推导（`nextActionSentence`），不是模型句子。只读 `public_action`/`taskStepText`/`elapsed_ms`/时间，不碰模型正文与凭据。
   - 屏证（真 Chrome 390×844，隔离库）：`390-agent-timeline-local.png` —— 「Agent 工具时间线 · 11 步」；第 1 步「与你商量安排 [完成] 4 条已有路线 12:29:14 · 0.0 秒」，第 2 步「查找公开地点 [完成] 发现北京核心景点：故宫 8 处地点 12:29:23 · 0.3 秒」；底部「下一步：草案已保存；确认时间后可以准备正式候选。」
   - 另一趟 13 步的读数里出现「被拦下」徽标（RESEARCH 轮里 `ask_traveler` 被后端白名单拦下），说明状态来自真实工具结局，不是装饰：`agent-timeline-390.txt`。
2. **接受旁的计划差异**（`ClassroomPresenterPanel.tsx`，`data-testid="rev-presenter-diff"`）：从服务器自己的 `ReplanDiff`（`removed/added/moved/cost_delta_minor/travel_delta_min`）取数，渲染「接受后计划会这样变」：移除、加入、时间挪动（早/晚 N 分）、路上（多/少 N 分）、费用（多/省 ¥N；数值缺失写**未知**）。地点键只显示可读标题，读不到标题就写「一处没有取名的地方」，不把 place id 端给老师。
3. **接受后刷新外层**：接受成功即派发 `citynexus:plans-updated`（工作台已在监听），控制台自身 `act()` 结束也会 `refresh()`；这样地图/日程/下一站不会停在接受前的版本。

**没证到的**：接受旁差异与接受后刷新只过了 `tsc -p tsconfig.check.json`（RC=0）与 Vite 编译（两个模块 200），**没有**在带有 PRESENTED 提案的真栈上拍到屏。按「没看到就不准说完成」，这一项记 **PARTIAL**，下一班需要课堂栈 + 一次性票 + 预置提案各一次才可转 ACCEPTED。

## 11. 第 3 刀：课堂手册过期断言 + PR #55 合入核对

1. **手册勘误**（`20261025_CLASSROOM_DEMO_RUNBOOK.md` 顶部新增 2026-10-26 块）：入口必须有票（`ENTRY_DOOR=PAIRING`，无 `#pair=` 403 `DEMO_PRESENTER_REQUIRED`）；按钮名是「接受这次事件的调整」；simulation 五表已随新后端自动建（"端点未部署"作废）；守护可以按且必须按（失败有「再请一次守护」、事件落定有「事件处理完了，继续模拟」），"不要按/点了只能重启"作废；未变项写明随机城市池真栈 0/3、平板 `USER_VERIFIED=PENDING`。
2. **速查卡同步**（`20261025_CLASSROOM_QUICK_CARD.md` 第 7 条）：补「收尾中先刷新、超过一分钟再重启」与「事件处理完了，继续模拟」两个分支。
3. **PR #55（head `a01f2e68`）核对**：
   - 冲突：`git merge-tree --write-tree HEAD a01f2e68` → rc=0、tree `a2731237`；`gh` 判 `MERGEABLE/CLEAN`。
   - 代码：在 `fb36e86f84` 的临时 worktree 上 `merge --no-commit`，只自动合并 `goal_tasks.py` 一处；`tests/test_issue49_*.py` **100 passed / 25.71s**。
   - 真栈：合并后起临时 uvicorn（60461、demo 库副本、`CITYNEXUS_DEMO_DATABASE_PATH` 指向该副本）——`/api/v1/health` **200**（`database=ok`、`ai=DISABLED_BY_OPS`）、`/api/v1/demo/session` 无 key **403 `DEMO_PRESENTER_REQUIRED`**、`/simulation/cities` 无令牌 **401**（路由已挂、鉴权生效）。
   - 结论：**本地已按集成负责人身份合并为 `9b51c7ea48`（父 `fb36e86f84` + `a01f2e684c`）**；运行中的课堂栈尚未重启到这一代（重启会重置演示库），所以"课堂整链同代"仍记 **NOT-YET-DEPLOYED**。

## 12. 430 复核与第二个缺陷的更正确认（2026-10-26 13:12 本地）

- **票价确认是生效的**：430 那趟的两份方案各自收到 `POST .../accept-unknown-price` 200；库里两份的 `explanation.authority_state` 都是 `COST_UNKNOWN_ACCEPTED`、`cost_unknown_policy=USER_ACCEPTS_UNKNOWN_PRICE_NOT_INCLUDED`；用同一份代码离线复算 `plan_authority_blocker(plan, places, used_place_ids=…)` 返回 **None**。所以那两句「7 项费用待确认」不是 consent 没写进去。
- **它是方案卡自己的一句话**：`MobilePlanWorkbench.PlanSchedule` 按 `activity.cost_status` 计数，不看 `authority_state`；票价确认后仍写「N 项费用待确认」，与同一屏「票价这一项你已经确认先不计入预算」互相打架。已改为：确认后写「这 N 项费用你已经确认先不计入预算（总价不含这些项）」，未确认时保留原句（`data-testid="rev-plan-costs"` → `rev-plan-unknown-costs`）。`tsc -p tsconfig.check.json` RC=0，Vite 编译 200。
- **430 仍没到 ACTIVE**：r17（430×932、全新会话 `3efeb2dd…`）第一轮连吃两次 `MODEL_TIMEOUT`（恢复腿各按一次，第二次也用掉），第二轮恢复尚未完成时我停掉了探针——这趟是模型侧抖动，不是产品判定。430 的 ACTIVE 仍记 **未证**；要证它，需要在网关平稳时重跑同一脚本，且把「选用按钮在屏但不可用」的 `SELECT_STATE` 读数抓全（r17 已把这条诊断装进脚本）。
- 归属：`MODEL_TIMEOUT` 归网关（同一时段 390 那趟成功）；「费用句与确认矛盾」归产品，已修；「选用按钮不可用」若再现，先看 r17 的 `SELECT_STATE`（count/visible/enabled/disabled/parent class），再决定是 `needsRefresh` 残留还是别的门。

## 13. 课堂栈同代与接受旁屏证的边界（2026-10-26 13:24 本地）

- **课堂栈已换代并全绿**：见 §11。探针是在合并后的 `9b51c7ea48` + 本班前端改动上跑的。
- **没有取到 `rev-presenter-diff` 的屏**：预置提案是 **journey 级 replan**（`proposal 1b39c704…`，无 simulation run），而控制台的接受卡只处理 **run 的 `PAUSED_FOR_ACCEPTANCE` + PRESENTED 提案**；页面此时写「尚未开演」，我的差异块因此不渲染。要在屏上看到它，必须先开演并在守护轮产出一份 run 绑定提案——那一步要模型，而本轮网关连续 90 秒超时（16 token 的探针也超时），所以这一格仍是 **PARTIAL**，不是"已验"。
- **顺带记一条口径**：journey 级预置提案由「行程守护」卡接受（RUNBOOK 主线），run 级提案由控制台接受；两者不要互相代替。这一条与 RUNBOOK 的勘误一致，未发现矛盾。

## 14. 交接给下一班（网关故障期间的现读与命令）

- **现读 1**：本班末（13:30 本地）模型网关 `http://127.0.0.1:7863/v1/chat/completions` 对 16 token 的请求 **60 秒超时**；同一时段课堂栈/试玩栈/高德/票门都正常。`MODEL_TIMEOUT` 与 430 的两次失败都发生在这个窗口里，归网关，不归产品。
- **现读 2**：前端生产构建通过（`vite build` ✓ 7.49s，PWA 56 条 3342.27 KiB），本班三处前端改动（讨论门、工具时间线、费用句）都在产物里。
- **现读 3**：390 那趟 ACTIVE 的库内下一站：`current_activity` 序号 1 故宫 12-03 09:00（`real-place-62c2e606…`），下一项序号 2 景山公园 12-03 14:00；与屏上「现在：故宫博物院 / 接下来：景山公园」一致。
- **网关恢复后按序做**：
  1. `PROFILE=… RW=430 RH=932 node trial/human_walk/_go_to_active_chrome_r17.mjs`（已带 `SELECT_STATE count/visible/enabled/disabled/parent` 诊断与「disabled 先刷新再重试」）；目标是 430 的 `commit 200 / start 200` 收据。
  2. 在 ACTIVE 会话里做「只改第二天晚餐、其他不动」：记改前 6 个 slot 的 `title/start_at`，发「只把 12 月 4 日晚餐换成…其他日期和安排都别动」，再读同一 journey 的活动表，逐项比 `start_at` 是否只在目标格变化（漂移=别的格开始时间变了）。
  3. 开演 → 注入闭馆 → 守护（约 3–6 分钟）→ 控制台出现 `rev-presenter-diff` → 截图：这是接受旁差异与「接受后刷新外层」唯一缺的屏证。
- **不要做**：不要在网关超时时重跑 390/430 并把它记成产品失败；不要把 journey 级预置提案当 run 级提案去按控制台的接受键。

## 15. 接受后刷新外层：补上真正的读者（2026-10-26 13:34 本地）

- 原来只有方案工作台监听 `citynexus:plans-updated`；控制台在 13:1x 接受后派发的同一个事件，**地图/日程/状态那一屏没有读者**，所以"接受成功"只刷到方案卡。
- 已在 `MissionCockpit`（旅程/地图那一屏的数据入口）加入同一事件的监听：`detail` 为空或等于本行程时 `setRefresh(v+1)`，重读 `getJourneyMapPlaces` 与已存任务；与服务台的工作台监听同形。
- 验证（接线级，真事件+真网络）：在课堂栈真 Chrome 里进入 `2e9cd67d…` 的旅程屏，落地后已有 1 次 `GET /api/v1/journeys/2e9cd67d…/map-places` 200；派发一次 `citynexus:plans-updated`（detail=该 journey id）后，**又出现 1 次** `GET /map-places` 200（`DELTA 1`，`plans-updated-wiring-390.txt`）。这证明"旅程/地图那一屏"现在真的会因该事件重读；接受键本身→外层换新仍要在网关恢复后用守护接受那一趟拍屏（见 §14 第 3 条）。
- 课堂主线的另一条接受路径本来就会整页重载（`GuardianRealityPanel.settleProposal` 在 accept 后 `window.location.reload()`，注释写明"这份计划已不存在，要重读"），所以两条路现在都覆盖：课堂卡接受→整页重读；控制台接受→`plans-updated`→旅程屏重读。
- 构建：`tsc -p tsconfig.check.json` RC=0；`vite build` ✓（PWA 56 条 3342.47 KiB）。

## 16. 失败路径：把模型结局说出来（真超时屏，2026-10-26 13:44 本地）

- 网关从 13:14 起对 8–16 token 的请求也超时（40/45/60/90 秒四测全 TimeoutError），这给了本班一条**真实**失败屏：新旅程 `…`（本次探针）发一句话后，`POST /goal-tasks/{id}/run` 在约 185 秒处返回 `MODEL_TIMEOUT`，屏上出现
  「**现场模型这一轮超过三分钟没有回，结果没有保存；可以直接重试这一轮。**」
  （`data-testid="rev-agent-failure"`，`failure-path-390.txt` t=210.4）。
- 同屏还有客户端自己的 180 秒等待条：「本次响应等待超时；刷新可查看服务端任务进度。」＋「重试这一轮 / 先浏览已找到的地点」两个按钮（`390-failure-named.png`）。两条信息不冲突：一条说这次请求等超时了，一条说服务端给出的模型结局与"结果没保存"。
- 修的是原来那句对 429/超时/5xx 一视同仁的「这次有一部分还没完成」：现在按 `failure_code` 分成 429（限流）、TIMEOUT（三分钟没回）、其它 `MODEL_HTTP_x`、空响应、运行时未启动五档，每档都说清"结果有没有保存、能否重试"。`tsc -p tsconfig.check.json` RC=0。
- 仍然没做的：429 那一档没有当场复现（本班只在上午撞到一次 `MODEL_HTTP_429`），所以屏证只有 TIMEOUT 这一档。

## 17. 课堂入口与「接受这份调整」的真读数（2026-10-26 13:58 本地）

- **打印的 Tablet 地址这次兑不上**：连续三趟（390，新 profile）打开 `…/revolution#pair=<印刷票>` 都停在冷首屏、「从一句话开始」，hash 未被清、`POST /demo/pairing/redeem` 无记录——不是加载慢。改从票文件 `D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket` 取 `tickets[]` 逐张尝试（不打印票值），第一张即 `redeem=[200]`，页面进到「北京 · 2日行程 / 行程执行中 / 第一站：故宫博物院 · 12月3日 09:00」。结论：**印刷票可能已被启动器自己的截图腿消耗；下一班一律用票文件里的票**（脚本 `_classroom_accept_tickets_r23.mjs`）。
- **接受按钮没出现**：进入后点「行程守护」（命中），等 30 秒仍无「接受这份调整」；同屏能力卡写「行程守护 / 添加同行者后使用」。也就是说这个单人 ACTIVE 旅程上没有可点的守护接受卡（与 RUNBOOK 写的「点行程守护看卡片」不一致——要么这条路在单人场景被门控，要么预置提案只挂在控制台侧）。**没有拍到接受、没有改库**，如实记。
- **屏证缺口**：本探针的三张截图（before / guardian / after）文件未落盘（`SHOT` 已记、PNG 不存在），原因是多次静默失败的 `page.screenshot`；不拿不存在的图当证据。文字读数在 `classroom-accept-tickets-390.txt`。

## 18. 勘误与真闭环：课堂守护接受 + 第一站日期（2026-10-26 14:12 本地）

**勘误（§17 的两句作废）**：
- 「接受按钮没出现」——**探针定位错**，不是产品缺陷。用 `button[aria-expanded]` 精确定位「行程守护」开关后：`aria-expanded false → true`，面板 `.rev-guardian-panel` 渲染，`[data-testid="rev-guardian-proposal"]` 与 `[data-testid="rev-guardian-accept-replan"]` 都在且可点。§17 里「同屏写『添加同行者后使用』」是**另一个能力卡**，不是守护开关。
- 判据是否受影响：课堂接受路径从「缺证据」改为**已有真闭环证据**；控制台 run 级差异块（`rev-presenter-diff`）仍缺屏证，不受此勘误影响。

**真闭环读数（390×844，票文件第 0 张，`redeem=200`）**：
| 步 | 读数 |
|---|---|
| 提案卡 | 「找到一份可行的调整」「移除故宫博物院；路上少 66 分钟」「规则引擎生成 · 不是大模型现场推理」 |
| 接受 | `POST /replans/{id}/accept → 200`；`replan_proposals.status=ACCEPTED`，`proposed_plan_version_id=f64b81ae…` |
| 换代 | journey `active_plan_version_id` `e74a5edb`(v2 SUPERSEDED) → `f64b81ae`(v3 ACTIVE)，**MATCH True** |
| 计划 | v3 两项：天安门 12-03 09:00 `COMPLETED`、天坛 12-04 09:00 `ACTIVE`（当前站） |
| 屏上 | 重载后「第一站：天坛公园 · 12月4日 09:00」，`现在：天坛公园`（`guardian-accept-390-after.png`、`guardian-accept-390-panel.png`） |

**同一屏暴露并已修的缺陷（第三个）**：调整前标题写「第一站：天坛公园 · **12月3日 09:00**」——标题取当前站、日期却取**全行程最早 slot**（已完成的 12-03 天安门）。已改为日期跟随被命名的那一站（`LiveRecovery.tsx`：`liveNow.start_at` 优先，取不到才回退最早 slot）。屏证：`first-stop-date-390.png`（修复后「第一站：故宫博物院 · 12月3日 14:00」，旧实现会写 09:00）、`guardian-accept-390-after.png`（接受后「天坛 · 12月4日 09:00」）。`tsc` RC=0。

**取证腿修复**：课堂页面 `page.screenshot` 一直超时（30s/12s 都卡，等字体/动画）；改走 CDP `Page.captureScreenshot` 后稳定落盘（321 KB / 155 KB）。以后所有课堂屏证一律走 CDP，不再用 `page.screenshot`。

## 19. 430 复跑（网关恢复后）与两扇门互锁（2026-10-26 14:25 本地）

网关 14:12 恢复（200 / 6.5 秒）后立刻跑 430×932：`journey a22411b7…` / `task deeb9691…`，研究、草案（7 项、rev 1）、`plan a89739f8…`（CANDIDATE、mobility 已冻、`COST_UNKNOWN_ACCEPTED`）、冻结 5/5 全过；**仍停 DRAFT，没到 ACTIVE**，原因不是模型。

**首次抓到的 `POST /departure/commit → 422` 拒绝句（此前 §7 记为"没抓到"，本条取代）**：
> 这版方案排不下：两段安排之间留的赶路时间不够（1 段）。在出发待办里把后一项的开始时间挪晚，或把前一项的结束时间挪早，再按一次「选用这份方案」。

**按它给的下一步做，撞上第二扇门**：点「根据路线重新安排」→「按这一版安排」→ `POST .../prepare-plan → 422`：
> 第 7 项「南锣鼓巷（可选·胡同漫步）」 20:41–21:41：结束时间超出了这趟旅行的结束。改这一项的时间再保存，其余不用动。

即：**不动**（20:00–21:00）→ 前门→南锣 41 分钟车程、0 分钟余量 → commit 422；**按建议推后 41 分钟** → 21:41 越过 21:00 的行程结束 → prepare 422。两扇门互锁，而草案编辑器没有「删掉这一项」的入口（第 7 项在草案里本身就标着「可选」）。这是本轮最硬的产品阻塞，归**replan 候选/计划编辑**，不归模型。

**同屏两句互相矛盾（已修）**：卡片写「屏上的出发待办都齐了，可以直接选用这份方案。」，下方方案卡写「这一版还需要把待办逐项补完才能选用。」——前者把"没有可问的事实"当成"可选用"。已改为「屏上的出发待办都问过了；能不能选用，以方案卡上的按钮为准。」（`departureGaps.ts`，`tsc` RC=0；屏证待下一次方案卡出现时补）。

**费用口径不一（未修，记录）**：同屏一处按**安排项**写「这 7 项费用你已经确认先不计入预算」，另一处按**地点**写「这 6 处门票仍未核实」。数字都没错（7 项安排落在 6 个地点），但读者会以为是两个结论。待统一口径。

**今天改的费用句已在 430 屏上生效**：方案卡显示「这 7 项费用你已经确认先不计入预算（总价不含这些项）。」（`390-g6-final` 同源屏文，日志 `go-active-430-go6.txt`）。

## 20. 勘误（§19 一句作废）

§19 写「草案编辑器没有『删掉这一项』的入口」——**错**。`GoalDraftEditor` 每一项展开后就有「移除这项安排」（`remove(dayIndex, slotIndex)`，`GoalDraftEditor.tsx:58`），保存走同一份 `PUT .../draft`。所以 430 的两扇门互锁**有解**：展开第 2 天第 4 项「南锣鼓巷（可选·胡同漫步）」→ 移除 → 保存草案 → 重新保存候选 → 冻结 → 选用。
- 受影响读数：§19 的「这是本轮最硬的产品阻塞…归 replan/计划编辑」降级为**交互发现性**问题（删站在草案区、不在出发卡上，撞到 422 的旅客看不到它），不是"无路可走"。
- 判据变化：430 仍缺 ACTIVE 的收据，但原因从"无解互锁"改为"脚本未走删站这条路"；下一步按删站路径重跑。

## 21. 交接增补（14:27 本地）

- **430 的正确下一步路径**已装进 `_go_to_active_chrome_r26.mjs`：研究完成 → 若「选用」被 422 挡（赶路不够）→ 打开「按天调整行程」→ 在草案里展开标题含「可选/南锣」的那一项 → **「移除这项安排」→「保存草案」**（等「草案已保存到这趟旅行」）→ 回出发卡勾选并「保存为正式候选方案」→ 冻结 → 确认票价 → 刷新方案 → 选用 → 出发。这条路径走的是产品自己的两扇门，不碰库。
- **课堂屏证一律用 CDP**：`Page.captureScreenshot`（`page.context().newCDPSession(page)`）在课堂页稳定落盘；`page.screenshot` 在该页 10–30 秒必超时（等字体/动画），不要再拿它当唯一取证腿。
- **入口票**：一律读 `D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket` 的 `tickets[]` 并逐张试；启动器打印的地址可能是已被它自己消耗的那张。

## 22. 430 的真阻塞：研究轮被普通消息打回讨论模式（2026-10-26 14:38 本地）

**先撤回一个归因**：§19/§20 把 430 的阻塞记成「赶路不够 + 删站入口」，那是**方案已存在**之后的门。14:28 那次从空白重跑，卡在更前面：**研究轮结束后草案 0 个槽位、`research_places` 0 个**，`DRAFT_SLOTS 0 / NO_OPTIONAL_SLOT`，删站路径根本没机会走。

**现读证据**（`citynexus_v3_gozero_1026.db`，journey `363c3f6e-83ae-4f30-802a-6ff119bb5ffb`）：

| 读数 | 值 |
|---|---|
| `journey_missions.status` | `PARTIAL_READY`，`failure_reason` 为空 |
| `goal_task.interaction_mode` | `DISCUSS` |
| `goal_task.research_places` | `[]`（0 个） |
| `goal_task.draft_artifact` | 只有 `days/revision/status`，0 个 slot |
| 研究 run `14015e0a…` 的 step 2 | `discover_places` **BLOCKED**，`reason_code=TOOL_NOT_ALLOWED`，`query_length=0` |
| 同 run 的 step 1 | `inspect_journey` COMPLETED |

即：模型想检索地点，被**本轮工具白名单**挡了；白名单只有两个工具，于是它只能继续说话，最后交出一句「我会检索北京景点与餐馆」而没有地点。

**根因**（`backend/app/agent/goal_tasks.py`）：

1. `_ALLOWED_TOOLS`（含 `discover_places`）只在 `consent.online_research` 为真时启用；`interaction_mode == "DISCUSS"` 时白名单被强制成 `{ask_traveler, inspect_journey}`（约 1367 行）。
2. 14:30:15 点「不选了，直接按现在的方向开始研究」真发出 `interaction_mode=RESEARCH`，任务确实升级过一次。
3. 14:30:41 用户按提示又补了一句地点（聊天坞的普通消息**一律携带 `DISCUSS`**），`task["interaction_mode"] = interaction_mode` **无条件写回**，模式掉回 DISCUSS（原 1269 行）——此后所有研究工具都被挡，任务以 `PARTIAL_READY` 收尾。

这不是「模型不行」，也不是「高德没配」：模型试了正确的工具，门把它挡了。

**修复**（已改，`goal_tasks.py`）：模式**单向升级**——一旦任务已是 `RESEARCH`，聊天坞带来的默认 `DISCUSS` 不再把它打回去。有显式研究请求时仍按原两条臂升级。`tsc` 不涉及后端；后端用 `CityNexus/.venv`（3.12）重启后 `/api/v1/health` = 200。

**过程事故（记录）**：重启后端时 `taskkill /T` 把启动器父进程树一起收了，前端 :14461 同时下线（`ERR_CONNECTION_REFUSED`）。已单独重起 vite（`CITYNEXUS_BACKEND_PORT=60361`，dev 200），库文件没动。以后只对监听该端口的 PID 本身动手，不用 `/T`。

**课堂控制台 run 级差异（r29 读数）**：注入一次性票后进屏成功，第一站「天坛公园 · 12月4日 09:00」（§18 的日期修复仍在）；点「开演（模拟两日）」→ `模拟进行中 · 12-03 09:00`；点一次「到下一站」→ `模拟行程已完成 · 12-04 10:00`，界面写「两日模拟走完，这趟行程已封存」。**这一轮没有 CLOSURE 事件**，所以 `PAUSED_FOR_ACCEPTANCE` 与 `rev-presenter-diff` 都没出现（与 r18 的 `DIFF false` 同因）。要拿 run 级差异块，得让模拟序列里带一个事件；这需要重新起一次课堂演示（会重置 demo 库），排在 430 收口之后。

**票的可用做法**（本机 canary，不打印票值）：`demo_pairing.py` 的 issue 需要启动器随机生成的 presenter key，重启后就换了；但票表只校验 `sha256(ticket)`。复制库一份备份后，往 `demo_pairing_tickets` 插一行（`expires_at=now+3600`）即可用 `#pair=` 进屏；票是一次性的，用完再插。落盘只写 `journey_id` 与文件名。

## 23. 接受旁的差异块（真屏 + 真点击，2026-10-26 14:48 本地）

**课堂栈重起（prepare_classroom_scene_r1.py）**：`DEMO_READY=true`、`PAIRING=OK`、`CITY_IDENTITY=BOUND:110000`、`SAVED_PLAN=true`；journey `2e9cd67d…` 仍为 `ACTIVE`，新方案 `e74a5edb-3f6d-40c3-910c-52e449619d40`；注入事件 `880cec4e…`（`CLOSURE`）；直接 replan 提案 `d28062b2…`（`PRESENTED`，`replan_http_status=201`）。票值只在 `.demo_pairing_ticket` 与启动器输出里，本报告不抄。

**屏上差异句**（`[data-testid="rev-guardian-proposal-diff"]`，390×844，`guardian-diff-390-panel.png`）：

> 找到一份可行的调整
> **移除故宫博物院；费用：不变；路上少 66 分钟。**
> 规则引擎生成 · 不是大模型现场推理

这三段分别来自 `pendingProposalSentence`（`GuardianRealityPanel.tsx`）：`removed` 的地点标题 → `added` → 每个 `moved` 的「时间：X 从 A 挪到 B（晚/早 N 分钟）」→ `cost_delta_minor`（0 写「不变」，非 0 写「多/省 ¥N」，非数值写「未知」）。本提案没有 `moved` 项，所以屏上没有「时间：」行——这是数据形状，不是渲染缺口。

**真点「接受这份调整」**：`ACCEPT_HIT true`（`elementFromPoint` 命中按钮自身）→ `POST /replans/…/accept` **HTTP 200** → 9 秒后回读第一站 **「天坛公园 · 12月4日 09:00」**，路线「约 54 分钟」（`guardian-diff-390-after.png`）。

**run 级 `rev-presenter-diff` 仍缺**：课堂控制台只在 `PAUSED_FOR_ACCEPTANCE` 渲染它。r29 实测：开演 → `模拟进行中 · 12-03 09:00` → 点一次「到下一站」→ `模拟行程已完成 · 12-04 10:00`，界面写「两日模拟走完，这趟行程已封存」；这一轮的模拟序列里没有 CLOSURE，所以没有暂停点。要拿 run 级差异，得让演示序列带事件（重启课堂演示后再开演），排在 430 收口之后。

## 24. 430 的三次重跑：模型网关 503，不是产品门（2026-10-26 15:12 本地）

**模式修复在真栈上生效了**：14:47 读 `journey 8bdeb603` 的 `goal_task.interaction_mode` = **RESEARCH**（此前同一位置是 DISCUSS）。但地点仍是 0：

| journey | 时间 | 结局 | 上游读码 |
|---|---|---|---|
| `8bdeb603…` | 14:39–14:47 | `FAILED_RECOVERABLE` | run `2657bf91` **MODEL_TIMEOUT**（06:39:19→06:42:20）、run `dc214a13` **MODEL_HTTP_503**（06:42:23→06:44:45） |
| `b5062aca…` | 14:59–15:02 | `FAILED_RECOVERABLE` | `MODEL_HTTP_503` |

同一时刻直接打网关（`/v1/chat/completions`，8 token）**HTTP 200 / 15.9 秒**——网关活着，长上下文的研究轮被上游 503。屏上是产品自己的失败句（脚本点到了「按讨论的方向开始研究」的重试按钮，`recover-ask`），不是假死。**430 的 ACTIVE 仍缺**；390 的同号收据（§12–§13）不受影响。

**「只改半天」的入口事实**：`MissionCockpit.tsx:387` 只在**未出发**时把这一块叫「按天调整行程」；`journey.status === "ACTIVE"` 时同一位置是「执行与待办」，没有草案编辑器。所以已在执行中的 390/课堂旅程都改不了半天，必须在 DRAFT/CANDIDATE 上做。

**gozero 栈开票的办法（已验）**：`redeem` 要求 `CITYNEXUS_DEMO_DATABASE_PATH` 指向实际库（否则 503 `DEMO_DATABASE_NOT_ISOLATED`）。`_restart_gozero_backend_r1.py` 已加这一项；往 `demo_pairing_tickets` 插一行后 `POST /api/v1/demo/pairing/redeem` 回 **200**，票绑定 `a22411b7`（未出发、CANDIDATE、DB 里草案 7 个 slot）。

**进去之后的新读数（未定性，待查）**：屏上「按天调整行程」写 **0 项安排 · 0 天**、「1 份正式候选方案」，而同一 journey 的 `goal_task.draft_artifact.days[].slots` 合计 **7**。前端读 `task.draft_artifact`（`MissionCockpit.tsx:392`），DB 读 `intent_json.goal_task.draft_artifact`——两处对不上。还差一次逐字段对拍（GET 返回体的 `draft_artifact` vs DB），确认是读取清洗还是取了另一个 mission；在没对拍前不改代码。

## 25. 只改一个下午，其他时段不漂移（430×932 真屏 + 真保存，2026-10-26 15:25 本地）

**装置（明确披露）**：`journey a22411b7`（未出发，DRAFT，草案 7 项）在隔离的 gozero 试玩栈上；一次性票由 `demo_pairing_tickets` 注入、`redeem` 换 15 分钟 bearer；前端会话与本地任务指针在页面加载前写入（`sessionStorage` 的 bearer/session-id、`localStorage` 的 `citynexus.v8.journey_id` 与 `citynexus.revolution.goal-task.<traveler>.<journey>`）。这些是**环境准备**；下面每一步都是屏上真按钮：点「我的旅程」→ 点「按天调整行程」→ 切 Day 2 → 展开第 2 个时段 → 改「安排」→「保存草案」。

**改前**（`half-day-430-before.png`）：

- Day 1：上午 故宫博物院（午门进·神武门出）｜下午 景山公园（登万春亭看全景）｜晚上 王府井步行街（晚餐+逛街）
- Day 2：上午 天坛公园（祈年殿·回音壁·圜丘）｜**下午 天坛园内慢走/园中园细看·休息**｜晚上 前门大街（老字号晚餐+逛街）｜时间灵活 南锣鼓巷（可选·胡同漫步）

**动作**：只把 Day 2 下午那一项的标题改成「天坛园内慢走/园中园细看·休息（只改这一段）」，时段仍是「下午」，然后「保存草案」。

**保存回执（屏上原文）**：「草案已保存到这趟旅行」（`SAVE_RESULT`）。

**改后回读**（`half-day-430-after.png`）：

- `DAY1_UNCHANGED true` —— Day 1 三项逐字未变。
- Day 2 只有那一段变了；上午的天坛、晚上的前门大街、时间灵活的南锣鼓巷都在原位，时段标签一个没动。
- 截图与逐字清单：`trial/results/20261026_gozero/half-day-390.txt`（日志名沿用 r32 的 390 前缀，实际视口 430×932）。

**更正 §24**：§24 末尾写「屏上 0 项 vs DB 7 slots，待查」——**不是产品缺陷**。`MissionCockpit.tsx:234` 用本地指针 `citynexus.revolution.goal-task.<owner>.<journeyId>` 定位任务，没有指针就不发那一次 GET（这是「本机指针只定位任务，读取仍由服务端授权」的设计）。补上指针后 7 项立刻显示；GET 返回体与 DB 逐字段一致（2 天 / 7 slots）。§24 那句「两处对不上」作废。

## 26. 430×932 从冷首屏走到 ACTIVE（同一条 Journey/Task，2026-10-26 16:10 本地）

**本轮最硬的一层不是模型，是试玩栈没开"真实城市检索"**。研究轮的工具步骤里 `discover_places` 三家 provider 都是 **3 毫秒返回 0**、`http_status` 为 null、`status=PROVIDER_DISABLED`、`reason_code=REAL_CITY_DISABLED`——开关在 `backend/app/core/config.py:111`（`CITYNEXUS_REAL_CITY_ENABLED` / `CITYNEXUS_REAL_CITY_MODE`），而 `_cmdr_v3_serve_human_r1.py` 与我的重启脚本都没写这两行。高德本身是好的：`GET /api/v1/providers/v9` 回 `amap.status=READY / provenance=LIVE`。

**修复**：两个启动脚本各补 `CITYNEXUS_REAL_CITY_ENABLED=true`、`CITYNEXUS_REAL_CITY_MODE=live`，重启后端。修复后同一轮研究里：`research_places` **56** 个、草案 8 项 **8/8 都带 `place_id`**（故宫博物院、景山公园、前门大街、全聚德前门店、天坛公园、清真天義顺涮肉、北海公园、什刹海前海）。

**屏上具名拒绝**（真点「选用这份方案」→ `POST /departure/commit` **422**）：

> 这版方案排不下：晚餐：全聚德（前门店）在你排的这段时间不开放；什刹海前海（晚餐与胡同散步）在你排的这段时间不开放。把这一项挪到它的开放时间，或在探索里换一个地点，再按一次「选用这份方案」。

这是 §19/§20 那条「两扇门互锁」之外的第三种形状：**营业时间与排程冲突**，而屏上给了两条可走的路（挪时间/换地点）。

**走的路径（全是屏上真按钮）**：按天调整行程 → Day 1 展开「晚餐：全聚德（前门店）」→ **移除这项安排**；Day 2 同样移除「什刹海前海」→ **保存草案**（回执「草案已保存到这趟旅行」）→ 勾「按以上时间准备方案」→ **保存为正式候选方案**（`prepare-plan` 201，新 plan `2e9b2c23…`）→ 确认费用 → 冻结转场（`5/5`，其中 5 段超过 1 公里已换成公共交通核实）→ **选用这份方案**（`departure/commit` **200**）→ **准备出发**。

**同号收据**（现读 `citynexus_v3_gozero_1026.db`）：

| 项 | 值 |
|---|---|
| journey | `d2efa5b4-183b-4fe5-9cf5-7b86099abf05` → **ACTIVE** |
| goal task / mission | `23010c0d-47a5-40df-a9cc-55e5728e0dac` |
| active plan version | `2e9b2c23-055c-4d0f-b92a-7c17f581a1bc` → **ACTIVE** |
| 旧候选（被新候选取代） | `1b6bb394…` 仍是 CANDIDATE |
| 出发后第一屏 | 「旅途正在继续 / 行程执行中」；第一站 **故宫博物院（午门入，中轴线慢走）· 12月3日 09:00**，接下来景山公园 |

截图：`select-430-before.png`（候选卡 8 项与具名拒绝前）、`select-430-after.png`、`go-live-430-after.png`（ACTIVE 首屏）。日志：`select-430.txt`、`go-live-430.txt`。

**两个尺的坑（记录）**：①「生成正式候选方案」在屏上写作「**保存为正式候选方案**」，脚本按旧名点击 MISS，于是选用了旧候选并复现同一条 422；②同一屏可同时存在两张候选卡（旧的不消失），`rev-plan-select` 取 `.first()` 会点到旧卡——取最后一张才选中新候选（`SELECT_CARDS 2` → commit 200）。

## 27. 课堂控制台的 run 级差异块：真屏 + 真接受 200（2026-10-26 16:25 本地）

**怎么造出暂停点**：控制台在 `run.status === "RUNNING"` 时给当前站三个注入按钮（闭馆/下雨/延误半小时）。走法：开演（`POST /simulation/runs` **201**）→「模拟进行中 · 12-03 09:00」→ 点「闭馆」（`POST …/runs/7044b8b3…` **200**）→ run 变「**等待守护决策** · 12-03 09:00」→ 点「交给守护助手」→「守护正在分析 · 12-03 09:00」→ 约 5 分半后出现差异块。

**屏上差异块**（`[data-testid="rev-presenter-diff"]`，`run-diff-390-block.png`）：

> 接受后计划会这样变
> 移除：故宫博物院
> 路上：少 66 分钟
> 费用：不变

**真点「接受这次事件的调整」** → `POST /api/v1/replans/e7912b9c-93ef-47fd-bc1b-6a7dc6c92c0e/accept` **HTTP 200**；接受后同屏读到「**这次事件已经落定，可以继续模拟。**」与「行程已经启动」。

**同一屏还多出一句误导**（`run-diff-390-after.png` 原文）：

> 进度里记着提案编号，但看不到可接受的内容；请重启课堂演示（双击启动器）。

成因：接受成功后提案状态变 `ACCEPTED`，`simulationProposal` 读不到了，但 run 里仍记着提案 id，于是「提案 id 有 / 内容没有」那条分支与「事件已落定」同时为真。已在 `ClassroomPresenterPanel.tsx` 给该分支加 `!pendingResolved`（tsc RC=0）——只有「有 id、读不到内容、且事件没落定」才是它描述的真异常。这直接违背「接受后不要叫演示者重启」的产品口径，属本班修掉的第三处「接受成功却劝重启」。

日志：`run-diff-390.txt`（含每次刷新读数与 run 状态行）。

## 28. 交付卡（截至 2026-10-26 16:45 本地；代码尖 `e35242fdb4`，文档尖 `5151891a63`；`tsc` 与 `vite build` 均 RC=0）

### 28.1 两条真机路径，各自同号

| | 390×844（第一档） | 430×932（第二档） |
|---|---|---|
| journey | `693a693a-6289-422c-9ca4-b2a860db5ef5` ACTIVE | `d2efa5b4-183b-4fe5-9cf5-7b86099abf05` ACTIVE |
| goal task | `49a999d6-dcf5-4c98-85a8-9055be068a18` | `23010c0d-47a5-40df-a9cc-55e5728e0dac` |
| 候选 → 选中 | `4cab4148-3295-4a27-8ca9-699d62b59d87` ACTIVE | `2e9b2c23-055c-4d0f-b92a-7c17f581a1bc` ACTIVE（旧候选 `1b6bb394…` 仍在） |
| 研究产出 | 13 步工具、64 个地点 | 24 步工具、56 个地点 |
| 出发后第一屏 | 第一站 故宫博物院 · 12月3日 09:00 | 第一站 故宫博物院（午门入，中轴线慢走）· 12月3日 09:00 |
| 刷新保留 | — | `my-trips-430-reloaded.png`（前后逐字一致） |

### 28.2 点击路径（全部屏上真按钮，无 API 代点）

- **390**：冷首屏写目标 → 继续规划 → 对话设置勾两项 → 发送 →（首问）不选了，直接研究 → 研究出草案 → 保存为正式候选 → 确认票价 → 冻结转场 → 选用这份方案（commit 200）→ 准备出发。
- **430**：同上到候选；「选用」被具名拒绝（两处晚餐不开放）→ 按天调整行程 → 两项「移除这项安排」→ 保存草案 → 保存为正式候选（新 plan）→ 确认费用 → 冻结 5/5 → 选用（commit 200）→ 准备出发。

### 28.3 第 2 刀（差异块）两种形态都拿到了

- **journey 级**（守护屏）：`移除故宫博物院；费用：不变；路上少 66 分钟。` → 真点接受 `POST /replans/…/accept` **200** → 第一站变天坛公园（§23）。
- **run 级**（课堂控制台）：开演 → 注入「闭馆」→ 等待守护决策 → 交给守护 → 差异块 `移除：故宫博物院 / 路上：少 66 分钟 / 费用：不变` → 真点接受 **200**（§27）。

### 28.4 本轮修掉的产品问题（都有修前屏证/读数）

1. 研究轮被聊天坞的默认 DISCUSS 打回，工具集缩成两个 → 补料消息保持研究轮（`goal_tasks.py`，测试 16 passed）。
2. 试玩栈没开真实城市检索 → `REAL_CITY_DISABLED`（3ms、0 地点）→ 两个启动器补 `CITYNEXUS_REAL_CITY_ENABLED/MODE=live`（§26）。
3. 「和 Agent 补齐出发资料」写完话按发送走讨论轮，Agent 只能反问 → 该执行请求改走研究轮（`WorkspaceActions.tsx` / `departureGaps.ts`）。
4. 接受 200 之后同屏还劝「重启课堂演示」→ 给该分支加 `!pendingResolved`（§27）。
5. 方案卡在确认未知费用后仍数着「N 项待确认」→ 改口径（早前 §17）。
6. 待办与卡片同屏两句矛盾 → 改「以方案卡上的按钮为准」（§19）。

### 28.5 失败与刷新路径（真实读数）

- 模型上游不稳：`MODEL_TIMEOUT` / `MODEL_HTTP_503` → 任务 `FAILED_RECOVERABLE`，屏上给「按讨论的方向开始研究」重试（§24）。
- 出发门拒绝：`POST /departure/commit` 422，屏上具名句点名「全聚德（前门店）」「什刹海前海」不开放（§26）；另一形状是「赶路时间不够（1 段）」（§19）。
- 刷新：430 ACTIVE 后 `page.reload()`，第一站/现在站/执行中三处逐字一致（`my-trips-430.txt`）。

### 28.6 KNOWN_BLOCKERS（如实）

- **平板 USER_VERIFIED = PENDING**：需要真人用自己的设备点一次；我没有代替。
- **课堂随机城市池 0/3**（早前读数）：不挡本趟演示（用行程自己的城市），但达标仍缺。
- 课堂这轮的两处晚餐冲突，产品只提供「挪时间/换地点」两条路，**没有一键改到开放时段**；本次走的是删站。
- 430 那趟的 goal task 终态是 `PARTIAL_READY`（研究部分来源仍写「以官方通知为准」），但计划与出发都已落定。

### 27.1 修后复验（同一条 run，刷新即验）

run `7044b8b3…` 停在 `PAUSED_FOR_ACCEPTANCE`（已接受、事件已落定），只用刷新就复验到修复生效：

| 读数 | 修前（`run-diff-390-after.png`） | 修后（`resolved-note-390.png`） |
|---|---|---|
| 已落定句 | 有 | **有**：「这次事件已经落定，可以继续模拟。」 |
| 「看不到可接受的内容…请重启课堂演示」 | 有（与上一句同屏） | **无**（`MISMATCH_COUNT 0`、`HAS_RESTART_ADVICE false`） |

### 28.7 补：ACTIVE 后的「下一站」读数（同一 journey）

`go-live-430.txt` 的出发后首屏原文含：「第一站：故宫博物院（午门入，中轴线慢走） · 12月3日 09:00」「现在：故宫博物院（午门入，中轴线慢走）」「**接下来：景山公园（万春亭看中轴线）**」；`my-trips-430.txt` 记录 `page.reload()` 前后这三处逐字一致，截图 `my-trips-430-plan.png` / `my-trips-430-reloaded.png`。

### 27.2 run 级接受之后，外层旅程确实换了计划

同一条课堂 journey（`2e9cd67d…`），在 §27 那次 run 级接受（`/replans/e7912b9c…/accept` 200）之后重新打开外层屏：

| 读数 | 接受前（§23 的旅程级那次之后） | run 级接受后（`outer-after-runaccept-390-a/b.png`） |
|---|---|---|
| 第一站 | 天坛公园 · 12月4日 09:00 | **天坛公园 · 12月4日 09:00**（故宫已被移除，直接从天坛起） |
| 现在 | 天坛公园 | 天坛公园 |
| 刷新后 | — | 第一站/现在站**逐字一致** |

说明：控制台接受按钮里那句 `window.dispatchEvent(new CustomEvent("citynexus:plans-updated", …))` 不是装饰——同一 tab 的外层屏在 8 秒内读到新计划，`page.reload()` 后仍一致。

## 29. 工具时间线「不泄漏」的判据（2026-10-26 16:50 本地）

第 2 刀要求「不泄漏模型私有正文 / 凭证 / 敏感参数」。这不是靠肉眼，靠渲染路径上的字段白名单：

- 每一行的组成（`WorkspaceActions.tsx:681`）：序号 → 工具名（中文化）→ 状态徽标 → 一句结果 → 本地时间 → 「下一步」。
- 那句结果只由 `taskStepText(result)` 生成（`WorkspaceActions.tsx:155`），它只读这些键：`route.mode / route.distance_m / route.duration_seconds`、`status`、`provider`、`reason_code`、`draft_revision`、`candidate_count`、`option_count`、`place_count`、`area_count`、`observation_ids.length`、`cached_references.length`。
- **不在渲染路径上**：`arguments_json`（工具参数原文）、`query` 原文、模型的 reasoning / 正文、坐标数值、任何 key 或 bearer。
- `public_action` 是模型自述的一句「这一步做了什么」，属产品要求展示的下一动作，不含参数原文。

屏证：`agent-timeline-390b.txt`（「Agent 工具时间线 · 11 步」，8 个状态「完成」）与 `390-agent-timeline-local.png`（390×844，本地时间列）。

## 30. 只改晚餐那一段，其余三项（含另一天）逐字不动（2026-10-26 17:00 本地）

**装置**：`journey a22411b7`（未出发，草案 7 项）；一次性票注入 + `#pair=` 进屏（环境准备，明示）。屏幕上真按钮：我的旅程 → 继续这趟 → 按天调整行程 → Day 1 → 展开「晚上 · 王府井步行街（晚餐+逛街）」→ 改「安排」→「保存草案」。

**改前**（`dinner-430-before.png`）：
- Day 1：上午 故宫博物院（午门进·神武门出）｜下午 景山公园（登万春亭看全景）｜**晚上 王府井步行街（晚餐+逛街）**
- Day 2：上午 天坛公园｜下午 天坛园内慢走/园中园细看·休息（只改这一段）｜晚上 前门大街（老字号晚餐+逛街）｜时间灵活 南锣鼓巷（可选·胡同漫步）

**动作**：只把 Day 1 晚上那一项的标题改成「王府井步行街（晚餐+逛街）（只改晚餐这一段）」，时段仍是「晚上」。

**保存回执（屏上原文）**：「草案已保存到这趟旅行」。

**改后回读**（`dinner-430-after.png`）：
- Day 1：**只有晚上那一项**多了后缀；上午故宫、下午景山逐字未变。
- `DAY2_CHANGED []` —— Day 2 四项**一项没动**，连上一轮改过的「（只改这一段）」也原样保留。

**关于脚本里的 `DAY1_UNCHANGED false`**：这一行是「Day 1 整块是否与改前完全一致」，因为目标项就在 Day 1，它当然为 false；真正的判据是「除目标项外无变化」，由上面逐条列出。脚本命名容易误读，这里点名。

## 31. 接受之后「地图」这一格：如实记为未满足（2026-10-26 17:02 本地）

按第 2 刀「接受成功后主动刷新外层 Journey/PlanVersion/活动/**地图**/状态」逐格核对，地图这一格**没有通过**。同一趟课堂 journey（run 级接受 `200` 之后）打开「地图」层，截图 `map-after-accept-390.png` 原文：

> 现实地图　**0 处地点**
> **模拟旅客 1 位 · 暂无研究地点**
> 模拟旅客：天坛公园 · 39.8805, 116.4046（WGS84，模拟位置，不是物理 GPS）
> 地点分布预览 · 未加载外部底图（两个浅色圆点，标注「根据实际坐标显示相对方位，不代表道路或路线」）

也就是说：**计划里有 6 个带坐标的槽位，地图层却写「0 处地点 / 暂无研究地点」**。差异在于数据源不是同一张表——地图读 `GET …/map-places`（journey 候选），计划读 `PlanVersion.activities`；这趟课堂演示的候选为 0，所以接受后地图仍空。这与「接受后地图应反映新计划」不符，列为 **KNOWN_BLOCKER（地图数据源不一致）**：改它要动候选与计划的读侧 join，不是一行文案，本班窗口不开这个改动。

第二处（同一屏，未修）：地图说明行「点击图钉可定位已保存安排：加载 OpenStreetMap」被底部固定输入条压住一半（截图中可见）。属「固定输入条遮内容」这一类，已记录，未改。

**因此「接受后刷新」这条的准确状态**：Journey 状态与活动（第一站/现在站）已换并刷新后保持（§27.2）；**地图未满足**；PlanVersion 以 `active_plan_version_id` 换代 + 第一站变化间接为证。

## 32. 接受后地图「0 处地点」：先勘误，再摊两道读侧墙（现读）

**勘误 §31 的一句**（§31 原文已随 `2176c811a8` 入线，此处不改旧正文）：§31 写「这趟课堂演示的候选为 0」。现读不是 0 —— 课堂库 `D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db` 里 journey `2e9cd67d-10ca-4ecd-920b-76c81a350c71` 的 `real_place_candidates` 是 **amap 四十条 + overpass 十六条**（`select journey_id,provider_key,count(*) from real_place_candidates group by journey_id,provider_key`），试玩库 `citynexus_v3_gozero_1026.db` 里 journey `d2efa5b4-183b-4fe5-9cf5-7b86099abf05` 是 **amap 五十六条**。候选一直在库里，是读侧没把它们放出来。§31 的屏证本身（地图写「0 处地点 / 暂无研究地点」）仍然成立。

**第一道墙在服务端**，`map_place_projection`（`backend/app/planning/travel_brief.py:150`）里有两层筛子：

- `RealPlaceCandidate.provider_key.in_(("photon", "overpass"))` 把高德整类滤掉 ⇒ 那四十/五十六条高德一条都进不来。
- 留下的还要 `_bootstrap_scope_entries(evidence)` 里存在 `member_id`+`traveler_id` 都对上当前成员的 scope，`if not scopes: continue`。现读一枚 amap 行与一枚 overpass 行的 `evidence_json` 键集，只有 `captured_at, cost_evidence, evidence_completion, opening_hours, provenance, provider, request, ttl_seconds` —— 根本没有 `bootstrap_scopes`（这两条候选的 `status=DISCOVERED`、`materialized_place_id` 已指向 `places`，属"旅程级发现"另一条血统）。⇒ 那十六条 overpass 也全被 `continue`，屏幕上才是 `candidates: []`。
- 更要紧的是这个投影**完全不读 `journey.active_plan_version_id` 的活动**。同一库现读该计划的 6 个活动全部带 place：故宫博物院 / 景山公园 / 前门大街 / 天坛公园 / 某餐馆（天坛店）/ 陶然亭公园，`provider_key=amap`、`coordinate_system=WGS84`、`source_coordinate_system=GCJ02`（`select … from activities a left join places p on p.id=a.place_id where a.plan_version_id=?`）。旅客已经接受的站在地图答里没有一格。

**第二道墙在前端**，`WorkspaceMap.validPoint()`（`frontend/src/trial/mobile/WorkspaceMap.tsx:25`）写死 `!(typeof place.provider === "string" && place.provider.toLowerCase() === "amap")`，即"高德来源一律不上底图"；而进「高德地点」列表的条件 `isAmapPoint()` 又要求 `coordinate_system === "GCJ02"`。两条夹在一起：一条 `provider=amap` 且**已经转成 WGS84** 的计划站既画不进图、也不进高德列表，只会落进 `otherCoordinatePoints` 那句「N 处其他研究地点坐标尚未用于地图」。

**为什么不能只把 `"amap"` 加进那个 `in_(…)`**：`_candidate_payload`（`backend/app/execution/bootstrap_discovery.py:719`）用 `_osm_identity(row)` 造 `source_url`，署名位是 `candidate_scope.get("source_attribution") or OSM_ATTRIBUTION`（`backend/app/execution/bootstrap_discovery.py:711`）。高德行没有 OSM id，加进去就会写出「数据来自高德、署名 © OpenStreetMap」的错标 —— 这正是署名那条规矩要挡的。全仓现读也只有 `OSM_ATTRIBUTION`/`OSM_ATTRIBUTION_URL` 两枚常量（`backend/app/integrations/discovery/photon_poi.py:36`），没有高德署名常量可复用。


## 33. 这一刀：四件改动（已施工，本节与产品改动同笔提交）

1. **服务端补第二条臂**（`backend/app/planning/travel_brief.py`）：`map_place_projection` 先按现有臂收旅客自己的私有观测（未改），再在 `journey.active_plan_version_id` 存在时把活动按 `activities.place_id → places` 补成点 —— `origin="PLAN_ACTIVITY"`、经纬度与 `coordinate_system`/`source_coordinate_system` 逐字从 `places` 带出、`source_url` 取 `places.metadata_json.source_urls[0]`（高德即 `https://uri.amap.com/marker?…`）、`scheduled_start_at` 用活动自己的 `start_at`；同一 place 若已被第一条臂给出（靠 `materialized_place_id` 记 `seen_places`）不重复。没有排到地点的活动（`place_id` 为空，例如"午餐"这类自由时段）inner join 天然不进来。
2. **署名按来源分家**：新增 `_provider_attribution(provider_key)` —— amap 给 `© 高德地图（AMAP）` 且 `source_attribution_url` 为 `None`（不编 URL），其余仍取 OSM 那两枚常量。计划站的 `provider_provenance` 干脆不发：`places` 行没有可证的观测出处，留空比给它一个"LIVE_PROVIDER"诚实。
3. **前端把判据从"哪个供应商"换成"存的坐标是哪套"**：`validPoint()` 去掉 `!(provider === "amap")` 那半句，只保留 `coordinate_system === "WGS84"` —— GCJ02 数字照旧不上 OSM 底图（`isAmapPoint` 那条「高德地点」列表一字未动），已经转成 WGS84 的高德来源站则可以画了。来源链接统一走新的 `sourceLink()`：OSM 元素 URL 给「查看地点来源 ↗」，`uri.amap.com/marker` 给「在高德地图打开 ↗」，图钉弹层与下方列表共用同一把判子。
4. **文案不再替底图代署名**：`OpenStreetMap 地图地点 N 处` → `地图地点 N 处`（同一行的「高德地点 M 处」没动），列表 `aria-label="OpenStreetMap 地点"` → `aria-label="地图地点"`，计划站多一行「已排入当前方案」（`data-testid="rev-map-planned-stop"`）。

**改动点名一处断言（不是改松换绿）**：`frontend/e2e/revolution-amap-research-ui.spec.ts:128` 原钉整句 `OpenStreetMap 地图地点 1 处 · 高德地点 1 处`，随文案改为 `地图地点 1 处 · 高德地点 1 处`。两个计数（1 处 / 1 处）与它真正判的行为（高德 GCJ02 不进底图、单独成列）都没放松。**这条 spec 本次未执行** —— 它要 `npm run dev` 那档带后端的栈；只做了类型检查。

**本次跑过的读数**（解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`，即 3.12.14 那枚 venv；cwd `D:/moodle/_cmdr_rescue_v3_1022/backend`）：

| 跑法 | 命令 | 读数 |
| --- | --- | --- |
| 新增回归 + 同域旧 suite | `-m pytest tests/test_qoder_map_active_plan_stops_r1.py tests/test_mobile_travel_brief.py -q -p no:warnings` | `10 passed`（新file 二条；旧 map-places 那几条含 `len(points)==1` 未动仍绿） |
| 前端类型 | `npx tsc -p tsconfig.check.json --noEmit` | `TYPECHECK_RC=0` |
| 后端 | `map-places` 新增字段只加不减，消费侧现读只有 `MissionCockpit.tsx:267` 的 `allMapPoints`（未落 `origin` 的点走原分支），故未跑全量 | 未执行全量 |

新回归的两条各判什么：`test_accepted_stops_reach_the_map_with_their_own_source` 要 `[candidate_id] == [planned.id, unconverted.id]`（含"没有 place 的活动不出现"这条反证）、高德点署名不含 `OpenStreetMap`、`coordinate_system=WGS84` 与 `source_coordinate_system=GCJ02` 同时在场、`source_url` 逐字等于库里的 marker 链、GCJ02 那枚仍带 GCJ02 出去（让读侧继续不上图）；`test_a_plan_that_is_not_active_adds_no_map_points` 先要 `candidates == []`，把同一枚 place 换成 active plan 的活动后要点 `[stop_id]` —— 证明"是 active 这一格把它放上地图"，不是多了一条无条件臂。

## 34. 这一代的两条外部读数（现读，非本刀所造）

**(1) 一条预存在的红，点名并给对照臂。** 本刀之外的读数：把新增回归与相邻四份同域 suite 一起跑，`40 passed / 1 failed`，红的是 `backend/tests/test_in_transit_reroute.py::test_reroute_endpoint_uses_current_observation_and_keeps_active_plan`，`AttributeError: 'types.SimpleNamespace' object has no attribute 'simulation_enabled'`，抛点在 `backend/app/main.py:28439` 的 `persisted_simulation_business_clock` 中间件（该 middleware 由 `a8f9b8ed16`「feat(simulation): persist signed two-day execution and Guardian scene handoff」引入，即 PR #55 那条线，昨夜已入线）。对照臂（不是靠读代码下判）：把 `backend/app/planning/travel_brief.py` 单独退回上一枚提交 `2176c811a8` 的版本再跑那一条 —— `1 failed`，同一枚 AttributeError，随后 `git checkout ab2ca5913a -- …` 恢复（恢复后 `git status --short` 对该文件零行）。⇒ 这条红与 §33 那一刀无关，是那条测试自己的 `settings` 桩没跟上 simulation 合并后的字段；修法属于该线（要么桩补字段、要么中间件读 `getattr(settings, "simulation_enabled", False)`），不在本刀窗口里动别人的断言。

**(2) Codex 的 PR #56 对现尖的只读合并预测。** `git fetch origin refs/pull/56/head:refs/local/pr56` 取回 `a40d5f9c49`（该 PR 在 07:15Z 开、现已换尖）；`git merge-tree --write-tree --name-only ab2ca5913a refs/local/pr56` **RC=0、只输出树 `9e0d4bc192…`、零枚冲突路径**。按只读口径报：这是预测不是落地，未 merge、未跑真栈。文件集对账（按 merge-base 两侧各自 diff）：本线自 merge-base 起 30 枚文件、#56 侧 46 枚，交集**只有 `backend/app/agent/goal_tasks.py` 一枚** —— 我把 `stick_to_research` 装在那儿（§24 那刀），#56 在同文件 `interaction_mode` 附近加 54 行。文本层预测不撞，语义层同一扇门：**#56 若落线，必须重跑 `backend/tests/test_qoder_draft_revision_receipt_r1.py`（现尖 16 passed）才算同代**。#56 正文自己点名的未完项与本班重叠：「课堂Chrome四站、接受后地图刷新、重开浏览器身份/独立打印票、原始屏证上传与实体USER_VERIFIED仍待Qoder/用户完成」——其中「接受后地图刷新」正是 §32/§33 这一刀，且 #56 未触碰 `backend/app/planning/travel_brief.py`（其 46 枚文件里没有这枚），所以那侧没有与本刀竞争的改动。

## 35. 第二次真机走把这一刀逼出第二半（390×844，现尖代码，2026-10-26 23:20 本地）

走通了出发：同一浏览器会话里逐枚真点，`HTTP POST http_status=200 /api/v1/journeys/064ff631-bc60-45ab-b68c-ffdc2ca86f70/departure/commit`，journey `064ff631…`、goal-task `19d3cbe8-0e3f-4c43-a27a-6aaf30645811`、`plan_versions` 现读该 journey 仅 `24a70a0a-b8c0-42b0-993d-35a092ca8ead` 一枚且 `status=ACTIVE`、`journeys.status=ACTIVE`、`active_plan_version_id` 同号；那一版 5 条活动全部带 `place_id`，对应 `places` 五行均 `provider_key=amap`、`coordinate_system=WGS84`、`source_coordinate_system=GCJ02`。收据 `trial/results/20261026_gozero/armA-hy3-map-planned-390.txt`，屏证 `armA-390-g8-map-preview.png`、`armA-390-g8-map-loaded.png`。

按「地图」层之后的读数（同文件 `MAP_` 段，逐字）：

- `MAP_PANE 1`、计数行现读 **「地图地点 0 处 · 高德地点 5 处」** —— §33 那句文案已经在屏上了（不再是「OpenStreetMap 地图地点」）。
- `MAP_PLANNED_TAGS 0`、`MAP_LIST_ITEMS 0`、`MAP_PINS 0`、`MAP_CANVAS 0`。
- `MAP_AMAP_LINKS 5`：五枚点都带着「在高德地图打开 ↗」落在**高德列表**里，而不是画在图上。
- `MISS load-map`：那一屏根本没有「加载地图」这枚键。读渲染分支可知这是条件渲染（`frontend/src/trial/mobile/WorkspaceMap.tsx:171` 起，`points.length > 0 || travellerOnMap` 才渲染预览块与加载键）——试玩栈没有模拟旅客，`points` 为 0 时那枚键就不存在。这条**不是**「固定输入条压住」那一类，是分支没进去；先前把 `MISS` 当成点不到会读错。

屏证到此只够证一半。§33 的服务端臂把计划站发出去之后，前端仍把它们吐回高德列表：`MissionCockpit.tsx:267` 的 `allMapPoints` 先 `results.set(point.candidate_id, …)` 收下 `map-places` 的点，再遍历 `research.places/areas/unknown` 用**同一个 id** `results.set(point.id, …)` 覆盖，而覆盖时的坐标系是按供应商猜的（`frontend/src/trial/mobile/MissionCockpit.tsx:273`：provider 是 amap 就记 `GCJ02`）。于是 `places` 行自己声明的 `WGS84` 被研究副本的 `GCJ02` 顶掉 —— `validPoint()` 按 CRS 拒画、`isAmapPoint()` 按 CRS 收进高德列表，图上无处、列表有名。

有一格本轮**没有**证到，写清楚：这次探针的响应监听器是在 React 自己拉完 `map-places` 之后才挂上的（`MAP_CALLS []`、`MAP_CALLS_AFTER []`），所以「那五枚到底是 `map-places` 给的还是研究线索给的」在屏上无读。`map-places` 会带出计划站这一条，凭的是 §33 的新回归与同代库现读，不是这一张屏。

**本刀的第三件（补上第二半）**：`frontend/src/trial/mobile/MissionCockpit.tsx:278-279` 加守卫 —— 同一 id 已经有一枚 `coordinate_system === "WGS84"` 的点时，不让非 WGS84 的研究副本顶掉它；两侧都是 WGS84、或本来没有既存点时，行为与改前逐字相同。注释里写的是为什么：那串 GCJ02 数字画在 OSM 瓦片上会偏几百米，而且顶掉的同时会把旅客已经接受的那一站连它自己的来源署名一起丢掉。`rev-map-planned-stop` 这枚 `data-testid` 只有服务端那条臂会带（研究副本不写 `origin`），所以下一趟走查里它的计数就是「计划站真的经 `map-places` 上了图」的判子。

**红集合对照（具名对拍，不是总数）**：`-k "departure or draft or plan or map"` 选中面，现尖 `49 failed / 399 passed / 9 errors`；只把 `backend/app/planning/travel_brief.py` 退回上一枚 `2176c811a8` 再跑同一条命令 → `51 failed / 397 passed / 9 errors`。两侧 `FAILED` 名单排序后互相 `comm`：**现尖独有的新红 零枚**；只在基线独有的恰是本刀新增的两条（`tests/test_qoder_map_active_plan_stops_r1.py::test_accepted_stops_reach_the_map_with_their_own_source`、`::test_a_plan_that_is_not_active_adds_no_map_points`）——撤掉产品改动它们必须红，这正是反向对照该给的结果。解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`（3.12.14），cwd `D:/moodle/_cmdr_rescue_v3_1022/backend`；选中面共 448 条参与、2297 条 deselect，**不是**全量 2401 口径，因此不据此判其它域。

同代前端两道门重跑：`npx tsc -p tsconfig.check.json --noEmit` RC=0；`npx vite build` RC=0（产物 `dist/v10-sw.js` 等，见 `BUILD_RC=0`）。

## 36. 撤回 §35 那句成因，并把「哪一格没送到」装成读数（arm B，430 那趟在路上）

arm B 是同代码、新浏览器 profile 的整趟重走（`trial/results/20261026_gozero/map-planned-390-r46.txt`，journey `8e2f7b90-5097-4870-8c8f-c368ac7b8ecc`、goal-task `db6baf38-aa27-495d-acc0-650fbe9abf02`、计划 `4495fc16-7932-4c5d-a1bf-007a7f8e9275`）：`departure/commit` `http_status=200`（t=468.1），`POST /journeys/…/start` `http_status=200`（t=474.2），库现读 `journeys.status=ACTIVE`、`active_plan_version_id=4495fc16…`、该版 6 条活动全部带 `place_id`。屏上随后（t≈579）与整页 reload 之后（t≈615）读数同类：

| 读数 | 值 |
| --- | --- |
| `MAP_PANE` | 1（地图层确实开了，`HIT map-layer true`） |
| `MAP_COUNT_LINE` | 「地图地点 0 处 · 高德地点 6 处」 |
| `MAP_PLANNED_TAGS` / `MAP_LIST_ITEMS` / `MAP_PINS` / `MAP_CANVAS` | 0 / 0 / 0 / 0 |
| `MAP_AMAP_LINKS` | 6（六枚都只在高德列表里） |
| `RELOAD_MAP_COUNT_LINE` / `RELOAD_PLANNED_TAGS` / `RELOAD_LIST_ITEMS` | 「地图地点 0 处 · 高德地点 6 处」/ 0 / 0 |

而同代同库的服务端现读（只读引擎直连 `D:/moodle/_cmdr_v3_live_1022/citynexus_v3_gozero_1026.db`，进程内调 `map_place_projection`）给的是 **6 枚**，逐枚 `coordinate_system=WGS84`、`region_status=MATCHED`、`selection_state=READY_FOR_NATIVE_PLAN`、`origin=PLAN_ACTIVITY`，坐标如 `39.916, 116.391 / 39.895, 116.394 / 39.895, 116.390 / 39.881, 116.405 / 39.936, 116.396 / 39.940, 116.379` —— 前端 `validPoint` 的每一条判据都过。签名 API 那一层也是通的：§33 的新回归第一条就断言 `[candidate_id] == [planned.id, unconverted.id]`，跑绿。访问日志里 `GET /api/v1/journeys/8e2f7b90…/map-places` 有六条 `200 OK`（`D:/moodle/_cmdr_v3_port_1022/gozero_backend_restart.log`；uvicorn 的 access log 不带时戳，所以这六条分不出出发前还是出发后）。

**因此 §35 里这句要撤回**：「§33 的服务端臂把计划站发出去之后，前端仍把它们吐回高德列表 —— `allMapPoints` 先收 `map-places` 再用研究线索同 id 覆盖」。**这不是这一屏的原因**，或至少不是唯一原因：带着 §35 那道守卫重走，屏上读数与守卫前同类（0 上图 / 6 高德），如果"覆盖"是主因，守卫之后就该看到 6 枚上图。受影响并已作废的读数就是 §35 那一句成因本身；§35 里的屏上数字、DB 现读与 §33 的红集合对照不受这句话影响，照旧成立。

现在这条链剩下的唯一未证格是**「浏览器这一屏拿到的 `map-places` 里有没有那 6 枚」**：`MAP_CALLS []` 已经说明"打开地图层不触发一次读"（cockpit 只在挂载与 `citynexus:plans-updated` 时读，`MissionCockpit.tsx:237-249`），而 §35 的观察「接受后不重取」正是这一格，所以 6 枚 `高德地点` 完全可能只来自研究线索（`task.research_places`，其 `coordinate_system` 由供应商名推成 GCJ02）。上一轮我把"没重取"当成已解决的旧格（§27.2 证过 journey 状态与活动会换），这一格没证。

**已把量具装上**（不是改措辞，是加读数）：`trial/human_walk/_map_walk_r46.mjs:22-33` 起，页面一创建就挂响应监听，把**每一次** `map-places` 应答的 `http_status / candidates 数 / 第一枚的 origin·coordinate_system·region_status·selection_state` 逐次记进 `MAP_READS_EVERY`，reload 之后再记最后三次（`RELOAD_MAP_READS`）。`node --check` RC=0。判法预先写死，免得到时候挑读数：若 `MAP_READS_EVERY` 里出发之后的那一次 `candidates` 就是 6 且 `first.origin="PLAN_ACTIVITY"`，那屏上还缺的就是前端渲染那一环；若是 `candidates` 为空或时间戳全在出发前，缺的就是"接受后重取"那一环（也就是 §33/§35 都还没治的那格）。430×932 那一趟（profile `_chrome_gozero_map49`）正按这套读数跑。

§35 那道守卫不撤：同 id 上「行自己声明 WGS84」优先于「按供应商猜 GCJ02」这件事按现读仍成立，`backend` 里也确有 WGS84 的计划行；但它治的是"顶掉"，不治"没送到"，所以本节不把它记成已生效的修复，只记成一条仍然正确的判据。

## 37. 430 那一趟把最后一格定性了，并补上「接受后重取」这根线

`trial/results/20261026_gozero/map-planned-430-r46.txt`（profile `_chrome_gozero_map49`，journey `f49a9114-2a3d-4eda-977f-59b41d72ba46`、goal-task `74502216-383b-4861-868a-4a02af76fe29`，模型 `cn:hy3`）。这趟 `departure/commit` 回的是 `http_status=422`（营业时间冲突那一类：这一版把两处用餐排在来源答案之外），所以 journey **没有** ACTIVE、`active_plan_version_id` 为空。§36 装的逐次读数器在这种情况下给出：

- 每一次 `GET …/map-places` 都是 `http_status=200, candidates=0, first=null`（`MAP_READS_EVERY` 十四条同形；整页 reload 之后的最后三次 `RELOAD_MAP_READS` 也同形）。
- 屏上仍是「地图地点 0 处 · 高德地点 6 处」，`MAP_PLANNED_TAGS 0`、`MAP_LIST_ITEMS 0`，reload 后同形。

**这两行定的是 §36 留的那格**：没有 active plan 时服务端返回 0 枚是正确的，屏上那 6 枚「高德地点」全部来自研究线索（`task.research_places`，其 `coordinate_system` 由供应商名推成 GCJ02），与计划无关。⇒ §33/§35 改的读侧投影是必要的一半，但不是这一屏的全部；还缺一根线 —— 旅客按下「选用这份方案」之后，谁去重取地图。

现读那根线确实断着：提交走 `frontend/src/trial/mobile/MobilePlanWorkbench.tsx:249` 的 `commitJourneyDeparture(journeyId, plan.id, key)`，成功之后该组件只 `await refresh()`（重取的是这张工作台自己的快照）；而 `citynexus:plans-updated` 的发布者只有控制台接受那一支（`frontend/src/trial/mobile/ClassroomPresenterPanel.tsx:350`）与草案出发卡的五次（`frontend/src/trial/mobile/DraftDepartureCard.tsx:132`、`:155`、`:201`、`:248`、`:287`），旅客那条提交路径不在名单里。`MissionCockpit` 的地图读只在 `[journeyId, refresh, identityTick]` 变化时发生（`frontend/src/trial/mobile/MissionCockpit.tsx:250`），`refresh` 又只由该事件加一（同文件 `:261`），所以接受成功后地图拿着出发前的空答不动。

**已补**：在 `MobilePlanWorkbench.tsx` 的 `commitJourneyDeparture` 返回校验之后发出 `window.dispatchEvent(new CustomEvent("citynexus:plans-updated", { detail: journeyId }))` —— 现读落点 `frontend/src/trial/mobile/MobilePlanWorkbench.tsx:258`（提交调用在同文件 `:249`），注释写的是为什么：地图的点是挂载时读一次，390 实测 ACTIVE 的 journey 地图仍写 0 处，而同一版计划的六站就在 `places` 里；上面那句 `refresh()` 只重取本工作台。同代 `npx tsc -p tsconfig.check.json --noEmit` RC=0。这一格还没算闭上 —— 补完之后那一趟真机走查的读数写在下一节，绿了才撤 §31 的「未满足」，不绿就继续照 §31 的写法记。

## 38. 本晚四趟走查臂与还开着的那一格（逐臂读数，不合并）

| 臂 | 视口/库/收据 | 走到哪 | 地图层读数 |
| --- | --- | --- | --- |
| A（守卫前） | 390x844，`citynexus_v3_gozero_1026.db`，`armA-hy3-map-planned-390.txt` | `departure/commit` 200、`start` 200，journey `064ff631…` ACTIVE，计划 `24a70a0a…` 五条活动带 place | 「地图地点 0 处 · 高德地点 5 处」；PLANNED_TAGS 0；`MISS load-map` |
| B（守卫后、重取线前） | 390x844，同库，`armB-390-map-planned.txt` | `departure/commit` 200（t=468.1）、`start` 200，journey `8e2f7b90…` ACTIVE，计划 `4495fc16…` 六条活动带 place；库内进程现读该 journey 的投影 = 6 枚 `origin=PLAN_ACTIVITY / WGS84 / MATCHED / READY_FOR_NATIVE_PLAN` | 「地图地点 0 处 · 高德地点 6 处」；PLANNED_TAGS 0、LIST_ITEMS 0、PINS 0、CANVAS 0；reload 后同形；`MAP_CALLS []`（当时还没装逐次读数器） |
| C（装了读数器） | 430x932，同库，`map-planned-430-r46.txt` | `departure/commit` 422（营业时间冲突），journey `f49a9114…` 未 ACTIVE | 每一次 map-places `200 / candidates=0 / first=null`（含 reload 三次）；屏上「0 处 / 高德 6 处」 |
| D（重取线后） | 390x844，同库，`map-planned-390-r46.txt` | `departure/commit` 422，journey `142b19e1-b037-476d-a31d-6246deeaf9e7` 未 ACTIVE（探针仍在 replan 循环里） | 未到地图层 |

**还开着的那一格只有一处**：ACTIVE 的 journey 在浏览器里到底收到过什么。B 臂是 ACTIVE 且服务端投影现读有 6 枚，但那一年没装逐次读数器；C/D 两臂装了读数器却没走到 ACTIVE。C 臂顺带证了一件好事 —— 没有 active plan 时 `map-places` 返回 0 枚是正确的，屏上那六枚「高德地点」全来自研究线索，不是计划的站。

**为什么不能靠"再走一趟"就补上**：模型每趟给的排程不同，`departure/commit` 是否被营业时间闸门拒（`PLACE_CLOSED`，§38 下一条）是掷硬币；而一次重启后端就把身份弄丢（§39 第 4 条），所以每一臂都要从零走完整趟（约十分钟）。本晚四臂两次穿过出发门、两次被拒，穿过的那两次一次没读数器、一次没重取线。下一臂（若跑）的判据已预先写死在 §37 末段，不事后挑读数。

## 39. KNOWN_BLOCKERS（现尖，逐条带坐标与下一步）

1. **`PLACE_CLOSED` 的拒答没有可点的修正动作**（本晚实测两次，其中一次连回三拍）。flash 模型那一趟（`trial/results/20261026_gozero/map-planned-390-r46-flashloop.txt`）里 `departure/commit` 每拍 `http_status=422`，点名两处用餐安排「在你排的这段时间不开放」，同拍 `freeze-routes` 却回 `http_status=200`，于是「按讨论的方向重新安排」把同一版方案原样再交一次，句子逐字复发三轮。读侧原因成形：`applyReplan` 只搬 `gaps.rows` 里已经带提议时段的行（`frontend/src/trial/mobile/DraftDepartureCard.tsx:183-186`），而算提议时段的那扇门目前只为"赶路不够"这类 hop 写 `proposed_start/proposed_end`（`backend/app/agent/goal_travel_gaps.py:185`）；`PLACE_CLOSED` 在 `departureGaps.ts:309` 只被翻成一句人话，没接动作。**下一步不用重新调查**：prepare 已经把每站的 `OpeningCheck(sequence_no, title, verdict, reason_code, window, source_text)` 算好（`backend/app/agent/goal_preparation.py:158-167`）并随 `task["prepared_plan"]["result"]["opening_checks"]` 存进任务（同文件 `:426-427`），travel-gaps 按同一 `sequence_no` 把"到达时间在窗口外"的行提议到窗口内即可，沿用它自己的上界拒发规则（`LAST_PRACTICAL_HOUR = 22`，`goal_travel_gaps.py:44`），前端 `GapRow` 已能渲染「planned→proposed」那一句（`departureGaps.ts:484`、`:501`）。本刀没动它：它跨两扇门（后端提议 + 行 id 映射 + 回归），而模型每趟给的排程不同、屏上不一定复现，深夜开这一刀会把地图和它一起做成半件。
2. **平板 `USER_VERIFIED=PENDING`** —— 要主人亲机上 10 吋/11 吋那档，代理自测不算。
3. **课堂随机城市池 0/3** —— 本地库 `simulation_public_city_snapshots` 现读 0 行；Codex 的 PR #56 那侧在补原生城市事实（其正文自报北京 40 POI/3 几何边、杭州 32/3、苏州 31/3、南京 32/2 仍 BLOCKED），未落本线前课堂上仍可能抽到没有快照的城。
4. **重启身份回不来**（本晚两次实测）：启动器每次用 `secrets.token_hex(32)` 现造 `CITYNEXUS_TRAVELER_AUTH_SECRET`（`trial/human_walk/_restart_gozero_backend_r1.py:82`），换一次进程，旧 bearer 与浏览器 sessionStorage 一起失效，profile 也带不回签名（即已记的 #332）。这条直接决定屏证的形状：**每换一代产品码就得整趟重走一遍**（本晚走了三趟 390），所以任何"改一行看一屏"的想法在这条修好前都不成立。
5. **两条 e2e spec 未执行**（要 `npm run dev` 那档带后端的栈）：`frontend/e2e/revolution-amap-research-ui.spec.ts`（本刀改了它 `:128` 钉的那句文案）与 `revolution-sim-traveller.spec.ts`、`revolution-workspace-actions.spec.ts`（各自读 `加载地图`、`rev-workspace-place-list`，`revolution-workspace-actions.spec.ts:266`）。我只逐条读了它们对哪些字符串有断言并据此改文案，**没有跑过它们**。
6. **选中面 49 条红 + 9 errors 属预先存在**：具名对拍见 §35（现尖独有新红 零枚）；其中 `test_in_transit_reroute` 那条已定位到 simulation 合并带来的 `settings` 桩缺 `simulation_enabled`（§34），归那条线修。

## 40. 臂 D 的读数（2026-10-27 00:01 本地，补 §38 表里那一行）

`trial/results/20261026_gozero/map-planned-390-r46.txt`（profile `_chrome_gozero_map51`，journey `142b19e1-b037-476d-a31d-6246deeaf9e7`，带 §37 的重取线）。这臂仍没穿过出发门：`departure/commit` `http_status=422`，屏上拒答现读为两种因由并列 —— 「两段安排之间留的赶路时间不够（1 段）」与「前门大街 + 全聚德(前门店)晚餐在你排的这段时间不开放」，并各自给了动作（前者指「在出发待办里把后一项的开始时间挪晚，或把前一项的结束时间挪早」，这句是 `departureGaps.ts` 里 `INSUFFICIENT_TRAVEL_GAP` 那一支给的可按动作）；journey 未 ACTIVE。

逐次读数器给的是：`MAP_READS_EVERY` 每一次 `GET …/map-places` 均 `http_status=200, candidates=0, first=null`；地图层 `MAP_COUNT_LINE` 「地图地点 0 处 · 高德地点 7 处」、`MAP_PLANNED_TAGS 0`、`MAP_LIST_ITEMS 0`。与臂 C 同形，且都是**正确**行为：没有 active plan 就没有 `PLAN_ACTIVITY` 点，七枚「高德地点」来自研究线索。

所以 §38 那一格照旧开着，且现在有了明确的收法（不是再赌一趟模型）：拿 §33 那条新回归已经证明的服务端投影，在浏览器里补一次 ACTIVE journey 的 `map-places` 应答读数 —— 判据仍是 §37 末段那两格（`candidates` 等于活动数、`first.origin="PLAN_ACTIVITY"`、`MAP_PLANNED_TAGS` 与活动数相等）。下一次后端重启、或主人亲机走一遍任意一趟已 ACTIVE 的行程（390 或 430），这两格就能一次收掉。

## 41. 下一条阻塞的可执行配方（本晚没开这一刀，坐标已查全）

`§38` 第 1 条缺的不是判据而是"能把被点名的那一行挪好"。现读已确认材料都在行自己身上，所以不需要再问任何 provider：

- 每站当天开放与否的判定随身带在活动行上：`Activity.metadata_json` 里的 `opening_on_date` 是 `{"verdict", "reason_code", "window", "weekday", "defers_to_notice", "source_text"}`（写入点 `backend/app/agent/goal_preparation.py:343-346`）。
- 到达时间落在来源给的窗口之外时，判定就是 `TIME_OUTSIDE_WINDOW` 且 `window=[开门分, 关门分]`（两条臂都有：带星期规则那支 `backend/app/agent/goal_opening_date.py:264-266`，只报小时不报星期那支 `:284-287`）。
- 出"可挪的行"这一步照抄赶路那一支已有的形制即可：`day_index/slot_index` 取自 `task["prepared_plan"]["schedule"][sequence_no-1]`，并且先核对行上的钟点与卡片送来的钟点一致才发（`backend/app/agent/goal_travel_gaps.py:167-191`，其中 `:176-179` 就是那道 `SCHEDULE_ALIGNMENT_UNVERIFIED` 对齐闸）。位移量 `wanted = timedelta(minutes=window[0] - 到达分钟)`（允许为负＝挪早），时长不变；两条上界沿用同文件的 `LAST_PRACTICAL_HOUR = 22`（`:44`）与 `window[1]`（越窗即不发，宁缺勿造）。
- **必须一并改的一处**：`travel_gap_answer` 在 `not facts` 时就 `return {..., "rows": [], "reason_code": "MOBILITY_NOT_FROZEN"}`（`backend/app/agent/goal_travel_gaps.py:105-110`）——营业窗口的行与路线证据无关，这条早退会把新行整批吞掉；要么把窗口行在早退之前算好并带进那个 return，要么把早退改成只压制 hop 行。`rows: [] if blocked else out_rows`（`:196`）同理：跨夜的 hop 被挡时不该抹掉"晚餐挪早"这一行，这一处属于同一条要改的语义，改前先定口径。
- 卡片那一侧不需要新代码：`applyReplan` 就是按 `gaps.rows` 的 `day_index/slot_index` 合并 `proposed_start/proposed_end` 再走同一条保存门（`frontend/src/trial/mobile/DraftDepartureCard.tsx:183-193`），而 `GapRow` 早已带这两枚字段（`frontend/src/trial/mobile/departureGaps.ts:484`）。

为什么本晚不开：它同时改一门的早退语义与"被挡时发不发部分行"的口径（要裁），而这两点只能在真机反复过出发门才验得清；今晚四臂里两臂被拒两次通过，一次重启后端还丢一次身份（`§39` 第 4 条）。留成一条按上去就能做的单，比留半刀安全。

## 42. E 臂读数，以及把走查卡住的那一格从"产品缺陷"改判成"量具时序"

E 臂（`trial/human_walk/_map_walk_r47.mjs` → 收据 `map-planned-390-r47.txt`，journey `90eb846a-1eb0-4ba7-9d21-234987a9516f`、goal-task `72851eac-6a94-4290-99dd-1f1ee841fd0d`）新加的补救腿按得动：`HIT ask-refusal-2 true` / `ASK_REFUSAL_SENT 2 t=601.3`、`HIT ask-refusal-3 true` / `ASK_REFUSAL_SENT 3 t=670.7`，即把屏上那句拒答原样发给 Agent 再要求只改被点名的几处。门仍拒：`departure/commit` `http_status=422`，最后一拍只剩一种因由（「两段安排之间留的赶路时间不够（1 段）。在出发待办里把后一项的开始时间挪晚，或把前一项的结束时间挪早…」），`STATE t=899.4 {"inUse":false}`。地图层与 C/D 同形：`MAP_READS_EVERY` 每一次 `http_status=200, candidates=0, first=null`，屏上「地图地点 0 处 · 高德地点 7 处」、`MAP_PLANNED_TAGS 0`、`MAP_LIST_ITEMS 0` —— 没有 active plan 就是 0 枚，这一条是正确行为。

**更正 §41 的一处猜测。** 我把这一版被拒的计划（plan `23c2803b…` 状态 CANDIDATE、7 条活动、`mobility_evidence_json` 里 `facts` 有货）连同库里真实的 `JourneyMission.intent_json.goal_task.prepared_plan.schedule`（同样 7 枚）在进程内喂给赶路那扇门（`backend/app/agent/goal_travel_gaps.py` 的 `travel_gap_answer`），它**给得出行**：`hops` 里 `天安门广场漫游 → 故宫博物院` 短 18 分钟；`rows[0] = {day_index: 0, slot_index: 1, title: 故宫博物院（午门进·神武门出）, planned 11:00–12:00 → proposed 11:18–12:18, extra_minutes: 18, direct_cause: true}`，`frozen true`、`reason_code null`。我第一次跑出 `rows 0 / SCHEDULE_ALIGNMENT_UNVERIFIED` 是因为我自己传了空 `schedule`，那道对齐闸（`:176-179`）照实拒发——是闸在工作，不是缺陷。所以 §41 里"`rows: [] if blocked` 会把行整批吞掉"这一句对本例不成立（本例 `blocked` 为空），那条语义留作待查，但不再当作走查卡住的原因。

**走查真正卡住的那一格是量具的时序。** 卡片在按下「按讨论的方向重新安排」后要发一次 `travelGaps` GET 才把应用键摆出来（`frontend/src/trial/mobile/DraftDepartureCard.tsx:226` 取数、`:344` 仅 `planShown` 时渲染 `rev-v3-replan-apply`），而探针只等了 2.5 秒就判它不可见——日志上就是每拍 `HIT replan-N true` 之后没有 `REPLAN_APPLIED`，于是同一版被拒计划被一遍遍再选。已改：按下之后最长再等 20 秒（`trial/human_walk/_map_walk_r48.mjs`），F 臂正在跑，判据不变（`REPLAN_APPLIED` 出现 → 出发门 `http_status=200` → 地图层 `MAP_READS_EVERY` 出现 `candidates` 等于活动数且 `first.origin="PLAN_ACTIVITY"`、`MAP_PLANNED_TAGS` 同数）。

## 43. F 臂：等满 20 秒仍没等到应用键，缺口位置因此收窄

F 臂（`trial/human_walk/_map_walk_r48.mjs`，profile `_chrome_gozero_r48`，journey `1ab22a90-54b9-441e-a067-b5fd350bbb2b`）把 §42 那处时序改掉：按下「按讨论的方向重新安排」之后最长再等 20 秒才判应用键是否可见。读数：**仍然没有** `REPLAN_APPLIED`，`departure/commit` 依旧 `http_status=422`，journey 未 ACTIVE。

于是缺口从"门算不出可挪的行"收窄到一处具体的连接：门本身算得出（§42 用同一版被拒计划 + 库里真实 schedule 进程内跑 `travel_gap_answer` 得到 `rows[0]` 故宫 11:00–12:00 → 11:18–12:18、`reason_code null`），卡片上的应用键要 `planShown` 才渲染（`frontend/src/trial/mobile/DraftDepartureCard.tsx:344`），而 `gaps` 只在冻结那一步顺带取回（同文件 `:226`）、被拒之后没有任何一条路径再取它 —— 旅客看到的正是这句「在出发待办里把后一项的开始时间挪晚」却摸不到那个待办的应用键。下一刀的落点因此是**一行**：出发门拒绝之后，对同一枚 plan 再取一次 `travelGaps` 并把卡片切到 `planShown`（或让 422 的答复里带出可应用的行），而不是再改门的算法。

本晚到此为止的状态：`§31` 那格（接受后地图刷新）服务端与前端两处代码都在尖上（`25d5d418f8` 及前四笔），ACTIVE 那一屏的逐次应答读数仍未取到，因为它先得穿过出发门；`MAP_READS_EVERY` 这个量具已经装好，任何一趟走到 ACTIVE 的走查（或你亲机在任意已 ACTIVE 的行程上点一次「地图」）都能一次收掉。

## 44. 出发门之后走不到应用键的确切链条（收口本晚，交下一刀）

现读把这条链完整摊开，四臂卡的就是它：

1. 出发门拒绝后，工作台上出现的「根据路线重新安排」是 `frontend/src/trial/mobile/MobilePlanWorkbench.tsx:348-349`，它只做一件事：广播 `citynexus:replan-requested`。
2. 收到这个事件的是草案出发卡：`frontend/src/trial/mobile/DraftDepartureCard.tsx:261-263` —— 若卡上的 `rev-v3-replan` 这枚按钮存在就替旅客点它，**不存在则改去 `verifyRoutes()`**（重新核实并顺带取回赶路答复）。
3. `rev-v3-replan` 的渲染条件是 `gaps.rows.length > 0 && !planShown`（`frontend/src/trial/mobile/DraftDepartureCard.tsx:342`），应用键 `rev-v3-replan-apply` 只在 `planShown` 之后出现（`:344`）。
4. `gaps` 只有两个来源：卡自己 `verifyRoutes` 成功后那次取数（`:226`），或挂载时那个"已冻结就补读"的效应（`:80-88`），而后者要求 `result.mobility_frozen` 为真 —— 现读两处相互拉扯：准备那一步存进任务的答复把 `mobility_frozen` 写成 False（`backend/app/agent/goal_preparation.py:426`），卡片挂载时又是从这份存储答复重建 `result`（`DraftDepartureCard.tsx:76`，同一次重建还会 `setPlanShown(false)`、`setGaps(null)`）。

四臂里每被拒一次，探针都按了第 1 步那枚工作台按钮（`HIT replan-N true`），第 2 步因此走的是 `verifyRoutes()` 那一支，可是紧接着卡片又被 `:76` 的效应整块复位（一次 `refresh`/事件都会重跑），所以始终没有一次把 `planShown` 留住到应用键出现 —— 屏上就停在"叫你把开始时间挪晚"而摸不到挪的那枚键。**这是真实旅客会撞到的卡点，不是探针的错**；但两股因由（存 `mobility_frozen:false` 还是复位 `planShown`）到底哪一股先咬，需要一次针对性复现：在同一次拒绝之后连按两次工作台那枚按钮并盯 `rev-v3-replan` 是否出现，就能把两股分开。修法各自都是一行级（要么冻结答复里带上真实 `mobility_frozen`，要么复位时保留 `planShown`），不在本晚开刀。

本晚交付状态：地图读侧与署名/坐标系/重取四处代码改动已在尖上（远端 `06f280b1f6`），§31 那一格的屏证仍按 §37/§43 的判据待收。

## 45. 出发门过了：浏览器确实收到 6 枚计划点，缺口换到"两套 id 对不上"这一格

G 臂（`trial/human_walk/_map_walk_r49.mjs` → `map-planned-390-r49.txt`，journey `9b997fbd-e81b-480e-b2c2-2e332fa44bc5`、goal-task `c7eb2996-9aa6-436d-b10f-3d016ccf880a`）第一次同时满足两件事：`departure/commit` `http_status=200`，且**逐次读数器亲眼看到浏览器拿到计划点**：

- `MAP_READS_EVERY` 末段：`{"http_status":200,"candidates":6,"first":{"candidate_id":"real-place-dc53719dde4…","origin":"PLAN_ACTIVITY","coordinate_system":"WGS84","region_status":"MATCHED","selection_state":"READY_FOR_NATIVE_PLAN"}}`，reload 之后的 `RELOAD_MAP_READS` 三次同形。
- 库里同代现读：`journeys.status=PLANNED`、`active_plan_version_id=6a606ab3-9fe8-4122-b93a-aa4eb4e09796`、该版 6 条活动全部带 `place_id`；`JourneyMission…prepared_plan.result.mobility_frozen = true`（§44 猜的"存成 false 所以不补读"在这一版不成立）。
- 屏上仍旧：`MAP_COUNT_LINE 「地图地点 0 处 · 高德地点 6 处」`、`MAP_PLANNED_TAGS 0`、`MAP_LIST_ITEMS 0`，reload 后同形。

**所以 §36 的撤回只撤对了一半，真正的因由现在有据可查——是两套 id 命名空间：**

| 处 | 现读值 |
| --- | --- |
| 草案槽位 `draft_artifact.days[].slots[].place_id` | `amap:B000A81CB2`、`amap:B000A8UIN8` … 形如 `amap:<poi>` |
| 计划活动 `activities.place_id` | `real-place-dc53719dde41c9cb48b7b9b6` … |
| 两者交集 | 0 |

前端"已排入日程"的判子只按 id 相等（`MissionCockpit.tsx` 里 `draftPlaceIds.has(point.candidate_id)`，`:297-304`），而计划点的 `candidate_id` 是 `real-place-…`，草案给的是 `amap:…` ⇒ 永远不匹配，于是可见集只剩 55 枚研究线索里那 6 枚同名站（`id` 就是 `amap:…`、CRS 按供应商推成 GCJ02），落到「高德地点」列表、既不上图也没有「已排入当前方案」。**这正是本项目早已记过的老坑（同一物理地点两套 id，只按 id 比会静默匹配不到），本晚它换了个位置复现。**

**改法（已落尖 `f2f65020b9`）**：① `MissionCockpit.tsx` 的 `allMapPoints` 里，凡研究线索的 `id`/`provider_object_id` 等于某枚 `PLAN_ACTIVITY` 点的 `external_id`（库里现读 `places.external_id` 正是 `amap:B000A8UIN8` 这种形制，逐字可用），就不再列它——同一处站点不画两遍；② 行程判子改为跨命名空间桥接：先收草案槽的 id，再把"外部 id 已被排进草案"的那枚计划点自己的 id 也放进去；`WorkspaceMapPoint` 补 `external_id?: string`。`npx tsc -p tsconfig.check.json --noEmit` RC=0。屏证：H 臂（`_map_walk_r50.mjs`，profile `_chrome_gozero_r50`）在跑，判据沿用 §37 那两格（`MAP_PLANNED_TAGS` 与 `MAP_LIST_ITEMS` 应等于活动数、计数行应变成「地图地点 N 处」），不绿就照实继续挂 §31。

## 46. 勘误一处（§45 里的行号坐标写错，现读改回）

§45 写「前端"已排入日程"的判子只按 id 相等（`MissionCockpit.tsx` 里 `draftPlaceIds.has(point.candidate_id)`，`:297-304`）」——那三个行号是我凭上一段的排版估的，现读纠正：这条判子在 `frontend/src/trial/mobile/MissionCockpit.tsx:317`（`itineraryMapPoints` 那个 `useMemo` 的第一行条件）。

受影响范围只有这一处坐标；§45 的其余读数（`departure/commit http_status=200`、`MAP_READS_EVERY candidates=6 / origin=PLAN_ACTIVITY / WGS84`、草案槽 `amap:B000A81CB2` 对活动 `real-place-dc53719dde41c9cb48b7b9b6` 交集为 0、屏上「地图地点 0 处 · 高德地点 6 处」）都是同一时代现读取到的，逐字不改。判据本身也不受影响：`:317` 与它下面的 `defaultMapIds`、`photoPriorityIds` 用的都是同一个 `draftPlaceIds`，所以 §45 ②那处桥接改的正是这三处共同的输入。

同时记两条同代新读数，避免下一位再猜：H 臂（`map-planned-390-r50.txt`，journey `6d653155-12e2-4a3a-8e6a-46d7461708c1`）根本没走到出发门——`prepare-plan` 连回 `http_status=422`（round 2 内第 1 到 11 次保存全被拒），这一形态与 §38 那条"保存被拒"属另一族，本晚未展开；I 臂（`_map_walk_r51.mjs`，430×932，profile `_chrome_gozero_r51`）带着 §45 的桥接在跑，判据仍是 §37 那两格。
## 47. 选用门为什么打不开：现库现算的一格，和我自己仪表的一处截断

J 臂没走到 ACTIVE。这一格不再靠猜——加了一支只读仪表 `trial/human_walk/_read_plan_selectability_r1.py`
（sqlite URI `mode=ro`，不写一个字节），对 J 臂那趟 `journey_id=1acb10a6-c234-4765-a88a-4bd56f0985f7`
与候选 `plan_version_id=1da498bd-ff88-48f4-a5c5-ed3c3557beee` 现读现算，读数如下（UTC 17:29）：

| 格 | 现读值 |
| --- | --- |
| 旅程状态／活动计划 | `status=DRAFT`、`active_plan_version_id=null` |
| 候选状态 | `status=CANDIDATE`、`lifecycle=ACTIVE`、`source=MANUAL` |
| 冻结证据 | `snapshot_id=9229e777-…`、`expires_at=None` ⇒ `stale=False` |
| 权威门 | `authority_blocker='UNRESOLVED_ACTIVITY_FACTS'` ⇒ `selectable=False` |
| 未决事实构成 | `{"ADMISSION_PRICE": 6, "PLACE_REQUIRED": 1}`，`authority_state=COST_UNKNOWN_ACCEPTED` |
| 活动／地点 | 活动 7 项、`place_id` 齐全 6 处 |

于是「选用这份方案」这一按为什么从来不存在，有了确切的落点：`backend/app/services.py:992` 里
`selectable = lifecycle != STANDBY and not stale and authority_blocker is None`，而
`backend/app/services.py:742` 那段先返回——`compose_source == SELECTED_GOAL_DRAFT` 且
`backend/app/services.py:743` 在 `unresolved_facts` 里看见 `PLACE_REQUIRED`。6 行票价没有参与否决
（`authority_state` 已是 `COST_UNKNOWN_ACCEPTED`），挡住全局的只有那 1 行「确认了时间、还没排地点」。

**我自己的仪表有一处截断，得先勘误。** J 臂（以及它前面几臂）打印的是
`gaps.slice(0, 2)`，而 `.rev-plan-gap` 在 DOM 里先排 `MobilePlanWorkbench.tsx:134` 的费用带与
`:149` 的时段带，再排 `:375` 那句真正的 `selectionBlocker(plan)`。所以我从前几臂读到的"卡片只说等待
正式计划"是**被我自己切掉的**：那句真正的原因一直在屏上，只是没进我的收据。§44 里"被拒后卡片取不到
可挪行"这个说法，凡是指"卡片没说清原因"的部分，按这条作废。

仍然成立的产品缺口是另一半：**原因说清了，但那句话旁边没有一个可按的动作**。
`rev-plan-replan`（`:349`）只在 `selectBlocked` 为真时渲染，而这个状态只能由一次失败的 select 写入——
select 键在 `selectable=false` 时根本不渲染，所以那条路永远点不亮。旅客停在"另有 1 段时间还没有确定
地点"这一句前面，没有一条从这里出发的路。

本刀按这个缺口落下（未动服务端权威门，也不替它放宽）：
`frontend/src/trial/mobile/MobilePlanWorkbench.tsx:70` 新增 `placeRowsStillOpen()`，判据与服务端
`backend/app/services.py:742` 用同样两个 kind（`PLACE_REQUIRED`／`SOURCE_IDENTITY`），不正则屏上文案；
`:376` 在原因句下面渲染 `data-testid="rev-plan-open-place-explore"`「补上没排地点的那段时间 →」，
走的是组件已有的 `onExplore`（同文件 `:357`/`:361` 已用同一个动作，不是新造的门）。
`npx tsc -p tsconfig.check.json --noEmit` 退出码 0。

K 臂（`trial/human_walk/_plan_hand_r53.mjs`，profile `_chrome_gozero_r52`，收据
`trial/results/20261026_gozero/plan-open-hand-390-r53.txt`）想直接回到 J 臂那趟去量这一按，但没走到：
屏上 `TRIPS 行程` 那一格给的是「这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到
进度。」——cookie 还在、bearer 随 sessionStorage 一起没了，且这句话旁边只给了
「课堂演示：进入示例行程开始探索 →」这一条动作，没有"回到这趟行程"。这是 #332 那一格的又一个现场读数。
所以 K 臂对本刀的证词是 **NOT-STARTED**，改由 L 臂
（`trial/human_walk/_plan_hand_r54.mjs`，同一份走查骨架，收据名 `plan-open-hand-390-r54.txt`）从空白整趟
重走到那一屏来量。L 臂在跑，判据先写死在这里：`PLAN_GAPS_ALL` 要含那句 selectionBlocker 原文、
`PLAN_SELECT=0`、`PLAN_HAND=1`、`HAND_PRESSED true`（中心命中测试），且 `AFTER_HAND_HAS_EXPLORE true`。
四条不齐就不写"修好了"。

另记一件现场事实，与代码无关但会影响今晚后面所有臂：`df` 现读 D 卷可用
**354 MB／100% 满**（17:32）。我不动任何人的树，只把这一格挂着——新 profile 一枚约 39 MB，还能起两臂，
再起就要先腾。
