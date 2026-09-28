# ORD-0443 收据 · wb2api 网关读数与接入实测 · 2026-09-29 06:3x（本机时区）

红线遵守方式：密钥只从 `C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/config.json` 的字段
`api_key` 在运行时读进子进程环境；本收据与所有 JSON 里都没有它的值（发布前对 29 个文件做过逐字节
匹配扫描，命中数 0）。下面只写路径与字段名。

## 1 网关本体是活的，"三枚路由不答"不是网关的毛病

`GET /healthz`（无鉴权）答 http 200、92 B、0.48 s，并带 `X-Service: workbuddy2api` —— 这个身份标识
把"7863 上有人答"和"是本网关答"分开。带 Bearer 的 `GET /v1/models` 答 http 200、19,080 B、2.14 s，
**39 枚模型 id**；`GET /status` 答 http 200、4,122 B，池子 `healthy 5 / total 5 / cooling 0 / disabled 0`
（`realm_totals`：cn 3/3、global 2/2）。`/panel/` 200、51,501 B（与你量到的字节一致）。
之前那三枚"15 秒不答"是在带 `HTTP(S)_PROXY=127.0.0.1:7892` 的语境下量的，本机现在没人听这个口；
我这轮所有测量都用 `ProxyHandler({})` 直连，读数立刻就有了。

## 2 真实 chat 路由与逐枚模型 id（以读到为准，含对你原话的一处更正）

- 补全门：`POST /v1/chat/completions`（OpenAI 形状，`api_key` 非空时吃 Bearer）；
  另有本地翻译层 `codex-shim`（`shim.mjs:311`）把 `POST /v1/responses` 转成上面这扇门，默认口 :7864。
- 更正：你说"国际版 deepseek、国内版 GLM"。**读到的是反的**：deepseek 三枚全在 `cn:` 域
  （`cn:deepseek-v4-flash`、`cn:deepseek-v4-pro`、`cn:deepseek-v4.1-flash`），
  GLM 两边都有（`cn:glm-5.1/5.2/5.3/5.3-flash/5v-turbo` 与 `global:glm-5.2/5.3`）；
  `global:` 域另有 `gpt-5.3-codex`、`gpt-5.4/5.5/5.6-*`、`gemini-3.5-flash`、`kimi-k3` 等。
  全清单在 `WB2API_READOUT.json` 键 `probes.models_fast.model_ids`。

## 3 最小补全（三枚，状态码/字节/耗时）

`WB2API_COMPLETION.json`，`max_tokens: 1`，同一句话：

| 模型 | 状态 | 字节 | 耗时 | 正文 |
| --- | --- | --- | --- | --- |
| `cn:deepseek-v4-flash` | http 200 | 805 B | 2.02 s | 空串，`finish_reason: length`，`reasoning_tokens: 1` |
| `global:glm-5.2` | http 200 | 771 B | 0.96 s | `ok` |
| `cn:glm-5.2` | http 200 | 773 B | 1.82 s | `ok` |

deepseek 那格空正文不是通道坏：那一行 `completion_tokens: 1` 而 `reasoning_tokens: 1`，
一枚 token 全花在思考上，所以正文空是预算形状，不是没答。把同一扇门、同一个槽位再发一次做对照
（`WB2API_DEEPSEEK_16TOK.json`，跑手 `wb2api_deepseek_budget.py`）时，两档预算都 `TimeoutError`
（1 枚与 16 枚各 120 秒不答）——也就是说这条通道在 06:1x 能答、06:3x 就不能答了。

**没有 429**，所以"429 就切主通道"这半条没触发；下面第 8 节是复测，把那两枚以上状态都留着。

## 4 接进产品：零产品字节做不到，卡口在 shim，不在 CityNexus

产品侧的门（你自己 grep 的那三个变量名，实测只找到两个）：
`CITYNEXUS_AI_ENABLED`（`backend/app/core/config.py:16`）、
密钥 `CITYNEXUS_AI_API_KEY` 或 `DEEPSEEK_API_KEY`（`backend/app/core/config.py:23`）、
**URL 变量名是 `CITYNEXUS_DEEPSEEK_API_URL`，没有 `DEEPSEEK_API_URL` 这枚**（`backend/app/core/config.py:26`），
模型名 `CITYNEXUS_AI_MODEL`（`backend/app/core/config.py:18`）。

只给这些变量、不改任何产品字节时，产品的 Responses 客户端 `DeepSeekResponsesClient`
（`backend/app/integrations/ai/responses.py:264`）三种形状全失败（`ORD0443_SHAPES.json`：
plain 10.53 s、json_mode 1.16 s、with_tools 2.02 s 都 FAIL）。用一只本地回声服务把**产品实际上发出的
字节**钉下来（`ORD0443_WIRE_ECHO.json`）：`input` 是 `[{"role":"user","content":[{"type":"input_text",…}]}]`，
问题原文确实在网上。两个失败原因都在 shim：

1. `shim.mjs` 把出站固定成 `stream: true`，而分派只看 `body.stream === false`
   （`shim.mjs:302`）⇒ 产品不带 `stream` 字段，于是拿到 `text/event-stream`，客户端按 JSON 解就炸。
   我按 OpenAI 语义把默认改成"没写 stream 就是非流式"（补丁见 `shim_r2_patch.diff`）。
2. 就算改完，`responsesToChat`（`shim.mjs:42` 起）的 switch 只吃 `type: 'message'` 等**带 type** 的条目，
   产品发的是 `{role, content}` 不带 type ⇒ 整条被丢，上游只看到空会话，
   回 http 200 加一句客套问候。**这是最坏的一类假绿**：通道答 200，内容却是空的。
   证据：两句话的 `input_tokens` 恒等于同一个数（31），答案都是 "Understood. How can I help you today?"
   （`ORD0443_MESSAGE_TRAVELS.json` 第一次跑）。

