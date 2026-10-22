# Mobile Hermes 手机轨迹：中文验收报告

## 本次增量

- 分支：design/revolution-mobile-first-v1
- 产品代码提交：b975bf6150caac0f5c17cc41e6765198261a0125
- Issue #24 接续实现提交：35c211ea7f1f98c8ed75e7a9f024abc104f9fc3c（按同一现有 PR 增量提交）
- PR：[#23](https://github.com/Canshu-King/CityNexus/pull/23)
- Issue #21 最新最新评论与 Issue #24 正文已阅读；手机轨迹沿用共享 Hermes 时间线 hook。
- ACTIVE Journey 的行程助手收到服务端返回的 HERMES_NATIVE_MCP Run ID 后，会自动打开手机轨迹抽屉。用户可关闭后再从折叠状态条重新打开。
- 抽屉显示服务器事件、中文工具名称、时间和服务端提供的耗时；事件仍由签名 SSE 与历史接口提供，并按共享 hook 的事件 ID/sequence 去重、排序和恢复。
- ACTIVE 行程没有运行记录时显示当前状态；登录与读取失败分别提示。
- 工具事件名称和耗时已中文化；测试运行标记为“测试数据”。
- 判断依据取自当前任务的服务器摘要。
- 停止按钮调用签名接口；运行状态随服务器终态事件更新。
- 待审批事项引导用户前往行程恢复中心。
- 全项目文案复查：AI、地点、同行分享、路线估算、失败恢复和操作指南已整理为简短状态与下一步。

### Issue #21 后续增量：刷新后恢复同一条 Hermes 运行

- 新增只读签名接口 `GET /api/v1/journeys/{journey_id}/agent/hermes/latest-run`，按当前签名成员读取绑定的最近一条 Run。
- 手机“行程”页支持切回页面或刷新后恢复运行记录，并通过共享 hook 读取历史和连接事件流；切换签名成员时清除上一成员的详情。
- 共享事件 hook 解析 CRLF SSE、处理连接中断，并同步 `run.completed / run.failed / run.stopped` 状态。

## 验收证据

- TypeScript：在 frontend 运行 npm.cmd run typecheck:all，退出码 0。
- Vite：在 frontend 运行 npm.cmd run build，退出码 0；主 JS 1,809.25 kB（gzip 542.63 kB），仍有 chunk 体积提示。
- Chromium UI：`playwright.mobile-trial.config.ts` 的 7 项手机用例通过，视口 390×844。覆盖页面导航、地点卡片、地图触摸和 Hermes 轨迹恢复。
- 后端签名隔离：`backend/tests/test_mobile_hermes_run_binding.py`，TestClient 1 passed，使用独立临时 SQLite；当前成员 200、无签名 401、非成员 403、另一成员读取私有 Run 404；Hermes 上游调用数 0。
- git diff --check 通过。
- Hermes 运行轨迹 390×844：`assets/20261016-mobile-hermes-run-TEST-FIXTURE-390x844.png`，SHA-256 `3AF68678F17466149DB342328CEBC2F73B8E34D657D83370F9179AFACF8F02C1`。
- 刷新恢复轨迹 390×844：`assets/20261016-mobile-hermes-resume-TEST-FIXTURE-390x844.png`，SHA-256 `F197F0E588A27B7BB25F6B35D941B856CBFBEB9093DA3A6E8F6B58EFB933ABFB`。

## 当前结果

TypeScript、Vite、7 项 Chromium 手机 fixture 与后端成员隔离测试通过；手机轨迹使用 `TEST_FIXTURE`。主 JS 为 1,809.25 kB（gzip 542.63 kB）。

待验：签名 Hermes 工具调用、实体手机与双成员流程。

## 可追溯文件

- frontend/src/trial/mobile/MobileHermesRun.tsx
- frontend/src/trial/mobile/MobileHermesRun.css
- frontend/src/features/agent/nativeHermesTimeline.ts
- backend/app/main.py
- backend/tests/test_mobile_hermes_run_binding.py
- frontend/e2e/revolution-mobile-shell.spec.ts
