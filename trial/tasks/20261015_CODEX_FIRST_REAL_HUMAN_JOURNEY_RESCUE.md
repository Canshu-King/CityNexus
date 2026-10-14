# CityNexus Revolution | First Real Human Journey Rescue

**日期**：2026-10-15；**主责**：本地 Codex（独立修复分支）；**Qoder**：暂不同时改试玩版代码，仅按需做最后一轮极窄接手审查；**优先级 P0 用户无法使用**。

> **这不是代码风格清理、ORD 任务或新一轮 R111 研究。实际用户已经连续多次尝试、仍然无法进入下一步，准备睡觉。明早要看到可亲自使用的网页、真实的测试结果和一份简短的操作说明，而不是再看一份几百条核对清单。**

## 1. 真正的问题与现有证据

项目：`Canshu-King/CityNexus`，新的工作分支 `fix/revolution-first-human-e2e-20261015`，**基于** `trial/revolution-first-look-20261014` @ `ca00e365025932164a166fae9ca5fe8dedec6556`。

用户本人在 Windows 的 `D:\moodle\CityNexus-Revolution-Trial` 中，用 `py -3.13 trial\try_revolution.py --agent` 和浏览器 `http://127.0.0.1:14173/revolution` 真实操作，已经出现过以下严重产品失败：

1. **多层许可和阻断**：第一次需要填大量 WGS84、城市标签、类别、多个勾选框，点很久仍留在首屏。
2. **旧页面误路由**：用户粘贴 `/revolution**` 后退回原版 V8「新建行程」；已有窄修但路由必须仍测试。
3. **地名搜索成功、地图却空白**：Nominatim 返回 `连城县，龙岩市，福建省，中国` 等公开结果后，地图区域只有灰色方块（可见 OSM attribution），任何点击均无法可靠继续；把 OSM URL 输入框当作正常用户的后备操作同样失败。
4. **AI 脱离主流程**：仅显示 `HERMES_COMPAT_ENDPOINT · CONFIGURED_UNVERIFIED` 不代表调用成功。后续已经新增试用版只读 Hermes tool guide，但未有用户实机证明。
5. **最新致命反馈**：页面出现红色横幅 **「这一步没有完成。请检查网络后重试，已保存的行程不会因此消失。」**，用户仍无法完成一次探索。该通用文案源于 `frontend/src/trial/RevolutionQuickExplore.tsx::messageForError`（除 401/403/429 外所有失败归为同一句），**用户不知到底哪一步坏了**。源码旁有 `rawError` 折叠技术详情，但用户不应承担读栈和修网关的责任。

**不要臆断这个错误是 AI、Nominatim、Overpass、404、422、身份或 CORS 导致。现在截图不能定位阶段。** 需要以浏览器 Network 里的具体 `method/path/status`、脱敏响应 detail、同次后端日志和前端阶段为证据确定故障原因。一次失败一次定位，不要无边界重试外部服务。

已核对源代码：
- `frontend/src/trial/RevolutionQuickExplore.tsx`: `cityLookup`, `consultHermes`, `discover`, `saveWalk`, `go`, `run`, `messageForError`;已将**直接点击 Nominatim 返回的县城结果**改成 `useCenter(..., "EXPLICIT_GEOCODER_APPROX")`，不再强制地图瓦片 / OSM 链接。但是服务端是否认可此语义需要实际 API 回归。
- `frontend/src/api/citynexus.ts`: `requestJsonInner` 对非 2xx 抛 `CityNexusApiError(status, body, message)`，UI 目前没有针对请求阶段+服务器原因给人能看懂的区别；`suggestTrialDiscovery`、`bootstrapCitySearch`、`bootstrapDiscovery`、`saveBootstrapDiscoveryPocketWalk`、`transitionBootstrapPocketWalkGo` 都要核对。
- `trial/agent_preview_app.py`: 本地限定的 `POST /api/v1/journeys/{id}/trial-ai-discovery`，签名、DRAFT、成员、rate limit，并通过 7865/7863 OpenAI-compatible `tools` 向 Hermes 模型请求**只读**兴趣建议。**不是完整 AgentRun**。
- `trial/try_revolution.py`: 试玩版 backend 需用 `--app-dir trial agent_preview_app:app` 完整重启，光 Vite HMR **不会加载新 Python 模块**。不要破坏 `trial/.runtime/` 数据、私钥或本地修复过的 `package-lock.json`。
- `frontend/e2e/revolution-quick-explore-ui.spec.ts`: 当前测试使用假数据 + 模拟 token，不是 signed Journey 和真正 API 执行证明。它可以做 UI 断言，**不能给整个实机流程盖章**。
- `.github/workflows/revolution-trial-ux-smoke.yml`: 最新流水线 `38608162269` 已 **success**，只跑了 Python 语法/离线配置、TS typecheck、Vite build。**绿 CI + 用户红屏正是当前要解决的鸿沟。**

