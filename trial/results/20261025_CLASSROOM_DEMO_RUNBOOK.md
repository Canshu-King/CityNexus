# 课堂演示运行手册（3–5 分钟）

**一句话**：平板上点「课堂演示：进入示例行程」→ 打开「行程守护」→ 按「接受这次事件的调整」→ 行程当场变短。

> **2026-10-26 勘误（下面正文里这四句已过期，按这里走）**
> 1. **入口必须有票**：当前课堂栈 `ENTRY_DOOR=PAIRING`，无 `#pair=` 的旧地址会 `403 DEMO_PRESENTER_REQUIRED`；启动器一次发三张票，平板地址带的一次性票 120 秒有效。正文第 13 行"没有尾巴说明还没启用——当前课堂栈就是后一种"作废。
> 2. **按钮叫「接受这次事件的调整」**（控制台 `ClassroomPresenterPanel.tsx:285`）；正文里的「接受这份调整」是旧名。
> 3. **simulation 已合入**：新后端自动建五个 simulation 表，控制台随 run 出现；正文里"只在部署了端点时出现"与"差后端一处接缝"作废（PR #54，82 passed）。
> 4. **守护可以按，也必须按**：真栈成功轮 193 秒、失败轮 18 秒 `RETRYABLE_FAILURE`；失败时控制台有「再请一次守护」，`PAUSED_MODEL_UNAVAILABLE` 且事件已落定时有「事件处理完了，继续模拟」。正文"不要点「交给守护助手」""点了只能重启启动器"作废。
>
> 仍未变：随机城市池真栈 0/3（缺的是折线与城市身份，不是找不到地点），池子 BLOCKED 不挡开演；平板真机 `USER_VERIFIED=PENDING`。

> 今天改过三处，按旧版手册走的人只需知道这些：入口出错时红条固定在首屏顶端（换分页也不消失）；按「行程守护」卡片会自己滚到屏幕中间、按钮不会再被输入条压住；按下「接受这份调整」后页面会回到行程顶部，第一站的变化就在眼前。

## 开演前（电脑上，约 1 分钟）

1. 双击 `D:\moodle\_cmdr_v3_port_1022\start_classroom_demo.bat`（版本库副本：`trial/play_launcher/classroom_demo/start_classroom_demo.bat`，两份同源；脚本默认每次生成随机会话密钥，不写死）。
   它会：把演示库重置成有「北京 · 2日行程」的初始场景 → 起后端 `127.0.0.1:60391` → 起前端 `0.0.0.0:14492` → 预生成一张待接受的调整卡。窗口不要关。
   > 已实测（10-25 01:00）：同一份 bat 真跑到 `DEMO_READY=true`，replan 回 201，提案 PRESENTED。窗口最后会打印平板地址那两行；只看到 `The classroom stack did NOT start` 就是没起来，把窗口里最后一段报错原文留着。
2. 平板连与电脑**同一 WiFi**（地址随 WiFi 重连而变，不要照抄旧值）。
3. 平板浏览器打开启动器最后打印的那行 `Tablet address`（本次形如 `http://<电脑 LAN IP>:14492/revolution#pair=<票>`）。地址**必须带 `#pair=…` 尾巴**：这一支后端 `ENTRY_DOOR=PAIRING`，无票地址回 `403 DEMO_PRESENTER_REQUIRED`（见本节顶部第 1 条勘误）；票 120 秒内有效、只能用一次。
   > 这张票只在两分钟内有效、只能用一次。看到「这张课堂配对票已过期或已用过」时不要反复刷新：回电脑重跑第 1 步，用窗口里新打印的地址；重跑也会把场景恢复成初始状态。
   > 这个地址只在教室 WiFi 内用；不要把 14492 映射到公网或做内网穿透——演示栈的匿名读面还没收紧（Codex 在 Issue #47 处理）。

> 打不开时先看电脑浏览器同一地址；仍打不开就重跑第 1 步（会重置场景）。
>
> **上课前想自己先走一遍**：双击 `D:\moodle\_cmdr_v3_port_1022\rehearse_classroom.bat`（入库副本 `trial/play_launcher/classroom_demo/rehearse_classroom.bat`）。它会准备场景 → 用手机视口走完整链（会消耗掉那张提案）→ 再准备一次把场景恢复到 09:00 一张待接受提案。绿色走到最后一行就是通过；彩排会重写 `classroom-rehearsal-14.txt`，属正常。
>
> 随时自检（不改场景、不打印任何凭据）：
> `D:\moodle\CityNexus\.venv\Scripts\python.exe trial/play_launcher/classroom_demo/classroom_demo_selfcheck_r1.py`
> 看到 `DEMO_READY=true`、`JOURNEY_STATUS=ACTIVE`、`PROPOSAL_WAITING` 有 id、`CLOCK` 是 09:00 即可开演。
> 同一份输出里的 `SIM_CONSOLE` 只是情报：`NOT_DEPLOYED` 表示课堂后端还没有模拟执行端点、控制台不出现；`AVAILABLE:<状态>` 表示控制台已接上，此时时钟条会自动让位。

