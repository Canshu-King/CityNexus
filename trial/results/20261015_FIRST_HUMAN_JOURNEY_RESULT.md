用户现在能用：否（PR #20 尚未进入用户当前启动版本）。本轮已用独立 authoritative 后端和真实签名浏览器会话跑通桌面、手机的“连城 → 地点 → 双站保存 → GO → 刷新恢复”；城市和地点来自本机受控 TEST_PROVIDER。真实 Nominatim / Overpass、Hermes 模型请求和真人可用性仍未验证。

# Revolution 首次真人旅程修复结果

**Issue**：[#19 — Revolution 真人首次体验卡死](https://github.com/Canshu-King/CityNexus/issues/19)
**PR**：[Canshu-King/CityNexus#20](https://github.com/Canshu-King/CityNexus/pull/20)
**分支**：`fix/revolution-first-human-e2e-20261015`
**修复提交**：真人旅程修复为 `00471cb38f84b288d62eb60b71398ff74cd4108f`；启动器端口隔离跟进为 `4f27c8b0ed`；本轮签名首体验 E2E 与 TEST_PROVIDER 口径修正为 `2b85183f0a`。
**基线**：`trial/revolution-first-look-20261014 @ ca00e365025932164a166fae9ca5fe8dedec6556`

## 结论与原始红条

原始用户会话里的失败请求和后端原因仍是 **UNKNOWN**。不能据现有证据把它归因到 AI、Nominatim、Overpass、认证或某个 HTTP 状态。

此前一次隔离试跑因漏配本机 TEST_PROVIDER 配置而得到 HTTP 200 / `CITY_NO_RESULTS`；这是测试环境配置问题，不是原始红条证据。补齐仅指向 loopback 的提供方配置后，签名浏览器 E2E 使用本机 geocoder 和 Overpass 夹具走通地点、保存和 GO。503 恢复截图是人为注入的错误，只验证界面如何显示和恢复，不是原始故障证据。

已把万能错误文案改为按操作阶段和 HTTP 状态显示中文原因与一个恢复动作。技术详情只保留脱敏的 method/path/status 和 allowlisted reason code，不显示原始响应、访问令牌、trace 或完整 Journey ID。重复提交相同两站时，后端现在会重新投影当前成员的 GO 进度，避免把正在前往第一站的状态返回成 `NOT_STARTED`。

## 验收分档

| 闸门 | 状态 | 证据或限制 |
| --- | --- | --- |
| COMPILE_PASS | PASS | `npm run typecheck:all`、`npm run build`、Python 3.13 `py_compile` 通过。 |
| UI_FIXTURE_PASS | PASS | UI fixture 2 passed；错误矩阵 10 passed，含 401/403/404/409/422/429/502/503/timeout 和脱敏断言。 |
| SIGNED_BACKEND_PASS | PASS | 新增 authoritative E2E：独立签名会话、真实 `app.main` API、TEST_PROVIDER 地名与地点、保存两站、GO 和刷新恢复；未 mock API 路由。 |
| REAL_PROVIDER_PASS | BLOCKED | 本次没有请求真实 Nominatim / Overpass；本机没有本任务授权的 Nominatim 联系配置。 |
| MODEL_TOOL_PASS | NOT_VERIFIED | AI 保持关闭，没有发起可能计费的 Hermes 请求。 |
| HUMAN_USABILITY_PASS | NOT_VERIFIED | 自动化浏览器跑通；真实用户尚未亲自确认。 |
| FULL_OPERATOR_PASS | NOT_VERIFIED | 没有伪造 ACTIVE PlanVersion、AgentRun、GPS 到场或正式 Operator 结果。 |
| ORIGINAL_RED_BAR_ROOT_CAUSE | UNKNOWN | 原始后端日志为空，缺少失败请求、状态码和故障原因。 |

## 已运行的命令和结果

从仓库根目录运行：

```powershell
py -3.13 -m pytest backend/tests/test_r95_city_jump_and_provenance.py backend/tests/test_r100_pocket_walk.py backend/tests/test_r108_pocket_walk_go_mode.py -q
# 8 passed, 3 warnings

py -3.13 -m py_compile trial/agent_preview_app.py trial/try_revolution.py backend/app/execution/bootstrap_discovery.py
# exit code 0
```

从 `frontend/` 运行，使用 authoritative current-product Playwright 配置和隔离 SQLite：

```powershell
$env:CITYNEXUS_E2E_AUTHORITATIVE = '1'
npm run test:e2e -- --project=chromium e2e/revolution-quick-explore-ui.spec.ts
# 2 passed（real-seed setup + UI fixture）

npm run test:e2e -- --project=chromium e2e/revolution-quick-explore-errors.spec.ts
# 10 passed（real-seed setup + 9 个状态/超时用例）

# authoritative：独立 run ID/SQLite/随机 HMAC 密钥；AI 关闭；Nominatim 与 Overpass URL
# 只指向本机 TEST_PROVIDER 夹具；CITYNEXUS_EVIDENCE_DIR 指向仓库外临时目录。
npm run test:e2e -- --project=chromium e2e/revolution-quick-explore-signed.spec.ts
# 2 passed（real-seed setup + signed browser flow；手机 390×844、桌面 1440×900）

npm run typecheck:all
# passed

npm run build
# passed；Vite 输出既有的大 chunk 提示
```

Signed E2E 视口为精确的 1440×900 和 390×844。后端 Network 只记录脱敏路径与状态：创建 traveler/journey 为 201；两个视口各发一次 city-search API（200）；discovery、Pocket Walk 保存、GO 均为 200；刷新后从服务器恢复 `HEADING_TO_FIRST`；无关签名成员读取私人行程返回 403；地图瓦片请求数为 0。城市和地点来自本机 TEST_PROVIDER 夹具，重复地名查询允许由真实后端缓存返回。AI endpoint 未被调用。

- [Signed TEST_PROVIDER 桌面 1440×900](../../frontend/output/playwright/20261015-first-human-signed-testprovider-desktop.png)
- [Signed TEST_PROVIDER 手机 390×844](../../frontend/output/playwright/20261015-first-human-signed-testprovider-mobile.png)
- [此前 UI fixture 桌面 1440×900](../../frontend/output/playwright/20261015-first-human-desktop.png)
- [此前 UI fixture 手机 390×844](../../frontend/output/playwright/20261015-first-human-mobile.png)
- [注入 503 的恢复提示 390×844（非原始故障）](../../frontend/output/playwright/20261015-first-human-error-mobile.png)

本轮使用已校验的便携 Node 22.22.0；系统 Node 仍为 24.14.0。`npm ci` 曾因现有 lockfile 与 package.json 不一致失败，依赖只在隔离 worktree 用 `npm install --no-save --no-package-lock` 安装，`package-lock.json` 未修改。

## 2026-10-15 启动避让补丁

检查本机时，原试玩仍监听 `127.0.0.1:14173` 和 `127.0.0.1:18201`。没有停止或连接这两个服务。为避免用户更新时撞端口，启动器新增前端、后端及本地 fixture 的独立端口参数，并拒绝重复端口；npm lockfile 不匹配兜底改为 `--no-save --no-package-lock`。

在当前隔离分支用 `--sample --fresh --no-browser`、前端 `14183`、后端 `18211`、城市 fixture `18212`、Overpass fixture `18213` 启动成功。后端健康、`/revolution` 页面和两个本地 fixture 均返回 HTTP 200；随后结束了本次隔离进程。本次只使用 `TEST_PROVIDER` 与新 SQLite，没有联系真实地图服务或模型，也没有触碰原试玩进程和数据库。

## 一次性安全更新并启动

本机现有试玩仍占用默认端口 `14173/18201`。启动器会拒绝接管被占用的端口；下面改用 `14183/18211`，无需停止旧服务。命令只创建新的隔离 worktree，并以 `--fresh` 使用新 SQLite；若目标目录已存在就停止，不触碰原 checkout、原数据库、lockfile 或密钥。命令不带 `--agent`，不会发模型请求；LIVE Provider 只有在用户于页面逐项明确同意后才发请求。启动器要求联系邮箱时只在本机终端输入。

```powershell
$repo = 'D:\moodle\CityNexus-Revolution-Trial'
$trial = 'D:\moodle\CityNexus-Revolution-Trial-first-human-e2e-20261015'
$branch = 'fix/revolution-first-human-e2e-20261015'

if (Test-Path -LiteralPath $trial) {
  throw '目标目录已存在；未修改任何文件。请先检查该目录。'
}

git -C $repo fetch origin
if ($LASTEXITCODE -ne 0) { throw 'git fetch 失败；未启动试玩版。' }

git -C $repo worktree add --detach $trial "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw '创建隔离 worktree 失败；未启动试玩版。' }

Set-Location -LiteralPath $trial
py -3.13 trial\try_revolution.py --fresh --frontend-port 14183 --backend-port 18211
```

启动器的 npm lockfile 不匹配兜底现在使用 `npm install --no-save --no-package-lock`；即使需要安装依赖，也不会改写 `package.json` 或 `package-lock.json`。自动化签名 E2E 不会证明真人已可用，也没有连接真实地图服务或 Hermes。