## 2. 施工策略：只修人实际会碰的闭环

### 任务 A：先复现，把通用红条变成可诊断、可恢复的具体问题（必须先做）

- 在**独立测试身份/一次性临时数据库**启动最新试玩入口，保留用户真实 DB。不与运行中的 Qoder 或其他 Agent 端口串进程。
- 打开 `/revolution`，按用户路径用“连城”与简单意图逐步操作。捕获 Chrome/Playwright 的真实 `method/path/status` 和服务器错误代码，按阶段关联：AI、城市、选区、公开地点查询、候选保存、Pocket Walk、GO、正式 Operator。
- **错误展示**：普通用户看到如「AI 暂时没响应，可以不使用 AI 继续」 / 「地图服务暂时无结果，换地点或类别」 / 「登录过期，请重新登录」 / 「两个地点还没保存成功，重试保存」及一个主要恢复操作，不要再用万能红条。「技术信息」折叠最多保留可复制的**脱敏** request/status/code，不得把 API Key、Authorization、cookie、个人地址、完整敏感响应或 stack 泄露到 DOM、日志、GitHub。
- 不能根据字符串匹配 `error.message` 粗糙推断 HTTP 结果，优先利用已有 `CityNexusApiError.status`、`.body` 以及 `OriginResponseUnusableError` 和 `fetchWithReadDeadline` 状态，专门区分 timeout/429/503/500/422/404/401。空白地图只影响 optional map，不可阻塞主路线。
- **预期**：明确指出旧截图的这句「这一步没有完成」最可能从哪个 request、哪个 backend gate 抛出，写入证据。原因不确定就保留 UNKNOWN，不要写猜测成定论。

### 任务 B：默认成为“人类旅行助手”，不是后台管理控制台

**目标最短用户动作**（不用清数据）：

1. `/revolution` 一进入，正文顶部可以直接写「我在连城，今晚有三小时，想轻松走走」，点击 `让 AI 帮我想想`，这是一次明确的外部模型请求。模型不给 `tool_calls`、模型冷却、失去凭据或返回纯文字，都要友好解释且继续**手动**流程，不应卡住。
2. `连城` → **查找位置（一次清楚的 Nominatim 请求）** → 点击“连城县，龙岩市”整个结果卡片 → **自动进入下一屏**。不要求地图 tiles、不要求用户粘 OSM URL、不填写 WGS84，不额外重复“确认城市”和重复勾选。县城 geocoder 数据是 **APPROXIMATE CAMERA CENTER**；点击卡片只代表用户显式选择“从近似公开区域周边查”，必须与服务端 provenance 协议一致，不能假造 `MAP_TAP` 或 `GPS`。若该 backend 目前只允许地图点选，则补真正的用户选择近似区域合同/错误处理，不以关闭 provenance gate 换成功。
3. AI 建议/人手选类别 → **搜索附近地点**：只在用户明确点击后向 Overpass 送出已披露类别、约 2.5km 公开中心。无 LIVE_PROVIDER 结果就给有意义的结果状态和能继续的选项，**不得**引入 TEST_PROVIDER 冒充实地可去地点。
4. 真正收到至少 2 个同一次 `receipt_id` 的不同真实候选 → 选两站 → 服务端保存成员私有 Pocket Walk → 进入 GO MODE → 自报第一站 → 继续第二站 → 刷新保持服务器同一成员进度；无 route/travel-time 真值不得编造 ETA。
5. 遇到未验证营业、未知费用或地址，界面说人话，不把服务端 metadata/内部英文 protocol 枚举抛给用户。只在完全独立的高级调试区露出。
6. 如候选符合 `READY_FOR_NATIVE_PLAN`，让用户主动转入 `BootstrapJourneyStartPanel`、正式 Journey / `LiveRecovery` Operator。若不符合就保留私人 GO MODE，**不要伪造 ACTIVE PlanVersion**。

