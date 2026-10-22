# Revolution V3｜Codex 容量故障恢复交接（2026-10-22）

> **这不是新版本立项、不是从头重画 UI、不是重新部署。** 目的：在 Codex 原会话因“模型容量”错误无法执行时，从 GitHub **最后真实代码状态**恢复实用功能的开发，并允许 Qoder 临时接力。此文档由 GPT 核对远端后发布；不声称已经修复用户本机的 Codex 客户端或模型服务。

## 1. 真实基线（新 Codex / 临时 Qoder 必读）

- Repo：`Canshu-King/CityNexus`
- **Codex 产品分支**：`design/revolution-mobile-first-v1`；故障前最后产品 HEAD **`3c5cdd02e176a3f19fa5b4118063eb1230d658be`**，PR #23 (OPEN/DRAFT)。
- **Qoder 能力分支**：`reform/qoder-capability-adapters-1018`；核查时 HEAD **`33436585634dd71714b6058920f9bf1b5100aeee`**，PR #35 (OPEN)。
- 41 个 V3 原始参考文件已入 Codex 分支 `docs/revolution/v3-design/`。视觉参考是静态原型，不能替代真实数据和 Agent 调用。
- **Codex 交付记录**：`trial/results/20261020_V3_DRAFT_PREPARATION.md` 和 `trial/results/20261020_DRAFT_PREPARATION_LIVE.json`。已有三主导航、任务持续对话、照片/地图/日程、A/B/C 草案、签名出发读取；`POST /journeys/{jid}/agent/goal-tasks/{tid}/prepare-plan` 在原广州签名任务产生 HTTP201 与首次 `PlanVersion CANDIDATE`（3 项活动，刷新保持）。
- 历史候选 `54d2cfca-ad1f-4dd5-a198-128c21a1294c` **不可宣称已出发**：`selected=false` / `activated=false` / `selectable=false`，实名 Place 映射与营业/成本/路段证据缺失。该回执的行程时段落在 **2026-10-20**，恢复真实演示时应选择新的未来出发日期，不把过期时间当可出发证明。
- **已验证 GitHub 最后 Codex HEAD check**：`trial-build: success`；真正手机亲测 `USER_VERIFIED=PENDING`。

## 2. 先把“模型容量错误”与代码故障分开

目前没有用户原 Codex 窗口的完整错误码 / 日志，**不能**把服务暂时过载、用量耗尽、过长上下文、凭证故障一概判为“项目坏了”。用户恢复时：

1. 检查 Codex UI 的 **Settings → Usage**（若 CLI 则 `/status`），区分 quota/credits/reset 与 model overload；可用量耗尽不能通过无限刷新解决。
2. **不再在失败的超长旧会话里反复重试**。打开新的 Codex 任务／线程、仍关联同一工作目录与 repo。先用当前可选的 **GPT-6.1 Sol Medium**；如该模型继续报容量、用当前账号可用的 **GPT-6 Luna Medium** 或其他可用模型。不要要求 Maximum/Extra High 才能读一个 50 行差异；复杂决策再提高。模型不可用时以 UI 提供的选择为准。
3. 如果错误是 `server_overloaded` / HTTP503，有限重试一次并遵循 `Retry-After`；若是 `context_length_exceeded`，新线程只引用此 baton 和明确文件；若是 `usage_limit_exceeded` / `credit_balance_exhausted`，先处理额度；若是 `authentication_error`，检查正确工作区与认证。10 月 20 日的广泛服务事故被状态页标记为已恢复，但不等于此账户自动修复。
4. 不在 PR、CLI 日志、聊天里粘贴本地高德 API Key / bearer。恢复工作前确认 `git status` 与 `git branch --show-current`；保留所有未提交改动，绝不 reset/force-push。若 HEAD 因此 GPT 文档提交前进，先安全 fetch / rebase 或用单独 worktree，不丢代码。

## 3. 新会话只接这 **一个** P0 目标（不做 R 历史补测/文案长循环）

**目标：让用户现有 Agent 草案 CANDIDATE 最终有可操作的“逐项补资料 → 符合条件则选用 → 真实出发”界面。**

