# Codex V3 重新投入生产 | 双 Agent 接力任务书（2026-10-25）

## 首先看这几条

用户正式确认 Codex 恢复。**Codex 现在不是做旧 V1 前端，也不是直接抢 Qoder 的 PR #43。** 从本分支 `codex/sandbox-execution-security-20261025` 继续（基线 `9d4d2a853a727e05bcc76f27a1d5cfbf4e90e041`），执行 GitHub **Issue #47**。当前 rescue 分支仍由 Qoder 拥有并持续更新。Codex 从本枝提交独立 Draft PR，base 为 `rescue/v3-final-departure-20261022`，小步集成，不 force push、不从旧 V1 PR #23 整枝合并。

## 两条独立职责

**Codex：服务器内核/安全**
- 第一刀先确认并修复四条 Journey 私人 GET 的无凭证读取：`/journeys/{id}`、`/events`、`/twin`、`/experience`。复用 `resolve_journey_member_principal`（在役成员 200 / 未认证 401 / 非成员 403）。示例地点公共查询走独立脱敏端点，不因 demo mode 让私人数据公开。检查 `GET /api/v1/demo/session` 生成签名 bearer 的授权与隔离数据库边界。保留前端回归合法签名。
- 第二刀建立持久执行核心 `backend/app/simulation/`：明确 run_id+journey_id/seed、时钟、活动推进、模拟位置、场景事件、请求幂等和应用顺序。现在 `SimulationClock` 与 ClockStrip 只是第一层；不能用仅前端 `Date` 完成几天的领域步骤。复用 `execution_clock` 与 `SIMULATED_STATE_TRANSITION`，但不改 wall security clock、JWT/Provider 采集时间；不伪造设备位置。
- 第三刀把现有 `CitySignalFixture`、`refresh_demo_signals`、`autorun.pulse_journey`、`Guardian` 接到模拟事件 → 真实 Agent/工具 → 经过本人同意的 PlanVersion 修改，至少一例闭馆/迟到。P0 目标是两日模拟 Day1→Day2→SIMULATED_COMPLETED 和可重放事件日志，而不是又一个仅显示 `+1小时` 的 UI。
- 第四刀供给至少 3 个 provider 预检合格城市的 metadata/seed、真实 POI/路线快照和状态，Qoder 用于随机城市 UI。无数据就 BLOCKED，不用北京截图冒充陌生城市。

**Qoder：旅客和 Presenter 产品**
- Qoder 独占 `frontend/src/trial/mobile/`、`frontend/src/features/simulation/`、`trial/play_launcher/classroom_demo/` 和截图/用户讲解；保持老师可点的一键入口、预备真实 POI、随机城市按钮、真实 Guardian 卡、虚拟蓝点、完整可视事件时间线。
- Codex 不要修改上述 UI 文件。Qoder 暂时避免在 rescue 上同时修改 `backend/app/main.py` 的读取 ACL 与 Simulation 路由；任何新接口在 Issue #47 留下准确 contract。尤其不要两人同时改长达数万行的 main.py。

## 第一个可证明闭环

先推 Codex P0 安全提交和 401/403/200 的测试，然后一个用**同一 run_id+Journey** 在独立 demo DB 真执行的状态链：`SIM_STARTED`→虚拟 `+60min`→当前位置变化→ `SIM_ARRIVAL`→Day 2→`SIMULATED_COMPLETED`；之后继续接闭馆 Event→Guardian→Agent proposal。状态与事实必须在重启/刷新后读取一致。同 seed 可复现环境，但不可预编 Agent 的最终答案。

## 必须公开的真实边界

Qoder 目前的 18.3s 课堂彩排由预先生成的 Guardian 调整提案开始，浏览器点击接受/时间+1h/蓝点是产品真执行；它**没有**从随机城市规划到完整 Day 2，也**不是** 18 秒现场完成 Hermes 200 秒推理。`USER_VERIFIED=PENDING`（平板真实硬件未验），`PR #43 Draft`。Codex 的新分支本身只是交付接口，不能宣布已运行，必须 push 产品代码 SHA。

## 操作规范

1. `git fetch origin codex/sandbox-execution-security-20261025 rescue/v3-final-departure-20261022`，在本地新 worktree 切到 Codex 分支。不要复用 Qoder 的 working tree、数据库、端口或现场演示环境。
2. 直接打开 [Issue #47](https://github.com/Canshu-King/CityNexus/issues/47)，本任务书次之；旧 `AGENTS.md` 2026-10-22 的 Qoder sole-owner 规定只适用于当时的 rescue 分支，现由 2026-10-25 双人 overlay 覆盖。
3. 每个产品切片附 backend 有限回归、执行回执、前后权限状态、对接 API、禁止使用生产密钥/用户个人文件。能提供 390px 真实 Chrome 操作就提供，但不能因 GUI 未启动而把服务器真问题伪写成已完成。
4. 把新功能独立开 `codex/... -> rescue/...` Draft PR，明确需要 Qoder 对接的 URL、方法、认证、request/response 与 UI 交互；别在自己分支修改当前 rescue HEAD，也不自动并入旧 Codex PR #23。
5. 如用户尚未手动连接本地 Codex，本任务书不代表它已收到执行通知；本地会话需要 fetch issue 和分支才能动工。

**用户目标不是多一个开发者写文档，而是 Qoder + Codex 在数分钟课堂实操中完成一个真正运行、有突发事件和自主决策的完整随机城市旅程。**