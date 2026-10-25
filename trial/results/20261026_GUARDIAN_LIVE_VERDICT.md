# Guardian 现场验收：合入 PR #54 之后

日期：2026-10-26 凌晨（本地 03:0x–03:1x）；基线 `cedeaf2800`（PR #54 合入 rescue）、前端本轮改动见文末。

## 一、合入与自动测试

- `git merge-tree` 预检干净；合并提交 `cedeaf2800`，Codex 只改后端/tests/CI/结果文档，未碰前端。
- 合并前基线：`tests/test_wp01_wp03.py` **7 failed / 22 passed**（读 ACL 未签名）。
- 合并后按 PR #54 的 CI 范围跑：`tests/test_wp01_wp03.py tests/test_issue49_*.py tests/test_day_rhythm.py tests/test_goal_draft_patch.py` → **82 passed / 0 failed，22.44 秒**（venv 3.12.14）。
- 课堂栈重启到合并代码后：`classroom_demo_selfcheck` 显示 `DEMO_READY=true`、`ENTRY_DOOR=PAIRING`、`SIM_CONSOLE=AVAILABLE:NOT_STARTED`；`after_merge_check` 三探针 `all_green=true`。

## 二、现场守护三跑（同一课堂库，三次 prepare 各起一轮）

### 第一次（`guardian-live-78.txt`，18:49–18:52）

- 开演 `RUNNING` seq 0 → 闭馆 `PAUSED_FOR_GUARDIAN` seq 1（事件 `6ae8defe`）。
- 点「交给守护助手」后模型约 **194 秒**返回：history 写入 `GUARDIAN_RESULT`，`action_status=PROPOSAL_PRESENTED`、`proposal_id=f817465e`、`status=PARTIAL`；run 进 `PAUSED_FOR_ACCEPTANCE` seq 2。
- 回执缺陷：探针把 `/runs/current` 的裸 run 当成了 `{available, run}`，64 次轮询都写 `NO_RUN`（白等 127 秒）。产品本身在 194 秒已到等待接受。
- 点 Guardian 屏「接受这份调整」后仍 `PAUSED_FOR_ACCEPTANCE`；点「继续模拟」→ 409「这件事要在守护屏上按原生产品流程解决」。
- 库侧：`f817465e` 最终 `INVALIDATED`，其计划 `99c2f185` `REJECTED`；当前事件未显示为 RESOLVED。

### 第二次（`guardian-full-80.txt`，18:57–19:03）

- 模型请求失败：`guardian_outcome=EXTERNAL_FAILED / MODEL_REQUEST_FAILED`。
- **run 保持 `GUARDIAN_RUNNING` 超过 338 秒**（轮询 56 拍），progress `proposals=[]`、`guardian_runs[0].status=RUNNING`、`proposal_id=null`。
- 屏上「守护正在分析」；Guardian 屏却显示**规则引擎**提案「移除故宫博物院；路上少 66 分钟」，其 `trigger_event_id=880cec4e`（上一次行程变化），与当前事件 `155d3f40` 不同。
- 点「接受这份调整」后 13 秒内页面无可见变化（读数见回执）。

### 第三次（`guardian-full-81.txt`，19:05–19:11）

- 模型约 247 秒后成功：run 进 `PAUSED_FOR_ACCEPTANCE`，progress `proposals=[47aa3925…]` 且 `trigger_event_id=ac7493a9`（与 run 的 pending 事件一致）——**当前事件绑定这一条修复生效**。
- 但大屏 Guardian 卡片显示的还是旧事件提案；点「接受这份调整」后库侧：`b532dd45`（旧事件 `880cec4e`）→ `ACCEPTED`，`47aa3925`（当前事件）→ `INVALIDATED`；事件 `ac7493a9` 仍 `DETECTED`。
- 点「继续模拟」→ 409（事件未解决）。**接受旧提案不会解决当前事件。**

### 第四次（`guardian-accept-flow-82.txt`，19:13–19:16）

- 模型约 187 秒失败；这一次后端把 run 转成 `PAUSED_MODEL_UNAVAILABLE`（与第二次不同）。
- 屏上「现场模型不可用，已暂停」+ 模型提示；没有可接受提案（`EVENT_ACCEPT_BUTTON 0`）。
- 「事件处理完了，继续模拟」按钮存在，点击 → 409（事件 `c11955f1` 仍 `DETECTED`）——**又一处死按钮**。
- `guardian_outcome` 已带 `EXTERNAL_FAILED / MODEL_REQUEST_FAILED`，但旧屏没有消费它。

### 第六次（`guardian-plan-applied-92.txt`，19:50–19:54）——接受后模拟真的换计划

