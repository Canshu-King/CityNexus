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