## 台上（实测 18 秒，可慢慢讲）

4. 点底部「我的旅程」。
5. 点「课堂演示：进入示例行程」——进入「北京 · 2日行程」。
6. 指一下屏：第一站故宫博物院、之后天坛公园，路线「约 78 分钟」来自真实地图。
7. 点「行程守护」，卡片会自己滚到眼前：「找到一份可行的调整 / 移除故宫博物院；路上少 66 分钟。」
8. 点「接受这份调整」。页面自动刷新一次，第一站变成「天坛公园 · 12月3日 09:00」。
9. （可选 1 分钟）往下滚到「课堂时空模拟」条，先点「到下一站」：当前站从「故宫博物院」变「天坛公园」，走的是服务器状态机（模拟执行，不是物理到场），刷新后仍是天坛；再点「+1 小时」，模拟时间从 09:00 变 10:00。水印一直写着「不是实际定位或真实灾情」。
10. （可选 40 秒）点上方「地图」→「加载地图」，等一两秒让瓦片画出来：真实 OSM 底图上蓝色圆点在天坛，状态行标明 WGS84 与「不是物理 GPS」。
11. 收一句：**变化是服务器检测到的，方案是服务器生成的，只有你按下「接受」才改行程。**

## 如果当场出问题

- 卡片没出现：重开「行程守护」或等 3 秒；仍无 → 重跑第 1 步。
- 平板连不上：用电脑浏览器打开同一地址演示（步骤相同）。
先认屏幕上那条红色提示（它现在贴在首屏顶端，不会随分页消失）：
  - 「课堂入口需要启动器签发的一次性配对链接」：打开的是不带票的旧地址。回电脑重跑第 1 步，用带 `#pair=` 的那条。
  - 「这张课堂配对票已过期或已用过」：票超过两分钟或已经用过一次。同样重跑第 1 步拿新地址。
  - 「这趟课堂演示已经走完并封存」：这趟已经走到第二天结束。要再演一遍就重跑第 1 步（会重建场景），不要在旧屏上重来。
- 误点「开始探索 →」不会丢课堂：底部「我的旅程」就回到两个按钮那一屏，再点「课堂演示：进入示例行程」即可（实测回头路通，见走查一百一十七）。
- 误点「暂不调整」：提案会被记为已拒绝、卡片消失，这一课就少了那张调整卡；重跑第 1 步重新生成，不要试图在旧屏上找回。
- 完全没网：展示这三张截图（都是真话标注之后拍的）——
  - `trial/results/20261022_v3_human_chrome/rehearsal11-origin.png`（提案卡 + 规则引擎来源 + 模拟信号）
  - `trial/results/20261022_v3_human_chrome/rehearsal5-final.png`（按完后第一站天坛 + 时钟 10:00）
  - `trial/results/20261022_v3_human_chrome/rehearsal10-map.png`（地图蓝点在天坛）

## 已知边界（照实说，不必展开）

