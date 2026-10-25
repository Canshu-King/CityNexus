# 守护调用路径与 AI 开关（隔离实测）

日期：2026-10-26 02:07（本地）
栈：合并后的 `de06e6a7` backend，课堂库只读副本（源库未写），端口 60400。

## 环境

- `CITYNEXUS_AI_ENABLED=false`
- 从 env 移除 `CITYNEXUS_AI_API_KEY`、`CITYNEXUS_HERMES_API_KEY`、`CITYNEXUS_DEEPSEEK_API_KEY`
- `CITYNEXUS_SIMULATION_ENABLED=true`、`CITYNEXUS_DEMO_MODE=true`

## 动作（全部为产品 HTTP 调用）

1. `POST /api/v1/demo/pairing` → `redeem` 取 presenter bearer。
2. `PUT /api/v1/journeys/{id}/guardian/mission`（standing mission）。
3. `POST /api/v1/journeys/{id}/simulation/runs/{run}/scenes`（CLOSURE）→ `PAUSED_FOR_GUARDIAN`。
4. `POST /api/v1/journeys/{id}/simulation/runs/{run}/guardian`（`model_consent: true`）。

## 读数

- 六十秒时副本数据库已出现两条 `agent_runs`：
  - `deepseek` / `deepseek-v4-flash` / `RUNNING`
  - `hermes` / `cn:hy3` / `PARTIAL`
- run 状态 `GUARDIAN_RUNNING`（第 2 步），`virtual_now` 未推进。
- 请求在 300 秒门限内**未返回**（这是把上一轮 120 秒门限的观察延长后的读数）。

## 中间结论

- `ai_enabled=false` **不拦调用路径**：开关关掉、三枚 key 从 env 移除之后，Guardian 仍然创建并推进 `agent_runs`（与 ORD-0359 的「ai_enabled 不拦调用路径」一致）。
- 课堂侧影响：老师误按一次「交给守护助手」可能真的发起模型调用（存在费用与上下文外发），而不是快速得到「不可用」。

## 请求（Codex / #47）

1. Guardian 入口在 `ai_enabled=false`、凭据缺失或 provider 明确不可用时，应**先门后调用**：快速 503 或 `PAUSED_MODEL_UNAVAILABLE`，不要先创建 `agent_runs`。
2. 若产品决定「关闭开关仍允许守护」是预期，请在契约里写明，并让课堂 UI 在按下前说明会产生模型调用。

## 终态与缺陷链（02:08）

- `POST /guardian` 回 **200**，run 置 **`PAUSED_FOR_ACCEPTANCE`**（18:06:17 → 18:07:06，约 49 秒）。
- `guardian_runs.a9060944`：`trigger_event_id=d61152b8`（正是 run 的 pending event）、`proposal_id=21f0a92e`、`decision=RECOVERY_REQUIRED`、`status=PARTIAL`、`action_status=PROPOSAL_PRESENTED`、`reasoning_summary=Agent reached the configured tool-step limit.`
- **但** `replan_proposals.21f0a92e.trigger_event_id` 是 `880cec4e`（prepare 的旧 CLOSURE），不是 `d61152b8`。
- `progress` 投影：`guardian_runs[0].proposal_id = null`、`proposals = []`——UI 拿不到提案 id。
- 结果：run 停在「等待接受调整」，两个事件都 `DETECTED`；`/resume` 会被 `SIMULATION_EVENT_REQUIRES_SIGNED_RESOLUTION` 拦，接受又没有可用提案 id → **课堂按一次「交给守护助手」即死锁**。
- 另：`ai_enabled=false` 且三 key 移除不拦调用；三条 `agent_runs` 全 `PARTIAL`（deepseek、hermes×2）。

## 请求（升级为 P0）

1. `proposal.trigger_event_id` 必须等于该 guardian_run 的 `trigger_event_id`（当前串到旧事件）。
2. `progress` 必须投影 `guardian_runs[].proposal_id` 与 `proposals[]`（当前空），否则 `PAUSED_FOR_ACCEPTANCE` 无法被 UI 解除。
3. `ai_enabled=false` 时应先门后调用（快速 503 / `PAUSED_MODEL_UNAVAILABLE`）。
4. 课堂侧陈旧事件/旧提案卫生我在启动器里另做（只留最新一条 open 事件），属缓解不是修复。

