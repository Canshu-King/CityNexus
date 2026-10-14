用户现在能用：否（PR #20 尚未合并，当前 14173/18201 试玩仍运行旧代码）。本轮已确认并修复一个真实 `bootstrap-discovery` HTTP 500 根因；原红条截图与具体请求之间仍缺 request ID，不能断言它就是这条 500。用户无需碰旧数据库；如要先试修复分支，文末的隔离启动命令会用新端口和新 SQLite。

# Revolution 首次真人旅程修复结果

**Issue**：[#19 — Revolution 真人首次体验卡死](https://github.com/Canshu-King/CityNexus/issues/19)
**PR**：[Canshu-King/CityNexus#20](https://github.com/Canshu-King/CityNexus/pull/20)
**分支**：`fix/revolution-first-human-e2e-20261015`
**修复提交**：真人旅程修复为 `00471cb38f84b288d62eb60b71398ff74cd4108f`；启动器端口隔离跟进为 `4f27c8b0ed`；本轮签名首体验 E2E 与 TEST_PROVIDER 口径修正为 `2b85183f0a`。
**基线**：`trial/revolution-first-look-20261014 @ ca00e365025932164a166fae9ca5fe8dedec6556`

## 结论与原始红条

原红条截图没有 request ID，无法和单条请求一一关联；但试玩后端日志里确实捕获到一次可复现的失败链：用户提交附近地点搜索后，`POST /api/v1/journeys/:id/bootstrap-discovery` 返回 HTTP 500。该请求收到 Overpass HTTP 504，业务响应本应为 `PROVIDER_UNAVAILABLE`；持久化代码却把 `UNAVAILABLE` 写进 `provider_calls.status`，而实际 SQLite CHECK 只允许 `SUCCESS`、`FAILURE`、`TIMEOUT`、`DEGRADED`，因此提交时抛出 `CHECK constraint failed: status`，把上游超时放大成后端 500。

本次修复将审计状态映射为 `UNAVAILABLE → FAILURE`、`DISABLED → DEGRADED`，保留业务层的 `PROVIDER_UNAVAILABLE`，并让 UI 清楚说明“服务没有回答、地点情况未确认”，只在用户点击时重试，不误报成零结果。日志另有数次 `POST /api/v1/journeys/:id/trial-ai-discovery` HTTP 404，是旧后端未加载试玩 AI 路由的独立问题；AI 404 现在可原行程跳过并继续手动探索。因为没有关联 ID，不能证明哪条请求产生了截图中的那一条红条。

此前一次隔离试跑因漏配本机 TEST_PROVIDER 配置而得到 HTTP 200 / `CITY_NO_RESULTS`；这是测试环境配置问题，不是原始红条证据。补齐仅指向 loopback 的提供方配置后，签名浏览器 E2E 使用本机 geocoder 和 Overpass 夹具走通地点、保存和 GO。503 恢复截图是人为注入的错误，只验证界面如何显示和恢复，不是原始故障证据。

已把万能错误文案改为按操作阶段和 HTTP 状态显示中文原因与一个恢复动作。技术详情只保留脱敏的 method/path/status 和 allowlisted reason code，不显示原始响应、访问令牌、trace 或完整 Journey ID。重复提交相同两站时，后端现在会重新投影当前成员的 GO 进度，避免把正在前往第一站的状态返回成 `NOT_STARTED`。

## 验收分档

| 闸门 | 状态 | 证据或限制 |
| --- | --- | --- |
| COMPILE_PASS | PASS | 本轮 `npm run typecheck:all`、独立输出目录的 Vite build、Python 3.13 `py_compile` 均通过。 |
| UI_FIXTURE_PASS | PASS | 本轮 Node 22.22.2 authoritative Playwright 共 13 项通过：连续中文 fixture 流程、AI 401/404 可手动跳过、Overpass 504 恢复，以及 9 项 HTTP/超时错误矩阵。 |
| SIGNED_BACKEND_PASS | PASS | 既有 authoritative 签名浏览器流程通过；本轮 `test_r88_real_poi_exploration.py` 的两个后端用例通过，新增 504 回归验证 HTTP 200 + `PROVIDER_UNAVAILABLE` + 审计状态 `FAILURE`。 |
| REAL_PROVIDER_PASS | BLOCKED | 已观察到一次真实 Overpass HTTP 504；本轮不重复请求，真实 Nominatim / Overpass 当前仍未得到成功结果。 |
| MODEL_TOOL_PASS | NOT_VERIFIED | AI 保持关闭，没有发起可能计费的 Hermes 请求。 |
| HUMAN_USABILITY_PASS | NOT_VERIFIED | 自动化浏览器跑通；真实用户尚未亲自确认。 |
| FULL_OPERATOR_PASS | NOT_VERIFIED | 没有伪造 ACTIVE PlanVersion、AgentRun、GPS 到场或正式 Operator 结果。 |
| ORIGINAL_RED_BAR_ROOT_CAUSE | PARTIAL | 已确认一条真实地点查询 500 的根因；原截图与该请求的精确关联仍 UNKNOWN（日志无 request ID）。 |

## 已运行的命令和结果

从仓库根目录运行：

```powershell
py -3.13 -m pytest backend/tests/test_r95_city_jump_and_provenance.py backend/tests/test_r100_pocket_walk.py backend/tests/test_r108_pocket_walk_go_mode.py -q
# 8 passed, 3 warnings

py -3.13 -m py_compile trial/agent_preview_app.py trial/try_revolution.py backend/app/execution/bootstrap_discovery.py
# exit code 0
```

本轮针对新增修复执行：

```powershell
# 从 backend/ 运行；测试使用 conftest 创建的临时 SQLite，未连接原试玩数据库。
py -3.13 -m pytest tests/test_r88_real_poi_exploration.py -q
# 2 passed, 3 warnings

py -3.13 -m py_compile app/db/models.py app/execution/bootstrap_discovery.py tests/test_r88_real_poi_exploration.py
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

本轮最终 UI 回归在 Node 22.22.2 authoritative 模式下启动独立 backend（`:18221`）、frontend（`:4181`）、临时 SQLite 和仓库外证据目录；AI 关闭，UI 文件中的 provider/AI 请求均由 Playwright fixture 截获，没有访问真实地图/模型服务：

```powershell
$nodeDir = 'C:\Users\仓鼠王\.workbuddy\binaries\node\versions\22.22.2-3'
$env:PATH = "$nodeDir;$env:PATH"
$env:CITYNEXUS_E2E_AUTHORITATIVE = '1'
$env:CITYNEXUS_E2E_PORT = '4181'
$env:CITYNEXUS_BACKEND_PORT = '18221'
$env:CITYNEXUS_PYTHON = 'C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe'
$env:CITYNEXUS_DATABASE_URL = 'sqlite:///./_firsthuman_ui_firsthuman20261015e.db'
$env:CITYNEXUS_E2E_RUN_ID = 'firsthuman20261015e'
$env:CITYNEXUS_AI_ENABLED = 'false'
$env:CITYNEXUS_EVIDENCE_DIR = 'D:\moodle\_codex_workers\first-human-evidence-20261015e'
npx playwright test --config=playwright.config.ts --project=chromium --no-deps e2e/revolution-quick-explore-ui.spec.ts e2e/revolution-quick-explore-errors.spec.ts --output 'D:\moodle\_codex_workers\first-human-playwright-results-20261015e' --reporter=line
# 13 passed

npm run typecheck:all
# passed

npm run build -- --outDir 'D:\moodle\_codex_workers\first-human-build-node22-final-20261015'
# passed；Vite 提示主 bundle 超过 500 KB
```

Signed E2E 视口为精确的 1440×900 和 390×844。后端 Network 只记录脱敏路径与状态：创建 traveler/journey 为 201；两个视口各发一次 city-search API（200）；discovery、Pocket Walk 保存、GO 均为 200；刷新后从服务器恢复 `HEADING_TO_FIRST`；无关签名成员读取私人行程返回 403；地图瓦片请求数为 0。城市和地点来自本机 TEST_PROVIDER 夹具，重复地名查询允许由真实后端缓存返回。AI endpoint 未被调用。

- [Signed TEST_PROVIDER 桌面 1440×900](../../frontend/output/playwright/20261015-first-human-signed-testprovider-desktop.png)
- [Signed TEST_PROVIDER 手机 390×844](../../frontend/output/playwright/20261015-first-human-signed-testprovider-mobile.png)
- [此前 UI fixture 桌面 1440×900](../../frontend/output/playwright/20261015-first-human-desktop.png)
- [此前 UI fixture 手机 390×844](../../frontend/output/playwright/20261015-first-human-mobile.png)
- [注入 503 的恢复提示 390×844（非原始故障）](../../frontend/output/playwright/20261015-first-human-error-mobile.png)

本轮最终 UI/typecheck/build 使用本机便携 Node 22.22.2；系统 Node 仍为 24.14.0。`npm ci` 曾因现有 lockfile 与 package.json 不一致失败，依赖只在隔离 worktree 用 `npm install --no-save --no-package-lock` 安装，`package-lock.json` 未修改。

## 2026-10-15 启动避让补丁

检查本机时，原试玩仍监听 `127.0.0.1:14173` 和 `127.0.0.1:18201`。没有停止或连接这两个服务。为避免用户更新时撞端口，启动器新增前端、后端及本地 fixture 的独立端口参数，并拒绝重复端口；npm lockfile 不匹配兜底改为 `--no-save --no-package-lock`。

在当前隔离分支用 `--sample --fresh --no-browser`、前端 `14183`、后端 `18211`、城市 fixture `18212`、Overpass fixture `18213` 启动成功。后端健康、`/revolution` 页面和两个本地 fixture 均返回 HTTP 200；随后结束了本次隔离进程。本次只使用 `TEST_PROVIDER` 与新 SQLite，没有联系真实地图服务或模型，也没有触碰原试玩进程和数据库。

## 一次性安全更新并启动

本机现有试玩仍占用默认端口 `14173/18201`。要让原地址 `http://127.0.0.1:14173/revolution` 加载新代码，必须先停止旧 Uvicorn/启动器，再从新分支重启；下面的推荐命令改用 `14183/18211` 开独立实例，因此不需要停止旧服务，只需访问新地址。命令只创建新的隔离 worktree，并以 `--fresh` 使用新 SQLite；若目标目录已存在就停止，不触碰原 checkout、原数据库、lockfile 或密钥。命令不带 `--agent`，不会发模型请求；LIVE Provider 只有在用户于页面逐项明确同意后才发请求。启动器要求联系邮箱时只在本机终端输入。

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
