# 合入 Codex 分支之后的验证顺序（课堂栈）


## 合入前的冲突预检（2026-10-25 晚现读）

- merge-base 是 `9d4d2a853a727e05bcc76f27a1d5cfbf4e90e041`。
- Codex 侧改动面：`backend/app/simulation`、`backend/app/agent`、`backend/app`、`backend/tests`、`backend/db`、`docs/revolution`、`trial/tasks`、`trial/results`、`AGENTS.md`。
- 两侧唯一交集是 `AGENTS.md`，而两边对它的改动**逐字相同**（同一个 blob `ac79edfa54`），所以合并没有文本冲突面。
- 真正的风险是语义：Journey-read ACL 收紧后，匿名或失效令牌的读会从 200 变 401/403，而课堂的刷新恢复依赖本地 bearer；演示会话绑定 presenter 上下文后，旧后端的 `SESSION` 门会变成 `PAIRING`（启动器与前端已适配）。所以阶段 A 与阶段 C 的探针必须在合入后的真栈重跑，不能拿旧后端读数充数。

- 前端读面普查（合入前）：课堂用到的三个读——`frontend/src/api/citynexus.ts:3048` 的 journey、`:3084` 的 events、`:3204` 的 twin——都带旅行者 bearer，ACL 收紧不会把它们打回 401。另有两处没带 token 的守护读（`:3554` 的 `guardian/status`、`:3558` 的 `guardian/readiness`），目前不在 Issue #47 列的 ACL 范围内；若合入时 ACL 扩到守护面，这两处要补 bearer。`/experience` 在这份客户端里没有调用点。

前提：Codex 的 `codex/sandbox-execution-security-20261025`（PR #48）合入 rescue 分支后，课堂栈后端才具备票门（`/demo/pairing`）与模拟执行端点（`SimulationRun`）。下面每一步都标了「今天的证据」，标明它已在隔离栈或旧后端验过的是什么；合入后要在 14492 上重验的那一步会写「重验」。

## 阶段 A：课堂主链（合入当天先跑，约三分钟）

1. 双击 `D:\moodle\_cmdr_v3_port_1022\start_classroom_demo.bat`（重建演示库、重启后端、起前端，并打印带票地址）。
2. `classroom_demo_selfcheck_r1.py`：`ENTRY_DOOR` 应为 `PAIRING`、`DEMO_READY=true`、`SIM_CONSOLE` 应为 `AVAILABLE:*`（今天在旧后端读到的是 `SESSION` 与 `NOT_DEPLOYED`）。
3. `after_merge_check_r1.py`：读启动器留下的票，跑带票入口、投影卡片、局域网三支只读探针。今天它只验过「旧后端上自己拒绝」这一支；**票门分支是重验项**。
4. `rehearse_classroom.bat`：手机彩排。今天旧后端上 25.4 秒零错误；**合入后要在票门后端重跑**，并确认启动器打印的地址带 `#pair=…`、彩排能用这张票。

## 阶段 B：控制台与两日闭环（合入后才可用，今天在隔离栈验过）

5. 控制台出现：`rev-presenter` 应在行程页可见（今天旧后端里为 0，属预期）。开演与推进用 `_classroom_presenter_start_r24.mjs`；事件卡用 `_classroom_presenter_event_card_r25.mjs`。今天这两支在隔离栈（60400 + 14494）验过，**合入后要指回 14492 重验**。
6. 两日闭环：`_classroom_two_day_loop_r31.mjs`（真模型走完两日、守护屏接受、继续、次日完成）。今天在隔离栈 246 秒跑通；合入后真栈重跑一次，确认 `SIMULATED_COMPLETED` 与封存提示。
7. 控制台与时钟条的让位：run 存在后时钟按钮变灰并显示「已交给课堂控制台推进」。今天在隔离栈验过，合入后重验。
8. 慢网与守护：`_classroom_slow_replans_r40.mjs` 与 `_classroom_guardian_note_r35.mjs` 在隔离栈可用；合入后可指 14492 重跑（注意 r35 会真的把守护按钮按下去，课堂栈上不要跑，除非就是要演示守护）。

## 阶段 C：收尾与边界

9. 刷新恢复：`_classroom_refresh_r41.mjs`（旧后端今天绿）；合入后在票门后端重跑，确认刷新后仍回课堂、控制台仍在（`_classroom_run_resume_r34.mjs` 在隔离栈验过）。
10. 完成态重进：旧后端今天量到 `/demo/session` 换发空白草稿，入口只能提示重启启动器；合入后要重看这一点是否因后端口径变化而改变（Issue #47 评论 6396968665）。
11. 平板实物：`TABLET_OPEN` 只代表地址可达；主人亲手点按之前一直是 `USER_VERIFIED=PENDING`。

## 判定与回滚

- 任一步红：先把红行原样贴回 Issue #47/PR #43，不删证据、不改文案过闸。
- 课堂栈坏了而上不了课：重跑启动器即可重建场景；演示库在 `_cmdr_v3_live_1022`，不删。
- 所有探针都在 `trial/human_walk/`，证据落在 `trial/results/20261022_v3_human_chrome/`；今天新增探针与工具索引见交接件「今晚新增的工具与探针」一节。