在一次性导出里补上这两处（`shim_patch/shim_r2.mjs`，`node --check` 过；我没动你正在跑的 :7864 那份，
它也服务 Codex，动它属于共享状态），产品自己的客户端就真拿到内容了
（`ORD0443_PRIVATE_STACK.json`、`ORD0443_MESSAGE_TRAVELS.json` 第二次跑）：
"21 times 4" → 答 `84`，耗时 66.56 s；关门的追问 → 答
"Move the Nexus River Cruise to tomorrow morning."，耗时 1.71 s；两问 `input_tokens` 46/49 不同（内容真的在走）。

## 5 你因环境收不了的格子：重取结果

- `ai_state` 对偶（同一扇门两次进程，只差一枚变量）：关 → `DISABLED_BY_OPS`
  （`/api/v1/health` http 200、113 B；`/api/v1/agent/runtime-status` http 200、408 B）；
  接通通道 → `CONFIGURED_UNVERIFIED`（118 B、414 B）。
- `PROVIDER_REFUSED` 这格现在**量得到**了：通道接通但只给 10 秒预算时，
  产品自己的 mission 落 `status: DEGRADED`、`failure_reason: "DeepSeek Agent completion failed"`、
  `ai_state: PROVIDER_REFUSED`（`ORD0443_WIRE_A_B.json` 键 `on.copilot`，
  shim 侧对应三条 `AbortError`，见 `codex-shim/shim.log`）。
- **READY 这格收不了，因为词表里没有这个词**：`backend/app/agent/ai_availability.py:36-39`
  只有 CONFIGURED_UNVERIFIED / NOT_CONFIGURED / DISABLED_BY_OPS / PROVIDER_REFUSED 四枚，
  没有任何"已配置且已验证通过"的状态。所以通道再顺，`ai_state` 也只会停在
  `CONFIGURED_UNVERIFIED`。要那格，得先裁一枚新状态（这是词表决定，不是测量决定）。

## 6 接进产品还差的两级（都在产品外或都是 knobs，不需要新功能）

1. **产品侧一枚被借用的时限**：`backend/app/agent/runtime.py:282` 给 agent 的模型客户端用的
   `timeout_seconds = settings.impact_timeout_seconds`，默认 10 秒（`backend/app/core/config.py:36`，
   原本是 impact provider 的旋钮）。实测真实答案要 1.71–66.56 秒 ⇒ 十秒必然砍断。
   判别实验：只把这枚旋钮放到 180 秒，同一条命令的 mission 从 `DEGRADED/PROVIDER_REFUSED`
   变成 `COMPLETED/CONFIGURED_UNVERIFIED`（`ORD0443_E2E_PATCHED.json` 键 `cases`）⇒ 拦路的是时限旋钮，
   不是通道。修法该是给 AI 客户端自己一枚变量，不是把 impact 的旋钮拧大。
2. **shim 不吃 `text.format`**：产品的 `json_mode` / `response_schema` 走
   `body.text.format`，shim 里没有对应翻译（grep 无 `json_schema`/`response_format`）⇒
   结构化意图丢了。后果实测到了：mission 虽然 COMPLETED，但**没有产生任何中断事件**，
   于是 ORD-0432 那格仍是 `robust: true`、`risk_reason_codes: []`（同一收据键 `events_after: []`）。
   也就是说"模型说话 → 产品建事件 → 摘要点名"这条链现在断在 shim 丢 schema，不是断在 ORD-0432。

## 7 NOT_DONE（具名）

- 通道没接成产品可用状态：需要你先裁 shim 两处补丁归谁维护（一次性导出在我车道
  `evidence/…/shim_r2_patch.diff`），以及要不要给 AI 客户端单独一枚时限变量。
- 模型驱动的一次"中断上报→事件→摘要"整链复取：等上一条裁下来再取，否则量到的还是假绿。
- H8b（模型支撑的提示注入）与 H11 的模型驱动整跑：同上，依赖通道先可用。

## 8 复测（同一批槽位，25 分钟后）：通道的失败形是"挂住"，不是限流

跑手 `wb2api_recheck_r1.py`，读数 `WB2API_RECHECK.json`：

| 门 | 结果 |
| --- | --- |
| `GET /healthz`（无鉴权，先前 0.48 s 答 200/92 B） | 这轮 20 秒不答（TimeoutError） |
| `GET /status` 池子 | 仍报 `healthy 5 / total 5 / cooling 0 / disabled 0`（cn 3/3、global 2/2） |
| `cn:glm-5.2` | http 200、774 B、**22.81 s**，正文 `ok`，`finish_reason: stop` |
| `global:glm-5.2` | 45 秒不答 |
| `cn:deepseek-v4-flash` | 90 秒不答 |

同一枚 `global:glm-5.2` 在 06:1x 是 771 B、0.96 s 答 `ok`。所以这条通道现在能给的最好说法是：
**它确实能出真答案（两枚 200 带正文），但延迟没有上界，池子自报 healthy 也拦不住挂住**——
而产品的 agent 回合默认只给 10 秒（第 6 节）。这就是为什么我不把 ORD-0443 报成"已接进产品可用"：
可用的判据要包含延迟有界，而这里我量到的是 0.96 s、1.71 s、5.8 s、22.81 s、45 s 不答、90 s 不答。

判据留给号令者裁：要不要给通道加一枚墙钟上限与"槽位连续不答就摘掉"的实测门（池子已经有
`breaker_threshold`/`breaker_cooldown`，但它显然没管住"连接在、不答"这一形）。
