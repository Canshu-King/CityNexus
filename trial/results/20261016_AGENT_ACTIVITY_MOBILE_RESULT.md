VISIBLE_VERIFIED_RUN = PARTIAL
# Mobile Hermes 手机轨迹：中文验收报告

## 本次增量

- 分支：design/revolution-mobile-first-v1
- 产品代码提交：b975bf6150caac0f5c17cc41e6765198261a0125
- Issue #24 接续实现提交：35c211ea7f1f98c8ed75e7a9f024abc104f9fc3c（按同一现有 PR 增量提交）
- PR：[#23](https://github.com/Canshu-King/CityNexus/pull/23)
- Issue #21 最新最新评论与 Issue #24 正文已阅读；按要求复用了已有的共享 Hermes 时间线 hook，没有重写 AgentWorkStatus 或另建事件模型。
- ACTIVE Journey 的行程助手收到服务端返回的 HERMES_NATIVE_MCP Run ID 后，会自动打开手机轨迹抽屉。用户可关闭后再从折叠状态条重新打开。
- 抽屉显示服务器事件、中文工具名称、时间和服务端提供的耗时；事件仍由签名 SSE 与历史接口提供，并按共享 hook 的事件 ID/sequence 去重、排序和恢复。
- 判断依据只读取本次响应中与 mission_id 一起绑定的 reasoning_summary；没有摘要就显示“暂无可公开判断说明”。不会展示模型私有思维链、工具参数或原始返回。
- “停止本次运行”调用现有签名 CityNexus 停止接口；收到停止请求的 HTTP 成功后，界面仍等待服务器终态事件，不会先把任务标为已停止。
- 待审批轨迹只提示用户去行程恢复中心核对并授权；本抽屉不提供绕过现有授权流程的按钮。

### Issue #21 后续增量：刷新后恢复同一条 Hermes 运行

- 新增只读签名接口 `GET /api/v1/journeys/{journey_id}/agent/hermes/latest-run`。它从 `agent.native_hermes.run_bound` 审计记录中按当前已签名 traveler 和精确 JourneyMember 绑定选择 Run，再校验 Mission 仍属于当前 Journey；不接受浏览器本地存储的 run id，不启动 Hermes 或模型。
- 手机“行程”页可在切回页面或刷新后恢复当前成员最近一条 Run，复用已有 `useNativeHermesTimeline` 拉取服务器历史并以 bearer 鉴权连接事件流。恢复过程不重复 POST Copilot；切换签名成员时仍清掉旧人的运行详情。
- 共享事件 hook 补上 CRLF SSE 帧解析、跨连接关闭的有限重试，以及服务器 `run.completed / run.failed / run.stopped` 终态到手机状态的同步；收到完成事件后停止按钮随即隐藏。没有复制 AgentWorkStatus 或新建第二套事件模型。

## 验收证据

- TypeScript：在 frontend 运行 npm.cmd run typecheck:all，退出码 0。
- Vite：在 frontend 运行 npm.cmd run build，退出码 0；仍有既有的大 bundle 提示（最大压缩前 chunk 约 1.88 MB）。
- Chromium UI：`playwright.mobile-trial.config.ts` 指定 ACTIVE mobile Hermes 用例最终复跑 1 passed，视口 390×844。`TEST_FIXTURE` API/SSE 覆盖 CRLF 事件、运行状态/判断依据/工具轨迹、打开/关闭抽屉、刷新后恢复同一 Run、不重复 POST Copilot、完成后隐藏停止按钮和不显示原始工具名。首轮补跑暴露终态 UI 状态未同步，修复后以上一条最终复跑为验收结果；失败首轮不计入通过。
- 后端签名隔离：`backend/tests/test_mobile_hermes_run_binding.py`，TestClient 1 passed，使用项目独立临时 SQLite。当前成员的 latest-run 可读为 200；无签名为 401；未加入的外部用户为 403；另一名 Journey 成员只能恢复其自己的 Run，读取原成员私有 Run 仍为 404。此验证覆盖本地真实后端代码和鉴权，不证明发生了真实 Hermes 上游调用。
- git diff --check 通过。
- 手机尺寸截图：assets/20261016-mobile-hermes-run-TEST-FIXTURE-390x844.png
- 截图 SHA-256：98F967DDE220A09D883CE5C4B71F72F65926A965456669295042E671451A767F
- 刷新恢复后的 Chromium 390×844 截图：assets/20261016-mobile-hermes-resume-verified-TEST-FIXTURE-390x844.png
- 新截图 SHA-256：0F1AAAFE998E0F4D3FCD07BA0E1389637F5AE6B01EDA3EDEE3163D6E555D79CA。该图是浏览器 `TEST_FIXTURE` 画面，不是实体手机或真实 Hermes 运行截图。

## 证据等级与未完成项

当前结论仍为 PARTIAL。TypeScript 检查和 Vite 构建通过；构建保留既有大 bundle 提示（最大压缩前 chunk 约 1.88 MB）。Chromium 截图和浏览器轨迹都是 `TEST_FIXTURE`；签名成员隔离由真实后端代码的 TestClient 测试验证，但该测试没有调用真实 Hermes 上游。当前没有可安全连接的签名运行实例，本轮未发起真实模型/工具调用；没有读取或输出 API Key。

尚未取得真实 LIVE_PROVIDER / Hermes 工具调用记录、实体手机验收、430×932 设备验收或双签名用户浏览器 E2E 证据。报告中的截图不是实体手机截图，也不能证明真实 AI 工具调用成功。要把状态升为 YES，需要在受控隔离服务上完成一次真实签名用户 Run，并保留两名成员隔离和手机现场证据。

## 可追溯文件

- frontend/src/trial/mobile/MobileHermesRun.tsx
- frontend/src/trial/mobile/MobileHermesRun.css
- frontend/src/features/agent/nativeHermesTimeline.ts
- backend/app/main.py
- backend/tests/test_mobile_hermes_run_binding.py
- frontend/e2e/revolution-mobile-shell.spec.ts

## 2026-10-16 手机界面增量：状态与证据标识

- 继续复用 `MobileHermesRun` 和共享 `useNativeHermesTimeline`，没有重做 AgentWorkStatus、没有另建运行或事件模型。
- ACTIVE 行程尚无服务器运行时，页面明确显示“当前没有正在执行的 Hermes 任务”；并说明“Hermes 工具已就绪”不代表任务已经开始。恢复失败和未登录仍走各自错误提示，不伪装成空运行。
- 为服务端返回的 `semantic.interpreted`、`mission.planned` 增加中文事件名称；工具事件耗时改成“850 毫秒”或“1.2 秒”格式。
- 运行记录带有 `TEST_*` / `FIXTURE_*` provider 标记时，抽屉明确显示 `TEST_FIXTURE · 仅用于界面验收`，并说明夹具不能证明真实 Hermes 已运行；折叠状态也标成测试夹具事件。正常运行标为“签名服务器运行记录”。
- 新增手机抽屉截图：`assets/20261016-mobile-hermes-trace-truthful-TEST-FIXTURE-390x844.png`；SHA-256：`E08C9710820065D32F5D05577FDC0DD508D165A71F4BB678E18747B9225AC50E`。这是 390×844 Chromium TEST_FIXTURE 画面，不是实体手机或真实模型运行截图。
- 本次增量验证：`npm.cmd run typecheck:all` 通过；`npm.cmd run build` 通过，已有的大 bundle 提示未变；聚焦 Playwright Hermes 手机用例 1 passed；后端签名 Run 绑定测试 1 passed，使用隔离临时 SQLite。以上证据不构成 LIVE_PROVIDER 或真实 Hermes 工具调用证明。
- 没有可安全使用的真实 Hermes 签名运行配置，本次未发起上游 AI/工具调用；真实签名 Run、两名用户隔离的手机浏览器验收及实体设备验收仍待完成。

因此状态继续保持 `VISIBLE_VERIFIED_RUN = PARTIAL`。需要在受控隔离服务上由签名用户真正启动 Hermes Run，并验证服务器事件和成员隔离后，才能升级真实运行验收结论。
