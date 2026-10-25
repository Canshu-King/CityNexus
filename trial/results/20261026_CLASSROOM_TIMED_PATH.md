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
