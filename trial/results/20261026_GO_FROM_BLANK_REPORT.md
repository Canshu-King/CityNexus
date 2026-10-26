# 从空白到 GO：真实 Chrome 走查报告（2026-10-26）

派单：`trial/tasks/20261026_QODER_GO_FROM_BLANK_AND_AGENT_VISIBILITY.md`（基线 `a8a53d41f9…`）。
本文件只写**现读**：每条结论后面是屏幕读数、HTTP 状态或库里的行。产品 SHA 与同号收据在 §5。

## 0. 一句话

隔离试玩栈（`60361/14461`，库 `citynexus_v3_gozero_1026.db`，`db_kept=true`）上，真 Chrome（Playwright `channel:"chrome"`，390×844）从冷首屏输入真实句子，走到研究、草案、正式候选；**修掉的第一个真实阻塞**是「讨论问答看不到去研究的门」——修前 8 趟旅程全部卡在 `DISCUSS`，每趟只有 `ask_traveler/inspect_journey`、0 个 Slot；修后一次真人点击「不选了，直接按现在的方向开始研究」，同一 `journey/task` 产出 56 个真实地点、7 项安排、移动证据已冻结的 `CANDIDATE`。

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
- 另两趟同流程：`f1685791…/72d031ab…`（plan `e569d15f…`，commit 422）、`b49cfe49…/07527975…`（plan `3e3c55cc…`，9 条未决）
- 脱敏：以上均为库内 id 与状态，不含令牌、密钥或请求头。

## 6. 已知阻塞（如实写）

- **模型网关会超时/限流**：`MODEL_HTTP_429`（d62fc603）与 `MODEL_TIMEOUT`（2a07aa70、r12 之前一趟）；同一网关小请求实测 200/1.8–6.1 秒，说明是长补全偶发超时，不是断网。产品侧表现为「这次有一部分还没完成」；重按「开始研究」可续（r12 就是这样起来的）。
- **重开浏览器找不回这趟行程**：同一 Chrome profile 重开，屏上写「这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到进度」（`390-cont-journeys.png`）。令牌在会话里，不在磁盘上；所以本报告所有 GO 证据都来自**一次会话内**。
- **正式候选生成仍 422**：56 个真实地点没有一处同时具备开放时间与票价来源；界面已如实说明并指向草案候选路径，这是数据供给问题，不是本轮产品改动能消掉的。

## 7. 结果（2026-10-26 12:20 本地）

**CANDIDATE 到了，SELECTED/ACTIVE 没到**——卡在正式方案的事实完整性门，不是卡在研究。

三趟同一流程、同一产品版本的读数：

| 旅程/任务 | 草案 | 正式方案 | 选用的读数 |
|---|---|---|---|
| `e8f81207…` / `e99b4180…` | rev 1、7 项、56 地点 | `71973500…` 7 条未决（6 票价 + 1 无地点） | 未点（先补地点） |
| `f1685791…` / `72d031ab…` | rev 1、7 项 | `e569d15f…` 7 条未决（全票价），移动证据已冻、票价已确认 | **真点「选用这份方案」→ `POST /departure/commit` 422**；屏上方案卡转灰，只能「刷新方案」 |
| `b49cfe49…` / `07527975…` | rev 4、8 项、71 地点（Agent 两次 `replace_draft_slots` 补地点） | `3e3c55cc…` 9 条未决（8 票价 + 1 营业时间）；票价已由旅客确认（`POST .../accept-unknown-price` 200） | 无「选用」按钮；同一张卡同时写「8 项费用待确认」与「票价这一项你已经确认先不计入预算（8 处没有来源）」——**同一屏两句互相矛盾** |

结论与归属：

- **研究链路已经是真的**：一次真点（`rev-agent-skip-questions`）把任务从 `DISCUSS` 推进到 `RESEARCH`，同一 journey/task 产出 56→71 个真实地点、7→8 项安排、移动证据冻结 5/5 或 3/3（超 1 公里一律换公共交通核实），`POST .../prepare-plan` 201 建出 `CANDIDATE`。这一段是本轮修复的收益，且可重复。
- **卡住的是「正式计划要每一格都有地点、营业时间、票价来源」**：本次运行里 Agent 的草案先后出现「无地点的一餐」「营业时间未知的一处」；UI 只给票价留了「确认先不计入预算」的门，营业时间与无地点只能回问 Agent。
- **另有一处产品缺陷已读数**：票价确认后，出发卡写「已确认」，方案工作台仍写「8 项费用待确认」（后者用的是它自己那份旧 `explanation`），同一屏自相矛盾；这会让旅客以为确认没生效。
- **`POST /departure/commit` 422** 的拒绝句只在屏上出现一次、且被滚动带走；本批探针没有在白屏前抓到它（r15b 的 `SELECT_REFUSAL` 未触发，因为该趟连选用按钮都没出现）。要把它变成可复现读数，需要先让「营业时间未知」有一扇旅客可用的门。

## 8. 我没有做到的事（不冒充）

- **430×932**：本轮只跑了 390×844；430 未跑。
- **SELECTED / ACTIVE**：未达到；上面三趟都停在 `CANDIDATE`。
- **失败/刷新路径**：失败路径有（429/超时、422、无选用按钮），刷新路径只做到「刷新方案」按钮可用，未在成功链上跑通。
- **平板真机**：`USER_VERIFIED=PENDING`。
- **PR #55 合入**：只做了只读冲突预测（`git merge-tree --write-tree HEAD a01f2e68` → rc=0、tree `a2731237`，MERGEABLE/CLEAN），**未合入、未重启真栈复验**。

## 9. 下一步（按代价排序）

1. **裁语**：营业时间未知、无地点的一餐，是否允许旅客像票价一样「确认先按未知处理」？允许 → 正式计划的可选门放宽，blank→ACTIVE 当场可通；不允许 → Agent 的研究必须补到每一格，成本在模型轮次上。
2. 修「票价确认后方案工作台仍报 8 项待确认」：让工作台在 `accept-unknown-price` 后重建那份 `explanation`（本地或按版本重读）。
3. 把 `POST /departure/commit` 的 422 拒绝句在方案卡上原地保留（不随刷新消失），并在同一屏给出下一步。
4. 430×932 与失败/刷新路径补齐，再跑一遍 §3 的同一流程。

