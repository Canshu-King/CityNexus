HUMAN_CAN_USE = PARTIAL
LIVE_PROVIDER = PHOTON_HTTP_200_ZERO_USABLE
TWO_POI_FLOW = NOT_REACHED
WB2API_TOOL = PASSED (SIGNED_DRAFT_READ_ONLY_SUGGESTION)
SIGNED_AGENT_RUN = NOT_CREATED
ANDROID_PHONE = NOT_TESTED

# Mobile-First P0 进展｜2026-10-17

## 已交付产品

- ACTIVE 行程的「行程」页加入 WB2API 工作记录卡，并提供签名成员专属的运行创建、最近运行恢复和按请求编号读取接口。
- 创建运行前核验本人身份、行程状态和一次授权；服务端先持久化成员绑定，再请求模型。
- 兼容接口固定单一模型配置、关闭预算重试，只提供行程、状态和已有调整三种读取工具；服务端执行层拒绝其他工具。
- 手机只展示数据库已保存的工具名、状态和时间，不显示模型内部推理、工具参数或返回原文。

## 本机真实 AI 实测

- 在隔离试玩环境从 `/revolution` 页面发起三次签名 DRAFT AI 请求，均由 CityNexus 后端转发至本机 wb2api 网关并返回经过校验的建议。
- 请求使用 `auto:cheapest`；网关本轮实际选择 `deepseek-v4.1-flash`。
- 第二次覆盖情侣夜间活动到很晚、次日午后轻松出门的场景。模型返回经过服务端白名单校验的 `propose_public_discovery` 工具建议，类别为 `park/garden`，并提示实际开放时间须查公开地点来源。
- 真实 `tools` 协议探针返回 `inspect_journey` 工具调用帧；实际模型为 `global:deepseek-v4.1-flash`，`usage.credit=0`。这条探针只确认网关返回工具帧，没有执行工具或写入行程。
- 这证明 DRAFT 只读探索建议的真实模型工具调用已通。没有查询 POI provider，也没有创建持久化 AgentRun；响应中的 `provider_calls=0` 和 `agent_run_created=false` 与本次范围一致。
- 2026-10-17 本轮又从浏览器发起一次真实请求：页面显示「AI 建议已生成」，模型为 `deepseek-v4.1-flash`，后端返回 `park/garden` 类别的探索建议。请求没有访问地点服务、没有保存路线，也没有创建 ACTIVE 行程的 AgentRun。
- 390×844 实际页面截图：`trial/results/assets/20261017-live-ai-couple-draft-390x844.png`。
- 本机运行页：`http://127.0.0.1:14173/revolution`；本机 UI 与 API 健康检查均为 HTTP 200。

## 真实地点和行程流程

- Nominatim：此前一次真实查询返回厦门位置结果。
- Overpass：此前唯一一次真实 POI 查询返回 HTTP 502，没有重试。
- Photon：2026-10-17 在签名 DRAFT 页面完成一次真实搜索；Photon HTTP 200，返回 2 个要素，CityNexus 的公共地点校验保留 0 个可用地点，结果为 `LIVE_ZERO_RESULTS`。没有重试或切换来源。
- 当前没有可选的两个地点，因此 Pocket Walk 保存、GO 和刷新恢复没有进入执行。
- 手机实测截图：`trial/results/assets/20261017-live-photon-zero-result-390x844.png`。
- 因此两处真实 POI、Pocket Walk 保存、GO、刷新恢复仍未完成；本轮 AI 建议不能替代地点来源或实际营业时间验证。

## 验证

- `uv run --project backend pytest -q backend/tests/test_mobile_compat_agent_run.py`：1 passed，覆盖签名、成员隔离、DRAFT 拒绝、请求去重、输出隐藏和越权工具拒绝。
- `npm.cmd run typecheck`：退出码 0。
- `npm.cmd run typecheck:all`：UI 组件拆分后退出码 0。
- GitHub PR #23 提交 `286e70657a19de7c144ef9fd8699a47b189d583e` 与 `255c6c1e50e0e4b61b7cf4b190c31cfaa28595ce` 的 `trial-build`：PASS。
- 此报告中的新 AI 实测来自真实本机页面请求；上述 pytest 与既有手机截图仍分别按其 fixture / 浏览器证据等级理解。

## 2026-10-17 后续移动端检查

- 「换地区」按钮触摸高度从 38px 调整为 44px；浏览器快照在 375px 视口宽度下测得按钮为 112×44px。
- 点击切换「行程」→「我的」→「探索」后，没有新增地点搜索、AI 或支付请求。
- 城市选择和兴趣选择已拆成独立手机组件；首次进入页的按钮说明改为「点击后先创建行程草稿」。
- 390×844 浏览器初屏实测无横向溢出（文档宽度 390px）；只读取运行状态，没有发地点、模型或支付请求。
- PR #23 提交 `79b482891f5e886aadaf339326fa92af2f961c76` 的 `trial-build`：PASS（GitHub Actions run `38965055953`）。

## 尚未验收

- `TWO_POI_FLOW = NOT_REACHED`：Photon 返回 HTTP 200，但本次没有可用候选；两站保存、GO 和刷新恢复还没跑到。
- `SIGNED_AGENT_RUN = NOT_CREATED`：本次使用 DRAFT 只读建议入口，不代表 ACTIVE Journey 中已创建或持久化 AgentRun。
- `ANDROID_PHONE = NOT_TESTED`：当前为浏览器视口验收，尚无实体手机验收。

## 下一步

推进真实地点搜索与 Pocket Walk 两站保存、GO、刷新恢复；只有实际 ACTIVE Journey 可用时再验证服务端持久化 Hermes 轨迹。地点、开放时间和运行轨迹都以服务端或真实来源为准。
