# 草案的版本门：改在半天空档里，服务器怎么回答（2026-10-22）

这一趟不是「改半天」的成功读数，是它的**前一次尝试撞在版本门上**的读数，值得单独留着，因为它同时证明了两件平时看不见的事。

做了什么：一句话建北京行程 → Agent 问「北京“古迹+胡同小吃、慢慢逛”有几种舒服的走法，你更想以哪片区域为主？」（四枚选项）→ 按第一枚 → 第二个回合还在跑的时候，切到「日程」层，在第二天加一项「湖边慢走，不安排门票」、时段设「下午」、按「保存草案」。

服务器怎么答：`PUT .../agent/goal-tasks/{id}/draft` 回 **409**（`20261022_V3_AGENT_VERSION_DOOR_RECEIPT.txt:19`），屏上原话是「服务器的草案版本发生了变化。你的编辑仍在当前页面，请先确认新内容，再点上方「刷新任务」。」（`20261022_V3_AGENT_VERSION_DOOR_RECEIPT.txt:14`）。库里两次回合都在，两次都是 `ask_traveler:COMPLETED`（`20261022_V3_AGENT_VERSION_DOOR_RECEIPT.txt:22`）。

为什么这是有用的证据：草案写入的门按版本拒并发，不覆盖、不假装成功；拒的时候说的是旅客能照做的下一步，而不是错误码。这一格此前只在测试里钉过，这是第一次在真后端 + 真浏览器上读到它的原话。

我自己的仪表错在哪：它在看到 `NEEDS_DECISION` 之后就去改草案，没等第二个回合真正起走再落定，所以正好把手工编辑压在 `WORKING` 上。已改成「先等回合起走、再等它落定，若仍撞上版本门就按提示刷新后重试一次」，成功读数在 `20261022_V3_AGENT_HALFDAY_*`。

不宣称的事：这一趟没有把半天改动写进去（`revision` 仍是 0），也没有调任何地点供应商；屏上出现的什刹海、鼓楼、恭王府是模型给的话，没有落成地点行，营业时间与票价仍是 `UNKNOWN`。

## 更正（同日十五时）：那句屏上原话说的不是版本门

上面第三段把屏上那句话当成了「版本门」的读数。现在能测出服务器那一刻真正答的是什么了，两个理由码的对照在 `20261022_V3_AGENT_DRAFT_DOOR_BEFORE_FIX_RECEIPT.txt:7`（版本旧）与 `20261022_V3_AGENT_DRAFT_DOOR_BEFORE_FIX_RECEIPT.txt:10`（这一轮还在跑）：同一枚 `409` 下，`CONFLICT` 是唯一的码，区别只在 `error.message` 里，而那一代信封还没有 `reason_code`（`20261022_V3_AGENT_DRAFT_DOOR_BEFORE_FIX_RECEIPT.txt:7` 列出的键里没有它）。

浏览器读不到 `error.message`：`frontend/src/api/citynexus.ts:2792` 把异常的句子拼成「CityNexus API <状态码>: <路径>」，而 `21d646b837b9a0fc604465a570a2fd70468ec2e2` 那枚 `frontend/src/trial/mobile/GoalDraftEditor.tsx` 第 83 行的判断是 `includes("DRAFT_CHANGED_RELOAD") || includes("409")`——前半句永远假，后半句把每一枚 `409` 都收进版本门那句话。所以上一段引的屏上原话是真的，但**它归错了因**：按这一趟的时序（第二个回合还在跑）服务器答的应是「这一轮还在跑」，而屏上让旅客去点「刷新任务」。

已改：两扇门现在都带 `reason_code`（`backend/app/agent/goal_tasks.py:436`），屏上按它分句（`frontend/src/trial/mobile/GoalDraftEditor.tsx:10`，两枚理由各自的句子在 `:16` 与 `:17`）。改前的读数 `20261022_V3_AGENT_DRAFT_DOOR_BEFORE_FIX_RECEIPT.txt:10`，改后的读数 `20261022_V3_AGENT_DRAFT_DOOR_AFTER_FIX_RECEIPT.txt:10`。本文其余部分——被拒、编辑留在页面上、没有覆盖别人的写——不受影响。