真实 Agent 的两个等级分清：
- `MODEL_TOOL_SUGGESTION` = 试用引导里**真实模型返回的只读工具建议**，但没有执行地点查询也没有 AgentRun。
- `AgentRun` = ACTIVE Journey 通过现有 AgentToolGateway、身份和审批成功执行并有 durable tool_steps；单纯显示 `HERMES_COMPAT_ENDPOINT` 绝对不算。**不要为了 demo 修改这些语义！**

### 任务 C：一个真正的连续“人类体验”验收，而非重复 verifier

**最少做到**：

- Windows Python 3.13、Node 22，`py -3.13 trial/try_revolution.py --agent`（或独立的同构测试服务）可真实启动；端口/URL/进程来源有证据。包含后端 `agent_preview_app:app`，而不是误以为只是 Vite 改了。
- `npm run typecheck:all`、`npm run build`、`python -m py_compile trial/agent_preview_app.py trial/try_revolution.py`。
- 浏览器 1440x900 + 390x844 真正截图/录屏；测试**不看 JSX 假想完成，测试鼠标/手指实际操作**。从打开页面到“看见真实/诚实的地点搜索结果、选择、保存、GO、刷新”的连续交互，报告每一环的用户可见文字。
- **独立的 contract-backed browser E2E**：在本次测试自己启动的 backend、SQLite 和签名登录凭证上操作（不能只拦截 fetch 把全部接口伪造成成功）；另保留 UI-only TEST_PROVIDER fixture 测按钮。至少验证真实服务器收回并验证 Pocket Walk 的成员身份、状态和 revision；拒绝其他成员读取。
- 地图瓦片强制 abort，点城市卡片仍能进入下一屏。没有提前点“查找位置”不能发 Nominatim；没有主动点“搜索附近地点”不能发 Overpass；不点击 AI 按钮不能请求模型。
- 失败注入：404（忘了重启旧后端）、401 token、422（API 合同错）、502/503（模型/公开服务）、429（冷却）、超时。**分别出现区别清楚的中文提示及可操作的恢复动作**，不会停在万能红条。一个按钮点了有响应/等待/错误终态。
- 模型协议可在本地 mock 客户端上跑“有真实 tool_calls / 纯文本无 tool_calls / 错误 / 迟到 / 双击”测试；**真实 wb2api 只在本地有密钥、经用户原有授权并有成本/上限前提下执行至多一次有边界的只读试用**。在不知道 7865 是否仍有付费候选时不要自动大量扣费。不上传 key，不公布完整 prompt。
- 触摸、键盘、对比度、布局：一屏只有一个突出“下一步”，页面文本主要为自然中文。关闭 PWA/Service Worker 缓存干扰，用干净上下文与更新已有体验两种方式都试。
- 真 LIVE Overpass 实际不可达或者县城附近根本没 2 个可信点时，报告如实 BLOCKED，而非改 fixture 让它绿色。需演示时应选择有公开数据、具名来源的其他用户可选地区，不替用户偷偷换城市。
- **明确分档**：COMPILE_PASS、UI_FIXTURE_PASS、SIGNED_BACKEND_PASS、REAL_PROVIDER_PASS、MODEL_TOOL_PASS、HUMAN_USABILITY_PASS、FULL_OPERATOR_PASS。没有证据的项必须写 NOT_VERIFIED/BLOCKED，不能捆绑成总成功。

