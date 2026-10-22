# Revolution Lab：接入本机 wb2api 的真实 Hermes 工具 Agent

> 状态：2026-10-14 已向独立试玩分支提交配置和代码。**尚未从这次 GitHub 操作直接访问你电脑上的 7865/7863，也尚未收到 signed AgentRun 实机成功记录。**
>
> 原始本机网关教程脱敏版：`docs/LOCAL_WB2API_GATEWAY_GUIDE_20261014_REDACTED.md`。
> 目标：复用现有 `backend/app/agent/orchestrator.py::HermesJourneyAgent` 与 `backend/app/agent/gateway.py::AgentToolGateway`，**不是**另做一个会回复自然语言的假 Agent。

## 1. 接法及来源

原教程（2026-10-14）定义：

- 7865 = **免费优先路由**，模型只能写 `auto:cheapest`，具体模型名会被忽略；**链尾可能付费**。
- 7863 = **指定具体模型**，如 `global:deepseek-v4.1-flash`。
- 两者调用 `/v1/chat/completions`；必须 Authorization Bearer；不支持浏览器跨源直接调用。
- 本机已经设置 `WB2API_KEY`（但当前终端可能未继承）。
- Models may return `reasoning_content` and streaming chunks. Chat replies and `tool_calls` are separate capabilities; inspect the tool-call field directly.

CityNexus 原生 `DeepSeekJourneyAgent` 使用 `/responses`，**不能直接把 wb2api /chat/completions Base URL 塞到那个配置里**。

项目已经有 `HermesJourneyAgent` 适配器，支持 OpenAI-compatible `tools`/`tool_choice`/`tool_calls`，并遵守真实 Journey 的签名身份、工具授权和变更审批。试玩启动器配置它，而不是绕开它。

| 原教程字段 | 后端实际配置 |
|---|---|
| URL `http://127.0.0.1:7865/v1` | `CITYNEXUS_HERMES_API_URL=http://127.0.0.1:7865/v1/chat/completions` |
| Key | 后端环境中的 `CITYNEXUS_HERMES_API_KEY`，进程启动时从 `WB2API_KEY` 读取 |
| Model | `CITYNEXUS_HERMES_MODEL=auto:cheapest` |
| Router fallback | `CITYNEXUS_HERMES_MODEL_FALLBACKS=`（设为空；Router 自己决定备用候选） |
| 超时 | `CITYNEXUS_IMPACT_TIMEOUT_SECONDS=120` |
| Agent 类型 | `HERMES_COMPAT_ENDPOINT`（OpenAI-compatible adapter）；`HERMES_NATIVE_MCP`（MCP adapter） |
| 外部 AI | 显式 `--agent` 后 `CITYNEXUS_AI_ENABLED=true`，Guardian autorun 仍然关闭 |
| 交易 | mock-booking / mock-payment，不执行真实支付 |

登录凭据留在 Windows 环境 / 用户本地隐藏输入，`trial/wb2api_agent.py` 会把 Key 只注入 Uvicorn 后端子进程。没有任何 Vite `VITE_*` 密钥，浏览器只调用本地 CityNexus API。

## 2. 操作步骤（PowerShell）

先停止旧试玩程序（旧启动器窗口按 Enter）。确认已启动桌面 `WorkBuddy2API` 和 `FreeRouter`；若路由没启动，使用原教程指向的桌面启动器，不要把网关暴露公网。

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
git fetch origin
git restore --source origin/trial/revolution-first-look-20261014 -- trial/try_revolution.py trial/wb2api_agent.py trial/probe_wb2api_agent.py frontend/src/main.tsx frontend/src/trial/RevolutionFirstLook.tsx frontend/src/trial/RevolutionFirstLook.css
```

这条精准更新不会覆盖你的 `frontend/package-lock.json`（之前用 npm install 修复的依赖锁文件），也不触碰 Qoder、Commander、融合分支或原行程 DB。

检查当前 PowerShell **是否有** Key（不打印 Key 值）：

```powershell
[bool]$env:WB2API_KEY
```

若输出 `False` 也无妨，启动器会用隐藏输入询问本地密钥。**不要把网关 key 粘贴到 GitHub、issue、聊天截图或 `frontend/.env`。**

可选：检查 Router 健康（不产生模型调用）：

```powershell
Invoke-RestMethod http://127.0.0.1:7865/router/status
```

然后启动真正 Agent 版：

```powershell
py -3.13 trial\try_revolution.py --agent
```

程序会依次：

1. 在真实地图模式下本地询问用于 Nominatim 的联系邮箱，单独做用户位置搜索授权。
2. 提示这次**真实外部模型可能收到提交的 Journey 数据**，免费优先链尾仍可能付费，请输入 `y` 才允许接入。
3. 从 `WB2API_KEY` 读取凭据，否则本地隐藏输入；不打印、不提交、不写入前端。
4. 向后端独立进程注入 Hermes-compatible Agent 配置，仍保持同一个隔离 SQLite 试玩 DB。
5. 打开 `http://127.0.0.1:14173/revolution`。

