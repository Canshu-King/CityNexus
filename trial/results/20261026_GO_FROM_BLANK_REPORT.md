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