- 「课堂演示」入口只在演示模式存在（`CITYNEXUS_DEMO_MODE=true`），生产不出现。
- 手机屏上同时有旧恢复面板的两张「方案 A/B」卡（带内部 id）；正式入口是流程第 7 步那张。
- 平板上点按的实测仍待主人亲自走一遍（`TABLET_OPEN` 仅本机浏览器验证）。
- 时空模拟（虚拟时钟、地图蓝点）在面板浮球里，是另一段，不占这 5 分钟。
- 提案卡下那行字会随提案来源变化：本次写「规则引擎生成 · 不是大模型现场推理」，不要改口成「模型现场想出来的」。
- 事件行写「模拟供应商信号 · 课堂注入，非景区官方公告」：闭馆是课堂注入的场景，不是景区真发了公告。
- 「当前恢复第 3 轮」是库里真实历史轮次（前两轮已被取代），不是杜撰的数字。
- 地图瓦片首次加载要等 1–2 秒；蓝点可能先出现、底图后到，别在这半秒里下「地图坏了」的结论。
- 底图真挂（瓦片全被拦）时屏上会写「底图暂时没有加载成功，下面的地点列表仍可查看。」，蓝点与署名都在；这条阴性路径已实测（走查一百二十二）。
- 接受提案后回看「行程守护」，行动块仍写「需要调整行程 / 问题仍待解决」、恢复轮次会增长——那是**检测当时的结论**（Guardian 侧还没回写），不是接受失败；以行程屏第一站为准。
- 电脑现在连的是校园网「TUTE-Student」（WLAN 类别 Public，Node 的入站规则覆盖 Public）；平板要连**同一个校园网并完成认证**。校园网可能有终端隔离或夜间断网：平板打不开时先看电脑自己的浏览器，再退回手机热点（电脑连热点后重跑第 1 步拿新地址）。
- 这堂课里「守护」是**课前预跑**的：真模型在隔离栈上实测要两百多秒到五分半以上（`guardian-model-walk-1.txt:5`、`classroom-presenter-model-loop-26.txt:8`），不在三到五分钟的课堂预算里。讲解时说的是「服务器已经检测过、这张卡是它生成的」，不是「我现在让它现场想」。
- 值守日志 `_cmdr_v3_live_1022/classroom_watch.log` 每拍末尾带 `DISK_D=`（D 盘剩余吉字节），低于 0.3 就先搬冷数据再加写。若看到 ALERT 且时间落在演练/走查的几分钟内，多半是那一轮把场景走到了完成态；脚本不自动重置，恢复开局跑一次第 1 步即可。
- 接上模拟执行后，控制台上的「交给守护助手」很慢：隔离栈实测**两百多秒**才回来并生成一张调整卡（`classroom-preseed-vs-run-1.txt:8`），客户端等两分钟就先超时，老师看到的是按钮一直转（同一时刻库里是守护进行中，`:7`）。课堂上不要按这一键；模型确实可用时才把它当课后演示。
- 守护生成的新卡不会顶掉屏上已有的那张：行程守护面板取列表里第一张待接受的卡，列表按创建时间升序（`frontend/src/trial/mobile/GuardianRealityPanel.tsx:241`、`backend/app/main.py:25389`），所以课堂上按了守护，屏上仍是早先那张。
- 课堂主链走时钟条；`SimulationRun` 控制台只在后端部署了 simulation 端点时出现，且 run 存在后时钟条会自动让位（按钮变灰并写明已交给控制台）。两者不要混着按。
- 模拟两日走完会把行程标成已完成并封存（`classroom-presenter-start-24.txt:6`）；再演一遍必须重启课堂演示（重新跑第 1 步），不能在旧屏上重来。
- 「接受提案 → 继续模拟」这条真 Agent 闭环目前差后端一处接缝（注入事件与守护拾起的事件不是同一件），补丁建议见 `20261025_CODEX_SIMULATION_SCENE_TRIGGER_PATCH.md`；课堂上仍以时钟条 + 原生提案接受为准。

## 短回执（来自 `prepare_classroom_scene_r1.py` 的现读）

```text
DEMO_READY=1
WINDOWS_START=start_classroom_demo.bat
TABLET_OPEN=http://10.12.35.143:14492/revolution   (tablet: UNVERIFIED；以启动器现读为准)
AGENT_QA=direct-replan-only (agent path verified separately)
REAL_POI=1
SAVED_PLAN=1
RESTART_SESSION=1
FALLBACK_SCREENSHOT=trial/results/20261022_v3_human_chrome/rehearsal11-origin.png
```

## 讲解稿（每步一两句）

### 讲解稿与屏上文字的对照（照着念不会打架）

| 讲解句 | 屏上对应 | 读在哪 |
| --- | --- | --- |
| 真实地点与路线 | 「第一站：故宫博物院 · 12月3日 09:00」「已找到准确路线 · 约 78 分钟」 | `classroom-rehearsal-14.txt`、`classroom-desktop-flow-39-1-entry.png` |
| 模拟的闭馆信号 | 事件行「模拟供应商信号 · 课堂注入，非景区官方公告」 | 同上截图 |
| 服务器生成的调整卡 | 「找到一份可行的调整」「移除故宫博物院；路上少 66 分钟。」「规则引擎生成 · 不是大模型现场推理」 | `classroom-desktop-card-36.txt:3` |
| 等我按下接受 | 按钮「接受这份调整 / 暂不调整」 | `classroom-desktop-flow-39-2-card.png` |
| 时间推进一小时 | 「模拟时间：12/03 10:00 · 服务器第 1 版」 | `classroom-rehearsal-14.txt` 的 CLOCK_AFTER |
| 蓝点在真实地图上 | 「模拟旅客：天坛公园 · 39.8805, 116.4046（WGS84，模拟位置，不是物理 GPS）」 | `classroom-rehearsal-14.txt` 的 DOT_STATE |
| 走完会封存 | 「模拟行程已完成 · 不是实际到场」、按钮变灰 | `classroom-finish-47-end.png` |


1. **入口**：「这是一个会自己看路况、自己改方案的旅行助手；今天用一趟已出发的北京行程演示。」
2. **行程**：「这趟安排用的是真实地点与路线；故宫现在正在执行。」
3. **守护**：「后台的守护器收到一条模拟的闭馆信号（屏上也标着『课堂注入』），服务器自己生成了这张调整卡——不是我提前写好的台词。」屏上事件行写的是「模拟供应商信号 · 课堂注入」：闭馆这个场景是课堂注入的，从信号进来到提案生成这三步由服务器真的执行。
4. **接受**：「它没有直接改行程，它在等我按下接受。按下后，第一站真的变成天坛，路线上也少了一段步行。」
5. **时钟与地图**：「课堂时空模拟把时间推进一小时、把旅客位置画在真实地图上；水印一直提示这不是实际定位或真实灾情。」
6. **收束**：「场景是模拟的，但处理是真的：信号进服务器、提案由服务器算出、只有我按下接受才改行程，三步都在服务器上记账。」

