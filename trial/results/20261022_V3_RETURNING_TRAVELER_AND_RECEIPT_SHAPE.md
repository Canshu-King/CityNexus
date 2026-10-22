# V3 真人走查第十一棒：Agent 说的话与日程真的动了没有，以及关掉浏览器再回来的人

日期：2026-10-22（本地 18:0x–19:1x）。驱动方式：本机真实 Chrome 155，隔离测试 profile，CDP 9333，
414×900 视口；每一屏文字都从渲染后的 DOM 读回来，截图逐张用眼睛看过。工具替代说明：chrome-use 的
截图通道自 10-21 起仍是坏的（worker 挂了 31.9 小时，要主人重启扩展），本轮沿用已点名的替代腿
=真实 Chrome + CDP，不是无头、不是 DOM 注入。

---

## 一、屏上读到的三件事（改动之前）

### 1. Agent 的一轮里保存了日程，屏幕上却写着「这条回复没有改动日程」

`walk-11-log.txt:26` 屏上回执行原文：

```
RECEIPT_LINES=["这条回复没有改动日程（版本 0）","这条回复没有改动日程（版本 0）","这条回复没有改动日程（版本 1）"]
```

同一轮 `walk-11-log.txt:24` 是 `RESEARCH_POLL_6 t=60s working=false draftSlots=6`——日程从 0 格变成 6 格，
草案版本从 0 走到 1（服务端对拍见 `walk-11-server-side-transcript-readback.txt:8`，那一轮的
`[assistant] rev 1->1`）。旅客在同一屏上看见 6 条安排出现，同时看见一句「这条回复没有改动日程」。

原因在服务端而不是前端：`ask_traveler` 把回执两半都盖成"写这条问题时"的版本号
（旧代码 `app/agent/goal_dialogue.py` 注释原话是「A question never moves the schedule」）。一轮里
先保存草案、再用一个问题收尾，是这个 Agent 最常见的形状，所以这句"没有改动"天天在骗人。

### 2. 旅客读到的句子里带着 JSON 信封的尾巴

`walk-11-log.txt:18` 屏上第一段回复的原文片段：

```
… 第二天下午的湖边轻松散步，你更想选哪片水域？"}] 这条回复没有改动日程（版本 0） 什刹海（后海）…
```

服务端存的话原文（`walk-11-server-side-transcript-readback.txt:5`）：`'第二天下午的湖边轻松散步，你更想选哪片水域？"}]'`；
第二个例子是那一轮的新问题结尾多了一个裸引号（同文件 `:2`）。`"}]` 与 `"` 是工具调用 JSON 的信封符号，
不是模型想对旅客说的话，也不是旅客要打出来的东西。归因到"模型写的"还是"网关拼参数时带进来的"这一步
本轮没有实测读数（见第四节 NOT_MEASURED），修的是"它不许出现在旅客面前"这一道门。

### 3. 关掉浏览器再回来的人，屏幕上没有任何一扇门

`walk-14-log.txt` 是同一个人、同一台机器、只是重开了一次浏览器：

| 屏上位置 | 原文读数 | 行号 |
| --- | --- | --- |
| 本机还留着那趟旅行 | `journey={"id":"7cd5dda8-…","cityName":"北京","status":"DRAFT"}` | `walk-14-log.txt:2` |
| 浏览器会话凭证 | `SESSION bearer=absent session_id=absent` | `walk-14-log.txt:3` |
| 首屏 | 「你的下一趟旅行，从一句话开始 … 想怎么玩？ 目的地 日期与天数 更多偏好 …」 | `walk-14-log.txt:4` |
| 「行程」这一页 | 「开始探索一个地区后，你保存的路线和出发进度会显示在这里。」 | `walk-14-log.txt:7` |
| 「继续这趟」按钮 | `RESUME_BUTTONS=0` | `walk-14-log.txt:12` |

服务器侧那一趟有 6 条已保存的安排（`walk-11-log.txt:24`），本地也记得它，但两条列表都被"这次打开的
会话身份"挡在门外：`frontend/src/trial/RevolutionFirstLook.tsx:283` 的 `loadRecentJourneys()` 第一行就是
`if (!identity) return []`，`frontend/src/trial/RevolutionFirstLook.tsx:893` 的取列表条件是
`if (activeTab !== "trips" || journey || !bearer) { setSavedTrips([]); return; }`。也就是说
「最近的行程」和「行程」两页都要求手里已经有凭证，而凭证只活在 `sessionStorage`
（`frontend/src/lib/travelerSession.ts:1` 定键名，`frontend/src/lib/travelerSession.ts:17` 从 sessionStorage 取），
浏览器进程一走它就没了。

