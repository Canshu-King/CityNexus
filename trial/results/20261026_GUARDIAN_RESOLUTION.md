# 已接受终态与失败恢复（PR55 后端增量）

基线 `a041b3a5b9eebab0b916a007150316e3bbe07e11`。本刀修复两处实际课堂阻塞：已接受的本事件方案被 PARTIAL Agent 覆盖成“未解决”，以及失败尝试仍占据运行中状态、恢复需等待整段租约。

- `progress.guardian_outcome.code` 新增 `PROPOSAL_ACCEPTED`。当前 run 的场景事件为 RESOLVED、Guardian 指向原生 ACCEPTED proposal、proposal.source_agent_run_id 与该 Guardian 的 AgentRun 精确匹配时返回；PARTIAL 与早先失败 step 保留原始状态。错误事件、旧 Guardian 引用、其他来源 Agent 不能获得这项终态。Agent 自身仍为 FAILED_EXTERNAL 时保留失败。
- 课堂模拟的模型尝试失败后不再静默切到另一个 runtime；返回 PAUSED_MODEL_UNAVAILABLE，由用户显式重试。正常结束清理本次 lease。
- 既有签名 POST `/simulation/runs/{id}/recover` 可对当前尝试已经持久化的终态失败提前恢复，无需等待 30 分钟租约。其他事件、之前尝试、尚在 RUNNING 的 Agent 不适用；序号与幂等保持，原提交的旧运行中回执也随恢复归并，避免重复请求返回过期转圈状态。
- GET progress 始终只读，不启动模型、provider 或恢复写入。新增 `recovery.available`，供界面显示恢复动作；其可用性只读当前失败记录。

Qoder 可增量消费，旧字段保持：

```ts
type GuardianOutcome = { code: string; error_code?: string };
type Recovery = {
  available: boolean;
  reason_code: "MODEL_REQUEST_FAILED" | null;
  requires_signed_post: true;
  operation: "recover";
};
// guardian_outcome: {code: "PROPOSAL_ACCEPTED"} -> 本次建议已接受
// recovery.available -> 本人确认后 POST recover，携带当前 expected_sequence 和新幂等键
// 读取或刷新 progress 不会启动重试；恢复完成后再由用户明确请求 guardian。
// steps 增加 simulation_run_id/event_id/stage/duration_ms/failure_classification。
// 工具名为白名单，失败分类为稳定码；没有 prompt/参数/原始返回/key。
```

根在独立 SQLite 上串行运行：

```powershell
$env:PYTHONPATH='.'
$env:DATABASE_URL='sqlite:///:memory:'
& 'D:/moodle/CityNexus/backend/.venv/Scripts/python.exe' -m pytest tests/test_issue49_guardian_accepted_outcome.py tests/test_issue49_guardian_failure_settlement.py tests/test_issue49_guardian_outcome.py tests/test_issue49_guardian_scene_binding.py -q -o junit_family=xunit1 --junitxml='C:/Users/仓鼠王/cn51/classroom-20261026-qa/guardian-resolution-verified.xml'
```

结果 **26 passed / 4 warnings / exit0**。第一次新测试缺少共享 stack fixture 导入；补齐后发现关闭 session 后读取过期 ORM ID 的测试错误，改为关闭前保存标量 ID；最终无修改业务断言通过。HTTP 回归包含声明式模型替身返回 503、同 run 落库失败终态、原请求重放不重复调用、用户显式重试、匿名拒绝，以及当前失败提前恢复/旧事件旧尝试拒绝。它不代表真实外部网关 503 重测。

本次只提交后端与回归，未改 Qoder 界面/启动器或用户数据库；真实模型/签名接受链仍沿用此前 29dafc 的现场回执。新终态投影将对同一真实已接受链做只读复核，另附实际结果；前端是否显示新枚举由 Qoder 集成后验收。四站和城市几何供给继续单独推进，不能由本刀测试数替代。
