# Agent 说「已改」，日程没动：这一刀把两件事分开

走查时间：2026-10-22 17:20–17:31（本地）。工具：真实 Chrome 155（独立 profile，调试端口 9333，同一个标签页）。视口 414×900。Journey `ddfb8c11-1692-46ca-81f9-939eba2cb475`，任务 `fb98f0d2-88cd-470c-ad60-a9f332245184`。

## 走到哪了

按「按讨论的方向开始研究」之后，同一趟旅程真的产出了可编辑日程：状态「已有阶段性成果」，屏幕上「已整理 2 天 · 6 项安排」，服务端事件 39 条、工具结果 7 次（`trial/results/20261022_v3_human_chrome/walk-06-log.txt:6`、`:8`、`:11`）。日程层里 Day 1 / Day 2 六个时段都读得回来（`walk-08-log.txt:3` 起）。

刷新与三种视口也量过了：刷新后同一 Journey、6 项安排仍在（`walk-07-log.txt:4`）；390×844、430×932、1366×900 三档都没有横向溢出、发送键都在视口内（`walk-07-log.txt:13`、`:15`、`:17`）。

## 屏幕上发现的谎

旅客在输入框写：「11 月 2 日上午不去故宫了，改成天坛一带，其他安排都别动。」（`walk-08-log.txt:14`）

- 请求真的发出去了：`200 POST .../agent/goal-tasks/fb98f0d2-…/resume`（`walk-08-log.txt:100`）
- Agent 答：「明白，已把 Day1（11/2）上午从「故宫/天安门一带」改为「天坛一带」，其余 slot 全部保留不动。」（`walk-08-log.txt:16`）
- 日程没动：改之前第一条是「Day1 上午：中轴线古迹（故宫/天安门一带）」（`walk-08-log.txt:3`），改之后还是这一句（`walk-08-log.txt:19`），`SCHEDULE_CHANGED_ON_SCREEN=false`（`walk-08-log.txt:25`），工具结果次数仍是 7 次——这一轮根本没调用写工具

一句自信的话 + 一份没变的日程，屏幕上没有任何东西把这两件事分开。这正是任务书要防的那种断点。

## 改了什么

不替模型改口，也不猜它说了什么：服务器在存每一条 Agent 回复时，把这一轮开始与结束时的日程版本号一起存下来，屏幕按这两个数写一句话。

- `backend/app/agent/goal_tasks.py:1404` 记下这一轮开始时的版本，`backend/app/agent/goal_tasks.py:1532` 把 `draft_revision_before` / `draft_revision_after` 存在这条回复上
- `backend/app/agent/goal_dialogue.py:40` 提问类回复同样带上版本（提问不会改日程，两个数相同）
- `frontend/src/trial/mobile/WorkspaceActions.tsx:204` 由这两个数算出那句回执，`frontend/src/trial/mobile/WorkspaceActions.tsx:549` 挂在回复下面：版本变了写「日程：版本 3 → 4」，没变写「这条回复没有改动日程（版本 3）」
- 顺带两处读得下去的修：`frontend/src/trial/mobile/WorkspaceActions.tsx:189` 把模型写的 markdown 读成行（之前屏上出现字面 `**待办核查项**` 和成排的 `- `），`frontend/src/trial/mobile/WorkspaceActions.css:72` 与 `:74` 是它们的排版
- `backend/app/agent/goal_tasks.py:1451` 给收尾那一轮加一条要求：写给旅客的话用平实句子，不要贴内部状态码（屏上出现过 `（REAL_CITY_DISABLED）`）

## 钉住的读数

`backend/tests/test_qoder_draft_revision_receipt_r1.py` 三格：只说不写的回复两个版本相同；真写成功的一格版本发生变化；被拒的写（日期不在旅程区间内，`DRAFT_DATE_OUTSIDE_JOURNEY`）与「已保存」这句话各自留在自己的位置上。跑批：本文件加 `test_goal_tasks.py`、`test_goal_dialogue.py`、`test_qoder_draft_door_reason_codes_r1.py` 共 23 passed（`cd backend && D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest tests/test_qoder_draft_revision_receipt_r1.py tests/test_goal_tasks.py tests/test_goal_dialogue.py tests/test_qoder_draft_door_reason_codes_r1.py -q`）。

一件差点说错的事：我原以为「日期在旅程之外会被静默丢掉」，实测工具是明确拒绝并给出 `DRAFT_DATE_OUTSIDE_JOURNEY`（已写成第三格断言），所以这不是缺陷，只是我第一版探针读错了地方。

## 还没在屏上看到的

回执这句话要在真实屏幕上读一次才算数，而这需要重启这台机器上那套人肉走查后端；重启会换掉旅行者签名密钥（`_cmdr_v3_serve_human_r1.py:47` 每次启动随机生成），当前这趟 Journey 的会话会失效。所以顺序是：先按新代码起一套干净栈，从第一句话走到正式出发，回执、A/B/C 三方案、半天改动、出发门一起在那一趟上读。
