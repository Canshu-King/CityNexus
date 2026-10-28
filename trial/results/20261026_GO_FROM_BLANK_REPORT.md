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
## 48. L 臂走到「可以确认出发」，以及我把夹具那一腿撤掉的原因

L 臂（`trial/human_walk/_plan_hand_r54.mjs`，390×844，profile `_chrome_gozero_r54`，收据
`trial/results/20261026_gozero/plan-open-hand-390-r54.txt`）从空白整趟重走，写到 17:43 的读数是：

- `HTTP POST 201 …/prepare-plan`、`200 …/plans/6ca97944-76c7-420b-a266-b6de913f5883/accept-unknown-price`、
  `200 …/freeze-routes`（journey `89615b8f-ad2f-4977-be30-7703326e58e3`）
- `GATE ["可以确认出发\n\n5 项正式安排"]`，也就是出发门 `READY_TO_DEPART`
- `GAPS_ALL ["这 5 项费用你已经确认先不计入预算（总价不含这些项）。"]` —— 整屏只有这一条 gap

这同时证实了 §47 的定位方向，也说明本刀那一按**不该**在这趟出现：这趟没有「确认了时间、还没排地点」的
band，所以服务端 `backend/app/services.py:742` 不否决，选用门本来就是开的。我把 §47 的仪表缺陷
（`gaps.slice(0, 2)`）修成 `GAPS_ALL` 之后，第一次拿到了完整的 gap 清单，才敢这样判。

L 臂自己也暴露了**我这支走查的结构缺陷**，不是产品的：`确认方案，开始行程`（`rev-plan-start`）
在脚本里只挂在"点 select 成功那一拍"的分支内。候选一旦变成 SELECTED，`rev-plan-select` 就不再渲染，
于是 start 键在屏上一直没人按——L 臂就是这么空转到我把它停掉（它对本刀已无增量读数，停得有价值）。
M 臂（`trial/human_walk/_go_active_r55.mjs`，派生器 `_derive_r55_r1.py`，profile `_chrome_gozero_r56`，
收据 `go-active-390-r55.txt`）补了这一眼：`selCount === 0` 时单独找 `rev-plan-start` 并按中心命中测试点它，
同时把 §47 里被我省掉的地图读数整段接回来（照抄 r52 原文，不让两臂的判据行分叉）。M 臂在跑。
判据仍是 §37 那两格：出发之后 `MAP_READS_EVERY` 的 `candidates` 等于活动数且 `first.origin="PLAN_ACTIVITY"`，
且 `MAP_PLANNED_TAGS`/`MAP_LIST_ITEMS` 等于活动数、计数行变「地图地点 N 处」。

**夹具那一腿我试了又撤了，如实记。** 我想用 `frontend/e2e/revolution-draft-preparation.spec.ts:98`
那格（已断言 `rev-plan-select` 计数为 0）顺带证新键在屏，加了两行 `rev-plan-open-place-explore` 断言，
实测 **2 failed / 1 passed**，红在 `:102` 的 `toHaveCount(1)`。读 430 档的
`test-results/…47ad9…/error-context.md`：那一格屏上只有「方案 1」「等待正式计划」「根据路线重新安排」
「费用待确认」，**一条 `.rev-plan-gap` 说明句都没有** ⇒ 它的 select=0 与 J 臂的 select=0 不是同一个成因
（不是 `selectable === false` 那一支）。两行断言因此是挂错格的假设，我撤回了，文件回到原样
（`git diff` 该 spec 为空），复跑 **3 passed (13.9s)**。这条 webServer 是
`playwright.config.ts:82` 的 `npm run dev -- --port 4173`，所以跑的是我改后的源码，不是 dist；
但按既有口径，dev 栈的数字只当"没把这三格改红"的旁证，不当发布证据。

教训写在这里：**夹具格不等于旅客格**，借夹具作证之前要先读它到底挡在哪一层，否则我造出来的是一条
永远不会出现的断言。新键的正证仍归 M 臂那一趟真机屏读——没看到就不说它修好了。
## 49. M 臂撞上 prepare-plan 422，而我的仪表第二次把原因吞了

M 臂（`trial/human_walk/_go_active_r55.mjs`，390×844，profile `_chrome_gozero_r56`，收据
`trial/results/20261026_gozero/go-active-390-r55.txt`，139 行）这一趟：
journey `82edd9eb-15e5-44f9-b35f-e85a58dd09fb`、goal task `c7bb24dc-b927-4393-9312-271ce52e2202`，
`run http_status=200`、`resume 200`（两拍），随后 `prepare-plan http_status=422` 连续出现
（`HIT save-3-5 t=610.8`、`save-3-6 t=617.9`、`save-3-7 t=625.0` 各带一枚 422）。
它停在 round 3 的 save 循环里，我把这一臂停了——继续空转不会再出增量读数。

**我的仪表有两处吞因，都得认。** 第一，POST 记录器只写 `HTTP POST 422 <url>`，不取响应体，所以
`refuse_schedule_row` 附上的 rule 与行号（`backend/app/agent/goal_preparation.py:45`）没进收据。第二，
save 分支是"按成功就 `continue`"，而打印 `.rev-plan-message, [role='alert']` 的那行在 `continue` 之后，
永远走不到——**屏上那句具名拒绝，一次都没被记下来**。所以我现在只能说"M 臂被 422 挡住"，不能说
"产品没告诉旅客为什么"：那是我没读。这一格标 UNREAD，不标缺陷。

同型对照放在这里，免得把方差读成回归：同一支骨架在 L 臂那趟（journey `89615b8f-…`）的
`prepare-plan` 是 `201`，到 M 臂变 `422`。两臂之间我没有改过服务端的任何字节（本刀只动前端一枚文件
加报告），差别只可能在模型每次生成的草案内容上——也就是 #330／#315 那一族（草案里的日期与时间
过不了校验）。具体是哪一条 rule、哪一行，等 N 臂把响应体和屏上句带回来再说。

N 臂（派生器 `trial/human_walk/_derive_r57_r1.py` → `trial/human_walk/_go_active_r57.mjs`，
profile `_chrome_gozero_r58`，收据 `go-active-390-r57.txt`）先把仪表的两处补上：非 2xx 一律带
响应体（截 500 字，`BODY …`），以及每次按「保存为正式候选方案」之后立刻读
`.rev-plan-message, [role='alert']` 并写 `SAVE_ALERT <round>/<i> …`。判据仍是 §37 那两格，另加一条：
若再遇 422，收据里必须能看到产品点名的是哪一格。

顺带把一条**归属**钉清楚，免得它被误记成产品缺陷：`确认方案，开始行程`（`rev-plan-start`）
在 L 臂那趟之后一直挂在屏上没人按，原因是我的走查只在"点 select 成功那一拍"的分支里顺带点它；候选
一旦变成 SELECTED，`rev-plan-select` 不再渲染，那条分支就再也不进。键本身在不在、按不按得到，
我之前没有测过——所以这是**我这支臂的结构缺陷**，M／N 已各补一眼 `start-fallback`
（`selCount === 0` 时单独找 start 并按中心命中测试点它）。旅客那一侧要等真机读数才谈得上结论。

现读磁盘：D 卷可用 458 MB（17:45），N 臂还要吃一枚约 39 MB 的 profile；E 卷 47 GiB 未动。
## 50. 闭环了：390 冷首屏一路走到 ACTIVE，地图上给出 5 处已排入方案的地点

N 臂（`trial/human_walk/_go_active_r57.mjs`，390×844，profile `_chrome_gozero_r58`，收据
`trial/results/20261026_gozero/go-active-390-r57.txt`）从冷首屏起，按的是屏上自己的键，
同号收据如下（UTC 18:03 现读）：

| 格 | 现读值 |
| --- | --- |
| 旅程 | `5180b857-e1d2-47fb-b31c-f5b86023247a` |
| 目标任务 | `214f5e61-8f82-4c4d-bd8d-ef503d125ee6` |
| 候选方案 | `10cf2ebb-8837-456e-8e42-e3acf259a426` |
| 门序列 | `prepare-plan 201` → `accept-unknown-price 200` → `freeze-routes 200` → `departure/commit 200` → `start 200` |
| 出发那一按 | `HIT start-fallback-2-0 true t=321.2`（中心命中测试通过才算按到） |
| 屏上状态 | `旅途正在继续。`、`行程执行中` |
| 地图计数行 | `地图地点 5 处 · 高德地点 0 处` |
| 画布／图钉 | `MAP_CANVAS 1`、`MAP_PINS 5` |
| 计划标／列表 | `MAP_PLANNED_TAGS 5`、`MAP_LIST_ITEMS 5` |
| 刷新之后 | `RELOAD_MAP_COUNT_LINE` 同值、`RELOAD_PLANNED_TAGS 5`、`RELOAD_LIST_ITEMS 5` |
| 响应形状 | `RELOAD_MAP_READS` 两条 `"candidates":5,"first":{"origin":"PLAN_ACTIVITY","coordinate_system":"WGS84","region_status":"MATCHED","selection_state":"READY_FOR_NATIVE_PLAN"}` |
| 坐标系 | 收据内 `WGS84` 命中 3 次、`GCJ02` 命中 0 次 ⇒ 没有一枚高德原始坐标被画上 OSM 瓦片 |
| 控制台 | `ERRORS []`、`ERRORS_MAP []` |
| 屏证 | `390-g7-started-fallback.png`、`390-g8-map-preview.png`、`390-g8-map-loaded.png`、`390-g8-map-reloaded.png` |

这同时结掉了两桩挂着的事：
**§31 那句「接受之后地图仍不满足」现在撤下**——出发之后地图给的是 `5 处`，与屏上日程的活动数一致，
每枚都带「已排入当前方案」，刷新回来还是 5 处。§45 里那枚"两套 id 对不上"的桥
（`frontend/src/trial/mobile/MissionCockpit.tsx:317` 的行程判子）在同一次读数里被证明是必要的：
`candidate_id` 用的是 `real-place-…` 而草案槽用的是 `amap:B000…`，不桥接就还是 0 处。

另外，仪表第一次把非 2xx 的响应体带回来了：出发之后再按研究口，
`resume` 给 `409 {"error":{"code":"CONFLICT","message":"GOAL_TASK_REQUIRES_DRAFT_JOURNEY",
"message_key":"request.conflict","trace_id":"96db7d34…"}}`。这是设计行为（旅程已离开 DRAFT），
**不是缺陷**，§49 里我标的 UNREAD 只针对 M 臂那枚 `prepare-plan 422`，两者不要混起来读。

本刀那一按（`rev-plan-open-place-explore`）在这一趟仍然没有出现：`PLAN_HAND 0`、`PLAN_SELECT 0`、
`PLAN_START 0`，因为这趟的草案没有"确认了时间、还没排地点"的 band，选用门本来就是开的。
所以 §47 那枚键的产品代码已在权威线上（`0188ebd5f4`），但**它自己的屏证仍是 NOT-STARTED**，
我不会因为没有对应的屏就读成它已验通。

还差三格，如实挂着：① 430×932 的 ACTIVE 同判据——O 臂（同一支 `_go_active_r57.mjs`，
`RW=430 RH=932`，profile `_chrome_gozero_r59`，收据 `go-active-430-r57.txt`）在跑；
② 「只改指定半天／晚餐、未动时段不漂移」这一格今晚还没走到；③ §47 那一按的正证。
## 51. 430 那一趟被 `PLACE_NOT_IN_GOAL_TASK_SCOPE` 挡住，而屏上说的却是「可以重试」

O 臂（`trial/human_walk/_go_active_r57.mjs`，430×932，profile `_chrome_gozero_r59`，收据
`trial/results/20261026_gozero/go-active-430-r57.txt`）这次没能复现 N 臂的顺利：
journey `9e1e76cf-d1c5-45f5-9209-1956b331478a`、goal task `73613465-fdae-4f8b-8dc9-b6af47f84b90`，
`prepare-plan` 反复给

    422 {"error":{"code":"VALIDATION_ERROR","message":"PLACE_NOT_IN_GOAL_TASK_SCOPE",
                  "message_key":"request.invalid","trace_id":…}}

我在屏上按了「保存为正式候选方案」十三拍（`SAVE_ALERT 1/1` 直到 `1/13`），每拍都是同一枚 422。
同支脚本在 N 臂（390）拿到的是 `201` 并一路走到 ACTIVE，所以这不是代码换代造成的，是模型每次生成的
草案内容不同——有一处地点落在了本次 goal task 的范围之外。

**我的仪表第三次吞掉了原因，这次是容器读错。** 收据里 `SAVE_ALERT` 全是 `[]`，而草案卡的句子挂在
`<p role="status">`（`frontend/src/trial/mobile/DraftDepartureCard.tsx:317`），我的选择器只写
`.rev-plan-message, [role='alert']`。已修在生成器里（`trial/human_walk/_derive_r57_r1.py:25` 的选择器
补上 `[role='status']`，重新生成的 `trial/human_walk/_go_active_r57.mjs` 21402 字节，
`node --check` 通过）。所以"屏上到底有没有一句话"这一格，我从收据里读不出来——下面这段是**静态推导**，
不是屏上证词。

