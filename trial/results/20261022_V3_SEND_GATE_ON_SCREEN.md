# 按下「发送」之前，屏幕必须先说清楚它在等什么

走查时间：2026-10-22 17:01–17:13（本地）。工具：真实 Chrome 155（独立 profile，调试端口 9333，同一个标签页贯穿全程）。视口 414×900。地址 `http://127.0.0.1:14333/revolution`。

## 旅客看到什么（修复前）

第一次打开、填一句想法、按「继续规划 →」进入这趟旅行之后，屏幕底部就是输入框和「发送 ↑」。把整段目标输进去，按「发送 ↑」：

- `SEND_DISABLED_BEFORE_CONSENT=true` — 按钮是灰的（`trial/results/20261022_v3_human_chrome/walk-04-log.txt:11`）
- `DEAD_CLICK_CHANGED_SCREEN=false` — 按下去屏幕一个字都没变（`walk-04-log.txt:12`）
- `EXPLANATION_VISIBLE_ON_SCREEN=false` — 整屏找不到任何一句解释（`walk-04-log.txt:14`）
- 截图 `human-16-pressed-send-nothing.png`：输入框里是完整的旅行目标，右下角「发送 ↑」发灰，左边只有一个没有文字的 ⚙ 齿轮

原因藏在 ⚙ 里：那一步要勾「本次允许 AI 处理旅行目标（可能产生费用）」，勾上之后按钮才亮（`walk-04-log.txt:25`）。一个第一次用的人不会知道要去点齿轮，只会认为这个 App 按不动。

## 改了什么

把这两条本次授权从齿轮面板里搬到它解锁的那个按钮旁边；两条都已经允许之后，同一批行再搬回「对话设置」面板，保留随时取消的能力——一句话只有一个写者，屏幕上任何时刻只出现一份。

- `frontend/src/trial/mobile/WorkspaceActions.tsx:466` — `bothGranted` 决定这两行此刻住在哪
- `frontend/src/trial/mobile/WorkspaceActions.tsx:467` — 两行授权本身（原来在面板里）
- `frontend/src/trial/mobile/WorkspaceActions.tsx:624` — 底部输入条：没允许时显示在「发送」正下方
- `frontend/src/trial/mobile/WorkspaceActions.tsx:478` — 已允许时回到「对话设置」面板，可撤销
- `frontend/src/trial/mobile/WorkspaceActions.tsx:476` — 面板里只剩时间与偏好快捷项，标题跟着改成「加上时间与偏好」（`frontend/src/trial/mobile/WorkspaceActions.tsx:634`）
- `frontend/src/trial/mobile/WorkspaceActions.css:105` — 新位置的排版（整行铺开、四十四像素高、贴着输入框）

## 旅客看到什么（修复后）

同一个标签页、同一趟旅行（`ddfb8c11-1692-46ca-81f9-939eba2cb475`）：

- 两条都已允许时，输入条保持干净：`STRIP_INLINE_WHEN_ALREADY_GRANTED=false`（`walk-05-log.txt:4`），行确实还在、住在面板里：`ROWS_INSIDE_SETTINGS_PANEL=2`（`walk-05-log.txt:6`）
- 在面板里取消勾选之后，解释立刻出现在「发送」旁边：`STRIP_INLINE_NOW_VISIBLE=true`（`walk-05-log.txt:17`），位置 `STRIP_BOX 9,681,381,134`（`walk-05-log.txt:19`，在 900 高的视口内），按钮同时回到灰态 `SEND_DISABLED_AFTER_REVOKING=true`（`walk-05-log.txt:20`）
- 截图 `human-26-consent-inline-next-to-send.png`：未勾的那条就在输入框下面，看得见、点得着

## 这一趟 Agent 真做了什么（不是造好的方案）

按「发送」之后（勾完授权），屏幕上的回复是从服务器读回来的真实一轮：

- `walk-04-log.txt:38` 起：Agent 复述了目标，问「第二天下午你更偏爱上哪片湖」，给了三个带理由的选项（什刹海／北海公园／颐和园昆明湖），状态「等待你的决定」，事件计数 7 条、工具结果 1 次
- 点选项是走它自己的口：`POST .../agent/goal-tasks/fb98f0d2-88cd-470c-ad60-a9f332245184/resume` 返回 200（`walk-05-log.txt:56`），事件从 7 条涨到 14 条、工具结果涨到 2 次（`walk-05-log.txt:35`）
- 这轮任务本身也是屏幕上按出来的：`201 POST /journeys/ddfb8c11-…/agent/goal-tasks`（`trial/results/20261022_v3_human_chrome/walk-04-log.txt:82`）
- 第二轮它接着问「第一天上午先看哪一类古迹组合」，又是三个选项（`walk-05-log.txt:35`）

记一条产品断点（还没修）：Agent 可以连续问下去，屏幕上始终有「按讨论的方向开始研究」可以打断，但没有任何一句告诉旅客「问到什么时候算头、什么时候开始出方案」。这一句要在下一刀里补，而不是靠旅客自己猜按钮。

## 量具自己的毛病（说明白）

`walk-05-log.txt:8` 那一次 `uncheck()` 超时是量具的问题：勾选框在屏幕上是可点的（`walk-05-log.txt:14` 的 `PROBE` 里 `rowReachable=true`、`elementAtCentre=INPUT.`），改点整行文字就成功了（`walk-05-log.txt:16`）。没有把这次超时说成产品缺陷。

## 另一条断点：换个窗口打开，自己的行程不见了

同一份 profile 重新起一个浏览器进程（不是刷新），屏幕上回到「你的下一趟旅行，从一句话开始」的创建表单（`trial/results/20261022_v3_human_chrome/walk-04-log-superseded-instrument-fault.txt:3`），`SAME_JOURNEY_OPENED=false`、底部输入条也不在（同文件 `:4` 与 `:6`）；可浏览器本地仍然记着那趟行程的编号（同文件 `:2`）。原因是旅行者凭据放在 sessionStorage：同一标签页刷新还在，换窗口/换进程就没了，而首屏没有任何一句「你有一趟未完成的旅行，回来继续」。这条本轮没修，下一刀要么把入口做出来，要么把话说清楚。

## 还没验的

- 前端 e2e 整套没跑：`playwright.config.ts` 默认用系统 Python 起后端（`ImportError: StrEnum`）。本轮读到 `playwrightEnv.ts:81` 与 `:133` 支持 `CITYNEXUS_PYTHON` 覆盖，下一刀用真解释器跑 `revolution-workspace-actions.spec.ts`、`revolution-visual-travel.spec.ts`、`revolution-mobile-shell.spec.ts` 三枚受影响 spec，读数写在这里，跑不通就标 `NOT_MEASURED`
- 地图与照片：这一趟仍然写着「现实地图 0 处地点」（`walk-05-log.txt:21`），本轮浏览器发的请求全在本机后端（`walk-04-log.txt:82` 起的整段 API 流水，没有一条外部域名）
- A/B/C 三方案、改半天、刷新恢复、正式出发：还没走到