如果确实需要精确指名而非免费优先，可以用：

```powershell
py -3.13 trial\try_revolution.py --agent-direct-model global:deepseek-v4.1-flash
```

此时直连 **7863**，不经过 7865 免费候选链。按每次响应的 `usage.credit` 查看实际费用；2026-10-14 的零积分结果只对应那次请求。

## 3. 用户界面里 Agent 真正在哪里？

在 `/revolution`：

- **AI Agent 连接状态**显示 `GET /api/v1/agent/runtime-status` 返回的运行时身份。`HERMES_COMPAT_ENDPOINT` 表示端点配置已加载；模型响应与工具调用由后续请求结果显示。
- 新城市搜索、Pocket Walk、GO MODE 属于 **DRAFT 私人探索**。真实 AgentRun 在正式 Journey 的 Journey Operator 中显示。
- 从有来源的公开候选地点选择“作为正式行程的首地点”后，页面可通过原有 `BootstrapJourneyStartPanel` 显式确认**未知价格**，使用原生 `generatePlans -> selectPlan -> startJourney`；这一过程要求现有服务 API 真正成功，不偷偷插入虚构 PlanVersion。
- 正式 Journey 才展示原生 `LiveRecovery` / Journey Operator：可选择“照看这趟行程”，并通过原生 Agent/计划权限接口提交需求、检查状态、审批调整。
- 你也可以进 `/v8/live` 查看旧版实时行程工作台中的 AgentRun 与工具记录。普通 Copilot 离线回答标记为 `FALLBACK`。

R107/R108 的私人 Pocket Walk 在 DRAFT 中体验。正式 PlanVersion 需要用户另行确认；可分别创建两个 DRAFT 体验两种流程。

## 4. 只验证模型的 tool_calls 协议（可选，一发真实请求）

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
py -3.13 trial\probe_wb2api_agent.py
```

此脚本：
- 对 7865 发**一条** OpenAI-compatible `tools` 请求，使用一个虚构 UUID 和 read-only `inspect_journey` 定义；
- **不真正执行函数调用，不写 DB，不调用本地 Agent gateway**；
- 只输出 `TOOL_FRAME_PASS`、`CHAT_ONLY_OR_UNVERIFIED` 或 HTTP/连接错误、模型名、`usage.credit`，不回显密钥或聊天内容；
- 此请求**可能消耗积分**。在确认网关付费末端是否禁用后再运行。

`TOOL_FRAME_PASS` 表示模型返回工具调用帧。下一步是在真实 signed Journey 中运行 AgentRun，并检查服务器保存的工具步骤和授权结果。

## 5. 验收三档

| 阶段 | 完成条件 | 下一步 |
|---|---|---|
| L0 配置 | `/agent/runtime-status` 显示 `HERMES_COMPAT_ENDPOINT` | 发起一次模型请求，检查响应 |
| L1 协议 | `TOOL_FRAME_PASS`，并记录模型与 `usage.credit` | 在签名 Journey 中启动 AgentRun |
| L2 Agent | 真实签名 Journey 保存 AgentRun、tool_steps 和授权决策；刷新后仍可读取 | 在手机上验收完整用户流程 |
| L3 产品 | 用户在 `/revolution` 用真实地点和需求完成 Agent 流程，并在手机上验收同一版本 | 现场信息、支付和到场状态各自查看对应记录 |

工具请求可能返回普通文本、503、超时或模型错误。记录本次结果，并按请求限额处理后续重试。

## 6. 秘钥、费用及可用性

- 用户原始教程附件包含网关 Key；本次提交未加入该凭据。请在 wb2api 网关轮换此 Key。
- 网关 7865 最末端仍是可能付费的 `cn:space-bunny`；如果你的硬要求是绝对零积分，按原教程移除其路由兜底并重启 free-router，随后允许所有免费模型冷却时报 503。
- 用户点击启动 Agent 或提交行程意图后，模型才接收对应上下文。地点、授权、承诺和付款状态来自服务器记录。
- 本次完成远程源码核对；本机 WorkBuddy2API 与真实 `tool_calls` 结果待实测。
