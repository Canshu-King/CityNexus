# Guardian 当前场景提案与 AI 开关修复

对应 Issue #47 评论 6401253491（2026-10-26）；交付 PR #54，独立后端分支。

课堂调用返回旧事件的 proposal_id 时，原接口仅凭存在编号就进入 PAUSED_FOR_ACCEPTANCE，而 progress 正确排除了旧事件提案，导致页面无法接受或继续。

本次改动：

- Simulation Guardian 在消费 sequence、创建运行记录或进入模型前检查 AI 开关；关闭返回 503 SIMULATION_AI_DISABLED，保留当前场景及 sequence，启用后可重新请求。
- Guardian 实际模型结果的提案须属于同 Journey、同 trigger_event；不符合时保留拒绝原因和模型运行证据，返回可重试状态，不将旧提案当成本次新方案。
- Simulation API 再核对当前场景及 PRESENTED 状态，只有可接受的当前提案才进入 PAUSED_FOR_ACCEPTANCE。旧记录误绑提案的引用清空并标 UNRESOLVED，以允许重新处理。
- progress.readiness 增加 ai_enabled；关闭时 missing 含 AI_DISABLED。既有 model_credentials_configured 仍只表示凭据配置。

验收：根会话独立 SQLite，42 passed，exit 0，29.13 秒。

```text
python -m pytest tests/test_issue49_guardian_scene_binding.py tests/test_issue49_guardian_context.py tests/test_issue49_presenter_integration.py tests/test_issue47_simulation.py tests/test_issue49_guardian_outcome.py -q --junitxml=scene-binding-verified.xml
```

执行库 C:/Users/仓鼠王/cn51/classroom-20261026-qa/scene-binding-verified.db，JUnit 同目录 scene-binding-verified.xml。测试包含声明的模型替身，无真实外部请求。本次尚未重启课堂服务或完成页面的 Guardian→新提案→接受→resume 联调。其他工人的日期约束及 UI 未提交改动保留。

## 事件选择入口增量

request_replan 对带 server_owned_recovery_context 的恢复子任务，缺省事件使用服务器绑定事件；模型显式指定冲突事件返回 409 RECOVERY_TRIGGER_SCOPE_MISMATCH。普通任务仍使用原事件选择逻辑。补丁由现有 Luna Max 工人交付，根会话独立验证。

工具绑定新测试、既有缓存升级、旧缓存兼容与场景绑定回归：25 passed，exit0，19.94 秒；JUnit 为同 QA 目录 replan-trigger-verified.xml。首次测试发现旧缓存 SimpleNamespace 夹具缺当前序列化必需的四个谱系字段，已补 None，原缓存顺序、状态、幂等和越界断言未改。GitHub focused workflow 已加入这两份缓存回归。此轮无模型/provider 请求，尚不代表现场提案接受完成。

恢复任务的 list_replans 也只读取当前绑定事件；accept_replan 在 policy/审批/native writer 之前拒绝其它事件提案，避免先写错方案后才被 Guardian 结果校验发现。普通任务行为不变。工具绑定与现有 Agent runtime gate 回归 28 passed、exit0、7.36 秒；JUnit replan-write-gates.xml。新测试证明错误提案不会进入 policy，匹配提案继续进入原 gate；不表示测试代替实际接受签名或现场模型运行。