必须读取的三个入口（无需全仓重新总结）：
- `frontend/src/trial/mobile/DraftDepartureCard.tsx`、`MobilePlanWorkbench.tsx`、`MissionCockpit.tsx`
- `backend/app/agent/goal_preparation.py` 与实际注册的 GoalTask `prepare-plan` 路由（若名称不同，以 GitHub 真代码为准）
- Qoder 分支 `backend/app/place_source_lead.py`、`place_media_routes.py`、`plan_from_slots.py`、`departure_commit.py`、`departure_read.py`、`collective_consent.py`；**只移植需要的 signed API 和依赖，不整枝合并**。

可消费的最短产品闭环：
1. 从当前 Task 的 `prepared_plan_id` 和出发待办读取真实状态，使用新未来日期的 Journey 验证。显示“已生成候选／待补资料／可选用／已出发”真实阶段，不回第二套手动选点流程。
2. 对每个未绑定正式 Place 的 source lead，用 **已授权、可追溯的同城 provider/external_id 证据**检查/映射至受 Journey 约束的 canonical Place；需要后端持久化时复用已有显式工具，不凭名称猜测、不暗中制造 confirmed 事实。不满足则显示原来源候选和下一步并允许继续研究，不把整个任务冻结。
3. 取得足够真实路段/开放/成本证据后，通过现有服务端规则选择 CANDIDATE／出发；保留 `Idempotency-Key`、本人签名、真实可行性、日期 slot、不篡改 `PlanVersion`。不可行时如实返回 `BLOCKED` 和下一次用户能点的行动，而不是伪造 ACTIVE。
4. 明确规划下一棒的 Guardian/多人：同一 ACTIVE Journey，真正 proposer 的替代事件来源；2/3 不更新共享计划，达到服务器真实要求时 3/3 才生效。**这不是当前这棒的前置条件**。

下一次交付只认：有变化的产品 SHA、用户能点的按钮、实际 HTTP 写入读回与刷新、真实来源 vs fixture 的区分、390/430 可操作截图、可复现 blocker；局部通过就先 push，别让绿色测试成为一套只在测试室存在的软件。

## 4. Codex 仍无法使用时的独立接力

**Qoder 可临时接 P0 前端集成**，但不能把它直接写进自己 PR #35 的旧前端并谎称 Codex 分支已更新。流程：

- 从 Codex 产品 HEAD **`3c5cdd02e176a3f19fa5b4118063eb1230d658be`**（或已安全同步的后继 HEAD）创建 **独立 worktree/分支** `rescue/v3-final-departure-20261022`。保留 Qoder 的 `reform/qoder-capability-adapters-1018` 原 worktree 未提交内容。
- 限定改动：产品需要的 signed API、统一 Agent 草案准备/正式选用接线及最少有关后端能力。必要时从 Qoder 分支按文件/提交引入并做针对性回归，不整枝 cherry-pick 178 笔、不同基线的大 diff。
- 提交 PR，**base 指向 Codex 产品分支**，Codex 以后可以直接复用结果；GitHub 上报告准确 `BASE_SHA`、`PRODUCT_SHA`、`TESTED`、`RUNTIME_RESULT`。
- Qoder 优先这项真实旅客闭环，暂停无用户收益的文案/静态扫描重复战役。若用户明确允许也可让 Qoder直接代接力，前提仍是工作树隔离和测试。

## 5. 防再次“模型挂了项目一起停”

- 本文是 GitHub 上的 **外部可重建上下文**。下一次会话容量问题只需：repo、branch、HEAD、目标、最后运行结果和当前 blocker。
- 不用重新把 100+ 轮大聊天全部粘进新任务；不需要复制 41 张图片进聊天上下文，只读取仓库的设计目录。
- Github issue 评论/PR 评论 **不会自动唤醒桌面 Codex 或 Qoder**；需要用户在新任务中明确启动，或者其既有自动化监视器确实配置好。

## 6. 验收顺序与证据

1. `git status`、`git rev-parse HEAD`、实际目标基线。
2. 相关后端 narrow tests；前端 TS/typecheck/build；对应 Playwright 实际组件流，不为通过而改业务事实。
3. 在签名真实任务下只执行一次新鲜 E2E，记 ProviderCall、计划版本与 source fact；无真实提供方资料时清楚标注证据空缺。
4. 不能声称已完成：真实 ACTIVE、Guardian collective 连续闭环、手机硬件实测，除非新一轮真正拿到证据。

联系点：[Issue #42](https://github.com/Canshu-King/CityNexus/issues/42)、[Codex PR #23](https://github.com/Canshu-King/CityNexus/pull/23)、[Qoder PR #35](https://github.com/Canshu-King/CityNexus/pull/35)。
