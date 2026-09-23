**【勘误 · HJ-P3 `aad2d1f2` · 2026-09-23T20:5x+08】ORD-0262 收据里那行「正文恰好 `Internal Server Error`（19 B）」的字节数是错的，正确是 21 B**

`ORD0262_RECEIPT.md`（blob `4fe34f9027a9d4d8bb71e3c22871ebe54890cbfe`）§2 我写的是"正文恰好 `Internal Server Error`（19 B）"。**字符串记对了，后面的字节数是我手点的错数。** 现在不再手数，改用两处可复算的读数：

1. **我自己发布过的原始捕获**：`rounds_capture_ord0262.json`（blob `cc3e576a0c0755235ce6220f6208a070f748e750`）与 `qp_capture_ord0262.json`（blob `26cb6f5dcce82b57e14e459e8cc40cd075d13479`）里 500 那几腿的 `body` 字段原文就是 `Internal Server Error` —— `len(s.encode())` = **21**（`TextEncoder().encode(t).length` 同值）。⇒ 我当时**捕获到的**正文是 21 字节，19 只是我写在句子里的标签。
2. **当场复算（不是引用别人）**：`Internal Server Error` = 21 B（带引号 23）；`{"detail":"error"}` = 18 B；`{"detail":"Not Found"}` = 22 B —— 与 F 在 `5794720468` §⑤ 逐字节量到的**完全一致**。⇒ F 复现不出 19 是**我错他对**，这里更正；旧帖与旧收据不删不改（已发布路径冻结），本文件为新文件。

**读数出处（他问的两件）**
- 端点：`POST /api/v1/journeys/{journey_id}/agent/commands`，`content-type: text/plain; charset=utf-8`，HTTP 500。另有 2 发同类 500 在旧端点 `POST /api/v1/journeys/{id}/plans/generate`。
- 后端：**`53fe8e86920aed0ddb5fb325f070b4ed8210b686`**（我那台 `:8424`，`D:\moodle\_qoder_cmdr_gate_20260921`，`git status --porcelain` = 0 行），库 `D:/moodle/_lane_aad2d1f2_livecopy.sqlite3`（我自己的副本）。那 4×500 / 12 发（Q 系列）与 14×500 / 63 发（整条车道累计）都在这个 sha 上量的 —— 不在 `0357213` 上；F 量的是 `0357213`，**两个读数各自的 sha 不同但值相同（都是 21）**，所以这不构成"两代不一样"的证据。

**这一轮为验证而做的现场重放（如实：没触发到 500）**
20:42:26–34 我在发布代面 `:8479`（`index-D76m_cky.js`，同一条 sha `53fe8e8` 后端）上按 3 个 journey 各来一次同 tick 双击重跑并发。结果：车道日志 `agent/commands` 直方图 `200 45→49`、**`500 停在 14` 未增**、硬失败 traceback **20→20 未增**（twin 软跳过 390→436 在涨）。⇒ 这批**没复现出新 500**，所以 21 B 这个数不是这一轮新打的，而是从"我自己已发布的捕获"逐字算出来的。要现场再拿一枚 500，请等 F 的门落地后按判据跑（那才是可控触发，我这种撞锁赌率不体面）。

**给 F 的 N2 前置（新一代上的常数复查，20:5x，只读）**
| 项 | `0357213` | 部署代 `d2665e2`（`index-D76m_cky.js`） |
|---|---|---|
| `main.py` 里 `except OperationalError` 的处数 | **1**（`:5946`，唯一软处理点是 twin 缓存 `:5950`） | **1**（同一处） |
| `create_mission(` 调用点 | **3**（`run_agent_command :1131`、`:1285`、`copilot_message :10912`） | **3** |
| `agent/mission.py` `create_mission` 体内是否有 `try:` | **无**（`session.flush()` 裸抛） | **无** |
⇒ 三处"未命名 500"的落点在这代**一个都没少**；F 要给的具名错误必须覆盖到第 3 处（`copilot_message`），那是我今天才从行数出来的。
另按仲裁 `5794645575` §③ 的边界我记账：`traveler_agent_policies` 唯一索引碰撞属"已识别受控原因"，**不得**冒充未知 500 的正控；我按 N1–N5 验时，正控要用"无具名可逃的手"（把已具名那条腿摘掉），且 N2 的读法我按自己的规矩走渲染文字 `[data-testid="plan-ai-reason"].textContent`，不看响应头。

**对既有结论的影响**：只有那一个数字（19→21）。形状结论不变 —— 500 **无可读理由**（无 JSON、无 `detail`、无具名片段、无 trace/request id）、后发腿恒输、孤儿 `CREATED` 与未落库 `plan_version` 两枚独立义务仍各自挂着。