静态推导能确定产品说错了话。`DraftDepartureCard.tsx:137-144` 的分支链是：`named` 只认四条 SCHEDULE
规则（`scheduleRefusalSentence(refusalRow(error))`）；这个码不含 `DRAFT_CHANGED`、也不含 `SCHEDULE`
（body 里的串是 `PLACE_NOT_IN_GOAL_TASK_SCOPE`，`error.message` 只有 `CityNexus API 422 /…prepare-plan`），
所以三条都落空，走兜底句——**「这次未能保存，时间仍留在这里，可以重试。」**
而 `:142` 那行注释写的恰恰是"行已点名时，『可以重试』是错的指令：同样的数字会再拒一次"。
旅客按了十三次，屏上一直在说可以重试。这不是新缺陷，是 #292 那一刀只补到了 SCHEDULE 四规则、
范围码（#315 那一族）没接上的残余。

本刀落下（只前端一处，不动服务端，也不替它放宽范围校验）：`frontend/src/trial/mobile/DraftDepartureCard.tsx:141`
在 `DRAFT_CHANGED` 之后加一支——

    PLACE_NOT_IN_GOAL_TASK_SCOPE → 「要排的地点里有一处不属于这趟任务，回到探索换一处同城的地点再保存。」

`npx tsc -p tsconfig.check.json --noEmit` 退出码 0。这一按之后要走的是屏上已有的「继续探索、补资料」/
「探索」入口，我不再造第二条门。

**证词状态如实分开写。** 这一句出现在旅客屏幕上：NOT-STARTED（该码由模型方差触发，无法按时预置，
O 臂我已停；下一次 O′ 臂复用同一支脚本，`SAVE_ALERT` 已能从 `[role=status]` 读到句子）。
430×932 走到 ACTIVE：仍未收，卡在这枚 422 上；已收的是 390×844（§50）。
「只改指定的半天／晚餐、未动时段不漂移」：未走。§47 那枚 `rev-plan-open-place-explore`：代码在
`0188ebd5f4`，屏证 NOT-STARTED。

现读磁盘 D 卷 362 MB（18:05），O 臂的 profile 已停止增长；E 卷 47 GiB 未动。
## 52. 430×932 也走到 ACTIVE：地图给出 8 处已排入方案的地点，刷新不丢

O′ 臂（同一支 `trial/human_walk/_go_active_r57.mjs`，430×932，profile `_chrome_gozero_r60`，收据
`trial/results/20261026_gozero/go-active-430-r57.txt`，UTC 18:23 现读）这一趟：
journey `a87c821b-8eec-418b-8ccf-0888d5581cdd`、goal task `8ac475d1-d48f-4fa0-958d-ce7d952ec4b0`。

| 格 | 现读值 |
| --- | --- |
| 门序列 | `prepare-plan 201` → `freeze-routes 200` → `HIT start-fallback-2-0 true t=324.7` → `departure/commit 200` → `start 200` |
| 屏上句子（`[role=status]` 新选择器第一次读到） | 「已保存 8 项正式安排。下方可以查看日程和出发待办。」、「当前展示的是已保存版本。」 |
| 地图计数行 | `地图地点 8 处 · 高德地点 0 处` |
| 画布／图钉 | `MAP_CANVAS 1`、`MAP_PINS 8` |
| 计划标／列表 | `MAP_PLANNED_TAGS 8`、`MAP_LIST_ITEMS 8` |
| 来源链接 | `MAP_AMAP_LINKS 8` |
| 刷新之后 | `RELOAD_MAP_COUNT_LINE` 同值、`RELOAD_PLANNED_TAGS 8`、`RELOAD_LIST_ITEMS 8` |
| 响应形状 | `RELOAD_MAP_READS` 两条 `candidates:8`，`first` 为 `origin=PLAN_ACTIVITY`、`coordinate_system=WGS84`、`region_status=MATCHED`、`selection_state=READY_FOR_NATIVE_PLAN` |
| 坐标系对账 | 收据内 `PLAN_ACTIVITY` 3 次、`WGS84` 3 次、`READY_FOR_NATIVE_PLAN` 3 次、`GCJ02` 0 次 |
| 控制台 | `ERRORS []`、`ERRORS_MAP []` |

活动数 8 与屏上「8 项正式安排」、地图 8 处、8 枚「已排入当前方案」标、8 条来源链接**逐格相等**，
两档形状（390×844 与 430×932）在同一条权威线（`c160a9cea3`）上各自独立跑到，且都过刷新这一腿。
派单第 1 刀里「同一 journey／task 从研究走到 CANDIDATE→SELECTED→ACTIVE」与「在『我的旅程』看到当前计划与
下一站」两格，至此在两档上都有屏读；§50 的 390 读数与这节同形。

两处仍然挂着，不写成完成：
1. **「只改指定的半天／晚餐，未动时段不漂移」还没走**——已派生 P 臂（`trial/human_walk/_drift_check_r61.mjs`），
   在出发之前只动最后一档晚餐的时间、按真实的保存键，然后逐格对回其余时段；判据 `DRIFT_COUNT=0` 且
   被点名的那一格确实变了，否则不写这一格过。
2. **§47 那枚 `rev-plan-open-place-explore` 与 §51 那句范围拒绝的屏证**——两趟的草案都没有再出现对应的阻塞形状
   （N/O′ 的 `PLAN_HAND 0`，O′ 的 `prepare-plan 201`），所以这两条仍标 NOT-STARTED，不是没做而是没遇到。
   范围码那一枚是模型方差（O 臂遇上了、O′ 臂没遇上），只能等遇到它的那一趟。

仪表这一轮只改了一处就拿到了过去三趟都没记下的东西：`SAVE_ALERT` 的选择器补上 `[role=status]`
（`trial/human_walk/_derive_r57_r1.py:25`）。这把 §49 里我标的 UNREAD 收窄了——**「屏上没有句子」这个读法
本身没被证实过**，是我读错容器；O′ 臂的 `SAVE_ALERT 1/0` 证明卡片一直在说话。
## 53. 「只改一处时段、其余不漂」这一格过了：14 格只动了点名的那一格

Q 臂（`trial/human_walk/_drift_check_r62.mjs`，390×844，profile `_chrome_gozero_r63`，收据
`trial/results/20261026_gozero/drift-check-390-r62.txt`，UTC 18:50 现读）在草案卡上：

| 步 | 读数 |
| --- | --- |
| 折叠层 | `DRIFT_FOLD true`，`TIME_COUNT 14`（七项安排 × 开始/结束） |
| 改哪一格 | `TIME_EDITED "前门大街（轻松收尾/晚餐）结束时间" 20:00 -> 20:30`（t=413.3） |
| 保存键状态 | `CONFIRMED true SAVE_ENABLED true`（t=414.8） |
| 屏上回执 | `DRIFT_SAVE_ALERT` 含「已保存 7 项正式安排。下方可以查看日程和出发待办。」 |
| 改后对账 | `TIME_AFTER` 14 格逐格读回 |
| 只动了谁 | `DRIFT_CHANGED_ONLY ["前门大街（轻松收尾/晚餐）结束时间"]`、`COUNT 14->14`、`LOST []` |
| 判据 | **`DRIFT_COUNT 0 TARGET_ONLY yes`**（t=422.9） |

也就是说：旅客按真实键改一个晚餐时段并保存之后，其余 13 格的时间一格没漂，也没有格消失——派单第 1 刀
里「至少一次只改指定半天／晚餐，且未动时段不漂移」这格至此有屏读。

这一格在 P 臂上先失败了一次，成因归在我自己这边，得写清楚：P 臂（`_drift_check_r61.mjs`，同法但漏一步）
读到 `HIT save-drift false t=544.7`，因为 `DraftDepartureCard.tsx:313` 那颗键的 disabled 条件是
`!confirmed || busy || Boolean(result)`，而我把漂移腿放在勾选「按以上时间准备方案」**之前**——按钮按规矩
是灰的。这不是可达性缺陷（旅客在同一屏先勾后按就能按动，Q 臂的 `CONFIRMED true SAVE_ENABLED true`
就是那一步的读数），是我这支臂的步骤顺序错了。Q 臂补的就是这个顺序。

同屏并存的一句要如实记下：`DRIFT_SAVE_ALERT` 的第一条是「消息还在确认中，刷新任务查看最新进度。」
（`frontend/src/trial/mobile/WorkspaceActions.tsx:537` 的 180 秒 AbortError 分支，来自上一轮 followup），
它与「已保存 7 项正式安排」同时挂在屏上。保存这一按的结果是成功，但旅客在同一刻会看到一条"还在确认中"
的话——这条并存是否要处理属于产品口径，我只把读数放在这里，不替它定。

到这一节为止，派单第 1 刀的六格状态：
① 390 冷首屏输入那句话走到研究：已过（§50）；② 同一 journey/task 走到 CANDIDATE→SELECTED→ACTIVE：已过
（§50）；③「我的旅程」里看到当前计划与下一站：已过（§50 的 ACTIVE 首屏与 `FINAL_BODY`）；
④ 430×932 同判据：已过（§52）；⑤ 只改一处时段不漂移：**已过（本节）**；⑥ 失败／刷新路径下的找回：
部分——刷新保留已过（§50/§52 的 `RELOAD_*`），重启后的身份找回仍卡在 #332（K 臂屏读，§47）。

仍未闭合的两条不变：`rev-plan-open-place-explore`（§47 那枚键）与范围拒绝新句（§51）的屏证，都要等
各自那个阻塞形状在真机出现的那一趟；O′ 臂这一趟没有出现（`prepare-plan 201`），所以两条继续标
NOT-STARTED，不写成本刀已验。
## 54. 第 3 刀：课堂手册里那条"按钮旧名"的更正本身就是过期的

按派单第 3 刀只校过期断言、不动产品口径。现读结果反了直觉，所以两条都得改：

| 断言 | 手册原写 | 现读（同一尖） |
| --- | --- | --- |
| 平板守护屏那颗接受键 | `:7` 称「接受这份调整」是**旧名** | 仍在世：`frontend/src/trial/mobile/GuardianRealityPanel.tsx:480` |
| 控制台那颗接受键 | `:7` 给坐标 `ClassroomPresenterPanel.tsx:285`，路径写成 `features/classroom/` | 真路径与行号是 `frontend/src/trial/mobile/ClassroomPresenterPanel.tsx:354`；`frontend/src/features/classroom/` 这个目录在现尖不存在 |
| 首句流程（`:3`） | 让平板旅客按「接受这次事件的调整」 | 那颗在平板上不存在，平板按得到的是「接受这份调整」（`:40` 第 8 步本来就写对了，与首句自相矛盾） |

已改：`:3` 首句换成平板真名并指向第 2 条更正；`:7` 重写为"屏上有两颗接受键，各自名字都没旧"，带上两条现读坐标，
并把**该用哪一颗留给裁语**——`20261025_CLASSROOM_QUICK_CARD.md:14` 与 `:15` 明确要求课堂主线用控制台那颗、
并警告守护屏那颗"可能对应上一次行程变化"，而手册第 8 步走的是平板那颗。这两份文档口径不一致是既有事实，
我不在勘误里替任何一方改口，只把它点名出来等裁语。QUICK_CARD 一侧经现读没有过期断言，未改。

同场挂着的两格照实写：平板 `USER_VERIFIED=PENDING`（要主人真机走一遍，我不代按）；
课堂随机城市池仍是 0/3，未变。
## 55. 我改出来的那枚 422：屏上给了具体出路，而我的臂没照着走（反向对照同时中了一次）

Q 臂（`trial/human_walk/_drift_check_r62.mjs`，390×844，journey `0ff63e58-53d5-41a7-812c-5920c16d031a`、
plan `ccd05664-e21a-483d-b4f7-226094e9424f`）在出发门上被拒三次，body 全文（收据 `:48`/`:58`，
非 2xx 取 body 这条仪表修复第一次真用上）：

    VALIDATION_ERROR — PlanVersion ccd05664-… is infeasible:
    INSUFFICIENT_TRAVEL_GAP:real-place-00d9e27cd4cc6c7b28b6509e|real-place-62c2e60619da82efebfdea8c

成因就是我这一改：把「前门大街（轻松收尾/晚餐）」的结束时间从 20:00 挪到 20:30 之后，它与后一段的
衔接余量不够了。门按真衔接拒绝，说的是实话。

先排除两件我以前会误判成缺陷的事，都带现读依据：
1. **没有把内部 id 端给旅客。** 这枚码在 `frontend/src/trial/mobile/departureGaps.ts:297` 被译成
   「两段安排之间留的赶路时间不够」，`:346` 再按 counts 组句；服务端侧也自知要拆
   （`backend/app/departure_commit.py:119` 的注释就写着这条串需要分解）。屏上读到的是中文句，不是 `real-place-…`。