## 2026-10-25 晚：时钟条接真实模拟执行（`391f2cd5db` + `2130cbf675`）

- **LAN 票门阴性**：隔离栈（Codex 后端 `60400` + Vite `0.0.0.0:14495` 反代）从 LAN 请求 `/api/v1/demo/session`，直连 / 经代理 / 带 LAN Origin 三档全 `403 DEMO_PRESENTER_REQUIRED`，未发 token。回执 `presenter-proxy-bypass-1.txt`。UI 不搬 presenter key。
- **时钟条接 run**：run 存在时「+30 分钟」「+1 小时」发 `advance(minutes)`；「到下一站」循环 `advance` 直到本站完成或暂停；点前先读 `/runs/current`（避免刚开演时误发旧时钟，实测会 `http_status=409`）。旧时钟/旧活动 mutation 在 run 存在时完全不发。
- **两面板同步**：控制台 10 秒轮询 + 时钟条派发 `citynexus:simulation-run`；`PAUSED_REQUIRES_MISSION` 下不再显示服务端会拒的「继续模拟」。
- **390px 屏证**（夹具栈，见下）：
  - `clock-run-ui-1.txt`：09:00 第 0 步 → +30 → 09:30 第 1 步 → +30 → 10:00 第 2 步 → 到下一站 → 12:18 第 6 步；刷新同一步。
  - `clock-two-day-61.txt`：连按「到下一站」五次走完两日：10:00 → 12:18 → 20:18 → 次日 10:00 → 次日 15:00 `SIMULATED_COMPLETED`；三按钮禁用；屏上「模拟行程已完成 · 不是实际到场」。
  - `clock-scene-guardian-59.txt`：注入「下雨」→「等待守护决策」；「交给守护助手」→「缺少守护任务」；不再出现死按钮。
  - `clock-completed-60.txt`：历史已完成行程入口仍显示封存红条、无时钟条（完成态入口问题归 #47）。
- **夹具披露**：课堂库的 PLANNED 行程真实 `/start` 被 `PLACE_UNAVAILABLE` 拒；为验证 UI 接线，只在**复制库**把该行程/方案/首站置 ACTIVE（`_clock_run_fixture_r1.py` 首行写明），`runs/advance/scenes/guardian` 全是浏览器按钮发出的真 HTTP 调用。**不能拿这套夹具替代「新 run 从课堂开演」的证据。**
- **仍阻塞课堂开演**：`cities` = 1 城、POI 56、routes 0、`BLOCKED`（缺 `VERIFIED_CITY_ADCODE_REQUIRED` + `AT_LEAST_3_CAPTURED_ROUTES_REQUIRED`），`required_city_count=3`。等 Codex #47 的「先 1 城同 run Day2」口径；在那之前课堂仍用本机投屏 + 独立演示库。

### 现场库只读副本上的两日闭环（21:08）

- 源：`_cmdr_v3_live_1022/citynexus_v3_demo_1025.db`（课堂栈正在用的库）**只读复制**，源库未写。
- 该库的 journey 已是 ACTIVE、首站 COMPLETED、当前站 12-03 14:00、第三站次日 09:00；在副本上启动 Codex 后端（自动建表）后直接 `POST /simulation/runs` 成功（UI 点「开演」）。
- 390px 连按两次「到下一站」走完：`12/03 15:00 第 4 步` → `12/04 10:00 第 8 步 SIMULATED_COMPLETED`；三按钮禁用。回执 `clock-two-day-livecopy-61.txt`，截图 `classroom-clock-run-61-live-finish.png`。
- 边界：这是「已出发的现场行程」继续走完，不是「从 PLANNED 新开演」；课堂栈本体仍跑旧后端（watch 行 `SIM_CONSOLE=NOT_DEPLOYED`），Codex 后端合入并重启后才会在课堂出现这块控制台。

## 2026-10-25 21:26：Codex 隐私与执行内核已合入并上课堂栈（`de06e6a7` / `5f05540`）

- **合入**：codex 尖 `6136d0a1` → rescue（merge commit `de06e6a7`），零冲突；合并树后端五套 issue47/49 测试 **80 passed**，前端 `tsc` 清。
- **部署**：用课堂启动器 `prepare_classroom_scene_r1.py` 重启（按既定行为从 play 库重置演示库）。新后端建出 simulation 五张表；`/api/v1/demo/session` 无 key → **403 `DEMO_PRESENTER_REQUIRED`**（`entry-door-62.txt`，`ENTRY_DOOR=PAIRING`）；`/health` 200。
- **390px 真栈两日**：屏上「开演」创建 run → 两次「到下一站」：`12/03 15:00 第 4 步` → `12/04 10:00 第 8 步 SIMULATED_COMPLETED`，三按钮禁用，无 console 错误。回执 `clock-two-day-classroom-62.txt`，截图 `classroom-clock-run-62-live-classroom.png`。
- **入口链接**：启动器打印的平板链接是**一次性票、120 秒有效**；过期就再双击启动器（会重置演示库并打印新链接）。
- **平板 `USER_VERIFIED` 仍 PENDING**（等主人亲自点）。

