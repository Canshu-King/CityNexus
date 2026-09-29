# ORD-0443 补充收据 · 通道已经能把产品状态写出来了（附三枚具名缺口） · 2026-09-29 12:0x（本机时区）

这份**取代** `ORD0443_RECEIPT_r2.md` 第四、五节里那句"通道尚未接成可用"的判语：那一版我用响应体的字段名去猜产品有没有拿到内容，猜错了，判据报了假。
正确的读法是产品自己的库，所以我改从 sqlite 现读，零额外模型调用。跑手 `ord0443_wired_ab_r2.py`、
`ord0443_durable_ab_r1.py`，读数 `ORD0443_WIRED_AB_R2.json`、`ORD0443_DURABLE_AB.json`
（四枚的 blob 见块内逐条 40 位）。

## 一、同一句话、同一条门，两臂只差"接不接通通道"

门：`POST /api/v1/journeys/{journey_id}/agent/commands`（路由装饰在 `backend/app/main.py:1194`，以重基后的树现读）。
两臂各自独立的车道库、独立 uvicorn，通道那一臂的 shim 是**我车道里那份补丁副本**，跑在 OS 分配端口上，
你正在用的 :7864 一个字没动。

| 读数 | 关通道臂 | 接通道臂 |
| --- | --- | --- |
| 门的状态码 | http 200 | http 200 |
| 响应字节 | 247 B | 3,908 B（同键 `off.copilot.bytes`／`on.copilot.bytes`） |
| `journey_missions` 行数 | 0 | 1 |
| `agent_runs` 行数 | 0 | 1 |
| `agent_run_steps` 行数 | 0 | 0 |
| `events` 行数 | 0 | 0 |
| `audit_logs` 行数 | 4 | 10 |

接通道那一臂的两行是真的：`journey_missions.user_text` 存的就是我发的那句英文原话（头 120 字在
`on.mission.user_text_head`），`agent_runs` 那行 `provider_key = deepseek`、
`model_key = global:glm-5.2`、`status = COMPLETED`，而 `agent_runs.outcome` 里是模型自己写的话
（头 220 字在 `on.agent_run.outcome_head`）。判据 `verdict_channel_writes_product_state` = 真。

所以：**零产品字节**（两臂都没改仓里任何东西），只靠环境变量就能把这条通道接进出产品的写路径；
变量名是 `CITYNEXUS_AI_ENABLED`、`CITYNEXUS_AI_API_KEY`（或 `DEEPSEEK_API_KEY`）、
`CITYNEXUS_AI_MODEL`、`CITYNEXUS_DEEPSEEK_API_URL`、`CITYNEXUS_IMPACT_TIMEOUT_SECONDS`。

## 二、三枚具名缺口（都在产品里，不在网关里）

1. `journey_missions.compiler_model_key = mission-compiler-v2-fallback`、
   `compiler_provider_key = deterministic` —— 语义编译那一层没吃到模型，回落到了确定性档。
   与我先前量到的一致：shim 不翻译 `text.format`（产品的 `json_mode`／`response_schema` 走这一枚）。
2. `agent_runs.status = COMPLETED` 而 `agent_run_steps` **零行** —— 一次"完成"的运行没留下任何步骤。
   绿着但没干活的那一形。
3. `agent_runs.outcome` 模型开口要 journey ID —— 行程身份没进模型的上下文，尽管 mission 行里
   `journey_id` 是有值的。这条最贵：它意味着即便通道稳定，产品交给模型看的也不是同一份事实。

## 三、网关侧复测（同一批门，本次）

`/healthz` http 200、92 B、3.34 s；`/v1/models` http 200、19,080 B、7.48 s（三十九枚 id 不变）。
仍然**没有 429**，但同一枚 `/v1/models` 从早先的 2.14 s 走到 7.48 s，而 06:4x 那一轮它整条不答——
延迟没有上界这件事仍然成立。

## 四、我等你两句话

- shim 那两处补丁（流式默认值、不带 `type` 的 `{role, content}` 条目）归谁维护：我这份副本在
  `evidence/…/shim_r2_patch.diff`，要正式可用得决定是并进 `codex-shim` 还是产品自带一枚
  chat/completions 客户端。
- 上面缺口 2、3 是产品自己的事（一次 COMPLETED 运行没有步骤、行程身份没进模型上下文）：
  要不要我接单，你说一声；不接我就只把读数交在这里。
