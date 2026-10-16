HUMAN_CAN_USE = PARTIAL
LIVE_PROVIDER = BLOCKED
WB2API_TOOL = MODEL_NOT_VERIFIED
SIGNED_AGENT_RUN = TEST_FIXTURE_ONLY
ANDROID_PHONE = NOT_TESTED

# Mobile-First P0 进展｜2026-10-17

## 本轮实现

- 在 ACTIVE 行程的「行程」页加入 WB2API 工作记录卡。
- 新增签名成员专属的运行创建、最近运行恢复和按请求编号读取接口。
- 创建运行前确认本人身份、行程状态和一次授权；服务端先持久化成员绑定，再请求模型。
- 兼容接口固定单一配置模型、关闭预算重试，只提供行程/状态/已有调整三种读取工具；服务端执行层也会拒绝其他工具。
- 手机只展示数据库里保存的工具名、状态和时间，不展示模型内部推理、工具参数或返回原文。配置存在时不再显示“已连接”。

## 检查结果

- `uv run --project backend pytest -q backend/tests/test_mobile_compat_agent_run.py`：1 passed。覆盖无签名、非成员、DRAFT 拒绝、成员隔离、同请求不重复、响应隐藏参数/结果、越权工具不执行。
- `npm.cmd run typecheck`：退出码 0。
- 逐路径 `git diff --check`：通过。
- 正在运行的 wb2api 本机模型目录请求返回 200；当前隔离 CityNexus 后端 `/api/v1/health` 返回 `ai_state=DISABLED_BY_OPS`。本轮没有发出 Chat Completions 请求，也没有模型工具调用或真实签名 AgentRun。

## 城市探索实测

- Nominatim：一次真实查询返回厦门位置结果。
- Overpass：一次真实 POI 查询返回 HTTP 502。没有重试；两处 POI、Pocket Walk 保存、GO 和刷新恢复均未完成。

## 下一步

将隔离后端以本机 wb2api 配置启动，并在真实签名 ACTIVE 行程中由用户点击一次“检查行程”，检查服务端是否实际保存允许的工具步骤。城市 POI 流程待 Overpass 可用时重新安排单次有界验证。
