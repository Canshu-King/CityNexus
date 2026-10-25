# Issue #49：Presenter 后端接线

产品分支：`codex/sandbox-execution-security-20261025`，PR #48 → Qoder rescue。
可复制客户端：[examples/simulation-client.ts](examples/simulation-client.ts)。无 React 依赖，不改 Qoder UI。

## HTTP 顺序

所有请求使用同一个隔离数据库、同一 Journey 和同一 run。

1. 服务端 Presenter 用 `X-CityNexus-Presenter-Key` 调用 `POST /api/v1/demo/pairing {journey_id}` 取得 120 秒一次性 ticket；浏览器不要持有共享 Presenter key。
2. 浏览器 `POST /api/v1/demo/pairing/redeem {ticket}` 换取 900 秒签名 bearer。此 bearer 限定 Journey/数据库；成员和角色仍由数据库核验。
3. `GET /api/v1/journeys/{jid}/simulation/runs/current` 恢复运行。仅 `NOT_STARTED` 时调用 `POST .../runs {seed}`；开始条件仍为原生 ACTIVE Journey + ACTIVE PlanVersion。
4. `POST .../runs/{rid}/advance {expected_sequence}` 走下一原生阶段；加 `minutes` 可推进多站/跨日。
5. `POST .../runs/{rid}/scenes {expected_sequence,scene_id,event_type,activity_id}` 注入闭馆/天气/迟到。
6. 用户选择运行 AI 后，调用 `POST .../guardian {expected_sequence,model_consent:true}`。该调用会等待 Guardian；同时以独立 GET 轮询 `.../progress`，例如每 2 秒、页面离开即停。读取不会触发模型。
7. 显示 `guardian_runs`、`agent_runs`、`steps` 的持久状态。`external_model_call/FAILED_EXTERNAL` 显示模型失败，`TOOL_ERROR` 显示工具失败。配置存在与真实执行分开；没有步骤就不要播放编造的工具时间线。
8. 用户选择接受后，使用同一 bearer 调原生 `POST /api/v1/replans/{proposal_id}/accept`，然后读取 progress 的 `proposals[].acceptance_audit_ids` 和当前 PlanVersion。接受会保留原可行性、集体权限与原子写入检查，并记录 `AUTHENTICATED_TRAVELER`。接受入口也读取该 Journey 的持久虚拟业务时间。
9. 事件已由原生流程解决后，读取最新 run，再 `POST .../resume {expected_sequence}`；继续至 Day 2 和 `SIMULATED_COMPLETED`。刷新/重启后读 current/progress。

第 3–6、9 步的每个 POST 都需要独立 `Idempotency-Key`。保留该命令的 **原 body 和 key**；连接中断后先 GET，必要时只重放原请求。不要换 key 自动补发模型调用。每次成功后使用返回的新 sequence。

## progress 读取约定

`GET /api/v1/journeys/{jid}/simulation/runs/{rid}/progress` 要求签名 `JOURNEY_READ`，返回 `Cache-Control: private, no-store`。

- `events`：仅本 run 注入的事件，标为 `SIMULATED`。
- `guardian_runs`：同 Journey + 上述事件的 Guardian；不会把另一事件或旧执行当本次成功。
- `agent_runs/steps`：按子 mission 的 Journey/trigger_event_id 关联，包括 Guardian 尚未填最终 agent_run_id 的运行中记录。
- `proposals`：Guardian 对应事件的原生方案引用和签名接受审计 ID。
- `readiness.missing`：`MODEL_CREDENTIALS_MISSING`、`STANDING_MISSION_REQUIRED`、`OPEN_SCENE_EVENT_REQUIRED`、`RUN_NOT_AWAITING_GUARDIAN`；这是本地前置检查，`network_checked=false`。
- 不投影工具参数/结果、模型自由文本或原始错误；固定失败码是 `MODEL_REQUEST_FAILED` / `TOOL_CALL_FAILED`。
- `clock_policy`：行程业务使用持久虚拟时间；bearer 到期、模型 lease、审计和 provider capture 使用真实时间。

## 前端错误处理

| HTTP | 操作 |
|---|---|
| 401 | 重新配对，不循环重发旧请求。 |
| 403 | 显示当前角色不能执行，保留只读运行画面。 |
| 409 | GET current/progress 校准 sequence、事件和方案；由用户决定下一操作。 |
| 503 | 显示服务/隔离库暂不可用，保留已读状态；用户再次操作时重试。 |

模型调用失败也可能以 HTTP 200 返回 `PAUSED_MODEL_UNAVAILABLE`；看 run/Agent/step 状态，不把 HTTP 200 画成模型完成。

## 现场配置和数据接线

由 Qoder 启动器注入到**隔离后端进程**，不要写到浏览器或仓库：

- `CITYNEXUS_SIMULATION_ENABLED=true`、`CITYNEXUS_DEMO_MODE=true`、非 production 环境；`CITYNEXUS_DATABASE_URL` 与绝对 `CITYNEXUS_DEMO_DATABASE_PATH` 指向同一独立 SQLite。
- 随机 `CITYNEXUS_TRAVELER_AUTH_SECRET` 和 `CITYNEXUS_DEMO_PRESENTER_KEY`（至少 32 字符）；Presenter key 只用于服务端出票。
- 兼容模型：`CITYNEXUS_HERMES_API_URL` + `CITYNEXUS_HERMES_API_KEY` + 所需 `CITYNEXUS_HERMES_MODEL`；或原生 `CITYNEXUS_AI_API_KEY` + 对应模型/Responses 地址。配置不代表网关已经连通。
- 已有真实 ACTIVE 行程和 ACTIVE standing mission，权限为 `PROPOSE_ONLY` 时让用户接受；不创建假 ACTIVE 来补证据。
- 真实城市供给：用既有 GoalTask 的地区解析/地点/路线获取保存 provider receipts；`POST .../simulation/city-identity {source_task_id}` 绑定实际 adcode；`GET .../simulation/cities?seed=17` 检查。每城至少 5 POI、3 条合格路线；经明确选择 `POST .../cities/publish {publish_public_facts:true}` 后才进入公共目录。

本次 Codex 测试进程未配置模型凭据，未操作 Qoder 的现场服务/数据库。现场真实模型、三城供给及 Chrome 两日彩排由 Qoder 接入后验收；本地测试双替身不会计入这些实绩。
