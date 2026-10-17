# CityNexus Qoder P0 | 用户先走通：签名会话 → 立即进入行程 → 看见 Agent 工作过程
> 2026-10-17 / GPT 派工；收件对象：Qoder 主产品线与 Commander。主线 `mirror/integration-frontend-apple-pass1`；协调分支 `commander/control`。本文件**仅为任务书，不是已完成的实现**。
>
> 本次核对时 Qoder 权威 HEAD = `f5ecd9d854000e7eaa6ca07c55bd0436d4f80c68`；Commander HEAD = `e4cbe7ecd41c587a73681af5fdfd0824347d8a53`。施工前 fetch 最新 HEAD 并以当时真实基线为准，不重放旧 SHA。
>
> 关联：既有 [Issue #27](https://github.com/Canshu-King/CityNexus/issues/27)（缓存串人已经有 PR #28/#29/#30 合入）；Commander ORD-0685（签名身份门）已实现、实测 16/17 PARTIAL；**ORD-0687 是已派工的凭证签发/前端接入，不得复制出另一套身份系统**。
>
> 用户亲测 `127.0.0.1:14176/revolution` 属于 **Codex 隔离试玩分支**，当前因地名服务不可用无法自然进入第二步，而且看不到 Agent 工作过程。其对应 [#26](https://github.com/Canshu-King/CityNexus/issues/26) 已派 Codex 修复；**Qoder 不得抢改 Codex 的 `design/revolution-mobile-first-v1`，更不得把自己本机 V8 测试称为 14176 已修好**。

## 本轮唯一目标与交付原则

从用户角度，**一部手机、两位不同旅客**：打开 Qoder V8 → 新建自己的行程 → 立即看见行程主页（不被可选住宿查询扣住）→ 进入清晰的下一步操作 → 在“AI 工作动态”查看真实运行状态或准确解释为何没有运行 → 换人不回放前人的任何记录。

先交真实产品代码与一个可操作入口，再补精简截图和验收。**禁止一轮只更换尺、只刷新 ORD/账本、只提交测试报告/长审查文档。** 有实际 blocker 就点名一处，不无限重复 provider 或 Agent 付费请求。产品提交优先于报告提交。

## 施工顺序（每阶段产出可合入的小 PR，单阶段最多一个主 PR）

### A / P0 第一棒：收口 ORD-0687，真正让签名身份进到用户第一趟行程

**现状源码证据：**
- `backend/app/main.py:2537-2567` 的 `POST /api/v1/travelers` 仍返回 `traveler_schema(traveler)`，**没有 `access_token`**；
- `backend/app/main.py:2570` 已有 `GET /api/v1/travelers/session`，`backend/app/traveler_principal.py` 已有 `issue_traveler_token` / `resolve_traveler_principal`；
- `frontend/src/app/V8Experience.tsx` 的 `createJourney()` 在创建一趟行程时先直接 `POST /travelers` 新建旅客；当前没有读签名会话重用 traveler 的通路；
- `frontend/src/lib/agentSessionCache.ts` 目前只保留模块内存中的会话与事件，并会移除旧 localStorage 缓存；这是 Issue #27 已做出的保守修复，**不能因想保存聊天记录而撤销这个安全基线**。

**直接改代码：**
1. 后端签发一枚**只对应本次新创建 Traveler** 的短期签名 token（仅当 `CITYNEXUS_TRAVELER_AUTH_SECRET` 合法配置），创建响应/运行 OpenAPI 同代包含 `access_token?: string`。无 secret 则明确无字段或配置错误，不伪造签名；不通过传入任意已有 traveler_id 签发。带 token 的响应 `Cache-Control: private, no-store`，不得进入日志、前端错误提示或 GitHub 证据。
2. 前端在 `frontend/src/api/citynexus.ts` 附近新增唯一 session holder（适合 `frontend/src/lib/travelerSession.ts`）：token 仅放模块内存与 `sessionStorage`，**不进 localStorage / IndexedDB / URL / 埋点**；用 Bearer 调 `GET /travelers/session` 回读并匹配 `traveler_id`，不能信客户端自报 id。修改 `V8Experience.tsx::createJourney` 为“有合法签名会话则复用当前 Traveler；首次才创建 Traveler 并签发”，使**同一位旅客能够建多趟行程**而非每次一个新身份。
3. 身份变化、显式切人、登出、401/403、过期时，立即清除 Agent 内存缓存及可见轨迹，旧 Journey 指针只是引用，必须由服务端授权验证后显示。不可默认回放另一个人的 `citynexus.v8.journey_id`。受保护的调用统一加正确签名头，但别把“已带 Bearer”冒充“所有旧路由已执行服务器端成员授权”，明确列出尚未真正检查 caller 的旧 endpoint。
4. **关键安全判据：** 仅靠匿名 `POST /travelers` 拿到新 token，不等于已有账号登录与跨设备身份核实；15 分钟默认 token 过期后如尚无可信重新认证，必须明确“当前会话已过期，原行程未删除，但不可凭 traveler_id 自助恢复”，不可偷偷新建 Traveler 伪装恢复。恢复方案另需经真实认证，绝不发放“按 id 换 token”后门。
5. **缓存持久化不是本轮必须完成项**：除非两名签名查看者+服务端成员验证都过，保持现有“内存限定/刷新后不冒充恢复”，不要为了让自己刷新后有聊天记录而重新落盘泄露。

**A 验收（真实路由、独立临时库）：** 配 secret：新建 A → 得到签名 token → /session=本人 → 同一 A 建两趟 Journey；无 secret：不提供伪 token；过期、伪造、缺失 token 分别得到已存在的具名拒因；A/B 共用一个手机测试会话，切到 B 后**绝无 A 的问题/答复/tool.steps 闪现**；登出与刷新行为如实记录。至少一组 390×844 Playwright + 后端 contract tests + typecheck/build。变更至少包含后端 + 实际用户前端，**不能用只过 schema 证明完成**。

### B / P0 第二棒：一创建成功就进入“我的行程”，可选服务不得扣住入口

**现状源码证据：** `frontend/src/app/V8Experience.tsx::createJourney` 在 `POST /journeys` 成功、写入本地 journey_id 后，还 `await searchStayOptions(...)`，接着 `await load(journey.id)`，最后才 `navigate("hub")` 和关闭创建向导。住宿供应商超时可能让用户看着“准备中”，即使行程已落库。代码虽已有“停止等待”，但流程仍把核心入口放在可选异步操作之后。

**直接改代码：**
1. 拆成“**行程创建/主数据读取**”与“**可选住宿搜索/AI 规划**”两个明确状态。服务端确认写入后优先让用户进入可操作的 Today/行程页；住宿或第三方可选查询独立展示 `查询中 / 暂不可用 / 有结果` 与可恢复按钮，后台仍在处理时保持服务端事实准确。保留原有真实供应商许可与明确请求授权；无来源不得编造住宿或价钱。
2. 对 `POST /travelers`、`POST /journeys` 等无幂等键写入不得“超时后自动重发”：如果请求结果未知，屏上说明“正在核实，不能确认是否创建成功”，优先签名只读查证和用户显式选择，不得删除老行程、自动重置数据库或多建重复旅客。
3. 320/390/430 宽首次进入界面“一屏一个主要下一步”：已新建→打开这趟→告诉 AI 我的旅行需求（仅已可用时）/手动选地点/查看行程；如果地点或地图服务不能使用，显示应用内可点击的明确恢复路径，不能只给开发者术语、要求用户自己找 OSM URL 或坐标。V8 如果根本没有可调用的替代来源，诚实显示“此环境目前无法进行真实地点查找”，不偷偷插入虚构城市与 POI。
4. 保留现有 `MapPanel` 地图瓦片故障降级和暗色/无障碍修复，不重新做一套 UI 框架。可以复用 `--cn-touch-min`、`--cn-nav-clearance`、`AgentRunRail` 等现有能力。

**B 验收（一个真实用户序列）：** 用独立后端/临时库，点击 1 次新建后 `POST /travelers` 与 `POST /journeys` 的实际返回可追溯；人为令**可选住宿查询超时**，仍在确认创建成功后可打开/刷新自己行程；可选失败不使首屏永远 spinner；主按钮无底栏遮挡；提供同一 checkout 的手机截图与桌面截图。真实 provider 结果和模拟故障分开列，不要求多次公网击穿来凑成功。

### C / P1 第三棒：用户始终能找到 Agent 工作过程，没运行也说明白

**直接改代码，优先复用，不要另写假的 AI：**
1. 在 `/v8/hub`（Today）和当前行程页提供清晰的 `AI 工作动态 / 查看工作过程` 入口，展示 `未启用 / 已配置但未验证 / 正在执行 / 等待本人审批 / 失败 / 离线`，各状态来自真实 Gateway、AgentRun、服务端事件，而非前端假进度。DRAFT/尚无 Run 时显示“暂无真实 Agent 工作记录”的原因和下一步；禁用 AI 环境仍可使用普通行程。
2. 复用 `frontend/src/features/agent/CopilotDock.tsx::NativeMissionTimeline`、`frontend/src/features/agent/AgentRunRail.tsx` 与已有 `NativeRuntimeEvent`。对 `tool.started / completed / failed` 显示中文工具功能、真实时间/时长、来源及失败，只有真实已验证的摘要才能称“判断依据”；绝不展示模型私有思维链、原始敏感 tool 文本，也不把 WATCHING 叫“AI 正在思考”。
3. 复用 #27 的 403/404 拒绝显示逻辑。SSE `EventSource` **不能带任意自定义 Authorization header**，接签名用户前须核实真实服务端访问控制；不安全时采用带签名的只读拉取/轮询，不得开启无权限事件流。审批必须仍走现有服务端 authority，不以 UI 的绿色按钮代替授权。
4. 在 GitHub 新增一份简洁的**实拍图文教程**（建议 `frontend/docs/QODER_FIRST_TRIP_ILLUSTRATED_CN.md`）：首页→身份→创建→下一步→失败恢复→当前行程→Agent 工作记录→退出/换人。每张截图标号、按钮原文、预期状态；真实 Agent 暂不可用时必须照实写，不拿 fixture 伪作运行。

**C 验收：** 390×844 真浏览器看得到“工作动态”入口；没有 Run 时不会出现“执行中”的假状态；signed Run 存在时显示真实同人同 Journey 工具事件；服务器 403/404 不闪现前一人的内容；审批不能匿名提交。可用单次真实 provider/Agent trace（如有权限），否则诚实标 `NO_LIVE_RUN`，但不扣住已修好的首页交付。

## 合作边界：给 Codex 铺路，但不撞车

- Codex #26/#24 负责 `14176/revolution` 的现场 Nominatim 卡死、一键备用区域和移动 Agent 透明度；Qoder **不进它的工作树修改同名 TSX/CSS**。
- Qoder 在自己的 V8 修复身份和首旅程后，向 [Codex #26](https://github.com/Canshu-King/CityNexus/issues/26) 和 [#24](https://github.com/Canshu-King/CityNexus/issues/24) 只回交一份**可复用契约**：身份接口/显式状态表/时间线去重函数的具名路径与代码 SHA（不要复制整个框架）；Codex 决定在自己 branch 最小吸收。
- 不从 `commander/control` 的证据树推断产品分支已部署，不全仓强合、不 force push、不改共享真实库、不对外公网暴露 localhost。

## 时间盒 / 交付纪律

- **A：第一个施工 checkpoint。** 目标优先半天内给出实际前后端 commit 和 PR；如 ORD-0687 已有人施工，接力其现有 patch，不另开重复 ORD 分支。
- **B：紧随 A 的第二个 checkpoint。** 目标一次真实“创建成功却被住宿查询拖住”的红→修复→浏览器可进入 Today；先交用户入口再补长报告。
- **C：第三个 checkpoint。** 对运行记录入口和中文图文教程做收口；不拿实际 Agent 服务缺席拖住 A/B。
- 每 checkpoint：**一个真实代码 SHA / 改了哪个用户动作 / 同一运行下真实 HTTP 与浏览器读数 / PR 与可运行 URL 或本地启动命令 / 一个剩余 blocker**。总结果不超过一屏主报告；附链接可展开。不要每次再新增 10 个 ORD、上百行审查政策。
- 绝不声称“已上线/用户已玩过”，除非用户本人打开那条同 SHA 部署入口并完成操作。最终交付必须标注 `USER_OPENABLE`、`USER_VERIFIED`、`SIGNED_TRAVELER_SESSION`、`JOURNEY_READY_BEFORE_OPTIONAL_PROVIDER`、`REAL_AGENT_RUN` 分别是什么证据等级。

## 直接开工的最小文件清单

- 后端：`backend/app/main.py`、`backend/app/traveler_principal.py`（复用现有）、`backend/app/schemas.py` / `contracts/openapi.yaml`、签名会话 contract 测试。
- 前端：`frontend/src/app/V8Experience.tsx` 的 `createJourney` / boot、`frontend/src/api/citynexus.ts` 的请求层、`frontend/src/lib/agentSessionCache.ts` / 新的 session holder、`frontend/src/features/agent/CopilotDock.tsx` 与必要的 Today UI。
- 验证：`frontend/playwright.config.ts` 已能用独立 seed/test env；新用例不要写死私人端口或 fixture Journey ID；不引入新的验收运行器除非现有 Playwright 真的不支持。

**开始执行，而不是仅回复“已接受”。施工的下一个消息应包含本阶段至少一个真实产品代码 commit；若遇到不可绕开的安全阻塞，给出精确文件/函数/接口和错误，不伪造绿灯。**