这一条**本轮没有改**：能把旧行程接回来的做法要么让旅客凭证活得比浏览器久，要么给一条带证据的找回流程，
两者都改鉴权边界，属于主人/仲裁的决定，不是界面小修。屏上现在的问题不是"按钮是死的"，而是
**连按钮都不出现**，一个人只能从头再填一遍。

---

## 二、改了什么（服务端两处，各带一条测试）

### A. 回执记的是"这一轮开始时"的版本

`backend/app/agent/goal_dialogue.py:86` 的 `ask_question` 现在接第三个参数，`backend/app/agent/goal_tasks.py:1655`
那一处调用把本轮开始时的 `draft_revision_before_round` 递进去（同一个变量也是文字回复那条路径一直在用的）。
于是一轮里"保存了草案 + 以问题收尾"，屏上回执是「日程：版本 0 → 1」。

### B. 旅客面前不许有 JSON 信封尾巴

`backend/app/agent/goal_dialogue.py:16` 新增 `plain_traveller_text`：只吃**句尾**的 ASCII 信封符号
（`"` `}` `]` `,` 与它们之间的空白），其他一律不动；两个门口都用它——问题正文与选项（`:67`、`:68`、`:78`、`:79`），
以及纯文字回复（`backend/app/agent/goal_tasks.py:1544`）。旅客自己写的字不改（`plain_traveller_text` 只处理
助手侧输出）。若一句话去掉尾巴后是空的，`validate_question` 照旧以 `TRAVELER_QUESTION_INVALID` 拒掉，
不把空壳放到屏上。

测试读数（现读命令与解释器见第五节）：`backend/tests/test_qoder_draft_revision_receipt_r1.py` 十一档全过
（`11 passed in 1.45s`），新增两条分别是「一轮保存草案后以问题收尾 → `rev 0->1` 且屏上没有 `"}]`」与
「信封尾巴规则只咬句尾、放过正常中文句子（含 `预算 ¥500/人`、`什刹海（后海）`）」。目标族回归：
`test_goal_dialogue.py test_goal_tasks.py test_goal_task_routes.py test_goal_draft_patch.py
test_goal_preparation.py test_goal_artifacts.py` → 连上面那套一起 `56 passed in 5.79s`。

---

## 三、本轮仍然没走通的路

- 「准备出发 → 选用这份方案 → ACTIVE」这一段仍未拿到屏上读数。上一代（提交 282ad0e 里的
  `walk-10-log.txt`）走到的是 `DEPARTURE_BUTTON 选用这份方案 visible=false` 与 `0 份正式候选方案`，
  而 `DraftDepartureCard` 里那两步（勾「按以上时间准备方案」→ 按「保存为正式候选方案」）
  当时没有按到。这一代正在补按，读数写进本节末尾，未测出来之前门禁仍是 BLOCKED。
- 方案对比卡：上一代屏上把三版内容作为文字给出了，但 `.rev-goal-variant-card` 数为 0
  （`walk-10-log.txt` 的 `VARIANT_CARDS=0` 与 `VARIANTS_PANE_TAIL` 同时出现）。`GoalDraftVariants.tsx:54-63`
  把未选中的卡片设成 `hidden`，所以那个 0 到底是"只有一张可见"还是"整块没渲染"，本轮要用
  `VARIANT_TABS / VARIANT_VISIBLE_CARD` 两个新读数分开，不再拿一个计数当结论。
- 公开来源的地点事实（照片、票价、营业时间）今天仍然给不出：屏上 `0 处地点`、价格仍是
  `UNKNOWN`/参考估值，这一条不因 Agent 说得肯定而改变。

---

## 四、仪表条件（如实记下，不当成产品结论）

19:00 前后的四次走查里，被驱动的 Chrome **浏览器进程**四次在模型那一轮进行中消失，驱动报
`Target page, context or browser has been closed`，`tasklist` 当时 chrome.exe 计数为 0：

| 尝试 | 起来 | 消失 | 消失时正在做什么 |
| --- | --- | --- | --- |
| 10:42 起（D 盘 profile） | 10:42:19 | 约 10:47–10:48 | 走完首屏到草案，下一棒连不上 |
| 10:49 起（D 盘 profile） | 10:49:15 | 10:48:16 后拒绝连接 | 第二棒第一句就没连上 |
| 11:01（E 盘 profile） | 11:01:31 | 11:02:41 | 发出第一句话后 48 秒 |
| 11:05（E 盘 profile） | 11:05:46 | 11:07:22 | 发出第一句话后 48 秒 |