### 城市池与「1 城同 run Day2」的真相（21:28）

- 课堂真栈 `GET .../simulation/cities?seed=17` = 1 城（CN-RV-3507014DDE2C）、POI 56、routes 0、`BLOCKED`（缺城市身份/捕获路线），`required_city_count=3`（`cities-classroom-62.txt`）。
- **但这不挡开演**：`POST /simulation/runs` 只看 journey/plan 是否 ACTIVE，两日已走完。也就是说号令者要的「先 1 城同 run Day2」已经在课堂真栈成立；池子那行只是提示。
- 因此控制台文案是「可用 0 座，标准要 3 座；这趟演示用行程自己的城市，仍可开演」。

## 平板验收（五分钟，给主人）

1. 电脑双击 `start_classroom_demo.bat`，等窗口打印「Classroom ready」和平板地址。
2. 平板连同一 Wi-Fi，浏览器打开那行地址（**2 分钟内有效**；过期就再双击启动器）。
3. 滑到「课堂时空模拟」：应看到「模拟时间：12/03 09:00 · 服务器第 N 版」。
4. 滑到「课堂控制台 · 模拟执行」，点「开演（模拟两日）」；时钟条应变为「执行第 0 步 · 模拟进行中」。
5. 点「到下一站」两次：第一次到 12/03 15:00，第二次到 12/04 10:00「模拟行程已完成」（步数会随之前按过几次 +30 而变，以屏上时间和状态为准）。
6. 点「刷新读数」，历史里应出现「两日走完」。
7. 三格回执：开演后、第一次到站、完成态（截屏即可）。

### 平板等价路径：经 LAN IP 真走一遍（21:35）

- 重启启动器后，用 LAN 地址 `http://10.12.35.143:14492`（不是 127.0.0.1）加票门进入，390px：开演 → 09:30（第 1 步）→ 10:00（第 2 步）→ 到下一站 15:00（第 6 步）→ 刷新同一步；城市池文案与两块面板同步；无 console 错误。
- 回执 `clock-run-lan-63.txt`，截图 `classroom-clock-run-63-{pre,a,b,c,d}.png`。
- 仍缺的只有**主人亲自用平板点**（`USER_VERIFIED`）。

### P0-4 证据链：同一条 run（21:40）

- 课堂真栈当前 run：`7911eaee-0985-4816-af86-29eed5059c02`（journey `2e9cd67d`、city `CN-RV-3507014DDE2C`、seed 17、sequence 6、RUNNING、12/03 15:00）。这就是 LAN 探针 `clock-run-lan-63.txt` 第 6 步驱动的那一条。
- loopback 两日验收（`clock-two-day-classroom-62.txt`）走完在启动器重置前的另一条 run 上，那条的 id 已被重置覆盖、未留读数——不冒充。
- 读数：`run-id-classroom-64.txt`。

### 单一状态链实测（21:57，课堂库只读副本）

- 合并后端 + 课堂库副本（源库未写）：先用当前 sequence 推进（第 6 → 7 步、12/04 09:00），再用旧 sequence 推进 → `409 SIMULATION_SEQUENCE_STALE`；经旧 `/demo/simulation-clock/{journey}/advance` → `409 USE_SIMULATION_RUN_ADVANCE`，run 不动（仍第 7 步）。
- 回执 `single-state-chain-65.txt`；探针 `_single_state_chain_r1.py`。这与 UI 里那条竞态 409 相互印证。

### 票门一次性与无 key 拒绝（22:00，课堂库只读副本）

- 发票 201 → 首次兑换 200（拿到 token）→ **同一票二次兑换 401 `DEMO_PAIRING_INVALID_OR_EXPIRED`**；伪造四十三字符票 401 同码；不带 presenter key 发票 403 `DEMO_PRESENTER_REQUIRED`。
- 回执 `pairing-replay-66.txt`；探针 `_pairing_replay_r1.py`。源库未写。

### 一套推进控件（22:05）

- 控制台删掉「走到下一阶段」「快进一小时」两个按钮（与时钟条的三个键同义不同词）；RUNNING 时只留一句「推进用上面的『课堂时空模拟』三个键；这里只管事件、守护和恢复」+「刷新读数」。
- 390px 屏证：`clock-run-ui-1.txt`（+30 → 09:30 第 1 步、+30 → 10:00 第 2 步、到下一站 → 12:18 第 6 步）+ `classroom-clock-run-58-b.png`。

### 行程卡按状态改词（22:09）

