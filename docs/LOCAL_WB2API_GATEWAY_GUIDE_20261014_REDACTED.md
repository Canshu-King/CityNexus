# 教程：在本机其他项目里调用 wb2api 网关（GitHub 脱敏版）

> 来源：用户提供的《教程_本机项目接入网关_2026-10-14.md》，标注原始测试时间 2026-10-14 21:00。
> 文档用途：Python / Node / 脚本 / 网页 / OpenAI 兼容工具接入本机 wb2api。
> **保留原教程 0—7 章的主要配置、参数、实测和限制。为防止密钥泄露，原文多处硬编码 API Key 全部替换为环境变量 `WB2API_KEY`；本机用户名、局域网地址等也改为占位符。**
> “已实测”为原作者当日的本机记录；本仓库未复测。价格、路由池和服务状态会变化。

---

## 0. 三十秒版本

| 项 | 值 |
|---|---|
| Base URL（免费优先） | `http://127.0.0.1:7865/v1` |
| Base URL（指定具体模型） | `http://127.0.0.1:7863/v1` |
| API Key | **只从本机环境变量 `WB2API_KEY` 读取，不放在 GitHub** |
| 7865 模型 | **只能使用 `auto:cheapest`** |
| 7863 模型 | 具体型号，如 `global:deepseek-v4.1-flash` |
| 协议 | OpenAI 兼容 `/v1/chat/completions`，可 `stream` |
| 费用 | 7865 **免费优先**，但原教程明确链尾含可能付费的 `cn:space-bunny`；不要写成绝对零收费 |

Python 标准库（无第三方依赖）：

```python
import json
import os
import urllib.request

key = os.environ.get("WB2API_KEY")
if not key:
    raise RuntimeError("Set WB2API_KEY in your local environment")

req = urllib.request.Request(
    "http://127.0.0.1:7865/v1/chat/completions",
    data=json.dumps({
        "model": "auto:cheapest",
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 300,
    }).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    },
)
with urllib.request.urlopen(req, timeout=120) as r:
    result = json.loads(r.read())
    print(result["choices"][0]["message"]["content"])
```

## 1. 两个端口，两种行为

| | 7865 free-router | 7863 网关本体 |
|---|---|---|
| 可选模型 | `auto:cheapest` | 原教程报告共 51 个模型 |
| 模型名 | 写其他名称会被路由层忽略 | 具体 `cn:` / `global:` 模型名 |
| 价格逻辑 | 免费候选优先，最后可能转入付费兜底 | 按选中具体型号计费 |
| 适合 | 常规应用和弹性成本调度 | 精确指定模型、诊断和模型列表 |

原教程 2026-10-14 的候选链：

```text
global:deepseek-v4.1-flash
 -> global:hy3
 -> global:step-5-preview
 -> cn:hy3
 -> global:hy4-preview-f
 -> cn:space-bunny (paid fallback)
```

7865 自身不做最终密钥校验，但把 `Authorization` 原样转交 7863；因此 **两边都需要 API Key**，原教程实测缺失返回 401。

状态（不需 key）：`GET http://127.0.0.1:7865/router/status`，查看 `serving`、`cooling`、`cooldownLeftSec`、`fails`、累计统计。

## 2. 语言 / 客户端调用

### 2.1 Python 标准库及计费信息

```python
import os, json, urllib.request

key = os.environ["WB2API_KEY"]
req = urllib.request.Request(
    "http://127.0.0.1:7865/v1/chat/completions",
    data=json.dumps({
        "model": "auto:cheapest",
        "messages": [{"role": "user", "content": "只回复四个字：测试成功"}],
        "max_tokens": 300,
    }).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
)
with urllib.request.urlopen(req, timeout=120) as response:
    result = json.loads(response.read())
    actual = response.headers.get("x-free-router-model")
print(result["choices"][0]["message"]["content"])
print("实际路由模型", actual)
print("消耗 credit", result.get("usage", {}).get("credit", "NOT_REPORTED"))
```

### 2.2 Python OpenAI SDK

原教程说明本机未预装 `openai` / `requests`，需先 `pip install openai`。

```python
import os
from openai import OpenAI
client = OpenAI(
    base_url="http://127.0.0.1:7865/v1",
    api_key=os.environ["WB2API_KEY"],  # 显式指定，防止其他 OPENAI_API_KEY 顶包
)
r = client.chat.completions.create(
    model="auto:cheapest",
    messages=[{"role": "user", "content": "你好"}],
)
print(r.choices[0].message.content)
```