已排除的两条猜测：内存/页面文件吃紧（现读 commit 上限 73 347 MB、空闲虚拟 30 012 MB，两个页面文件各只用
约 3 GB ⇒ 不是提交上限不够）；Windows 崩溃记录（应用日志近 90 分钟内 chrome.exe 只有三条 INFO 级
`extension_garbage_collector` 记录，没有 1000 号 Application Error）。`profile.exit_type=Crashed`
在**正在运行**的探测实例上同样是 `Crashed`，所以它不能当证据——这条我已撤回。
未识别的成因仍在查，本轮把浏览器自己的 `--log-file` 打开，下一次掉线要拿它的话来写。
另外把测试 profile 从 D 盘（98% 满、余 6.5 GB）搬到 E 盘（余 52 GB）后仍然掉线，所以"盘满"不是解释。

这一条也解释了第三节那条门禁为什么难拿：旅程的凭证随浏览器进程一起消失，重开只能从头开始
（正是第一节第 3 条）。走查改成"一趟一口气走完"，不再依赖跨进程的会话。

NOT_MEASURED：`"}]` 是模型输出还是网关拼参数造成；Chrome 浏览器进程消失的成因。

---

## 六、更正：地点来源不是"网络不通"，是这台机器把出口指向了一个死掉的代理

本文件第四节写下"Chrome 掉线"的同时，`trial/results/20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md` 的门禁里
`AGENT_RESEARCH_GROUNDED = BLOCKED（公开地名来源今天网络不通）` 这一句**是错的**，19:32 现读如下：

```
env HTTPS_PROXY = http://127.0.0.1:7897
netstat -ano | grep LISTENING : 7897 无监听，只有 127.0.0.1:7892 在 LISTENING（pid 36792）
直连 https://photon.komoot.io/api/?q=故宫&limit=2  -> HTTP 200
  {"type":"FeatureCollection","features":[{"type":"Feature","properties":{"osm_type":"R","osm_id":9511883,…
同一 URL 走 env 里的代理 -> URLError <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
https://restapi.amap.com/v3/place/text?keywords=故宫&city=北京&key=NONE -> HTTP 200 body INVALID_USER_KEY(10001)
```

也就是说：这台机器**能**直接访问公开地名来源，而测试栈的后端进程从 shell 继承了
`HTTPS_PROXY=http://127.0.0.1:7897`（Clash Verge 的那条线此刻没有在世，`7892` 才是活着的监听口），
所以每一次真实查询都在本地就被拒绝了。旅客屏上的 `0 处地点`、票价 `UNKNOWN`、
Agent 那句「当前实时地理/票价数据源暂不可用」——那句界面话本身没错，错的是我把它的成因写成了"网络不通"。

本轮做法：新增 `D:/moodle/_cmdr_v3_port_1022/_boot_human_stack_r2.ps1`，起这套真人测试栈时清掉
`HTTP(S)_PROXY/ALL_PROXY` 并置 `NO_PROXY=*`（键仍只从网关自己的文件读进子进程环境，一个字节都没写进文件）。
这一条只改我起的测试栈进程环境，不动主人的系统代理、不动 Clash、不删任何东西。
最后一行那个 `key=NONE` 是我故意传的空值，用来说明这条链路上高德键未配置，不是任何真实密钥。

顺带把同一批"来源不通"的旧结论标为过期：`20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md` 里
`AGENT_RESEARCH_GROUNDED = BLOCKED` 的**原因句**作废，结论本身要等第七节那一趟真走一遍才能重判。

---

## 七、屏上那句"按你说的改"到底改了没有（第三处缺陷与修法）

Edge 那一趟（`walk-20-log.txt`）拿到的读数把第二处的修法照出了漏洞：

| 读数 | 原文 | 行号 |
| --- | --- | --- |
| 研究完那一轮的回执 | `["这条回复没有改动日程（版本 0）","日程：版本 0 → 1"]` | `walk-20-log.txt:20` |
| 旅客要求改半天之后 | `EDIT_RECEIPTS [… "这条回复没有改动日程（版本 1）"]` | `walk-20-log.txt:33` |
| 日程是否真的变了 | `EDIT_CHANGED_SCHEDULE=false` | `walk-20-log.txt:42` |
| Agent 那一轮说的话 | 「收到，按你说的改：**11 月 3 日下午从「湖边散步」换成「什刹海边咖啡馆坐着」，不走路**；其余安排原封不动」 | `walk-20-log.txt:32` 与 `walk-20-server-readback.txt:18` |