- 首屏三卡的第一枚原固定写「准备出发」，在已出发的旅程上会让人以为还没走；现按状态显示「行程进行中」「行程已结束」，只有未出发才叫「准备出发」（`data-testid=rev-open-trip`）。
- 390px 屏证 `classroom-clock-run-58-b.png`。

### 22:31 合入后一键核对已修好并全绿

- 启动器现在一次发三张票（`.demo_pairing_ticket` 的 `tickets` 数组），`after_merge_check_r1.py` 每支探针各兑一张；`ticketed_entry`/`projector_card`/`lan_path` 三支 rc 0，`all_green=true`。
- 顺带修了两支旧探针的票门入口（r36 用 env 票、r27 加 `#pair=` 并跳过旧菜单导航）——一张票只能用一次，三支共用在旧脚本里必然失败。

### 01:54 平板验收的客观读数（不等于 USER_VERIFIED）

- 仪器 `_tablet_evidence_r1.py`（只读）：解析当前后端日志周期的请求，统计非 loopback 客户端与路径，并读 run 的 sequence/status；落盘 `tablet-evidence-<时间>.txt`。
- 首跑抓到仪器自己的 bug：uvicorn 行以 `INFO:` 开头，我却用行首匹配 IP，于是 `requests=0` 与 `grep` 的 137 条打架；改成 `search` 后读数 136 条、外部 0 条。
- 01:54 读数：`NO_EXTERNAL_CLIENT`（外部 0），run `e354b9da…` 第 0 步 RUNNING、12/03 09:00，session 文件 240 秒新旧。平板还没访问过；且「有外部请求」也只证明有设备访问，不等于主人亲手点。

### 01:57 值守的夜间报警落点

- watch 每拍 OK 时删除 `classroom_ALERT.txt`；ALERT 时把那一拍与处理提示写进该文件（先跑 `classroom_demo_selfcheck_r1.py` 看哪项红，重跑 `start_classroom_demo.bat` 可重建场景；票过期不算 ALERT）。日志仍逐拍追加。
- 重启后首拍 `01:57:03 OK … SESSION=LIVE … SIM_CONSOLE=AVAILABLE:RUNNING`，ALERT 文件不存在。

### 01:59 完成态（journey COMPLETED）的屏上行为

- 用带 run 的 COMPLETED 副本复测：票门进入后是封存红条 + 行程空态，**时钟条与控制台都不渲染**（`clock-completed-60.txt`、`classroom-clock-run-60-completed.png`）。
- 所以老师点完第二次「到下一站」当下仍看得到完成态；刷新或重进才回封存页。给时钟条放宽 ACTIVE 条件不会改变这一点，未改代码。

### 02:05 接受调整支线的真读数（副本，无模型）

- 启动器留下的 1 条 `PRESENTED` 提案（`b00c1d49`，提议方案 `f84adc05`）→ `POST /replans/{id}/accept` 200 → journey 的 `active_plan_version_id` 从 `e74a5edb` 换成 `f84adc05`，提案状态变 `ACCEPTED`。
- run 若已开演，下次 `advance` 会因 `state.plan_version_id` 与 journey 不一致追加一次 `SIM_PLAN_CHANGED` 并继续用新方案（`backend/app/simulation/runtime.py` 的设计），不中断。
- 回执 `proposal-accept-68.txt`；探针 `_proposal_accept_r1.py`。

### 02:08 已知死锁（#47 P0）与现场临时做法

- 症状：run 在 `PAUSED_FOR_ACCEPTANCE`，但 `progress.guardian_runs[0].proposal_id=null`、`proposals=[]`；两个事件都 DETECTED，`/resume` 被 `SIMULATION_EVENT_REQUIRES_SIGNED_RESOLUTION` 拦 → 按「继续模拟」无效。
- 触发条件（实测）：`AI_ENABLED=false` + 三枚 key 移除、库里存在 prepare 的旧 CLOSURE 事件与 run 注入的新事件。guardian_run 绑 `d61152b8`，但产出提案绑到旧事件 `880cec4e`。
- 现场做法：**Codex 修复前不要点「交给守护助手」**；守护支线只做「看提案 + 接受」。点了只能重启启动器（会重置库）。
- 已报 #47（P0，四条请求 + DB 行），全文 `20261025_GUARDIAN_AI_SWITCH_REPORT.md`。

### 02:10 死锁态的屏上做法（已落地）

- `PAUSED_FOR_ACCEPTANCE` 时面板先读 `/runs/{id}/progress`：若没有 `PRESENTED` 提案、`guardian_runs[].proposal_id` 也空，**不显示「继续模拟」**，改显示「守护没有交出可接受的提案…请重启课堂演示（双击启动器）」。
- 390px 屏证（死锁副本 probe23）：`acceptance-note-70.txt`、`classroom-clock-run-70-acceptance.png`；`RESUME_BUTTONS 0`。
- 有提案时仍显示「继续模拟」（resume 门不变）；投影缺 `proposal_id` 是 #47 的 bug，修复后这段判断会自动走回有提案分支。