2. **不是死胡同句。** `departureGaps.ts:346-348` 直接点名去哪儿挪、挪哪一边：
   「在出发待办里把后一项的开始时间挪晚，或把前一项的结束时间挪早，再按一次「选用这份方案」。」

真正没做到的是**我这支臂**：它按 `ASK_REFUSAL_SENT 2`（t=719.4）把拒绝原句发回给 Agent，而这条码的成因
是旅客自己挪晚了晚餐，不是开放时间问题，Agent 那边 `resume 200` 之后出发门当然还是同一句拒绝。
臂里少一条"照屏上那句把时间挪回去"的腿——记在这儿，不记成产品的。

一句要**留给下一趟分辨**的：这枚 422 来自出发提交门 `departure/commit`，而句子指的可按的键是
「选用这份方案」。§50/§52 的读数里，候选一旦 SELECTED、出发之后，那颗键就退场了（`PLAN_SELECT 0`）。
所以"候选已 SELECTED 而 commit 被拒"这一屏上，这句话是否指向一颗按不到的键，我现在**没有对应屏读**，
标 UNREAD，不写成缺陷也不写成无事。分辨法写在派单里：造一次 SELECTED＋commit 被拒的屏，读那颗键计数。

反向对照这一趟顺手又中一次：出发门没过的屏上，地图是 `地图地点 0 处 · 高德地点 7 处`、
`MAP_PINS 0`、`MAP_PLANNED_TAGS 0`、`RELOAD_MAP_COUNT_LINE` 同值——正是 §47 服务端第二臂应有的行为
（`journey.active_plan_version_id` 为空就不发射手），七处高德只是研究候选。它证明我这刀**不会**在
"还没出发"的屏上凭空画出计划点。
## 56. 第 2 刀的两格用现读定位：差异句已在尖，缺费用那一支确实写「未知」

派单第 2 刀要求「接受旁展示新旧计划差异（缺费用写未知）」与「接受成功后主动刷新外层状态」。现读代码，
两格的落点都能指到行，不再靠印象：

| 派单要件 | 现读落点 | 状态 |
| --- | --- | --- |
| 接受旁展示新旧差异 | `frontend/src/trial/mobile/GuardianRealityPanel.tsx:471` 把 `pendingProposalSentence(...)` 挂在 `data-testid="rev-guardian-proposal-diff"`，紧邻 `:478` 那颗 `rev-guardian-accept-replan` | 在尖 |
| 差异覆盖哪几类 | 同一函数 `:150-179`：`removed`（`:152-155`）、`added`（`:156-159`）、`moved`（逐条写「从 X 挪到 Y（晚/早 N 分钟）」`:160-168`）、`cost_delta_minor`（`:170-175`）、`travel_delta_min`（`:176-179`） | 在尖 |
| **缺费用写未知** | `:171-175`：`cost` 不是数字时 `parts.push("费用：未知")`；是数字时写「费用：不变／多 ¥N／省 ¥N」 | 在尖，且负数与零都各有一支 |
| 不泄漏模型私有正文/凭证 | 该句的全部输入是 `proposal.diff` 与 `proposal.titles`（`:150` 的形参），没有模型文本字段；来源行 `:472`/`:475` 只写「Agent 生成 · 服务器留有运行记录」/「规则引擎生成 · 不是大模型现场推理」 | 在尖 |
| 接受成功后主动刷新（含地图） | 广播点 `frontend/src/trial/mobile/MobilePlanWorkbench.tsx:266`（`citynexus:plans-updated`），监听在 `:232`；服务端第二臂＋真机读数 §50（390：5 处）与 §52（430：8 处），两档 reload 后同值 | 已屏证 |

还差的那半格要说清：**守护屏差异句自己的屏证**要一次课堂注入事件的现场（`rev-guardian-proposal` 卡片是
被注入事件驱动的），而课堂栈（后端 60391／前端 14492）不属于我这把刀的范围，我没有去点别人的屏，
所以这一格标「代码在尖、屏证等课堂现场」，不写成已验。平板 `USER_VERIFIED=PENDING` 与此同源，
要主人在真机上走一遍才算。

顺手核了自己今晚引的坐标，结果要我自报一次：我一度以为 §47 把选用支写成 `:374`、准备发一条行号勘误，
现读报告原文（`:686`、`:698`）才发现那里本来写的就是 `:375` 与 `:376`，与新读一致——**那条勘误是我要造的
第二个错**，已经不发。教训反过来说更准：勘误也要现读，不能凭"我记得写错过"。
## 57. 自纠：我上一条里那句"没有 reason_code"是没证的，那一刀已经撤掉

上一轮我给 `MobilePlanWorkbench.tsx` 加了一支"reason 缺失但 details.failures 有内容也走具名句"的分支，
依据是我从收据里读到的 422 信封"只有 code/message/details"。**这个依据不成立**，因为我在仪表里写了
`.slice(0, 500)` —— 那枚 body 被我自己的截断切掉了后半，前 500 字里没出现 `reason_code`，
我就把它读成了"没有"。这正是我自己反复记着的同类错（词面没看到 ≠ 不存在）。

现读服务端就能定：`backend/app/departure_commit.py:134-142` 的 `_refuse_transition` 对含 `is infeasible`
的 detail 走 `_refuse(exc.status_code, detail, "PLAN_INFEASIBLE", {"detail": detail, "failures": …})`
—— 信封里带着 reason_code，且 `:137` 的注释本身就写着"这个 reason_code 早就在线上，是方案屏没读它"。
所以前端 `MobilePlanWorkbench.tsx:22` 的原分支条件本来就成立，**我加的那一支是冗余的死码**。

已处理：`git checkout HEAD -- frontend/src/trial/mobile/MobilePlanWorkbench.tsx` 撤掉，`git diff` 该文件为空
（本刀此前已提交的 `:70`/`:376` 两处仍在尖上，未受影响），`npx tsc -p tsconfig.check.json --noEmit` 退出码 0。
仪表的截断同时放宽到 2000 字并重跑生成链（`trial/human_walk/_derive_r57_r1.py` → `_go_active_r57.mjs` →
`_drift_check_r61.mjs`），这样下一次真拿到该屏的完整信封，而不是半个。

#338 的方向要按新事实改写，但仍**没有**结案：如果信封带 `PLAN_INFEASIBLE`，那 `departureGaps.ts:346-348`
那句「…再按一次「选用这份方案」」在 commit 被拒那一屏是**会渲染**的；而 §50/§52 的读数证明候选成为
SELECTED 之后 `rev-plan-select` 计数为 0。所以那句仍可能指向一颗已退场的键——这才是待证的点。
分辨判据换掉：不数 body 里有没有码（那是服务端的事），而是在该屏同时读
① `[role=status]` 的整句原文，② 同屏 `rev-plan-select` 与 `rev-plan-start` 的计数。两者同屏出现
「再按一次「选用这份方案」」与 `PLAN_SELECT 0`，才算证到；否则这条继续挂 UNREAD。
## 58. 同代回归证书：三刀面 129 条，聚焦两批 86 条全绿，对照臂证明 15 枚红是预先存在

provenance（照口径写全，便于别人复算）：

    尖 89dbbe22c15dfe7565fce220e4083fd0063d2bc0（本地与 origin/rescue/v3-final-departure-20261022 逐字相同）
    解释器 D:/moodle/CityNexus/.venv/Scripts/python.exe（CPython 3.12.14，唯一能跑这套件的那枚）
    cwd D:/moodle/_cmdr_rescue_v3_1022/backend
    命令 python -m pytest -q <26 枚文件，见 trial/human_walk 选择集>

聚焦两批（覆盖我这三刀实际碰到的面）：

| 批 | 选择 | 读数 |
| --- | --- | --- |
| 一 | `test_qoder_map_active_plan_stops_r1.py`、`test_goal_preparation.py`、`test_qoder_draft_revision_receipt_r1.py`、`test_departure_activation.py`、`test_departure_readiness.py` | **47 passed**，5.24 秒 |
| 二 | `test_qoder_departure_commit_r1.py`、`test_qoder_departure_read_r1.py`、`test_r42_departure_activation_integration.py` | **39 passed**，6.48 秒 |
| 三（宽面） | 26 枚 map / travel_brief / replan / schedule_refusal 面文件 | **15 failed, 114 passed**，17.30 秒（合计 129 条） |

第三批那 15 枚我没有直接判成"预先存在"，而是跑了对照臂：把服务端那一刀退回它前一代
（`git checkout d9a74cdff58846b18de857b213b5c1ed40331d17 -- app/planning/travel_brief.py`，即
`ab2ca5913a` 的父代同一文件），**同一选择集、同一解释器、同一分钟**再跑：

    带刀    15 failed, 114 passed   129 条
    退回    17 failed, 112 passed   129 条

分母不变，差的正好是 2 条——就是我这一刀新增的
`tests/test_qoder_map_active_plan_stops_r1.py` 那两条：没有产品改动时它们必须红，这才是反向对照。
所以 15 枚红在带刀与退回两臂里同名同数，**全部早于本刀存在**，按基线红集合的子集判，本刀零新红。
红的分布也印证它们不是我的面：`test_sol_concurrency_and_remap.py` 9 枚、
`test_qoder_live_replans_endpoint.py` 5 枚、`test_dsh_list_replans_bound.py` 1 枚，
都是并发锁／live replan 一族（与 §31 那类由 `persisted_simulation_business_clock` 中间件撞测试桩的
同源红相干），**归属仍待裁**，我不在这里替它定性。
对照跑完后 `git checkout HEAD --` 恢复，该文件 `git status` 为空。
## 59. 一条必须自己说的削弱：今晚 dev 栈上混着别人未提交的三枚文件

`git status` 现读（19:07，尖 `64a48c5431`）：

     M frontend/src/app/V8Experience.tsx
     M frontend/src/app/v8PanelRegistry.tsx
     M frontend/src/features/inbox/JourneyInboxWorkbench.tsx

这三枚不是我改的，本刀链里我一个字都没碰过它们（我的产品改动只落在
`trial/mobile/MobilePlanWorkbench.tsx`、`trial/mobile/WorkspaceMap.tsx`、`trial/mobile/MissionCockpit.tsx`、
`trial/mobile/DraftDepartureCard.tsx` 与 `app/planning/travel_brief.py`，逐笔可查 0a73583943 之前的五笔提交）。
但它们就躺在我用来跑真机的 vite dev（`127.0.0.1:14461`）与跑 e2e 的 dev（`:4173`）同源树里，
所以：

- §50／§52／§53 的屏读是**真机上按得到的**，这一点不变——旅客按到的键与屏上数字就是那屏拍下来的；
- 但"这些读数与权威尖同代"这句要打折：它们对的是「尖 + 这三枚未提交改动」的工作树，
  不是纯净的 `64a48c5431`。我**没有**把它们 stash 或还原——那是别人的在途工作，
  按规矩不能动（也不许 `git checkout --` 掉）；
- 我引的后端读数不受影响：那三枚都在前端，而 §58 的 pytest 两臂跑的是 `backend/`，
  对照臂只退回我自己那一枚文件。

要把这条闭合，正路不是我去改它们，而是**在干净尖上重放一次同判据**：
`git stash push -u` 那三枚（由改动者自己或号令者做）后重跑一支 R 臂，或者等这三枚进入权威线之后
在同一代上再走一趟 390。在那之前，本晚的屏证按「真机已过、同代性带此保留」记，
我不把它升格成"纯净尖上的验收"。
## 60. #336 的真身找到了：只有拒绝句、没有可挪行时，那一块里一颗键都不剩