上一轮的"只许再用一轮"提醒装在**纯文字回复**那条路上（`not raw_calls`），而模型这一轮是用
`ask_traveler` 收尾的——它把"我已经改好了"写在问题的开头，然后才问下一个问题，于是提醒根本没触发。
服务端对拍把这一步钉死了：`status=NEEDS_DECISION`、`pending_question` 存在、草案版本仍是 1
（`walk-20-server-readback.txt:1` 与 `:2`）。

改法：把这一下检查从"回合结束时"前移到"`ask_traveler` 被真正执行之前"
（`backend/app/agent/goal_tasks.py:1605`，识别词表在 `backend/app/agent/goal_dialogue.py:24`），
命中"话说已经改了但本轮版本没动"时，**不发出这个问题**，只用一回合已经批准过的模型轮要求它二选一：
要么现在用 `replace_draft_slots` 把旅客点名的那半天改掉，要么重新问一个不宣称已改的问题。
这条腿不写工具事件、不计工具次数，所以不会在 Agent 工作过程里留下一次假动作。
测试：`backend/tests/test_qoder_draft_revision_receipt_r1.py` 现在是
`test_a_question_that_reports_a_change_that_never_happened_is_sent_back_once`（宣称已改 → 被退回一轮 →
草案真的出现「TEST_FIXTURE 什刹海边咖啡馆坐着」，版本 1 → 2）与
`test_a_plain_question_without_a_claim_is_left_alone`（只是提问、没宣称改过 → 一次到位，
不多花一轮，屏上仍是 `NEEDS_DECISION`）。整个文件现读 `11 passed in 1.45s`。



## 五、可复现命令

```
# 后端目标族 + 新回执测试
cd D:/moodle/_cmdr_rescue_v3_1022/backend
PYTHONIOENCODING=utf-8 D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest \
  tests/test_qoder_draft_revision_receipt_r1.py -q
PYTHONIOENCODING=utf-8 D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest \
  tests/test_goal_dialogue.py tests/test_goal_tasks.py tests/test_goal_task_routes.py \
  tests/test_goal_draft_patch.py tests/test_goal_preparation.py tests/test_goal_artifacts.py -q

# 走查仪表（真实浏览器，CDP 9333，一趟一口气）
cd D:/moodle/_cmdr_v3_port_1022 && node human_walk_r12.mjs
```

---

## 八、最后一处：输入框打出来的"改半天"当时根本不允许改

`walk-26` 之前那两代（`walk-22`、`walk-23`）同一句话仍然不动日程，服务端对拍给出的不是借口而是状态：
那一轮 `status=NEEDS_DECISION`、`mode DISCUSS`、二十秒就结束（`walk-22-server-readback.txt:1`）。
原因在客户端一句话的默认值上：底部输入框每发一条都带 `interaction_mode=DISCUSS`
（`frontend/src/trial/mobile/WorkspaceActions.tsx:447`），而讨论轮的系统指令原文是
"Do not search, change or save an itinerary in discussion mode"——一个被明令不许动日程的模型，
面对一句改动指令，只剩"说它已经做完了"这一条路可走。

改法只在服务端一处：旅客自己打出的句子如果是指向某一天的改动（改动动词 + 时间词），
而这个任务确实已经有保存的日程，这一轮就按执行轮跑；只问问题的一句话仍然留在讨论轮
（`backend/app/agent/goal_tasks.py:1232`，两张词表在 `backend/app/agent/goal_dialogue.py:37` 与 `:38`）。
两档新测试钉住这条分界：「打字的改半天不再被留在讨论模式」与「关于行程的一句提问仍然是讨论」。

屏上结果（真实浏览器窗口、真人点击、同一 Journey、带真地点的那一代）：

- 回执行 `["这条回复没有改动日程（版本 0）","日程：版本 0 → 1","日程：版本 1 → 2"]` — `walk-26-log.txt:32`
- 第五条安排变成「下午 · 什刹海边咖啡馆坐着（萤火虫咖啡 后海店）」 — `walk-26-log.txt:39`
- `EDIT_CHANGED_SCHEDULE=true` — `walk-26-log.txt:40`
- 刷新之后仍然是那五条 — `walk-26-log.txt:42`

仍未走通：A/B/C 对比卡（`walk-26-log.txt:50` 两个计数都是零）；
「选用这份方案」在唯一有它的那一页上仍然不出现（`walk-22-log.txt:63`）。