### 02:15 resume 门已验证（夹具：事件已解决）

- 副本：run RUNNING → 注入 CLOSURE → `PAUSED_FOR_GUARDIAN`；把 pending event 置 `RESOLVED`（一行，夹具披露）→ `POST /runs/{id}/resume` **200**，status `RUNNING`、sequence 2。
- 回执 `resume-after-resolved-69.txt`。至此 P0-2 的 `/runs`、`/advance`、`/scenes`、`/guardian`、`/resume` 五动作都有读数；生产里 resume 要先由守护或接受把事件解决（死锁见 #47）。

### 02:16 票门彩排通过（阶段 A 第 4 步）

- 带票直达 → 守护提案「移除故宫博物院；路上少 66 分钟」（卡片在视口内，y=384 h=162）→ 接受 → 第一站变天坛公园 → 刷新后时钟 10:00 → 蓝点天坛（39.8805, 116.4046，WGS84 模拟位置）；25.1 秒、无 console 错误（`classroom-rehearsal-14.txt`）。
- 彩排会消费提案并改计划；跑完已用启动器恢复开场（`CLOCK=09:00`、`SIM_CONSOLE=NOT_STARTED`、新票、`DEMO_READY=true`）。
- 这也印证速查卡第 8 条：守护支线只需「看提案 + 接受」，不需要按「交给守护助手」。

### 02:19 控制台不再因一次网络抖动消失

- 之前任何一次 `refresh` 抛错（例如代理返回非 JSON）都会把 `hidden` 置真，控制台永久消失；progress 载荷坏掉时还会把 `acceptanceHasProposal` 置假、藏掉「继续模拟」。
- 现在：tick 的 catch 不再隐藏面板（只有两个端点都 404/405 才隐藏）；progress 坏载荷保留上一次读数。正常路径用 r58 复跑确认无回归（+30 → 09:30/10:00、到下一站 12:18 第 6 步、刷新同步、`ERRORS []`）。

- 02:21 已用真拦截复测：把 `.../runs/*/progress` 与 `/api/v1/plans/*` 改成 `502 text/html` 持续十三秒（跨一次十秒轮询），控制台仍在（`PRESENTER_VISIBLE 1`）、状态与推进提示都在、`ERRORS []`（`console-blip-71.txt`、`classroom-console-blip-71.png`）。

### 02:23 平板视口的两日链（1024×768）

- 夹具栈在 1024×768 走完：两次「到下一站」到 `12/04 10:00` 完成、三键禁用，无 console 错误；回执 `tablet-two-day-72.txt`、截图 `classroom-tablet-two-day-72.png`。
- 顺带抓到夹具自己的一个 bug：它把 `PAIR_OUT` 写死覆盖外部传入，导致这次回执落到手机版文件、把 r58 的手机回执顶掉（已从 git 恢复）；改成 `setdefault`。
- 这仍不是主人亲手点，`USER_VERIFIED` 保持 PENDING。

### 02:30 平板形状的命中缺陷已修（1024×768）

- 量到的缺陷：平板下时钟条三键在 y=640，`elementFromPoint` 命中 `TEXTAREA`——被固定在 `bottom:77px` 的 `.rev-mission-chat-dock` 与底部导航压住，手指点会打进输入框。
- 修法：`@media (min-width: 768px) { body:has([data-testid="rev-classroom-clock"]) .rev-mission-chat-dock { display: none } }`——只在课堂屏的平板形状隐藏聊天 dock，手机保持原样。
- 复测：`rev-open-trip`、`+30 分钟`、`+1 小时`、`到下一站` 四枚 `hit=true`、`inViewport=true`、`ERRORS []`（`tablet-hit-73.txt`、`classroom-tablet-hit-73.png`）；390 手机 r58 复跑无回归。
- 代价：课堂平板上没有页面级聊天 dock（助手输入框随之隐藏）；课堂主线用时钟条与调整卡。

### 02:42 带票入口直接落在「我的旅程」，首屏有控制台入口

