HUMAN_CAN_USE = PARTIAL
LIVE_PROVIDER = BLOCKED
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

- 在隔离试玩环境从 `/revolution` 页面发起两次签名 DRAFT AI 请求，均由 CityNexus 后端转发至本机 wb2api 网关，HTTP 200。
- 请求使用 `auto:cheapest`；网关本轮实际选择 `deepseek-v4.1-flash`。
- 第二次覆盖情侣夜间活动到很晚、次日午后轻松出门的场景。模型返回经过服务端白名单校验的 `propose_public_discovery` 工具建议，类别为 `park/garden`，并提示实际开放时间须查公开地点来源。
- 这证明 DRAFT 只读探索建议的真实模型工具调用已通。没有查询 POI provider，也没有创建持久化 AgentRun；响应中的 `provider_calls=0` 和 `agent_run_created=false` 与本次范围一致。
- 390×844 实际页面截图：`trial/results/assets/20261017-live-ai-couple-draft-390x844.png`。
- 本机运行页：`http://127.0.0.1:14173/revolution`；本机 UI 与 API 健康检查均为 HTTP 200。

## 真实地点和行程流程

- Nominatim：此前一次真实查询返回厦门位置结果。
- Overpass：此前唯一一次真实 POI 查询返回 HTTP 502，没有重试。
- 因此两处真实 POI、Pocket Walk 保存、GO、刷新恢复仍未完成；本轮 AI 建议不能替代地点来源或实际营业时间验证。

## 验证

- `uv run --project backend pytest -q backend/tests/test_mobile_compat_agent_run.py`：1 passed，覆盖签名、成员隔离、DRAFT 拒绝、请求去重、输出隐藏和越权工具拒绝。
- `npm.cmd run typecheck`：退出码 0。
- GitHub PR #23 当前提交 `286e70657a19de7c144ef9fd8699a47b189d583e` 的 `trial-build`：PASS。
- 此报告中的新 AI 实测来自真实本机页面请求；上述 pytest 与既有手机截图仍分别按其 fixture / 浏览器证据等级理解。

## 尚未验收

- `LIVE_PROVIDER = BLOCKED`：两处真实 POI、保存、GO 和刷新恢复缺少可用的 Overpass 响应。
- `SIGNED_AGENT_RUN = NOT_CREATED`：本次使用 DRAFT 只读建议入口，不代表 ACTIVE Journey 中已创建或持久化 AgentRun。
- `ANDROID_PHONE = NOT_TESTED`：当前为浏览器视口验收，尚无实体手机验收。

## 下一步

推进真实地点搜索与 Pocket Walk 两站保存、GO、刷新恢复；只有实际 ACTIVE Journey 可用时再验证服务端持久化 Hermes 轨迹。地点、开放时间和运行轨迹都以服务端或真实来源为准。