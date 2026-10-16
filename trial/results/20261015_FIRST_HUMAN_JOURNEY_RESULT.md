当前状态：PR #20 尚未合并；`14173/18201` 试玩仍运行旧代码。本轮修复 `bootstrap-discovery` HTTP 500。原红条截图未记录 request ID。

# Revolution 首次真人旅程修复结果

**Issue**：[#19 — Revolution 真人首次体验卡死](https://github.com/Canshu-King/CityNexus/issues/19)
**PR**：[Canshu-King/CityNexus#20](https://github.com/Canshu-King/CityNexus/pull/20)
**分支**：`fix/revolution-first-human-e2e-20261015`
**修复提交**：真人旅程修复为 `00471cb38f84b288d62eb60b71398ff74cd4108f`；启动器端口隔离跟进为 `4f27c8b0ed`；本轮签名首体验 E2E 与 TEST_PROVIDER 口径修正为 `2b85183f0a`。
**基线**：`trial/revolution-first-look-20261014 @ ca00e365025932164a166fae9ca5fe8dedec6556`

## 结论与原始红条

试玩后端日志记录到一条失败链：用户提交附近地点搜索后，`POST /api/v1/journeys/:id/bootstrap-discovery` 返回 HTTP 500。Overpass 返回 HTTP 504；业务响应应为 `PROVIDER_UNAVAILABLE`，但持久化代码写入 `UNAVAILABLE`，违反 SQLite CHECK 约束（仅允许 `SUCCESS`、`FAILURE`、`TIMEOUT`、`DEGRADED`），最终导致 500。原截图未记录 request ID。

修复将审计状态映射为 `UNAVAILABLE → FAILURE`、`DISABLED → DEGRADED`，业务层保留 `PROVIDER_UNAVAILABLE`。地点搜索失败时可手动继续探索。日志还记录数次试玩 AI 路由 HTTP 404；现在可跳过 AI 并继续探索。

此前一次隔离试跑因漏配本机 TEST_PROVIDER 配置而得到 HTTP 200 / `CITY_NO_RESULTS`；补齐仅指向 loopback 的提供方配置后，签名浏览器 E2E 使用本机 geocoder 和 Overpass 夹具走通地点、保存和 GO。503 恢复截图展示的是模拟故障流程。

错误提示现在按操作阶段和 HTTP 状态显示原因与恢复动作。错误详情显示脱敏 method/path/status 和原因码。重复提交相同两站时，后端会返回当前成员的 GO 进度。

## 验收分档

| 闸门 | 状态 | 证据或限制 |
| --- | --- | --- |
| COMPILE_PASS | PASS | 本轮 `npm run typecheck:all`、独立输出目录的 Vite build、Python 3.13 `py_compile` 均通过。 |
| UI_FIXTURE_PASS | PASS | 本轮 Node 22.22.2 authoritative Playwright 共 13 项通过：连续中文 fixture 流程、AI 401/404 可手动跳过、Overpass 504 恢复，以及 9 项 HTTP/超时错误矩阵。 |
| SIGNED_BACKEND_PASS | PASS | 既有 authoritative 签名浏览器流程通过；本轮 `test_r88_real_poi_exploration.py` 的两个后端用例通过，新增 504 回归验证 HTTP 200 + `PROVIDER_UNAVAILABLE` + 审计状态 `FAILURE`。 |
| REAL_PROVIDER_PASS | BLOCKED | Overpass 返回 HTTP 504；Nominatim / Overpass 成功响应待验。 |
| MODEL_TOOL_PASS | PENDING | AI 关闭，未发起 Hermes 请求。 |
| HUMAN_USABILITY_PASS | PENDING | 自动化浏览器通过；真人验收待做。 |
| FULL_OPERATOR_PASS | PENDING | ACTIVE PlanVersion、AgentRun、GPS 到场和 Operator 流程待验。 |
| ORIGINAL_RED_BAR_ROOT_CAUSE | PARTIAL | 已确认地点查询 500 根因；原截图无 request ID。 |

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

本轮 UI 回归使用 Node 22.22.2、独立 backend（`:18221`）、frontend（`:4181`）、临时 SQLite 和仓库外证据目录；AI 关闭，provider/AI 请求由 Playwright fixture 接管。

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

检查时，原试玩监听 `127.0.0.1:14173` 和 `127.0.0.1:18201`。启动器新增前端、后端及本地 fixture 独立端口参数，并拒绝重复端口；lockfile 不匹配时使用 `--no-save --no-package-lock`。

隔离分支以 `--sample --fresh --no-browser` 启动：前端 `14183`、后端 `18211`、城市 fixture `18212`、Overpass fixture `18213`。健康检查、`/revolution` 和两个 fixture 均返回 HTTP 200，之后结束隔离进程。数据源为 `TEST_PROVIDER`，数据库为新 SQLite。

## 一次性安全更新并启动

原试玩占用默认端口 `14173/18201`。新分支使用 `14183/18211` 启动独立实例，访问 `http://127.0.0.1:14183/revolution`。命令创建隔离 worktree 并以 `--fresh` 使用新 SQLite；不带 `--agent`。启用 LIVE Provider 时，页面会逐项请求用户授权。启动器要求联系邮箱时，在本机终端输入。

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

启动器使用 `npm install --no-save --no-package-lock` 处理 lockfile 不匹配。签名 E2E 使用 `TEST_PROVIDER`；真实地图服务、Hermes 和真人手机尚未验收。
