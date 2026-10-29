# 两扇 409 现在说两句不同的话（2026-10-22）

接管令里「失败可继续、不得假成功」这一格，今天在屏幕上补齐了：草案保存被拒时，屏上说的是**这一次真正的原因**，而不是所有 `409` 共用的一句。

## 原来坏在哪

服务器有两扇门都会答 `409`：这一轮还在跑（`backend/app/agent/goal_tasks.py:443`）与草案版本被别人挪走了（`backend/app/agent/goal_tasks.py:446`）。改之前，两扇门只在 `error.message` 里不同，而浏览器读不到那个字段——`frontend/src/api/citynexus.ts:2792` 把异常的句子拼成「CityNexus API <状态码>: <路径>」。屏幕上那句判断写的是 `includes("DRAFT_CHANGED_RELOAD") || includes("409")`（`21d646b837b9a0fc604465a570a2fd70468ec2e2` 那枚文件的第 83 行）：前半句永远假，后半句把每一枚 `409` 都归成「版本变了」，于是**轮还没跑完就被拒的旅客被告知去点「刷新任务」**。

改前的线上读数：`trial/results/20261022_V3_AGENT_DRAFT_DOOR_BEFORE_FIX_RECEIPT.txt:7`（版本旧）与 `trial/results/20261022_V3_AGENT_DRAFT_DOOR_BEFORE_FIX_RECEIPT.txt:10`（这一轮还在跑）——两行都只有 `code: CONFLICT`，信封里根本没有 `reason_code` 这个键。

## 改了什么

两扇门改由一处发名：`backend/app/agent/goal_tasks.py:436` 把理由码装进信封，两个名字在 `:424` 与 `:425` 各写一次；出发准备那条口（`backend/app/agent/goal_preparation.py:94` 与 `:97`）从同一处引这两个名字（`backend/app/agent/goal_preparation.py:21`）。屏幕按名字分句：`frontend/src/trial/mobile/GoalDraftEditor.tsx:10`，两句各自在 `frontend/src/trial/mobile/GoalDraftEditor.tsx:16` 与 `:17`，同时删掉了 `|| includes("409")` 那条兜底和把请求路径回显在屏幕上的那半句。

改后的线上读数：`trial/results/20261022_V3_AGENT_DRAFT_DOOR_AFTER_FIX_RECEIPT.txt:7` 带上了 `DRAFT_CHANGED_RELOAD`，`trial/results/20261022_V3_AGENT_DRAFT_DOOR_AFTER_FIX_RECEIPT.txt:10` 带上了 `DRAFT_RESEARCH_RUNNING`。

## 钉它的三格

`backend/tests/test_qoder_draft_door_reason_codes_r1.py` 三格各自挂坐标：版本门 `:35`（断言在 `:45`）、准备口同一理由 `:48`（断言在 `:61`）、轮未决那一扇 `:64`（断言在 `:92`，同格还反证了按下保存时任务确实是 `WORKING`，并证明回合结束后同样的写入会被收）。三格 `3 passed`；把 `:436` 那行拿掉后 `3 failed`，放回去又 `3 passed`。

## 屏幕上真的说了两句

一趟真点击：一句话建北京行程 → 勾允许 → 发送 → 第一轮落定（`trial/results/20261022_V3_AGENT_DRAFT_DOOR_PRESS_RECEIPT.txt:8`）→ 切「日程」加一项安排（还没保存）→ 另一个写者起一轮 → 这一页按「保存草案」→ 服务器答 `DRAFT_RESEARCH_RUNNING`（`trial/results/20261022_V3_AGENT_DRAFT_DOOR_PRESS_RECEIPT.txt:11`），屏上是「Agent 正在跑这一轮，等它结束再保存。你的改动还在这个页面。」（`trial/results/20261022_V3_AGENT_DRAFT_DOOR_PRESS_RECEIPT.txt:12`）。等这轮跑完，另一个写者把草案存走（版本 0→1），这一页再按保存 → 服务器答 `DRAFT_CHANGED_RELOAD`（`trial/results/20261022_V3_AGENT_DRAFT_DOOR_PRESS_RECEIPT.txt:16`），屏上是「服务器的草案版本发生了变化…再点上方「刷新任务」。」（`trial/results/20261022_V3_AGENT_DRAFT_DOOR_PRESS_RECEIPT.txt:17`）。两次拒绝各自的理由码在同一行清单里对得上（`trial/results/20261022_V3_AGENT_DRAFT_DOOR_PRESS_RECEIPT.txt:18`）。

等价的第二写者是这台机器上用旅客自己的凭证发出的 API 写，代表第二台设备，不是打桩。截图：`20261022_V3_AGENT_DRAFT_DOOR_DIRTY_390.png`（按之前）、`20261022_V3_AGENT_DRAFT_DOOR_RUNNING_390.png`（轮未决那句）、`20261022_V3_AGENT_DRAFT_DOOR_VERSION_390.png`（版本变了那句）。

## 相邻回归与我的仪表瑕疵

同代跑相关子集（`-k "goal or agent or departure or confirmation"`）：`311 passed`、`9 failed`，那九枚全在具名基线红集合里（`_suite_baseline_4549a77192.txt`），本拍没有新增红。

读数里有一行 `422 /api/v1/journeys/null/agent/goal-tasks/null`（`trial/results/20261022_V3_AGENT_DRAFT_DOOR_PRESS_RECEIPT.txt:19`）：那是我的仪表在还没拿到行程 id 时就开始轮询，不是产品发的请求；另外它的等待条件只认「先看到 WORKING 再看到落定」，所以第二次落定之后又空转了六分钟。两处都记在这里，不改读数。

## 不宣称的事

- 模型这一格是 TEST_FIXTURE（pytest 里那格用仓库既有的假助手接缝，标了 TEST_FIXTURE）；屏幕那一趟用的是本机回环网关的零计费档，一次外部地点供应商都没调。
- 屏上写的「湖边慢走」仍是旅客自己打的字，没有落成地点行；营业时间与票价仍是 `UNKNOWN`。
- 本机 Chromium，不是手机在手里的点击，`USER_VERIFIED` 继续 PENDING。
- 权威线 0 次移动；本拍只落在 `refs/heads/rescue/v3-final-departure-20261022`。