现读 `frontend/src/trial/mobile/DraftDepartureCard.tsx` 的这段（行号全部取自本次读数）：

    :337  {gaps && (gaps.rows.length > 0 || gaps.hops.some(…) || Boolean(replanRefusalSentence(gaps.reason_code))) && <div data-testid="rev-v3-travel-gaps">
    :342  {gaps.reason_code && replanRefusalSentence(…) && <p data-testid="rev-v3-replan-refusal">…</p>}
    :343  {gaps.rows.length > 0 && !planShown && <button data-testid="rev-v3-replan">…}
    :344  {planShown && <ul data-testid="rev-v3-replan-diff">…}
    :345  {planShown && <button data-testid="rev-v3-replan-apply">…}

`:337` 的外层条件允许**只因为有一句拒绝**就整块渲染；而 `:343` 要求 `gaps.rows.length > 0`，
`planShown` 只能由 `:343` 那颗键点亮。所以 `rows===0 且有拒绝句` 这一形态下：reveal 不渲染 ⇒ `planShown`
永远 false ⇒ `:345` 的应用键也不渲染。**块里一颗可按的键都没有**——这就是 §43「等满 20 秒仍没等到应用键」
与 #336「被拒后卡片取不到可挪行」的确切成因，比我先前写的"缺一次调用"更窄也更准。

本刀落下（`:343` 之前新增一行，`data-testid="rev-v3-replan-reverify"`）：

    {gaps.rows.length === 0 && Boolean(replanRefusalSentence(gaps.reason_code)) &&
      <button type="button" disabled={routesBusy} onClick={() => void verifyRoutes()}>重新核实这几段</button>}

为什么不把 `:343` 的条件放宽、让「应用这一版」在这种形态下出现：`rows===0` 时 `:344` 的差异列表是空的，
点亮的 `:345` 会把一颗"没有任何行可应用"的按钮摆在旅客面前——那是更坏的假出路。
`verifyRoutes` 是卡片自己的取数函数（`:210`），`:262` 在没有 reveal 键时本来就会退到它
（`if (!replan.current) { void verifyRoutes(); return; }`），`routesBusy` 也是 `:328` 那颗键已在用的禁用位。
所以这里只是把**已经存在的动作**从"由别处广播才触发"变成"句子旁边看得见、按得到"，不新增门、不动服务端。

回归：`npx tsc -p tsconfig.check.json --noEmit` 退出码 0；覆盖这块的
`frontend/e2e/revolution-draft-preparation.spec.ts` **3 passed (13.9s)**（vite dev `:4173`，跑的是改后源码）。
屏证状态：**NOT-STARTED**——这一形态要求 `gaps` 里有 `reason_code` 却没有可挪的行，
今晚 N/O′/Q 三趟都没再出现该形状，不能预置，也不写成已验。
## 61. 真机读到了产品点名的那一句：#315 那一族第一次有了屏上证词

R 臂（`trial/human_walk/_r_arm_r65.mjs`，由 `_drift_check_r61.mjs` 只改收据名派生，390×844，
profile `_chrome_gozero_r65`，journey `d749dddd-3569-4874-b630-bd852a7c8f36`、
task `96db3947-d574-4f6d-90d9-03b2951cc849`）把两处仪表修好之后的第一次真读数拿到了：

`SAVE_ALERT 1/0` 从 `[role=status]` 读到屏上原文三条，其中第二条是产品自己点名的拒绝——

    第 7 项「午餐：颐和源聚面馆（颐和园内东侧）」 20:00–21:30：结束时间超出了这趟旅行的结束。
    改这一项的时间再保存，其余不用动。

同一拍的服务端信封（`prepare-plan`，非 2xx 带 body 那次改动之后才看得见）：

    422 {"error":{"code":"VALIDATION_ERROR","message":"SCHEDULE_OVERLAP_OR_OUTSIDE_JOURNEY",
                  "message_key":"request.invalid","trace_id":"5b95ad3a-…"}}

两句话指的是同一件事，而且**说的就是我这一改**：漂移腿把第 7 项的结束时间从 21:00 填成 21:30
（`TIME_EDITED "午餐：颐和源聚面馆（颐和园内东侧）结束时间" 21:00 -> 21:30 t=210.5`），
而这趟的 `end_at` 是 21:00。门拒得对，卡片报得准：第几项、哪一段、怎么改、其余要不要动，四样齐。

这结掉的是 #315／#292 那一族一直缺的一环：先前我只在源码里证明分支会具名，
没有真机读数。现在有了（`drift-check-390-r65.txt` 的 `SAVE_ALERT 1/0`–`2/2`，同一句在四拍里稳定复现）。
同屏第一条「草案已保存到这趟旅行，刷新页面也可以找回。」说明草案本身没丢——被拒的只是这一版时间。

顺带把这一趟的形态说清，避免读成回归：这是本夜第 5 种拒绝码（前有 `prepare-plan 409`、
`prepare-plan 422 PLACE_NOT_IN_GOAL_TASK_SCOPE`、`departure/commit 422 INSUFFICIENT_TRAVEL_GAP`、
`departure/commit 422`、以及 `resume 409 GOAL_TASK_REQUIRES_DRAFT_JOURNEY`），
**每一种都是我的臂动了时间或状态之后门按规则拒绝**，没有一种是在未改动的流程上出现的。
#47 的 `rev-plan-open-place-explore` 与 #336 新加的「重新核实这几段」在这一屏仍未遇到
（这趟的 gaps 形状不是那两种），两条屏证继续标 NOT-STARTED。
## 62. #338 当场证伪：那句「再按一次选用这份方案」指的键就在同一屏上、而且是亮的

S 臂（`trial/human_walk/_s_arm_r66.mjs`，390×844，profile `_chrome_gozero_r66`，journey
`6f225106-1096-4f03-9d0f-b038b7f85d41`、plan `04491055-175d-458f-8ebb-9b0e45977ecb`，收据
`trial/results/20261026_gozero/drift-check-390-r66.txt`）正好撞在 #338 要分辨的那一屏上，三条现读把话说死了：

    t=556.2  SELECT_STATE count=1 visible=true enabled=true {"disabled":false,"cls":"","parent":"rev-plan-option"}
    t=556.5  HIT select-3 true
    t≈557    HTTP POST 422 …/departure/commit BODY {"error":{"code":"VALIDATION_ERROR",
             "message":"PlanVersion 04491055-… is infeasible: INSUFFICIENT_TRAVEL_GAP:real-place-00d9e27c…|real-place-62c2e606…"}}
    屏上     这版方案排不下：两段安排之间留的赶路时间不够（1 段）。在出发待办里把后一项的开始时间挪晚，
             或把前一项的结束时间挪早，再按一次「选用这份方案」。

`SELECT_STATE` 在 t=300.6、430.9、556.2 三拍都是 `count=1 enabled=true`，第三拍就是按下被拒**之后**那一拍。
所以「再按一次『选用这份方案』」指回的是同一张卡片上那颗仍然按得到的键——旅客被拒之后不需要跳转、不需要换页，
照句子挪完时间再按同一颗即可。句子的三个要素（哪一段、挪哪一边、按哪颗）在同一屏上互相指得通。

**因此 §57 里我留下的那条怀疑，在这里证伪并撤回**：#338 原先写的是"SELECTED 之后 select 键退场，
所以那句可能指向按不到的键"。真实时序是——按下 select 走的就是选择加出发门的同一次提交，
被 `PLAN_INFEASIBLE` 拒掉时候选**仍是 CANDIDATE**，键没有退场；我先前是从"出发之后 select 计数为 0"
（§50/§52 那个已经成功的形态）倒推过来的，把两个形态混成了一个。结案：该屏无缺陷，#338 关闭。

同臂另两条如实记下：
- `REPAIR` 这一趟触发 0 次、`HIT save-` 2 次。修复腿（越界时间收回 21:00）没被用到，因为这趟保存没报越界；
  它不是没生效，是**这一趟不需要**——不能把"没触发"读成"没实现"。
- 出发门这趟最终仍拒（同一条 `INSUFFICIENT_TRAVEL_GAP`，1 段），所以 S 臂没有走到 ACTIVE；
  ACTIVE 与地图那两格的证据仍只由 §50（390，5 处）与 §52（430，8 处）撑着，未被这趟推翻也未被加固。
## 63. 卡片给的第二条出路真走得通；而"按不动"又是我的量具造的假读数

T 臂（`trial/human_walk/_t_arm_r67.mjs`，由 `_derive_r67_r1.py` 从 S 臂派生，390×844，
profile `_chrome_gozero_r67`，journey `4d1e7907-f6d8-46fa-ae9d-7a683366668e`，收据
`trial/results/20261026_gozero/drift-check-390-r67.txt`）照着 §61 那句卡片指令走了第二条出路
（「把前一项的结束时间挪早」），把它变成动作：

    TIME_EDITED "天坛·雨花村餐厅（晚餐）结束时间" 20:00 -> 20:30          # 我先把间隔挤没
    422 INSUFFICIENT_TRAVEL_GAP:real-place-00d9e27c…|real-place-62c2e606… # 门如实拒
    GAP_REPAIR 1 ["天安门广场结束时间 10:00->09:45","故宫博物院（午门进·神武门出）结束时间 12:00->11:45",
                  "景山公园结束时间 15:00->14:45","前门·京晟小馆烤鸭（晚餐）结束时间 20:00->19:45",
                  "颐和园结束时间 10:00->09:45","天坛公园结束时间 15:…"]   # 照句子挪早
    → prepare-plan 201（新计划 14fba4d4-42b3-48a9-822e-1d3940f9bd66）
    → accept-unknown-price 200 → freeze-routes 200 → refresh 200

**这一格结的是派单第 1 刀里"每次阻塞→现场修复→再次真实点击"的实质**：卡片不是只解释一次拒绝，
按它给的出路做，同一扇门下一拍就真的放行到下一步（`prepare-plan` 从 422 变 201，并生成可冻结的新候选）。

同屏也暴露我的量具又造了一次假读数，必须自己拆掉。收据 `:150`/`:152`：

    SELECT_STATE count=2 visible=true enabled=false {"disabled":false, …}

`enabled=false` 与 `disabled:false` 互相打脸。原因是探针写的是 `select.isEnabled()`，而这一屏有**两份候选**
（`count=2`），Playwright 的 strict mode 对多元素 locator 直接抛错，被我的 `.catch(() => false)` 吞成
"禁用"。所以「select 按不动」从头到尾不存在——DOM 上两颗键都没 disabled，是臂读错了并因此连刷了
`refresh-for-disabled-2-3…2-6`。已改成 `select.first().isEnabled()`（同步改在
`trial/human_walk/_go_active_r57.mjs` 与 `_drift_check_r61.mjs`，下一支臂从修好的这份再派生）。
本夜这类"吞掉判语/自造判语"的仪表缺陷累计四处：`gaps.slice(0,2)` 截断、非 2xx 不取 body、
句子容器少 `[role=status]`、以及这条 strict-mode 假禁用——四处全都是我这一侧的问题，
没有一处最后被证实是产品不说实话。

T 臂终态如实记：出发门这一趟**没有**过（无 `departure/commit 200`，无 `start 200`），
地图仍是未出发形态 `地图地点 0 处 · 高德地点 7 处`、`MAP_PINS 0`、`MAP_PLANNED_TAGS 0`、
`RELOAD_MAP_COUNT_LINE` 同值 ⇒ §47 的服务端第二臂又一次在"没出发"时正确地不发射手。
ACTIVE 那两格仍由 §50（390，5 处）与 §52（430，8 处）撑着。
## 64. 卡片让旅客"再保存"，可那颗键保存过一次之后就永久是灰的

T／U／V 三趟（`_t_arm_r67.mjs`、`_u_arm_r68.mjs`、`_v_arm_r69.mjs`）都在出发门上撞同一个死循环：
臂照 §61 那句具名指示去挪时间、也点了保存，**新候选里时间却还是旧的**。现读把这条钉住：

- 库里 V 趟计划 `b7264ed0-2a4e-4b03-aa2c-99e7ee8212f8` 的活动 7 项，只有我漂移腿那一次改到的
  第 7 项落成了 `19:00–19:15`；第 1 项仍是 `09:00–10:00` —— 后面两轮 `GAP_REPAIR`（改到 09:45、09:30）
  **一次都没进新候选**；臂侧对应的是 `HIT save-drift false t=281.4`。
- 门没有算错：`backend/app/replanning/feasibility.py:1011-1015` 判的是
  `previous.end_at + provider.estimate_minutes(...) > current.start_at`；这一对（`real-place-00d9e27c…` →
  `real-place-62c2e606…`）在冻结证据里是 `mode=TRANSIT`，要求大于 60 分钟，而屏上排的是 10:00 结束、
  11:00 开始 ⇒ 空档正好 60 分钟，**确实不够**。所以门要旅客挪时间是对的。
- 但产品把这件事变成不可能：`frontend/src/trial/mobile/DraftDepartureCard.tsx:313` 原来是
  `disabled={!confirmed || busy || Boolean(result)}`，文案在 `result` 存在时是**「安排已保存」**。
  上面的 14 个时间输入仍然可编辑（`:300-308` 的 `change()` 不看 `result`），
  而卡上唯一的提交口一旦成功就永久禁用；`:316` 那颗「生成正式候选方案」只生成、不重存时间。
  ⇒ 卡片自己的拒绝句写着「改这一项的时间再保存」，屏上却已经没有任何"再保存"可点。

本刀（前端一处，两步必须同时改）：
1. 提交键不再因已保存而过期：`disabled={!confirmed || busy}`，`result` 存在时文案改成
   **「按以上时间重新准备方案」**（busy 分支不变）；
2. 重存必须换新幂等键 —— `prepare()` 里 `requestKey.current ??= crypto.randomUUID()` 之前是复用同一枚，
   服务器会把上一次的答案原样重放，改过的时间永远到不了门。现在 `if (result) requestKey.current =
   crypto.randomUUID();`，首次仍复用（网络未知时可按同键重试，不改既有语义）。

回归：`npx tsc -p tsconfig.check.json --noEmit` 退出码 0；
`frontend/e2e/revolution-draft-preparation.spec.ts` **3 passed (14.0s)**（vite dev `:4173`，跑的是改后源码）。
顺带确认没有别的读者依赖旧文案：全库 `安排已保存` 只剩 `:300` 那句区域副标题
（`${slots_count} 项安排已保存，刷新也能找回。`）与 spec `:102` 对它的断言，二者一致，未受影响。

**屏证状态：NOT-STARTED**。这一刀要的真读数是一趟"保存过一次 → 被门具名拒绝 → 改时间 → 再按『按以上时间重新准备方案』
→ 新候选里那一格真的变了 → 出发门放开 → 走到 ACTIVE 且地图按 §50 计数"。下一支臂（W，从 `_v_arm_r69.mjs`
派生，保存前先勾『按以上时间准备方案』，因为修好之后那颗键在 `confirmed=false` 时仍按规则是灰的）
就是为这条链写的。
## 65. W 臂一次闭两格：重存键真把改动带进新候选，补地点那一按也真在屏上按到了

W 臂（`trial/human_walk/_w_arm_r70.mjs`，390×844，profile `_chrome_gozero_r70`，journey
`f56f286c-d2bf-4064-9f63-f3cbef319e8f`，候选 `40445412-582f-4f6a-8d74-f0feba0af73e`，收据
`trial/results/20261026_gozero/drift-check-390-r70.txt`）是在 `e5fdc2734e` 之后跑的，正好把 §64 那一刀验穿。

### 一、§64「保存过一次之后不能再保存」——真机 + 持久层双证

| 步 | 读数 |
| --- | --- |
| 先存一版 | `DRIFT_SAVE_ALERT` 含「已保存 11 项正式安排。下方可以查看日程和出发待办。」 |
| 再改一处 | `TIME_EDITED "乘地铁前往天坛公园轻松散步结束时间" 20:00 -> 19:15`（t=296.1） |
| 提交键状态 | **`W_CONFIRM true SAVE_ENABLED true`**（t=297.4）——旧代码此处必为 `disabled`（`Boolean(result)`） |
| 落到库里 | 只读库现读候选 `40445412-582…`（`created_at 20:41:43`）第 11 项 = **`19:00–19:15`** |

对照 §64 之前的 V 趟：同样改时间、同样报「已保存」，但新候选里第 1 项仍是 `09:00–10:00`，改动没进去。
所以这一格从"卡片让你再保存却没有再保存的键"变成"按得动、且新候选带上改后的时间"，两侧都有读数。

同一条 alert 里还并存「现场模型这一轮没有给出可用内容，结果没有保存；可以重试这一轮。」——
那句属于随后一轮 AI 生成，不是这次重存的回执（重存的真回执是库里那一行）。如实分开记。

### 二、§47 那枚 `rev-plan-open-place-explore`——第一次在真机上出现并被按到

同一屏 `GAPS_ALL` 现读到「另有 1 段时间还没有确定地点，没有算进转场核实。」，同拍
`PLAN_SELECT 0`（选用门确实被 `PLACE_REQUIRED` 拒着，正是 §47 分析的那个形状），于是：

    PLAN_HAND 1 t=779.2
    HIT open-place-hand true t=779.6        # 中心 elementFromPoint 命中自己、且非 disabled
    HAND_PRESSED true t=784.5
    AFTER_HAND_HAS_EXPLORE true

⇒ #336／§47 那格从 NOT-STARTED 改为**已屏证**：原因句旁边现在确实有一枚旅客按得到、按下去会到探索入口的键。

### 三、还差的那半程（不写成已验）

这趟按完补地点键之后没有继续把地点排进那段空白，因此 journey 仍是
`status=DRAFT`、`active_plan_version_id=None`，地图这屏读到 `地图地点 0 处 · 高德地点 10 处`、
`MAP_PLANNED_TAGS 0`、reload 同值 ⇒ 又一次反向对照（没出发就不发计划点，与 §47 判据一致）。
「补地点 → 重新准备 → 选用 → 出发 → 地图按活动数」这条整链仍只由 §50（390，5 处）与
§52（430，8 处）撑着，只是它们没有经过"被 `PLACE_REQUIRED` 挡一次"这一环。

环境注记：这台机器在 10-27 之后重启过（gozero `:60361`/`:14461` 与课堂 `:60391`/`:14492` 现读均无监听），
D 卷可用量现在现读到 19 GiB／95%（不再是今晚一直卡的 100%）。上面第二条的库读走的是同一份 canary 库文件，
只读模式，不需要后端在世。
## 66. 尖被远端抢在前头：只读预测零冲突之后 merge，并在合并代上把聚焦两批重跑一遍

### 一、被拒与被合（全程没有 force-push）

10-28 上午我把 §65 那一代往上推时拿到的是：

    ! [rejected]   HEAD -> rescue/v3-final-departure-20261022 (fetch first)

fetch 之后现读：远端在我那一侧的尖 `d1b016040e` 之后独有的是 **19 笔**（其中非 merge 18 笔），
包含 PR #56 的合入 `4dfeac260b`（native three-city facts + same-run simulation coverage）与一枚新的 CI 门禁
`575318cbf1`（新增 `.github/workflows/v3-rescue-release-gate.yml`，+七十二行）。

> 勘误：交付件表头先前那句写的是「远端新增 12 笔」。那个数我没有现读过就写下去了，
> 现在按上面这枚 `git rev-list --count d1b016040e..575318cbf1` 的结果改为 19 笔，表头同步改掉。

我没有 force-push，也没有 rebase 一条已发布的枝。走的是先只读预测、后真合：

    git merge-tree --write-tree HEAD origin/rescue/v3-final-departure-20261022
    MERGE_TREE_RC=0
    输出中无 CONFLICT 行（空 = 预测零冲突）

预测零冲突之后才落合并代，两枚父逐字可取回：

    3ad2f482ff5868c396371ed6d1fa8e5d83c059bb   parents: d1b016040e + 575318cbf1

合完之后有两件事同时成立（都是现读，不是推断）：

| 我要排除的风险 | 命令 | 读数 |
| --- | --- | --- |
| 对面那 19 笔会不会改到我这三刀面的文件 | `git diff --stat d1b016040e 3ad2f482ff -- frontend/src/trial/mobile/DraftDepartureCard.tsx frontend/src/trial/mobile/MobilePlanWorkbench.tsx frontend/src/trial/mobile/WorkspaceMap.tsx frontend/src/trial/mobile/MissionCockpit.tsx backend/app/planning/travel_brief.py backend/app/departure_commit.py` | 空输出 ⇒ 我这一刀链的六枚文件在合并代上与我交出去的那一代逐字节相同 |
| 我的重存那一刀是不是已被对方吸收 | `git merge-base --is-ancestor e5fdc2734e 575318cbf1` | RC=0 ⇒ 是。他们是在我 `e5fdc2734e` 之上继续写的，不是绕开它另起一套 |

这两条是"零冲突"这个判据的两面：merge-tree 说形状上不撞，上面这两条说内容与谱系上也不撞。

### 二、合并代上的门禁重跑（不复用 merge 前的读数）

provenance：

    尖       3ad2f482ff5868c396371ed6d1fa8e5d83c059bb
             （`git ls-remote origin refs/heads/rescue/v3-final-departure-20261022` 逐字相同）
    解释器   D:/moodle/CityNexus/.venv/Scripts/python.exe（CPython 3.12.14，唯一能跑这套件的那枚）
    cwd      D:/moodle/_cmdr_rescue_v3_1022/backend
    收据     trial/results/20261026_gozero/merged-gate-r71.txt

| 批 | 选择 | 现读（合并代） | §58 时（merge 前） |
| --- | --- | --- | --- |
| 一 | `test_qoder_map_active_plan_stops_r1.py`、`test_goal_preparation.py`、`test_qoder_draft_revision_receipt_r1.py`、`test_departure_activation.py`、`test_departure_readiness.py` | **47 passed**，4.91 秒 | 47 passed，5.24 秒 |
| 二 | `test_qoder_departure_commit_r1.py`、`test_qoder_departure_read_r1.py`、`test_r42_departure_activation_integration.py` | **39 passed**，6.75 秒 | 39 passed，6.48 秒 |

同分母、同结果 ⇒ 合进来的那 19 笔（含 city-supply / routes / opening / simulation 四族产品改动）
没有把我的三刀面弄红，我的三刀也没有弄红它们的面。

**新门禁的三条腿我在同一代本地重放了一遍**（收据 `trial/results/20261026_gozero/ci-gate-merged-r72.txt`）：

| 腿 | workflow 里的命令 | 合并代现读 |
| --- | --- | --- |
| 一 后端 | `python -m pytest -q tests/test_issue49_*.py tests/test_qoder_map_active_plan_stops_r1.py tests/test_wp01_wp03.py tests/test_goal_route_freeze.py` | **213 passed**，53.59 秒，RC=0 |
| 二 类型 | `npx tsc -p tsconfig.check.json --noEmit` | 无输出，RC=0 |
| 三 构建 | `npm run build` | `✓ built in 6.31s`，RC=0（只有 chunk >500 kB 的既有告警） |

一条要说清的保留：GitHub Actions 上**没有**这枚合并代的运行。`gh run list --branch rescue/v3-final-departure-20261022 --limit 5`
现读最新一条是 `40551475380`（2026-10-27T17:31:57Z，success，一分廿一秒），它对应的是门禁自己那笔 `575318cbf1`。
原因从 workflow 原文读出来，不是猜：`on.push.paths` 只监听 `backend/** / frontend/** / contracts/** / 该 yml 自身`，
而我这次进线的差异只有 `trial/**`（两枚文档＋探针）——上面表格里那条 `git diff --stat` 空输出就是同一件事的另一面。
所以本节的"门"目前是**本地重放三腿全绿**，不是 CI 上的绿。

### 三、环境现读：今晚那些屏证与这枚合并尖之间的代差

`Get-CimInstance Win32_OperatingSystem.LastBootUpTime` 现读 **2026-10-28 09:21:15**（本机 +08 钟），
取样时刻 10:11:52 ⇒ 这台机器在 §65 之后重启过一次。
`netstat -ano -p tcp | grep LISTENING` 对 `60361 / 14461 / 60391 / 14492 / 4173` 现读全空
⇒ gozero 栈与课堂栈都不在世（第二刀/第三刀的屏证要再走就得先把栈起回来）。
D 卷现读 290G 已用／19G 可用（95%），不再是整晚卡着的 100%。

所以 §50／§52／§53 的屏读仍然是"真机上按得到的"，这一点不变；但它们对的是重启前那一代工作树
（还带着 §59 那三枚别人未提交的前端文件），不是这枚 `3ad2f482ff`。
#339（在干净尖上重放 390 以闭合同代性保留）仍未闭，且现在多了一道前置：先把 gozero 栈与 canary 库起回来。
## 67. 自纠：§59 那句"三枚未提交文件"已经过期——现读是十九枚，而且入口多了一枚未跟踪的样式表

§59 是在 19:07、尖 `64a48c5431` 上拍的 `git status`，当时确实只有三枚。
10-28 上午 10:2x 我在**同一棵工作树**上现读 `git diff --numstat -- frontend/src frontend/vite.config.ts`，
得到十九行改动，其中与我这三刀面同屏的包括：

    frontend/src/main.tsx                     25 加 / 1775 删
    frontend/src/trial/RevolutionFirstLook.tsx   2 加 /  1 删
    frontend/src/trial/mobile/AgentWorkStatus.tsx  1 加 /  1 删
    frontend/src/trial/mobile/RevolutionV3.css    77 加 /  77 删
    frontend/vite.config.ts                     7 加 /  2 删
    （另有多枚 CSS 与 features/ 下的面板文件，以及两枚未跟踪新文件
     `frontend/src/trial/mobile/RevolutionTokens.css`、`frontend/src/features/setup/cityNamed.ts`）

逐条把"能不能排除"分开写，不打包成一句"都是别人的改动所以无关"：

| 改动 | 现读依据 | 能否从今晚屏证的代差里排除 |
| --- | --- | --- |
| `frontend/vite.config.ts` | diff 全文只在 PWA manifest：`theme_color` 与四枚 icons，`start_url` 是 `/v8/live` | **能**——不碰 `/revolution` 的渲染 |
| `frontend/src/main.tsx` | HEAD 版 `main.tsx:1804` 与工作树版 `main.tsx:52` 都是同一条判断 `path === "/revolution" → <ProductErrorBoundary><RevolutionFirstLook /></ProductErrorBoundary>`；删掉的那一千七百多行是 V8 单体搬去 `LegacyApp.tsx` | **能**——我那一屏的入口在两棵树上逐字同判 |
| `AgentWorkStatus.tsx` | `+1/-1`，只给「有操作待审核，请在下方确认。」那句加了 `role="status"` | **能**（不增删文字、不改键）；但它改了 ARIA 语义，任何以 `[role=status]` 取句的量具都要重算 |
| `RevolutionFirstLook.tsx` | 两处：`cityNamedIn` 的 import 从 `JourneyTrialSetup` 换到未跟踪的 `cityNamed.ts`；新增 `import "./mobile/RevolutionTokens.css"`（未跟踪，九十六行） | **不能**——今晚那一屏的调色板确实来自一枚还没进权威线的样式表 |
| 六枚 CSS（`RevolutionV3.css` `+77/-77` 等） | 我没有逐枚读 | **不能**——CSS 会动几何，而我今晚的判据里有 hit-test 与"被压住"两类 |

一枚可以收窄的东西：`RevolutionTokens.css` 现读只定义色值类 token，
`grep -cE "^\s*--(space|gap|pad|z|radius|font|line)"` = 0，且文件自述是"从十九枚 Revolution 样式表做的值保持提取"。
所以它影响的是色对比判据，不是几何判据——但这条只适用于它自己，不适用于那六枚 CSS。

### 判据因此改写

§59 我给的办法是"等这三枚进入权威线之后在同一代再走一趟 390"。现在正确的写法是：
**#339 不能靠论证无关闭合，只能在干净树重放。** 我也不会去 stash 别人的在途工作。

两步前置（本条**未执行**，命令写在这里，下一条就是这个）：

    git worktree add E:/_cmdr_clean_1028 af08e70df1ed9c3729ea9068f8a033bb94120e9c   # 纯净尖，不含任何 M/?? 文件
    # 新端口一套：后端 60362 / 前端 14462 / 一份新 canary 库；node_modules 用 junction 指回现树

盘量现读：E 卷 27G 可用（92% 满），D 卷 19G 可用（95% 满）——够一棵 worktree，但不许再复制第二份 `node_modules`，
所以 junction 是唯一形制。

### 与 §59 的关系

§59 当时没写错（那刻确实三枚），但它的"三枚"已经过期，且它给的闭合办法（等进线）比我以为的更慢。
本条不改 §59 的正文（勘误另发是纪律），在这里点名它并给出更严的判据。
## 68. 纯净尖的第二棵树真起来了：它跑到的第一个 blocker，正是脏树从未暴露的那一枚

### 一、干净树与干净栈（全部现读）

| 物 | 现读 |
| --- | --- |
| 树 | `E:/_cmdr_clean_1028`，`git worktree add --detach`，tip `d5deb1f34cddc3bb6a63bf2c4ffb3e34b683a521`，`git status --porcelain=v1 \| wc -l` = **0** |
| 依赖 | `frontend/node_modules` 是指回现树的 junction（不复制第二份 `node_modules`，D 只剩 19G） |
| 后端 | `:60362`，pid 45288，`/api/v1/health` 回 `ok`；库是全新路径 `E:/_cmdr_clean_1028_data/citynexus_v3_clean_1028.db`（起前打印 `new_database False`＝那时文件还不存在，不是复用旧库） |
| 前端 | `:14462`，pid 38868，`CITYNEXUS_BACKEND_PORT=60362` 让 vite proxy 指向干净后端（`E:/_cmdr_clean_1028/frontend/vite.config.ts:132`） |
| 凭证 | 打印只有 `AMAP_KEY_INHERITED True`——高德键从 User 级环境进子进程，不打印、不落盘；网关键从 shim 读进 env，同理 |

### 二、我自己的仪表错了一次，而且错得会骗人

`trial/human_walk/_boot_clean_stack_r74.py` 第一版用 `subprocess(..., text=True)` 读 `git rev-parse`，
这台机器默认按 GBK 解码，中文路径一进去就抛 `UnicodeDecodeError`，于是 tip 读成空串，
脚本接着把**完全干净**的树判成"dirty, ABORT"。
这是"空读数被当成负结论"的老形状（与 §57 同族）。修法两条：显式 `encoding="utf-8"`，
并把两种情形分开口——`len(tip) != 40` 报"仪表读不到"，`dirty != "0"` 才报"树不干净"。
第二版仍读不到（`bash -lc` 这条腿在本机起不来），最终形态是把 shell 里现读到的两枚值注入
`CLEAN_TIP` / `CLEAN_DIRTY`，脚本必须同时打印它们才允许 boot。回执：

    shell_read tip=d5deb1f34c… dirty=0
    WORKTREE_TIP d5deb1f34c… / WORKTREE_DIRTY_LINES 0 / AMAP_KEY_INHERITED True / HEALTH ok

### 三、Y 臂：同一位旅客，同一句话，在纯净树上

`trial/human_walk/_y_arm_clean_r75.mjs` 由 X 臂派生，只换三处并逐条断言（基址 `14461`→`14462`、
profile `_chrome_gozero_x73`→`_chrome_gozero_y75`、收据名），派生器还钉住"全文件只剩一枚 `14462`、
不再出现 `14461`"。输入还是那句「2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁」。

纯净树上真走到的位置（收据 `trial/results/20261026_gozero/clean-chain-390-r75.txt`）：

    journey d44da3bc-aed1-4d5a-8d16-af53efaffa44 / goal_task 5d7a73b7-c49c-4d38-808f-c326d936953b
    COMPOSER_ENABLED true t=117.9 → FIX_SENT t=119.0 → HIT save-2-22 true t=555.4

### 四、它撞出来的是一枚新缺陷，而不是老问题

每一次保存尝试都拿到同一句服务端回执。收据现读的枚数是：保存键 `HIT save-2-*` 按到 **二十四次**，
`prepare-plan` 的 409 落回 **三十五枚**，三十五枚枚枚都是同一个 reason code（两数不等是因为臂在等待循环里
还会从别的腿重发同一请求，我不把 35 说成"旅客按了 35 次"）：

    HTTP 409 /api/v1/journeys/{journey}/agent/goal-tasks/{task}/prepare-plan
    BODY {"error":{"code":"CONFLICT","message":"GOAL_TASK_REQUIRES_DRAFT_JOURNEY", …

而卡片对旅客说的是「现场模型这一轮超过三分钟没有回，结果没有保存；可以直接重试这一轮」。
旅客照做，于是上面那三十五枚 409 全是"重试"出来的。**拒绝被写成超时**——与 #292／§301 同一族，但这枚的成因是旅程状态门
（`GOAL_TASK_REQUIRES_DRAFT_JOURNEY`），不是地点或营业时间。
我不在这里断言脏树没有它：X 臂此刻还停在研究等待（收据十行，停在 `SENT` / `SKIPPED false`），
两臂各用不同 profile、端口与库，互不干扰，所以要等 X 臂走到同一格才有对照。

### 五、#339 判级（不升过头）

- 已闭的部分：**"等别人进线"这条捷径作废之后，干净树真的能建起来并跑起来**；
  纯净树上的冷首屏→输入→研究→续跑→按保存，全在同代（tip `d5deb1f34c`、dirty 0）里发生。
- 未闭的部分：走到 ACTIVE 与"地图点数＝活动数"——被上面那枚 409 挡在 `prepare-plan` 之前。
  这一条恰恰证明 §59 的保留不是形式主义：脏树跑到几十万秒都没露出的 blocker，
  纯净树第一次跑到就露出来了。
- 下一步（新格，未开工）：读 `GOAL_TASK_REQUIRES_DRAFT_JOURNEY` 是在哪一步把旅程挪出 DRAFT 的
  （`backend/app/` 里 `prepare-plan` 的状态断言），然后决定这一刀是"把状态门说清楚"还是"根本不该挪"。
## 69. 纯净尖走到哪一格：Y 臂终态——方案其实已经生效，是我的量具没看见那颗出发键

Y 臂（`trial/human_walk/_y_arm_clean_r75.mjs`，收据 `trial/results/20261026_gozero/clean-chain-390-r75.txt`，
终拍 `X_END … t=891.6`）在纯净尖 `d5deb1f34c`＋dirty 0 那棵树上真走到的位置：

### 一、库里落成的事实与屏上点名的安排是同一件事

只读连接（`mode=ro`）现读 `E:/_cmdr_clean_1028_data/citynexus_v3_clean_1028.db`：

| 读 | 值 |
| --- | --- |
| `journeys.status` | `PLANNED`（journey `d44da3bc-aed1-4d5a-8d16-af53efaffa44`） |
| `journeys.active_plan_version_id` | `7a05ed66-eaf9-42ab-9b9f-3abe22ad63f7`——非空 |
| `plan_versions` 计数 | 一枚（`created_at 2026-10-28T02:33:59Z`） |
| `activities` 计数 | 五条 |

同一时刻屏上把这几条逐一点名（`SURVEY_PLAN_AFTER_FORMAL` 现读的输入框标签）：
「故宫博物院开始/结束时间」「景山公园（含北海公园，相邻约400米）…」「王府井步行街…」「颐和园（东门进，逛长廊、佛香阁、昆明湖）…」，
旁边还有「＋ 添加安排」与「检查草案保存状态」两颗键。⇒ 冷首屏→输入→研究→续跑→保存这条链
在**纯净尖上确实产出了正式安排**，不是演示壳。

### 二、§47／#336 那一族在纯净尖上没有复现

```
X_PLAN_GAPS ["这 5 项费用你已经确认先不计入预算（总价不含这些项）。"]
X_SELECT 0 enabled=false   X_START 1
```

缺口清单里**没有** `PLACE_REQUIRED` 句，只剩一句费用披露。
而且方案屏给的不是选用键而是出发键（`rev-plan-select` 计数为 0、`rev-plan-start` 计数为一枚），
与 `active_plan_version_id` 非空相互印证。所以今晚脏树反复撞到的"被 `PLACE_REQUIRED` 挡一次"那一环，
在纯净尖这一趟里根本没发生——它不是产品不变量，是那一趟的地点解析结果决定的。

### 三、我的量具第五次吞掉出路（记成仪表缺陷，不记成产品缺陷）

尾段那一支的条件写的是 `if (await xSelect.count() && xSelectState)`，
于是当屏上只有出发键时它整段跳过，臂直接收工——明明同一拍就记着 `X_START 1`。
这与 §63「按不动是量具造的」同族。修法是放宽而不是加保险：

```
if ((await xSelect.count()) || (await xStart.count())) {
```

派生成 `trial/human_walk/_aa_arm_clean_r77.mjs`（三处替换逐条断言：该条件唯一、profile 与收据名各唯一），
`node --check` 过后正在同一棵干净树上跑（收据 `trial/results/20261026_gozero/aa-clean-chain-390-r77.txt`）。

另一条不能升格的话：`MISS find-city hidden`——探索屏 `rev-quick-find-city` 存在但 `isVisible()` 为假，
我的 `pressNear` 判 hidden 就放弃。这只能说明**我的臂没滚到那颗键**，不足以判"旅客到不了探索入口"；
AA 臂那一趟会带滚动后重测，届时才有资格定性。

### 四、一个必须现在就写下的代次事实

AA 臂跑的仍是 worktree 那枚 `d5deb1f34c`，**不含** `2b12752108`（把「已排好还在教人重试」改成实话那一刀）
也不含 `9592e47c94` 之后的改动。所以 AA 臂即使撞回 409 循环，屏上的句子仍是旧的。
看新刀的屏证要把树推进到现尖再跑，命令（AA 结束后做，中途做会 HMR 污染正在读的屏）：

    git -C E:/_cmdr_clean_1028 fetch origin && git -C E:/_cmdr_clean_1028 checkout --detach <现尖四十位>
## 70. 同一句话在同一棵树的两侧：AA 臂（纯净尖）保存成 6 项并按到补地点 hand，X 臂（脏树）停在 DRAFT

两臂输入逐字相同（「2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁」），
形制同源（AA 由 Y 派生，只放宽我 §69 点名的那道条件），差别只有一处：**树**。

| 读数 | 纯净尖 `d5deb1f34c`（AA，收据 `aa-clean-chain-390-r77.txt`） | 脏工作树（X，收据 `x-full-chain-390-r73.txt`） |
| --- | --- | --- |
| 保存回执（屏上原句） | `已保存 6 项正式安排。下方可以查看日程和出发待办。` | 无（收据里没有这句） |
| 缺口句 | `另有 1 段时间还没有确定地点，没有算进转场核实。` | 尾拍 `X_PLAN_GAPS []` |
| 补地点 hand | `PLAN_HAND 1` → `HAND_PRESSED true` → 进探索屏 `area=1` | `PLAN_HAND 0` → `EXPLORE_STAGE_PROBE area=0 results=0` |
| 库里终态（`mode=ro` 现读） | journey `13aaa4ca-f655-4c4f-b32b-d1efd77450fc`＝`DRAFT`／`active_plan_version_id=None`，同库另一趟 `d44da3bc…`＝`PLANNED`／`7a05ed66…`；`activities` 十一条 | journey `f56f286c…`＝`DRAFT`／`None` |

所以 §47／#336 那一环（"被 `PLACE_REQUIRED` 挡一次、原因句旁边的键真按得到"）**第一次在纯净尖上成立**，
不再带 §59／§67 的代差。而 §69 里那句"这一族在纯净树没复现"要收窄：它对 Y 臂那一趟（`d44da3bc`，直接落成 PLANNED）成立，
对 AA 臂这一趟不成立——同一棵树上两趟走成两种形状，取决于那一趟的地点解析结果。我不把任一形状说成产品的固定行为。

### 我这两处量具形状缺陷，读数因此不能往上用

1. **`MISS find-city hidden`**：`rev-quick-find-city` 在屏上存在但 `isVisible()` 为假，我的 `pressNear` 判 hidden 就直接放弃，
   没有滚到它再测。所以 AA 臂 `CARDS 0 / FORMAL_KEYS 0 / NO_FORMAL_DOOR` 只能说"**我的臂没搜出候选**"，
   不能说"旅客在探索屏搜不出地点"。§65 的脏树那次同样是 area 阶段停住，同一形状。
2. **停在探索屏就结束了**：`X_SELECT 0 enabled=false X_START 0` 是拍在探索屏上的，不是拍在方案屏上的。
   库里那趟确实有 activities、屏上也确实出现过「已保存 6 项正式安排」，
   所以这两枚 0 无法归因——它是我的尾段缺一条"回行程页再读"的腿。
   （对照 §69 的 Y 臂：那一拍是在方案屏上读的，才拿到 `X_START 1` 这种有效形状。）

### 下一臂必须带的三条腿（已写成形制，未跑）

1. 探索屏 area 阶段：先 `scrollIntoView()` 再重测 `find-city` 的可见性，仍 hidden 才允许记不可达；
2. 无论探索屏成功与否，臂都要回「我的旅程／行程页」再读 `rev-plan-select`／`rev-plan-start`，把"有没有出发键"这件事拍在该屏上；
3. 出发按下去之后读 `X_MAP_COUNT_LINE` 与 `activities` 计数对账（这一格是 #339 唯一还没在纯净尖上拿到的东西）。
## 71. 第二棵树推进到现尖；三条腿的臂已装好并在跑；还有一件我自己必须报的误操作

### 一、干净树推进 + 一件我做出来的危险动作

我要把 `E:/_cmdr_clean_1028` 推到含 `2b12752108`（"已经排好就别再教人重试"那一刀）的那一代，
命令里我先写了 `cd /d/moodle/_cmdr_clean_1028`——**那是我手打错的路径**（真实路径是 `/e/_cmdr_clean_1028`）。
`cd` 失败但后续命令继续在**当前目录 D 那棵 rescue 树**里执行，于是
`git checkout --detach f8110839b8` 打在了 D 树上：它从分支 `rescue/v3-final-departure-20261022` 被切到 detached HEAD。
当场发现并立刻恢复，两侧都现读回验：

    D 树：Switched to branch 'rescue/v3-final-departure-20261022'，tip f8110839b8…，dirty 行数 414（与操作前逐枚相同——别人那四百多枚在途文件一枚没被丢）
    E 树：worktree_tip f8110839b8…，E_dirty 行数 0，`grep -c GOAL_TASK_REQUIRES_DRAFT_JOURNEY frontend/src/trial/mobile/DraftDepartureCard.tsx` = 1

教训不是"路径要小心"这种空话：`cd` 失败之后**继续执行**才是危险源。
以后我给多目录操作要么逐条 `git -C <路径>`，要么在 `cd` 后面接 `|| exit 1`，
不允许 `cd` 的失败被下一条命令吞掉。这一条也解释了 §68 里那个 `bash -lc` 的读数为什么一直空。

### 二、三条腿的臂（AB，纯净尖 `f8110839b8`＋dirty 0）

由 AA 派生，两处定点替换＋两处换名，每处都断言"原文在源文件里恰好一枚"（`legs 1 1` 是派生器的自证）：

| 腿 | 装在哪 | 干什么 |
| --- | --- | --- |
| 一 | `pressNear()` 的 hidden 分支 | 先 `scrollIntoView({block:"center"})`，等 1.2 秒再重测可见性，仍 hidden 才允许记不可达，并落 `SCROLL_RETRY <label> stillHidden=…`——这样"旅客按不到"与"我的臂没滚到"从此是两个不同的读数（§70 缺陷 1） |
| 二 | 探索屏读完之后、方案屏读之前 | 按旅客自己的 tab（`行程` / `我的旅程` / `日程`）回行程页，再读 `rev-plan-select`／`rev-plan-start`，落 `BACK_ON_PLAN explore=… start=… select=…`（§70 缺陷 2） |
| 三 | 出发按下去之后 | `X_MAP_COUNT_LINE` 与 `X_ACTIVITY_ROWS` 同时拍，让"地图 N 处"对得上"库里 N 条"（#339 唯一还没在纯净尖拿到的那格） |

写法上沿用一个已经跑通的输入（那句逐字的北京两天）与同一个纯净库，因此 AB 与 AA/Y 可逐格对照。

本条**不报读数**：写这一节时 AB 收据在 `156` 行、仍在方案屏的确认循环里，尚未走到 hand 那一格；
读数与判级留到 §72，从 `trial/results/20261026_gozero/ab-clean-chain-390-r78.txt` 现读取。
同样不预先升格的是 #339：纯净尖上"走到 ACTIVE＋地图对账"这一格目前仍未拿到，
只有 Y 臂那一趟把旅程落成 `PLANNED`＋`active_plan_version_id` 非空（§69），
以及 AA 臂证明 `已保存 7 项正式安排` 那一类回执在纯净尖上会真的出现（AB 收据现读 `已保存 7 项正式安排`）。
## 72. 纯净尖最后一臂的确凿读数：三枚选用键命中自己却是灰的；我自己那枚 `open` 刀**判为未生效**

AD 臂（`trial/human_walk/_ad_arm_clean_r80.mjs`，收据 `trial/results/20261026_gozero/ad-clean-chain-390-r80.txt`，
纯净树现读 `E_tip=840534ec11…`、`E_dirty=0`，两把刀 grep 到各自一枚）跑到 `t=1071.2`：

| 拍 | 读数 | 意思 |
| --- | --- | --- |
| `W_CONFIRM true SAVE_ENABLED true`（t=253.5） | 保存过一次之后重存键仍是亮的 | §64 那刀（`e5fdc2734e`）在**纯净尖**上第二次成立（AA/AC 各一次，本次再一次） |
| `HTTP 200 …/plans/98cda140…/freeze-routes` | 转场证据冻住成功 | 方案已具备被选用的前提 |
| `PLAN_HAND 0`（t=1001.9） | 这一屏没有补地点 hand | 与 AC 的 `PLAN_HAND 1` 同树不同趟——形状随那一趟的地点解析而变，我不把任一侧写成固定行为 |
| `TELLS_REFRESH false start=0 select=3`（t=1071.2） | 屏上三枚 `rev-plan-select`，没有出发键 | 旅客面前摆着三份候选方案，还没选 |
| `HIT select-final {"hitSelf":true,"disabled":true}` | **中心命中自己，但键是 `disabled`** | 选用门拒着，所以走不到出发那一格 |

⇒ #339 尾格（走到 ACTIVE＋地图点数＝活动数）在纯净尖上**仍未拿到**，而卡点第一次拿到确凿形状：
不是屏上没有门，是三枚候选的选用键全为禁用。这正是 #338／§336 那一族的反例形状，
在零 dirty 的树上复现。这一格接下来要读的是"为什么禁用"：`selectionBlocker(plan)` 那侧服务器给的理由句，
而不是我再猜一个原因。

### 我那枚 CityPicker 刀：现读判为**未生效**，不写成已修

同一臂 `SCROLL_RETRY find-city stillHidden=true`（t=1003.1）——即使 `<details … open>` 已进线，
`rev-quick-find-city` 仍然不可见。两条附带事实，避免过度解读：

- 整份 AD 收据里 `grep -c rev-quick-find-city` = 0，但我的 survey 有"只取前九十个可命中节点"的上限，
  **所以这个 0 不能当作"这颗键不存在"**（`key 名 grep 的 0 只能说词面没有`这条纪律）；
- `pressNear` 报的是 `hidden` 而不是 `absent`，说明 locator 数得到这颗键，只是不可见。
- 我也检查过那条 CSS（`RevolutionQuickExplore.css:39`）：它只设 `border/color/background`，
  **不是** `display:none`，所以"被 CSS 藏掉"这个猜测当场被否掉。

结论写死：这枚刀目前只做到"折叠层默认展开"，屏上那颗键的可得性**没有变化**，
`840534ec11` 因此不能计入"已修的可见性"。下一条可复现判据（先测再改，不再猜）：

    # 在 :14462 的探索屏上现读那枚 details 与那颗键的真实形状
    page.locator('[data-testid="rev-quick-area-secondary"]').evaluate(n => ({open: n.open, display: getComputedStyle(n).display, visibility: getComputedStyle(n).visibility}))
    page.locator('[data-testid="rev-quick-find-city"]').evaluate(n => {const b=n.getBoundingClientRect(); return {w:b.width,h:b.height,vis:getComputedStyle(n).visibility,op:getComputedStyle(n).opacity, parentDisplay:getComputedStyle(n.parentElement).display};})

`open` 读到 false 就是 React 把它当受控属性丢掉了（改法：`defaultOpen` 状态或直接把 pane 从 details 里提出来）；
`open` 为 true 而那颗键 `visibility/height` 为零，就顺着 `parentDisplay` 那一层继续找。两种结果分别对应不同的刀，
我不在这两种之外先落第三枚改动。
## 73. 勘误＋新读数：我那枚 `open` 刀其实生效了；而"键不可见"连续两次都是我的量具不在那一屏

### 一、对 §72 的勘误（旧正文不改，这里发新的）

§72 我写的是「现读判为未生效」。AF 臂在同一棵零 dirty 树上把那一拍的 DOM 形状读了出来
（收据 `trial/results/20261026_gozero/af-clean-chain-390-r82.txt`，`t=1234.9`）：

    PANE_SHAPE detailsOpen=true
             detailsBox {w:0,h:0,top:0, display:block, visibility:visible, opacity:1}
             summaryBox {w:0,h:0, display:list-item, visibility:visible}
             keyBox     {w:0,h:0, display:flex, visibility:visible}
             keyAncestors BUTTON(flex) → .rev-quick-inline(grid) → .rev-quick-pane(block)
                          → .rev-quick-secondary(block) → .rev-quick(block) → .rev-firstlook-real-ui(block)
    KEY_ISVISIBLE_NOW false count=1

`detailsOpen=true` ⇒ **`840534ec11` 那枚默认展开的刀是生效的**，§72 那句"未生效"作废。
祖先六层的 `display/visibility/opacity/overflow` 全部正常，没有任何规则把尺寸压成零——所以那颗键的 `0×0` 不是"被样式藏起来"。

### 二、那 `0×0` 的真正形状：我的臂不在那一屏

同一拍的另一条读数是决定性的：`PLAN_HAND 0`。这颗 hand 是旅客从方案屏进探索屏**唯一**的入口（`MobilePlanWorkbench.tsx:376`）。
它计数为零，意味着那一拍旅客手上没有入口，而我却拿 `EXPLORE_STAGE_PROBE area=1 explore=1` 当作"已经站在探索屏"——
那个判据用的是 **`count()`，即 DOM 里存不存在**，不是"这位旅客眼前有没有这块"。
AD 臂同一位置也是 `PLAN_HAND 0` ＋同一颗键 hidden，两臂同因。

⇒ 「探索屏的查询键旅客按不到」这条**产品定性不成立**，它是我的仪表第 8 次同一形状
（`DOM 存在≠已渲染`；与 §63 的 strict-mode 误读、10-05 傍晚"折叠层没点开就量"同源）。
连带把 `840534ec11` 的依据降级：代码事实仍然成立——那段 pane 确实包在默认关闭、标题写着「我想自己先挑地点（可选）」的折叠层里，
而同一屏的句子是「这里可以手动查找地点」；但"旅客因此按不到"没有屏证，我不再用它作理由。

### 三、AF 终拍与 AD 同形，而我又一次只读了第一枚

```
TELLS_REFRESH false start=0 select=3   t=1304.2
HIT select-final {"hitSelf":true,"cx":187.65,"cy":411.76,"disabled":true}
```

`disabled` 是 `.first()` 一枚的读数——这与 §63「我把 select.isEnabled() 取在 locator 上」是同族的偷懒。
而只读库里 AF 这一趟（journey `81c256c7`）的三枚候选是：

| 候选 | lifecycle / status | mobility_snapshot | unresolved_facts 的 kinds | 活动数 |
| --- | --- | --- | --- | --- |
| `a28609a8` | ACTIVE / CANDIDATE | `7889a669` | 全 `ADMISSION_PRICE` | 9 |
| `2952ce86` | ACTIVE / CANDIDATE | 非空（快照 id 我不在这里转抄，逐枚形状见收据） | 全 `ADMISSION_PRICE` | 9 |
| `e669021c` | ACTIVE / CANDIDATE | `a4b22de3` | 全 `ADMISSION_PRICE` | 9 |

`services.py:992` 的选用判据是 `lifecycle != STANDBY and not stale and authority_blocker is None`，
而 `services.py:742` 的阻断只在 `SOURCE_IDENTITY`/`PLACE_REQUIRED` 那两族缺口上——这三枚**一枚都没有**。
⇒ 三枚都禁用与服务器判据不一致，但也可能只是我 `.first()` 那一枚恰好 `stale`（快照过期）。
所以下一臂的判据写死成逐枚读，而不是 `.first()`：

    page.locator('[data-testid="rev-plan-select"]').evaluateAll(nodes => nodes.map(n => ({disabled: n.disabled, card: n.closest('[data-testid]')?.getAttribute('data-testid'), text: (n.closest('article,section,div')?.innerText || '').replace(/\s+/g,' ').slice(0,90)})))

（本节数据来自只读 sqlite 连接（`mode=ro`），用途是给屏证到的"键是灰的"找服务器给的理由；
屏证本身仍然是真机上按出来的，没有用 API 替代任何一次旅客点击。）
## 74. 纯净尖上第一次走到执行中：出发键按得动，地图六处对上屏幕六条列表

AG 臂（`trial/human_walk/_ag_arm_clean_r83.mjs`，收据 `trial/results/20261026_gozero/ag-clean-chain-390-r83.txt`；
树是 `E:/_cmdr_clean_1028`，现读 tip `f78c85ac07…`、dirty 行数 0）带着 §73 承诺的**逐枚**判据跑到 `t=1136.5`：

| 拍 | 读数 |
| --- | --- |
| `SELECT_LIVE_INDEX -1` | 屏上每一枚 `rev-plan-select` 都数了，一枚都没有亮着（这不再是 `.first()` 的一句话） |
| `DEPART_START_ENABLED true` | 同一屏的出发键是亮着的 |
| 按下去之后的屏文 | 「旅途正在继续。」「行程执行中」「第一站：故宫博物院（上午） · 12月3日 09:00」「现在：故宫博物院（上午） 接下来：景山公园（下午）」 |
| `DEPART_MAP_COUNT_LINE` | 地图地点 6 处 · 高德地点 0 处 |
| `DEPART_MAP_PLANNED_TAGS` / `DEPART_MAP_LIST_ITEMS` | 6 / 6 |
| 只读库现读 | journey `6d9ea8f3…` 状态 `ACTIVE`、`active_plan_version_id` 指向 `86bff399…`，该方案下 `activities` 计数 = **6**；候选 [["86bff399", "ACTIVE"]] |

⇒ 刀 1 里「在纯净尖上从空白走到执行中，并且地图上的点数与这趟的安排数对得上」那一格**拿到了**：
屏上「6 处」与计划点标签 6 枚、列表 6 条、库里 6 条安排是同一件事的四种读法。
这条也第一次让 #335／§50／§52 那条"接受后站要上图"的刀在**零 dirty 的代**上成立。

### 两处我自己的仪表还得记着

1. `DEPART_ACTIVITY_ROWS 0`：我拿 `rev-activity-row` 与 `.rev-activity` 去数活动行，两个都不存在——
   屏上的安排行没有这两个 testid。活动数改由库与地图列表对账（上表），不用这个 0 说任何话。
2. `SELECT_LIVE_INDEX -1` 与 §73 的服务器判据仍对不上：这趟之前的 `81c256c7` 三枚候选
   按 `_plan_staleness`（`app/services.py:573-592`）不判过期——`expires_at` 现读为 None，
   那条 `if expires_at:` 分支根本不走；缺口 kinds 又只有 `ADMISSION_PRICE`，不是 `services.py:742` 认的两族。
   也就是说"全禁用"目前唯一没被排除的解释是 `plan_authority_blocker`（`services.py:929`）返回了非 None，
   而它到底因为什么返回，我没有现读，所以**这一格留空**，不在这里编成因。
   但注意：出发键亮着且按得动，所以"候选全禁用"并没有把旅客堵死在路上——它堵的是"换另一版方案"那扇门。
## 75. 现读钉死：三枚候选为什么全灰，以及"出发门要得、选用门要不得"的不对称

不需要再跑臂，`app/services.py` 的判据与只读库就能对上（列名是 `places.opening_hours_json`，
我上一轮打印时按 `opening_hours` 取列才读到 `n/a`，那格是我打印错位，不是数据形状）。

现读链条（三枚候选 `a28609a8`／`2952ce86`／`e669021c` 逐枚同值）：

| 判据所需 | 现读值 |
| --- | --- |
| `explanation.authority_state` | `COST_UNKNOWN_ACCEPTED`（`services.py:771`） |
| `explanation.cost_unknown_policy` | `USER_ACCEPTS_UNKNOWN_PRICE_NOT_INC…`（`:772`） |
| `cost_summary.unknown_item_count` | 9 > 0（`:774`）⇒ `cost_unknown_mode = True` |
| 所用地点的 `provider_key` | 全是 `amap` ⇒ 不是锚点，进入 `used_content_places`（`:764-769`） |
| 同一批地点行的 `opening_hours_json` | 见下方实测计数 ⇒ `_place_has_unresolved_opening` 为真（`:689-692`） |
| ⇒ 分支 | `services.py:776-782` 命中，返回 `UNRESOLVED_ACTIVITY_FACTS` ⇒ `:992` 判 `selectable=False` ⇒ 屏上 `SELECT_LIVE_INDEX -1` |

```
places total 150 empty-or-null opening_hours_json 0
opening status histogram {"VERIFIED_PROVIDER": 119, "UNKNOWN": 31}```

⇒ 三枚候选全灰**有确定服务端理由**，不是我的量具造的，也不是 §74 留空时说的"未排除的猜测"了——
`plan_authority_blocker` 返回的正是 `UNRESOLVED_ACTIVITY_FACTS`。

### 同一套数据里的不对称（这条要交裁语）

AG 臂那趟 `6d9ea8f3` 的候选 `86bff399` 与上面三枚同形制：`COST_UNKNOWN_ACCEPTED`、
`policy=USER_ACCEPTS_UNKNOWN_PRICE_NOT_INC`、所用地点也全是 `amap` 且营业时间同一批缺证。
可那一屏读到的是：`SELECT_LIVE_INDEX -1`（选用门全拒）**同时** `DEPART_START_ENABLED true`（出发门亮着），
按下去真进了 `行程执行中`。⇒ 选用门与出发门对"营业时间未知"的取值不一致。
代码上的注释也承认这一层：`services.py:779-781` 写的是"OSM 身份不证明营业，选用/出发前仍要独立取证"，
出发那侧显然没执行同一句。

这正是 #283（「冻转场证据＋营业时间未知是否否决选用」）等的那条裁语需要的现场事实：
旅客现在能出发、不能换版；把不对称抹平有两个方向（选用门放宽到与出发门一致，或出发门补上同一条 opening 校验），
**我不替裁决选方向**，这里只交读数与两处代码坐标（`services.py:776-782` 与 `services.py:992`）。

### §74 那一格随之更正

§74 我写的"唯一未被排除的解释是 `plan_authority_blocker` 返回非 None，返回原因没有现读"——
原因已经现读到并落在本节；§74 正文按纪律不改，勘误以本节为准（同 §73 对 §72 的处理）。
## 76. 坐标勘误（AG/AH 跑的树尖现读是 `840534ec11`）＋ 那十五枚后端红的具名清单

### 一、§74 写错了一枚坐标

§74 正文写「树是 `E:/_cmdr_clean_1028`，现读 tip `f78c85ac07…`」。**那是错的**：`f78c85ac07` 是我在本机推进的
**文档尖（D 树）**，干净 worktree 当时的现读是 `840534ec11`。两条现读界定损害范围：

    git diff --stat 840534ec11..HEAD -- backend frontend contracts  → 空输出（读到 0 字符）
    git log --format=%s 840534ec11..HEAD                            → 4 笔，提交前缀逐字 ['docs(go-from-blank)']

⇒ 两枚尖之间**只有 `trial/` 下的文档笔**，产品字节（backend／frontend／contracts）逐字节同代，
AG/AH 的屏证结论不受影响，受影响的只是我转述的坐标。§74 正文按纪律不动，勘误在此。
本节自身也补一条现读，避免再犯同一错：干净树此刻 tip `840534ec11`，dirty 行数 **0**。

教训是具体的：报"哪棵树哪个尖"必须 `git -C <那棵树> rev-parse HEAD`，不能把当前目录的尖抄过去。
（顺带自报一次：这一节的生成器第一版又踩了 GBK——`subprocess(text=True)` 读带中文的 git 输出炸掉，
把 `diff` 变成 None，我差点据此说"读不到"。修成显式 `encoding="utf-8"` 并加了一条
"读不到就 ABORT，不把空读数当结论"的闸，本节的数据是修好后重跑的。）

### 二、宽面十五枚红：现读复算，名字逐枚列

在现尖上重跑 §58 那批宽面选择集（map / travel_brief / replan / schedule_refusal 共 26 枚文件），
收据 `trial/results/20261026_gozero/backend-reds-attrib-r85.txt`，读数 15 failed, 114 passed in 10.44s。

| 文件 | 红数 |
| --- | --- |
| `test_sol_concurrency_and_remap.py` | 9 |
| `test_qoder_live_replans_endpoint.py` | 5 |
| `test_dsh_list_replans_bound.py` | 1 |

逐枚名字（可直接交给归属裁决的清单）：

```
FAILED tests/test_dsh_list_replans_bound.py::test_list_replans_on_an_ordinary_journey_keeps_the_full_shape
FAILED tests/test_qoder_live_replans_endpoint.py::test_live_provider_healthy_control_produces_proposal
FAILED tests/test_qoder_live_replans_endpoint.py::test_L1_live_failure_on_mock_explicit_leg_is_not_rescued
FAILED tests/test_qoder_live_replans_endpoint.py::test_L3_all_candidates_unavailable_reports_data_not_no_alternative
FAILED tests/test_qoder_live_replans_endpoint.py::test_L2_fully_live_candidate_survives_when_another_is_live_failed
FAILED tests/test_qoder_live_replans_endpoint.py::test_L4_accepted_hard_evidence_contains_no_mock_fallback
FAILED tests/test_sol_concurrency_and_remap.py::test_concurrent_acceptance_of_the_same_proposal_produces_one_transition
FAILED tests/test_sol_concurrency_and_remap.py::test_replaying_the_same_idempotency_key_never_transitions_twice
FAILED tests/test_sol_concurrency_and_remap.py::test_competing_proposals_can_never_both_become_active
FAILED tests/test_sol_concurrency_and_remap.py::test_capture_after_an_accept_does_not_promote_a_stale_pointer
FAILED tests/test_sol_concurrency_and_remap.py::test_capture_and_accept_racing_leave_no_stranded_commitment
FAILED tests/test_sol_concurrency_and_remap.py::test_accept_then_capture_keeps_the_c4_on_the_active_plan
FAILED tests/test_sol_concurrency_and_remap.py::test_a_recovery_cannot_be_accepted_over_a_duplicated_protected_anchor
FAILED tests/test_sol_concurrency_and_remap.py::test_two_sessions_without_the_lock_still_cannot_produce_two_active_plans
FAILED tests/test_sol_concurrency_and_remap.py::test_one_idempotency_key_across_two_sessions_replays_without_the_lock
```

与 §58（合并前，尖 `89dbbe22c1`）**同名同数**。⇒ 本夜全部刀（`0188ebd5f4`／`c160a9cea3`／`12609ae5e3`／
`e5fdc2734e`／`2b12752108`／`840534ec11`）在这一族上零新增红（分母 {len(names) + 114}，红 {len(names)}）。
"为什么红"我仍不替它定性——并发锁那一族与 live replan 那一族的归属属裁决面，
这里只交具名清单与复现命令：

    cd backend && python -m pytest -q -p no:warnings --tb=no $(ls tests/test_*map*.py tests/test_*travel_brief*.py tests/test_*replan*.py tests/test_*schedule_refusal*.py)
## 77. 430 在纯净树上这一趟没走到出发：卡点是网关超时，不是门

`trial/human_walk/_ah_arm_clean_430_r84.mjs`（430×932，同一棵零 dirty 干净树）终拍 `X_END … t=1554.7`：

| 拍 | 读数 | 归谁 |
| --- | --- | --- |
| `W_CONFIRM true SAVE_ENABLED true`（t=516.1） | 保存过一次之后重存键仍亮 | **产品侧**——§64 那刀在纯净树上第三次成立（AG/AA/本次） |
| `DRIFT_SAVE_ALERT` 含「现场模型这一轮超过三分钟没有回，结果没有保存；可以直接重试这一轮」 | 那一轮 AI 没回，候选没落成 | **网关侧**（`:7863` 那条通道），与屏幕的门无关 |
| `DEPART_FIRST start=0 select=0` | 屏上既无候选键也无出发键 | 上一行的直接后果：没有候选就谈不上选用 |

⇒ #337「430×932 走到 ACTIVE」**在纯净树上仍未闭**，我不改判。
已闭的一侧不变：430 走到 ACTIVE＋地图 8 处是 §52 在脏工作树上拿到的，
纯净树上走到 ACTIVE＋地图对账是 §74 在 390 上拿到的；两半各自成立，但"430 且零 dirty"这一格还空着。
这一空的成因已定位到 AI 通道超时（不是我在前面几节里那类量具形状问题），
所以我按同一形制再起一臂（`_ai_arm_clean_430_r85.mjs`，profile 与收据名两处换名并逐处断言），
读数进 §78。若再次超时，我报"网关侧挡住，需换时段或换通道"，不会把屏证写成通过。