- 接受前：`plan=e74a5edb`，当前活动故宫 `5b60b374`。
- 点「接受这次事件的调整」后 5 秒内：pending 事件 `cec1a1eb` `RESOLVED`，活动计划变成 `9a191191`，当前活动 `e01a9328`。
- 新计划的全部活动只有两行：**天安门广场（已完成）+ 天坛公园（ACTIVE）**；故宫已被移除。
- 点「继续模拟」→ `RUNNING` seq 3；点「到下一站」→ 12/04 09:00 游览天坛 → 12/04 10:00 完成，`SIMULATED_COMPLETED` seq 7，三键禁用，无 console 错误（`classroom-plan-applied-92.png`）。
- 1024×768 平板同剧本另跑一次（`guardian-plan-applied-tablet-93.txt`，**227 秒**）：入口、开演、闭馆、守护（187 秒出提案）、接受（5 秒落定）、继续、到下一站完成全部命中；新计划同样只剩天安门+天坛，`ERRORS []`。
- 390 手机同剧本再跑一次（`guardian-plan-applied-phone-94.txt`，281 秒）：历史里出现「计划已按守护调整」。口径说明：该 run 的 `history_json` 只有 **1 条** `SIM_PLAN_CHANGED`（sequence 4），而屏上文本连显 3 次。独立场景 r95（开场 + 4 次 +30）量到 `li_count=5`、`historyLength=5`，说明 `slice(-5)` 在真页面生效；r94 的 9 条无法在 r95 复现，保留为一次观察，不宣称缺陷，也不据此改后端。前端已把历史行的 key 从 `sequence` 换成 `index+event+time`（r94 的最近五条里存在重复 sequence，React 会复用节点）；r96 复跑仍是 5 条、无 console 错误。
- 1280×900 投影同剧本（`guardian-plan-applied-projector-97.txt`，**271 秒**）：同样换计划并完成；历史只显示 5 条（r94 的叠加未再出现），`ERRORS []`。三档整链（390 / 1024 / 1280）至此齐全。
- 慢网回归（合入后现尖，`console-blip-97.txt`）：把 progress 与 plans 两条读路由改成 502 HTML 持续 13 秒，控制台仍可见、状态仍「模拟进行中」、提示行在、`ERRORS []`。勘误：本轮第一次拿 r71 跑时默认指向 14495 且 Node 直接崩，我看的是 02:21 的旧回执；已改用课堂栈的 r97 真跑，旧回执不再当本轮证据。
- 结论：接受调整在模拟执行里真的生效；课堂可以讲「少去故宫、直接去天坛」。

### AI 关闭（隔离副本，`ai-off-guardian-86.txt`）

- 在 60410 起独立后端，DB 为课堂库副本 `canary_ai_off_1026.db`，`CITYNEXUS_AI_ENABLED=false`；课堂栈 60391/14492 未动。
- 开演 201 / `RUNNING` seq 0 → 闭馆 200 / `PAUSED_FOR_GUARDIAN` seq 1 → guardian **503，0.01 秒**，message `SIMULATION_AI_DISABLED`。
- run 仍 `PAUSED_FOR_GUARDIAN`、sequence 1 不变；progress `guardian_runs=0`、`ai_enabled=false`、`missing` 含 `AI_DISABLED`；服务端日志 0 traceback。
- 结论：开关在消耗 sequence、创建运行之前生效（这是现场读数，不只是替身测试）。

## 三、结论（按归属）

### 守护屏提案归属（r90 → r91，现场对照）

- r90（旧代码）：run 已是 `PAUSED_FOR_ACCEPTANCE`、当前事件 `bc4a439f` 有自己的模型提案；守护屏却显示「规则引擎生成 · 不是大模型现场推理」（上一次变化 `880cec4e` 的节点）。
- 两个成因：`/simulation/runs/current` 返回的是裸 run（没有 `run` 包装），原代码读 `current.run.state` 永远为空；`/replans` 的契约里没有 `created_at`，按它排序也拿不到真正最新的节点。
- 修法：兼容裸 run；再读该 run 的 progress，取 `PRESENTED` 提案 id，在列表里按 id 匹配；当前事件没有对应节点时，屏上写「当前模拟事件的调整在课堂控制台接受」，不再把别的事件的节点摆在接受按钮上。
- r91（新代码）：同一现场下守护屏 `origin="Agent 生成 · 服务器留有运行记录"`，`ERRORS []`；提案卡仍在视口内（`guardian-panel-live-91-panel.png`）。

**已修好（可证）**