## 3. 交付要求（Codex 明早留的东西）

1. 在 `fix/revolution-first-human-e2e-20261015` 实现真实修复，提交并 push。按需小步改，不得长期占住不提交，附明确 commit SHA。
2. 开一个以 `trial/revolution-first-look-20261014` 为 base 的**修复 PR**（不要对 Qoder 主线 PR），内容包括修复根因、最短用户体验结果、3 张真正的截图（desktop、mobile、错误恢复）、测试执行命令与成功/失败数量。
3. 更新 `trial/tasks/20261015_CODEX_FIRST_REAL_HUMAN_JOURNEY_RESCUE.md` 旁的 `trial/results/20261015_FIRST_HUMAN_JOURNEY_RESULT.md`。文档开头就写 **「用户现在能用：是/否，阻塞在哪，明天用户要不要运行任何命令」**，不要先写 50 页框架证明。
4. 提供一个 Windows PowerShell **一次性、安全更新+启动命令**，只覆盖必要的产品源码，不删 `trial/.runtime`、SQLite、本机授权、`WB2API_KEY`、`frontend/package-lock.json`；明确停止旧 Uvicorn 进程才能生效。不能再要求用户手动输入坐标或消化英文错误码。
5. 任何需要 Qoder 改共享后端的缺口，由 Codex 在 PR 明确列出“具体服务端合同+最小补丁”，**Qoder 只接该项**，不启动跨分支全量融合。
6. 产品成功的最终闸门不是 test count，而是用户自己打开同一页面能走完连续的操作。**没有浏览器可用性证据，不得宣称 DONE。**

## 4. 施工边界

- 不碰 `commander/control`、`mirror/integration-frontend-apple-pass1`、Revolution 主分支或用户主产品环境。
- 不隐藏严重错误，不删授权/成员隔离，不移除 provenance gate，不造 LIVE_PROVIDER/ToolRun/到场凭据，不开启真实支付或订票；不要“为了过测试”给 AI 回答编造景点。
- 不能无界请求 Overpass/Nominatim 或反复外部 Hermes; 问题越多越要停下来精准修单个失败门槛。
- 不允许“查一下仓库又写任务书，又过了一夜什么都没修”。**时间配比：根因定位 20%、产品修复 60%、实际用户验收 20%。**

## 5. 给同一个本地 Codex 的简明指令

```text
请立即接手 Canshu-King/CityNexus 的 P0 真实用户解卡。
先 fetch，切换 fix/revolution-first-human-e2e-20261015，
全文执行 trial/tasks/20261015_CODEX_FIRST_REAL_HUMAN_JOURNEY_RESCUE.md。
用户已经实际打开过 Revolution 多次仍无法完成，最新屏幕只显示
「这一步没有完成。请检查网络后重试……」。
你的任务不是审计和复查，不是重开 R 或 ORD，而是找到这个错误背后的
真实 failed request / backend reason，修到人可以从 AI 自然语言入口、
连城县选择、真实地点查询、双站保存、GO MODE、刷新恢复中持续往前。
先实测再修，修了再以真实浏览器实测；保留任何无法取得的 provider/AI
证据为 BLOCKED/NOT_VERIFIED。优先实际改代码，不能只写下一棒任务书。
测试通过后 push 修复分支、建 PR 到 trial/revolution-first-look-20261014，
并用简短中文在结果文档开头告诉用户明早打开网页实际该看到什么。
原有用户 DB、lockfile、凭据一概不删不公开。不执行有风险的真实支付/预订。
```