### 2.3 Node.js 18+（内置 fetch）

```javascript
const key = process.env.WB2API_KEY;
if (!key) throw new Error("WB2API_KEY required");
const resp = await fetch("http://127.0.0.1:7865/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${key}`,
  },
  body: JSON.stringify({
    model: "auto:cheapest",
    messages: [{ role: "user", content: "你好" }],
  }),
});
if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
const data = await resp.json();
console.log(data.choices?.[0]?.message?.content);
```

### 2.4 curl（Windows cmd）

```bat
curl http://127.0.0.1:7865/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer %WB2API_KEY%" ^
  -d "{\"model\":\"auto:cheapest\",\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}"
```

### 2.5 流式输出

```python
stream = client.chat.completions.create(
    model="auto:cheapest",
    messages=[{"role": "user", "content": "写一首短诗"}],
    stream=True,
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

原教程的 SSE：可能先收到 `delta.reasoning_content`，后收到 `delta.content`；结束帧 `data: [DONE]`；最终 `usage.credit` 可能在末尾出现。**reasoning_content 是模型附加字段，不是可供安全/授权判断的事实。**

### 2.6 网页 / CORS

原教程实测网关 OPTIONS → 405，未启用 CORS。**不要直接在浏览器写 `fetch("http://127.0.0.1:7865")`；也不要把 API Key 硬编码在前端。**

仅在本地开发时可使用 Vite 代理（但前端若自带 key 仍会泄露；生产/真实使用应由后端携带密钥）：

```javascript
// vite.config.js — 配合后端持有鉴权信息更安全
export default {
  server: {
    proxy: {
      "/wb2api": {
        target: "http://127.0.0.1:7865",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/wb2api/, ""),
      },
    },
  },
};
```

### 2.7 GUI 工具

- 地址：`http://127.0.0.1:7865/v1`
- API Key：从本机 `WB2API_KEY` 安全填入
- 模型：`auto:cheapest`
- 精确指定：`http://127.0.0.1:7863/v1` 加模型名

## 3. 2026-10-14 原教程的“免费清单”（非当前保证）

| 原教程模型 | 上下文 | 原教程观察 |
|---|---|---|
| `global:deepseek-v4.1-flash` | 1M | 当日 cost_per_1k=0，大请求主力 |
| `global:hy3` | 192K | 免费链成功率较高 |
| `global:step-5-preview` | 1M | 新候选 |
| `cn:hy3` | 192K | 国内池后备 |
| `global:hy4-preview-f` | 1M | 当日成功率较低，靠后 |
| `cn:space-bunny` | 未载明 | 付费兜底，原教程约 0.0013—0.0035 分/千 token |

原教程还指出：`cn:hy4-preview-f` 曾限免，至 10-14 被测为 0.2744 分/千 token；同名 `cn` / `global` 价格独立。**实际价格必须重新核实**，不能凭倍率图标或历史清单推断。

自查：带 key 的 `GET http://127.0.0.1:7863/v1/models`、响应 `usage.credit`、本地面板 `http://127.0.0.1:7863/panel`，或本机 `python wb2api/measure_price.py <模型> 600`（注意这会发一条真实模型请求）。

## 4. 注意事项

### A. 钱和额度

1. 默认 7865 + `auto:cheapest`；**免费优先但不保证免费**。
2. 想绝对禁止付费兜底，原教程建议将 `cn:space-bunny` 从 `free-router/config.json` 中禁用，**并重启 router**；全免费链冷却时应允许 503 而不是偷偷付费。
3. 7863 按指定模型当时价格计费。
4. 并发上限原教程为 6（global 池 4）；不要并发压测。需付费批量测试先取得用户确认。

### B. 重试 / 大小 / 兼容性

5. `503 all_free_models_cooling`：按 `retryAfterSec` 稍后重发；避免无界重试及重复有副作用操作。
6. 请求体上限 8MB，较大 PDF/图片需拆分或先抽取文本。
7. `response.model` 可不带 `cn:` / `global:` 前缀；7865 的 `x-free-router-model` 告知实际路由模型。
8. 两端都必须携带 Authorization，否则 401。
9. 7863 的 `reasoning_effort` 可以不传或使用模型支持的档位；7865 自动转换。
10. 原教程实测 `/router/status`、`/v1/models` 可能绑定 `0.0.0.0`，局域网其他设备可以读到部分模型/状态信息；请检查 Windows 防火墙。

### C. Windows 环境坑

11. 系统配置可能有 `HTTP_PROXY` / `HTTPS_PROXY`；确认 `NO_PROXY=127.0.0.1,localhost`。纯本地 httpx 客户端可设置 `trust_env=False`，避免意外走代理。
12. 本机还可能有**其他** `OPENAI_API_KEY`，要显式传 `WB2API_KEY`。
13. 原教程称网关通过计划任务 `WorkBuddy2API` + `FreeRouter` 自启；若没起，按自己的本地启动器启动，不要从其他工作目录直接运行可执行文件。
14. 网关进程必须保留其专用工作目录，否则可能找不到 `config.json` 导致密钥/账号错位。
15. 原教程运行的网关是自建 v1.12.0 + filefix，不应直接用官方新版二进制覆盖补丁。
16. 其他设备需要使用电脑**当前局域网 IP**（通过 `ipconfig` 查询），并确认网络隔离与防火墙策略，别把 Key 或 7863/7865 直接暴露到公网。

## 5. 错误速查

| 状态 | 可能原因 | 建议 |
|---|---|---|
| 401 `invalid_api_key` | 缺 key 或 key 不对 | 检查当前环境 `WB2API_KEY`，不要回显其值 |
| 503 `all_free_models_cooling` | 免费链冷却 | 看 `retryAfterSec`，稍后再试 |
| 502 / ProxyError | 系统代理劫持 localhost | 设置 `NO_PROXY` |
| `Connection refused` | 本地网关未运行 | 使用原网关启动器 |
| CORS / OPTIONS 405 | 网关不允许直接跨域调用 | 服务器端转发，不在浏览器保管 Key |
| 413 | 请求体超过上限 | 拆分内容 |
| 401 且面板能开 | 网关启动时工作目录不对 | 用正确的本地启动器 |
| 7865 忽略模型名 | router 固定候选链 | 7863 直连具体模型 |

## 6. 服务管理速查

| 做什么 | 原教程方式 |
|---|---|
| 查免费链 | `GET http://127.0.0.1:7865/router/status` |
| 看积分 | `http://127.0.0.1:7863/panel` |
| 启动全部 | 桌面「启动 WorkBuddy2API.lnk」或专用 `Start Gateway.cmd` |
| 重启 router | 在自己本机 `wb2api` 工作目录运行 `python wb2api/restart_router.py` |
| 看日志 | 本机 `wb2api/free-router/router.log`（原教程称 2MB 自动轮转） |
| 工作目录 | 按用户本机实际安装路径，不要在 GitHub 记录个人主目录 |

## 7. 原教程实测记录（2026-10-14 约 21:00）

| 原教程测试 | 原教程记录 |
|---|---|
| 7865 `auto:cheapest` 非流式 | HTTP 200 / 约 1.5s，`global:deepseek-v4.1-flash`，`credit=0` |
| 7865 流式 | HTTP 200，SSE 约 240 帧，`credit=0` |
| 7863 直接 `global:deepseek-v4.1-flash` | HTTP 200 / 约 2.0s，`credit=0` |
| 7865 无 key | 401 |
| 7863 无 key | 401 |
| OPTIONS CORS 预检 | 405 |
| `/router/status` | `healthy: true`，当时 6 条候选 serving，累计 13171 次请求，成功率 92.3% |

原教程共记录三次真实模型调用且当时 `credit=0`。**本 GitHub 版本仅保存这份用户提供的测量记录，不宣称重新调用过本机网关。**

---

## 附：接入 CityNexus Revolution Lab

详见 `trial/REVOLUTION_AGENT_WB2API_CONNECT.md`。Revolution 的现有 `app.agent.orchestrator.HermesJourneyAgent` 需要完整 POST 地址：

```text
CITYNEXUS_HERMES_API_URL=http://127.0.0.1:7865/v1/chat/completions
CITYNEXUS_HERMES_MODEL=auto:cheapest
CITYNEXUS_HERMES_MODEL_FALLBACKS=
CITYNEXUS_HERMES_API_KEY=(backend-only, from local WB2API_KEY)
```

**不是** DeepSeek 原生 `/responses`；7865 不接受准确指定模型名。只有真正返回 `tool_calls`，并通过真实 Journey AgentRun 和授权 API，才算 Agent 能用。