- WP01 签名测试从 7 红到 0 红（22 → 82 passed）。
- Guardian 提案绑定当前事件：第三次现场 `47aa3925` 的 `trigger_event_id` 与 run pending 一致。
- AI 关闭快速 503 已在**隔离副本**现场验证（见下节）。
- 守护屏接受路径现场闭环（r100）：屏上是当前事件的 Agent 提案，点「接受这份调整」后 4 秒内事件 `RESOLVED`、提案 `ACCEPTED`，回控制台点「继续模拟」→ `RUNNING` sequence 3（`guardian-panel-accept-100.txt`）。
- 双屏同一 run（r102）：平板开演并 +30，投影在 2.5 秒内读到 `09:30 · 第 1 步`，两屏无错误（`two-screen-sync-102.txt`）。
- 无票只开根地址时的入口文案：在「我的旅程」点「课堂演示：进入示例行程」，红条写清「课堂入口需要启动器签发的一次性配对链接…」，按钮仍在、无错误（`entry-no-ticket-99.txt`）。

**仍未闭环（Issue #47 保持开放）**

1. Guardian 屏的「接受这份调整」与 simulation 的当前提案不是同一条：屏上给的是旧事件提案，接受后当前事件不 RESOLVED（第三次现场四行库读数）。
2. 模型失败后 run 的转态不稳定：第二次 >338 秒仍 `GUARDIAN_RUNNING`，第四次约 187 秒转 `PAUSED_MODEL_UNAVAILABLE`。
3. 前端原先把「继续模拟」挂在「有提案」而不是「事件已解决」上，产生死按钮；`guardian_outcome` 未被消费。

**前端本轮已改（待下一轮现场复验）**

- `ClassroomPresenterPanel.tsx`：消费 `guardian_outcome`（`EXTERNAL_FAILED`/`AGENT_UNRESOLVED`/`MODEL_NOT_CONFIGURED` 各给一句真话与出口）；「继续模拟」只在 pending 事件 `RESOLVED/IGNORED` 时出现；`PAUSED_FOR_ACCEPTANCE` 有当前提案时新增「接受这次事件的调整」，调 `acceptReplan(proposal.id)`（该路径后端接受时会把 trigger event 标 RESOLVED）。
- `GuardianRealityPanel.tsx`：候选从「第一个 PRESENTED」改为「最新的 PRESENTED」，避免课堂里先展示上一次变化的提案。
- 类型检查通过；现场闭环已在第五次跑证明（见下）。

### 第五次（`guardian-accept-flow-83.txt`，19:18–19:22）——闭环

- 模型成功；run `PAUSED_FOR_ACCEPTANCE`，pending 事件 `b6e4e0a7` `DETECTED`，进度 `proposals` 里是当前事件提案 `cad2a52e`。
- 屏上出现新按钮「接受这次事件的调整」（`EVENT_ACCEPT_BUTTON 1`）。
- 点一下，**5 秒内**：pending 事件变 `RESOLVED`，提案 `cad2a52e` 变 `ACCEPTED`；「继续模拟」出现（`RESUME_BUTTON 1`）。
- 点「继续模拟」→ run 回到 `RUNNING`（sequence 3）。
- 全程无 console 错误（`ERRORS []`）。
- 计划引用（已查代码，不是待裁）：暂停期间 `run.state.plan_version_id` 仍是启动计划；`backend/app/simulation/runtime.py:320` 在下一次 advance 末尾把它同步到 `journey.active_plan_version_id`，并在检测到变化时写 `SIM_PLAN_CHANGED`（`runtime.py:235`）。所以下一次「到下一站」会按新计划走。
- 截图文件：`guardian-accept-flow-83-before-accept.png`、`-after-accept.png`、`-resumed.png`、`-scene.png`、`-after-guardian.png`。

### 完成态重进（现尖副本，`completed-reentry-98.txt`）

- 用现尖代码把课堂两日走完，再以 **sqlite backup** 复制成独立副本。第一次用裸 `cp` 只复制主文件、漏掉 `-wal`，读回 `simulation_runs=0` 才发现拿到的是开场库；改成 backup 后读到 `RUNS (1, SIMULATED_COMPLETED)`、`JOURNEY COMPLETED`。
- 独立栈（60400 后端 + 14495 前端）发新票进入该副本：屏上红条「这趟课堂演示已经走完并封存；再演一遍请重启课堂演示（双击启动器）。」，`clock=0`、`presenter=0`、`entry=0`、`tab=0`，无 console 错误。
- 结论：完成态重进是封存提示，不是空白课堂屏；课堂控件不渲染。

### 第六次（`guardian-failure-watch-107.txt`，04:49–04:52）——成功轮的转态时刻

