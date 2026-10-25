# Issue #49：Codex 后端联调交付

产品提交：`fafc0fcf538e4daad60e75d1fc2b284ded495376`。
父提交：`07fab22c84201e2ae99f6571900e7b7ae4dc087d`。
工作树：`D:/moodle/_codex_workers/citynexus-sandbox-security-20261025`。
PR #48 / `codex/sandbox-execution-security-20261025`；目标为 Qoder rescue，未直接修改或合并目标分支。

## 已实现

1. 新增签名只读 `GET /api/v1/journeys/{jid}/simulation/runs/{rid}/progress`。按本 run 场景事件关联 Guardian/子 mission/AgentRun/工具/提案/签名接受审计；模型尚未返回时，前端也能读取已提交的工具记录。配置状态独立于执行记录；读取不请求模型。只给出固定状态、允许的工具名称和失败码。
2. 模拟 Guardian 调用明确指定本 run 的 `pending_event_id`。较高严重度的其它事件、旧 EXECUTED Guardian、其它事件的恢复队列不能代替这次场景。事件与 run 不匹配时拒绝且不消耗 sequence。
3. 原生签名接受入口透传 `AUTHENTICATED_TRAVELER`/实际 traveler_id，并补持久虚拟时钟上下文。原路径 `/replans/{id}/accept` 不含 Journey ID，原来的 Journey-path 中间件覆盖不到此入口。原子写入/可行性/集体权限检查保留。
4. 交付无框架依赖 TypeScript 客户端与短接线说明：`docs/revolution/examples/simulation-client.ts`、`docs/revolution/ISSUE49_PRESENTER_QUICKSTART.md`，含配对、恢复、advance、scene、guardian、轮询、原生接受、resume 和 401/403/409/503 处理。

## 实测

共 **92/92 PASS**。均为独立 SQLite 与签名测试身份；本轮没有真实 provider/model 请求。

| 项目 | 结果 |
|---|---|
| 新增 Issue49 聚焦测试 | 17/17 |
| Issue47 私有读取/模拟/真实 socket 代理/配对/城市来源/原生门禁回归 | 63/63 |
| Guardian phase 与 adaptive watch 原有回归 | 8/8 |
| R28 原生执行真相回归 | 4/4 |
| TypeScript 客户端 strict/noEmit | exit 0 |
| 改动模块 Ruff F / diff-check | 通过；main.py 既有 15 条 F 问题与父提交完全一致，无新增 |

具体覆盖：390px UI 不属于本轮；本轮测试同一 run 两天、每天两站，seed 17/409，走原生阶段至 SIMULATED_COMPLETED 后从新 DB session/HTTP 恢复。Guardian 测试使用明确的失败模型替身，验证真实 Guardian 控制代码的时钟、持久 Agent/step 读取、失败后暂停及同 key 重放不重调。信号刷新复用同一注入 Event，provider capture 保持真实时间。签名接受测试验证 401/403、用户身份和虚拟时间传递到原生写者，写者为测试替身，**不构成原生接受成功或现场模型成功证据**。

原始结果：
- `20261025_ISSUE49_INTEGRATION_JUNIT.xml`：80 passed。
- `20261025_ISSUE49_NATIVE_REGRESSION_JUNIT.xml`：12 passed。

复现命令（在此工作树设置 `PYTHONPATH=backend`，使用已存在 backend venv）：

```text
python -m pytest backend/tests/test_issue49_presenter_integration.py backend/tests/test_issue47_private_reads.py backend/tests/test_issue47_simulation.py backend/tests/test_issue47_proxy_pairing.py backend/tests/test_issue47_city_and_native.py -q --tb=short --junitxml=trial/results/20261025_ISSUE49_INTEGRATION_JUNIT.xml
python -m pytest backend/tests/test_guardian_phase_policy.py backend/tests/test_adaptive_watch_policy.py backend/tests/test_r28_execution_truth.py -q --tb=short --junitxml=trial/results/20261025_ISSUE49_NATIVE_REGRESSION_JUNIT.xml
tsc --strict --target ES2022 --lib ES2022,DOM --noEmit --skipLibCheck docs/revolution/examples/simulation-client.ts
```

## 接续点

本地交付对应 #49 的 Codex 后端部分。Qoder 将 PR48 接入 rescue 后，用同一真实 Journey/run 完成 Chrome 两日闭馆/天气 → 真模型/工具 → 签名接受 → 完成 → 刷新/重启彩排。当前没有这一整条现场证据，也没有三城两 seed 的真实来源验收。

本会话进程没有模型配置，未读取私人 Key 或操作 Qoder 现场 DB/端口。接线说明列出了兼容模型所需 URL/Key/model、standing mission、签名角色、隔离 DB 以及三城来源的既有获取/绑定/发布接口。接入者可以从 progress.readiness 直接看到本次运行缺哪项。

GitHub CI 本轮未提供检查结果；以上均为本地实际执行结果。工作树未改 Qoder 的 UI/启动器；本报告不代表 #49 整体关闭或最终设备验收。
