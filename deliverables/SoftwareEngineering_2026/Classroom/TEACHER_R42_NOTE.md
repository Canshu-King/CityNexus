# R4.2 课堂 Visio 回环修正说明（只改 Teacher_02 这一张）

1. **补的是线，不是字**：`Classroom/Teacher_02_Agent_User_Flow.vsdx` 里新增一条原生连接线，从「继续调整方案（回到第 3 步）」顶边连到「调用地点与路线工具」底边。读回文件本身：该连线同时 glue 在两个方框上（`page.Connects` 两条记录），端点 BeginX/Y = (6.625, 4.360)、EndX/Y = (6.625, 5.130)，`EndArrow=4`（有箭头）、`BeginArrow=0`（尾部无箭头），所以方向只能是"回到第 3 步"。检查器：`Evidence/scripts/se_r42_loop_proof_r1.py` → `Evidence/logs/se_r42_loop_proof.json`。
2. **为什么落在这一格**：`request_replan` 是网关注册的工具（`backend/app/agent/gateway.py:365`、实现 `:545`），由 mission 计划排入（`agent/mission_plan.py:118`），守护流程也会确定性地直接派发它（`agent/guardian.py:418`），执行位置就是 `agent/runtime.py:405` 那个循环里的 `dispatch`（`:486`）。提案落成 `PlanVersion(status="CANDIDATE", source="REPLAN")`（`main.py:12460`），切换活动计划必须走 `accept_replan`（`main.py:13098`）并带 `Idempotency-Key`——所以回环终点是工具那一格，而不是直接改库。
3. **没有压字也没有交叉**：`Evidence/scripts/se_visio_cross_check_r1.py` 读回 9 条连线，`crossings=0 throughShapes=0 offPage=0 unreadable=0`，且审计过程未改写文件（`unchanged=true`）。
4. **真机看过**：`Evidence/scripts/se_r42_eye_r1.py` 用可见 Visio 只读打开、最大化、整页适配后 PrintWindow 截整窗口，存 `Classroom/previews/Teacher_02_Agent_User_Flow_window.png`（1920×1128，标题栏带 `[只读]`，截图前后 .vsdx 摘要一致）。
5. **可编辑性往返**：`Evidence/scripts/se_r42_roundtrip_r1.py` 改一处非关键文字 → `SaveAs` 到 E: 的副本 → 冷重开，副本里连线仍 glue 在 `['t2n3','t2n7']` 且端点不变；把方框移动 (+0.5, +0.3) 英寸后线尾跟到 (7.125, 4.66)，复位后箭头仍停在第 3 步底边——线是真的附着，不是画上去的。正式原件 `sha256` 前 16 位 `f78dc06dd2a4c6d8`，proof / eye / roundtrip 三个检查器读到的是同一枚，往返前后未变。
6. **顺手纠正的一处失真**：「继续调整方案」原来是灰色虚线（本图的"尚未实现"样式），但上面第 2 条说明它已经落地，所以改成与 Agent 工具面同色的实线框。Project 文件、Teacher_01、取证版 Visio 一律未动。