- 同一路径（开演 → 闭馆 → 交给守护助手），这次模型成功：**193 秒**（第 31 拍）从 `GUARDIAN_RUNNING` 转到 `PAUSED_FOR_ACCEPTANCE`。
- 转态后 `guardian_outcome.code=PROPOSAL_READY`；`guardian_runs=[{"status":"PARTIAL","action":"PROPOSAL_PRESENTED"}]`；提案 `5b658074-6691-4db0-9bad-688bfa620853` 为 `PRESENTED`。
- 屏上（`classroom-guardian-failure-107.png`）只有「接受这次事件的调整」「刷新读数」与「这次事件已经有一份可接受的调整」提示，**没有**「再请一次守护」——与状态条件一致。
- 无 console 错误（`ERRORS []`）。
- 代码侧确认（`backend/app/simulation/api.py:340-405`）：守护请求是**同步**执行的，`run.status` 在 `scan_guardian` 返回后才写；所谓「停在 GUARDIAN_RUNNING 338 秒」只能是请求尚未返回，而不是转态逻辑丢失。`guardian_run.status=PARTIAL` 本身不等于失败——`progress.py:150` 先看有没有匹配当前事件的 PRESENTED 提案，有就判 `PROPOSAL_READY`。
- 本轮新增前端出口：`PAUSED_MODEL_UNAVAILABLE`、事件未落定、非 `MODEL_NOT_CONFIGURED`、且没有可接受提案时，显示「再请一次守护」，调同一个 `guardian` 端点（后端 `api.py:318-323` 明确允许在 `PAUSED_MODEL_UNAVAILABLE` 重试）。**这一按本轮没有现场点过**：本轮是成功态，按钮按条件不出现；失败态现场仍待下一轮抓，届时才把 `rev-presenter-guardian-retry` 记为已验。

### 第七次（`guardian-retry-108.txt`，05:00–05:03）——失败态的「再请一次守护」真按到了

环境：隔离栈后端 60400 / 前端 14495，库是课堂库的 **sqlite backup 副本** `citynexus_v3_guardian_retry_1026.db`。课堂库与 60391/14492 全程没写。

故障注入（明确披露，是失败 setup、不是伪造成功）：副本里复制一条 CLOSURE 事件并把 `run.state.pending_event_id` 指向它、run 置 `PAUSED_MODEL_UNAVAILABLE`、旧提案置 `INVALIDATED`、旧 guardian_run 的 `proposal_id` 清空；第三次另把该事件补进 `run.history_json` 的 `SIM_SCENE_INJECTED`（否则进度投影认不出 pending）。

读数：

- 进入时：`PAUSED_MODEL_UNAVAILABLE`、无提案、`pending=fa724437…`、`outcome=UNKNOWN`。
- 按钮：`RETRY_BUTTON 1`；命中自测 `visible=true, inViewport=true, hitSelf=true, disabled=false`，文本「再请一次守护」。
- 点一下：`sequence 2→3`、`GUARDIAN_RUNNING`；**18 秒**后回 `PAUSED_MODEL_UNAVAILABLE`。
- 这一轮 `outcome={"code":"EXTERNAL_FAILED","error_code":"MODEL_REQUEST_FAILED"}`；`guardian_runs` 最新一条 `{"status":"PARTIAL","action":"RETRYABLE_FAILURE"}`，`proposal_id` 为空。
- 屏上（`guardian-retry-108-after.png`）：「再请一次守护」仍在，提示变为「现场模型这次请求失败了，没有交出建议。可以再请一次守护；连续失败就重启课堂演示（双击启动器）。」——这正是本轮新加的分支，**不再**说「刷新不会继续」，也不再把老师支到没有对应提案的守护屏。
- 无 console 错误（`ERRORS []`）。

同一条路前一晚连跑两轮（未补 history 的注入）：按钮同样一次命中、点击后同样 17.7 秒回失败；但进度投影认不出那个不在 history 的 pending，`guardian_runs` 过滤为空、`outcome=UNKNOWN`，屏上仍是旧文案。这说明：**第三轮的「补 history」不是为了让按钮出现，而是为了让进度投影与真实注入保持同一形状**。

## 四、下一步

- 已验：当前事件提案 →「接受这次事件的调整」→ 事件 `RESOLVED` →「继续模拟」→ `RUNNING`（第五次）。
- Guardian 屏接受已现场闭环（r100），该项不再等裁语；仍待 Codex：模型失败后 run 的转态为何一次 >338 秒、一次约 187 秒。（计划引用一项已查代码：下一次 advance 会同步，见上。）
- 第六次补上了成功轮的耗时基准（193 秒）与「同步调用、返回即转态」的代码事实。
- 第七次：失败态的「再请一次守护」按钮与文案都在真后端上按过（18 秒回 RETRYABLE_FAILURE，按钮仍在）；`RETRYABLE_FAILURE` 是可重试，不是终态。
- 仍待 Codex 一枚事实：`guardian_outcome` 只给 `EXTERNAL_FAILED/AGENT_UNRESOLVED/MODEL_NOT_CONFIGURED/UNKNOWN`，**没有 RETRYABLE_FAILURE 这个码**；前端只能从 `guardian_runs[].action_status` 读它。是否要把它升为一等码，归 Codex 定。
- 平板亲手点仍 `USER_VERIFIED=PENDING`。