- 之前：配对成功后仍停在「探索」页，而时钟条在页面 y≈2693（390）／2972（1024），老师要翻三屏多才找得到；页面上也没有任何指向控制台的提示。排查时确认 `MissionCockpit` 只在 `activeTab==="trips"` 时带 `space="journey"`，原先的跳转按钮因此从未渲染。
- 现在：① 配对成功后 `setActiveTab("trips")`（只作用于票门分支）；② 首屏在图层切换键下方显示一条课堂入口「课堂演示 · 模拟时间与推进都在课堂控制台里 / 去课堂控制台 ↓」，点按滚到时钟条；③ 若时钟条还没加载，按钮会等 900ms 重试一次，仍找不到就显示「这台机器没有课堂模拟控制台」而不是死按钮；④ 标题副句改为独立一行，不再与行程名粘连（平板实测「北京 · 2日行程旅途正在继续」）。
- 屏上读数（`jump-clock-76.txt`，真栈、两视口、无 console 错误）：390×844 入口 `top=405`、`inView=true`、`hitSelf=true`，点击后 `clockTop=0`；1024×768 入口 `top=455`、`inView=true`、`hitSelf=true`，点击后 `clockTop=0`。截图 `classroom-jump-phone-before-76.png`、`classroom-jump-phone-76.png`、`classroom-jump-tablet-before-76.png`、`classroom-jump-tablet-76.png`。
- 03:30 又补投影 1280×900：入口条 `top=477`、`hitSelf=true`，点击后 `clockTop=0`（`jump-clock-87.txt`、`classroom-jump-projector-before-87.png`）。三档视口的判定已并入证据索引。
- 回归：课堂真栈复跑开演三键（`clock-run-ui-77.txt`）：开演 → +30 两次（09:30 第 1 步、10:00 第 2 步）→ 到下一站（15:00 第 6 步）→ 刷新同一步，`ERRORS []`；随后启动器恢复开场（`CLOCK=09:00`、`SIM_CONSOLE=NOT_STARTED`、`DEMO_READY=true`、`ENTRY_DOOR=PAIRING`）。
- 提交 `86fed39052`（本枝），改动只含 `MissionCockpit.tsx/.css`、`RevolutionFirstLook.tsx` 的配对落页与探针/证据。

### 02:44 入口落位后的平板回归

- 命中：1024×768 开演后四控件 `hit=true`、`inViewport=true`、`ERRORS []`（`rev-open-trip` y=350、三键 y=640；`tablet-hit-73.txt`、`classroom-tablet-hit-73.png`）。
- 聊天坞：手机 390 仍是 `dock=flex` 且时钟键 `hit=true`；平板 1024 是 `dock=none` 且时钟键 `hit=true`；两视口无 console 错误（`live-dock-75.txt`、`classroom-live-phone-75.png`、`classroom-live-tablet-75.png`）。
- 页面因入口条增高约 25px（手机 docHeight 4686、平板 5074），时钟条位置随之下移；跳转按钮仍一步到位。
- 回归后已重置开场：`CLOCK=2026-12-03T09:00:00+08:00`、`CLOCK_VERSION=0`、`SIM_CONSOLE=AVAILABLE:NOT_STARTED`、`ENTRY_DOOR=PAIRING`。

### 03:22 守护链在真栈闭环（PR #54 合入后）

- 合入 Codex 的 PR #54（merge `cedeaf2800`），CI 范围 82 passed；课堂栈重启后三探针 all_green。
- 现场四次失败/成功轮之后，第五次（`guardian-accept-flow-83.txt`）：开演 → 闭馆 → 交给守护助手（模型约 3 分钟）→ `PAUSED_FOR_ACCEPTANCE` 且进度里有当前事件提案 → 控制台「接受这次事件的调整」→ **5 秒内**事件 `RESOLVED`、提案 `ACCEPTED` → 「继续模拟」→ `RUNNING` sequence 3；无 console 错误。
- 控制台现在的三个门分开写：有提案才显示接受；事件未落定不显示继续；模型失败/未解出/未配置各给一句原因（`rev-presenter-guardian-failed` / `-unresolved` / `-unconfigured`）。
- 模型失败后 run 的转态仍不稳定（一次 >338 秒停在 `GUARDIAN_RUNNING`、一次约 187 秒转 `PAUSED_MODEL_UNAVAILABLE`）；守护屏的接受路径仍可能指向旧事件提案。这两条与「接受后 run 的计划引用是否更新」已写进 PR #54 评论 6402087085，等 Codex 回。
- 老师现场口径已同步到速查卡第 7、8 条：可以点「交给守护助手」，按控制台给出的接受/继续走；守护屏的「接受这份调整」不在课堂主线用。
- 合入后两日主线也复跑：`clock-two-day-merge54-84.txt`，开演 09:00 第 0 步 → 12/03 15:00 第 4 步 → 12/04 10:00 第 8 步完成，三键禁用、完成提示「不是实际到场」、无 console 错误；跑完已重置开场。
- 接受后模拟真的换计划：活动只剩天安门广场 + 天坛公园，故宫被移除；再点「到下一站」直接到 12/04 10:00 完成（`guardian-plan-applied-92.txt`、`classroom-plan-applied-92.png`）。讲课时要说这是「少去一站」的预期结果。
- 回执：`20261026_GUARDIAN_LIVE_VERDICT.md`；提交 `419e892a40`、`0aab8594fc`。

## 补记：城市池「可用 0 座」的现读（10-26 16:39）

- `simulation_city_identities`：**1 行** —— journey `2e9cd67d…`、`provider=amap`、`adcode=110000`、`public_name=北京市`（16:16 绑定）。
- `simulation_public_city_snapshots`：**0 行**。
- 因此「可用 0 座，标准要 3 座」的缺口是**没有任何已发布的城市快照**；身份已有。要凑到 3 座必须逐城发布真实 `snapshot_json`（含 sha256 与 published_by），不能凭空造。
