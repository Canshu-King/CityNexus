VISIBLE_VERIFIED_RUN = PARTIAL
# Mobile Hermes 手机轨迹：中文验收报告

## 本次增量

- 分支：design/revolution-mobile-first-v1
- 产品代码提交：b975bf6150caac0f5c17cc41e6765198261a0125
- PR：[#23](https://github.com/Canshu-King/CityNexus/pull/23)
- Issue #21 最新最新评论与 Issue #24 正文已阅读；按要求复用了已有的共享 Hermes 时间线 hook，没有重写 AgentWorkStatus 或另建事件模型。
- ACTIVE Journey 的行程助手收到服务端返回的 HERMES_NATIVE_MCP Run ID 后，会自动打开手机轨迹抽屉。用户可关闭后再从折叠状态条重新打开。
- 抽屉显示服务器事件、中文工具名称、时间和服务端提供的耗时；事件仍由签名 SSE 与历史接口提供，并按共享 hook 的事件 ID/sequence 去重、排序和恢复。
- 判断依据只读取本次响应中与 mission_id 一起绑定的 reasoning_summary；没有摘要就显示“暂无可公开判断说明”。不会展示模型私有思维链、工具参数或原始返回。
- “停止本次运行”调用现有签名 CityNexus 停止接口；收到停止请求的 HTTP 成功后，界面仍等待服务器终态事件，不会先把任务标为已停止。
- 待审批轨迹只提示用户去行程恢复中心核对并授权；本抽屉不提供绕过现有授权流程的按钮。

## 验收证据

- TypeScript：在 frontend 运行 npm.cmd run typecheck:all，退出码 0。
- Vite：在 frontend 运行 npm.cmd run build，退出码 0；仍有既有的大 bundle 提示（最大压缩前 chunk 约 1.88 MB）。
- Chromium UI：playwright.mobile-trial.config.ts 下指定 ACTIVE mobile Hermes 用例，1 passed。视口 390×844；API 与 SSE 使用 TEST_FIXTURE 路由，覆盖状态、判断依据、工具轨迹、打开/关闭抽屉和禁止显示原始工具名。
- 后端签名隔离：backend/tests/test_mobile_hermes_run_binding.py，TestClient 1 passed，使用独立 TEMP SQLite。本人 Run 可读为 200；无签名为 401；外部用户为 403；同 Journey 的另一成员读取该私有 Run 为 404。上游 Hermes 状态客户端是测试替身，因此这证明后端鉴权逻辑，不证明发生了真实 Hermes 调用。
- git diff --check 通过。
- 手机尺寸截图：assets/20261016-mobile-hermes-run-TEST-FIXTURE-390x844.png
- 截图 SHA-256：98F967DDE220A09D883CE5C4B71F72F65926A965456669295042E671451A767F

## 证据等级与未完成项

当前结论是 PARTIAL。Chromium 截图和浏览器轨迹都是 TEST_FIXTURE；签名成员隔离由真实后端代码的 TestClient 测试验证，但该测试没有调用真实 Hermes 上游。检查时本机 8000、8001、5173、14273 端口没有 CityNexus 服务监听，所以这轮没有能安全连接的真实运行实例；没有读取或输出 API Key。

尚未取得真实 LIVE_PROVIDER / Hermes 工具调用记录、实体手机验收、430×932 设备验收或双签名用户浏览器 E2E 证据。报告中的截图不是实体手机截图，也不能证明真实 AI 工具调用成功。要把状态升为 YES，需要在受控隔离服务上完成一次真实签名用户 Run，并保留两名成员隔离和手机现场证据。

## 可追溯文件

- frontend/src/trial/mobile/MobileHermesRun.tsx
- frontend/src/trial/mobile/MobileHermesRun.css
- frontend/src/features/agent/nativeHermesTimeline.ts
- backend/app/main.py
- backend/tests/test_mobile_hermes_run_binding.py
- frontend/e2e/revolution-mobile-shell.spec.ts
