# 课堂主线一次真机计时：从进屏到「两日走完」4 分 48 秒

探针：`trial/human_walk/_classroom_timed_path_r109.mjs`；回执：`classroom-timed-path-109.txt`；截图：`classroom-timed-path-109.png`。390×844 真实页面，点击前每个按钮都做 `elementFromPoint` 命中自测，无 console 错误。

## 每一步（elapsed 为从打开页面算起）

| 动作 | 到这一步的累计秒 | 本步耗时 | 屏上/服务端读数 |
|---|---|---|---|
| 配对进屏 | 9.2 | 9.2 | `run_id=null`、`status=NOT_STARTED` |
| 开演（模拟两日） | 14.2 | 5.0 | `RUNNING`，sequence 0 |
| ＋30 分钟 | 16.1 | 1.9 | `RUNNING`，sequence 1 |
| 闭馆 | 19.9 | 3.8 | `PAUSED_FOR_GUARDIAN`，pending `e180574c` DETECTED |
| 交给守护助手 | 278.5 | **258.6** | `PAUSED_FOR_ACCEPTANCE`，提案 `831b9905` PRESENTED，`outcome=PROPOSAL_READY` |
| 接受这次事件的调整 | 281.8 | 3.3 | 事件 `e180574c` RESOLVED、提案 ACCEPTED |
| 继续模拟 | 285.1 | 3.3 | `RUNNING`，sequence 4 |
| 到下一站 | 287.9 | 2.8 | **`SIMULATED_COMPLETED`，sequence 8** |

**整条主线 288 秒（4 分 48 秒）**，其中守护一步占 259 秒（4 分 19 秒）；其余七步合计 29 秒。

## 课堂怎么用这个数

- 老师按「开演 → ＋30 分钟 → 闭馆」只要 10 秒就能把场景摆好；真正的等待全在守护。
- 守护那 4 分 19 秒是讲课窗口：卡片上的「等待接受调整」不会自己消失，老师可以离开控制台讲这段旅程，回来再按接受。不要在这段时间反复按「交给守护助手」（按钮已灰）。
- 接受之后到完成只有 6 秒（接受 3.3 秒 + 继续 3.3 秒），最后「到下一站」2.8 秒就封存——收尾要提前说，否则一眨眼就过去了。

## 附带发现（一句给 Codex）

事件 RESOLVED、提案 ACCEPTED 之后，`guardian_outcome` 仍返回 `AGENT_UNRESOLVED`（`classroom-timed-path-109.txt` 的 `STEP ACCEPTED` 与 `FINAL` 两行）。`backend/app/simulation/progress.py:150` 先判「有没有匹配的 PRESENTED 提案」，被接受后提案不再是 PRESENTED，于是落到 163-167 的 `guardian.status == "PARTIAL"` 分支。这个码在终态下会被读成「守护还没解决」，而实际它已经交出提案并被接受。屏上被 `SIMULATED_COMPLETED` 遮住，课堂看不见；但任何读 `guardian_outcome` 的消费者都会误判。归 Codex 定：把「已有 ACCEPTED 提案」判成 `PROPOSAL_READY`（或新码），别落到 `AGENT_UNRESOLVED`。

## 复现

```
python trial/play_launcher/classroom_demo/prepare_classroom_scene_r1.py   # 重置开场并出票
node trial/human_walk/_classroom_timed_path_r109.mjs                      # 约 5 分钟
```

## 封存那一刻的屏（`classroom-timed-path-109.png`）

- 时钟条：`12/04 10:00`、「模拟行程已完成」、三个推进键已禁用、一行「两日模拟已走完（不是实际到场）」。
- 控制台：「模拟行程已完成 · 12-04 10:00」，只留「刷新读数」，一句「两日模拟走完，这趟行程已封存。再演一遍请重启课堂演示（双击启动器）。」
- 历史五条：出发 12-04 08:06、到达 12-04 09:00、游览 12-04 09:00、完成一站 12-04 10:00、两日走完 12-04 10:00。
- 无「接受」「继续」残留按钮；无 console 错误。

## 1024×768 平板横屏（两次）

- **v1**（`classroom-timed-path-1024-v1.txt`）：守护 162.1 秒成功，接受 165.5 秒，继续 168.8 秒；随后探针报 `BLOCKED_BUTTON 到下一站`。
  **不是遮挡**：同形态独立诊断（`clock-next-hit-122.txt`）读到 `rect=847,259 121×44`、`hitSelf=true`、`enabled`、`dockRect=null`。v1 的拦截是探针在状态切换那一瞬读到 `disabled=true`，已给 `press` 加三次重试。
- **v2**（`classroom-timed-path-1024.txt`）：守护 **379.4 秒仍未转态**；这一刻 `run.status=GUARDIAN_RUNNING`，而 `guardian_outcome=EXTERNAL_FAILED / MODEL_REQUEST_FAILED`——**失败已记在 guardian/agent，run 状态还没写**，这就是「停在守护中」的机制现场。探针超时后仍去点后续（`MISS_BUTTON 继续模拟`、`BLOCKED_BUTTON 到下一站`，后者按钮 disabled），已改为「超时即停，不点后续」。
- `FINAL` 读到 `PAUSED_FOR_ACCEPTANCE` + 提案 `69834d00` PRESENTED ⇒ 那次 scan 最后返回了。
- 成功/转态时长档：**162.1 / 193 / 259 / 379+ 秒**；课堂预算要按「可能 6 分钟以上」写，卡片已改为 3–6 分钟。

## 断外网也走得动（`classroom-offline-125.txt`，390 真机）

用 Playwright 拦掉所有非本地域（只放行 localhost / 127.0.0.1 / 10.12.35.143，其余 `abort("internetdisconnected")`），再走课堂主线：

- 配对成功、身份在位；开演 `RUNNING#0` → ＋30 `RUNNING#1` → ＋1 小时 `RUNNING#2` → 到下一站 `RUNNING#6`。
- **外部请求被拦 0 条**；无 console 错误。屏上（`classroom-offline-125.png`）时钟条与三键照常，控制台注入按钮照常。
- 结论：课堂的三键推进与事件注入全走本地栈，校园网断也不影响主线；只有守护那一步要靠外部模型（会失败/变慢），失败后按「再请一次/重启」两条出口。

## 1280×900 投影形态（`classroom-timed-path-1280.txt`）

- 前四步全部可达：配对 8.0 秒 → 开演 12.8 → ＋30 14.6 → 闭馆 18.4（`PAUSED_FOR_GUARDIAN`，pending `225376a7`）。
- 守护 **379.9 秒仍未转态**（第二次 379+，与 1024 v2 同档）；这次探针按新规则「超时即停」直接收尾，没有再去点被禁用的推进键，`ERRORS []`。
- 结论：投影形态的按钮可达性与 390 一致；慢的是守护这一步，与屏幕形态无关。
- 课堂预算据此写「3–6 分钟」，并知道**偶尔会更久**；卡片不再承诺「四分钟」。
