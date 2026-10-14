用户现在能用：否。修复已推送到分支并开 PR，但尚未进入用户当前启动版本；真实 Provider、真实模型工具和真实用户操作仍未验。明早需要先停掉旧 Uvicorn，再运行下方一次性 PowerShell 命令。

# Revolution 首次真人旅程修复结果

**Issue**：[#19 — Revolution 真人首次体验卡死](https://github.com/Canshu-King/CityNexus/issues/19)
**PR**：[Canshu-King/CityNexus#20](https://github.com/Canshu-King/CityNexus/pull/20)
**分支**：`fix/revolution-first-human-e2e-20261015`
**修复提交**：`315a71b3f48440722cd2f883d6e0e44376f16683`
**基线**：`trial/revolution-first-look-20261014 @ ca00e365025932164a166fae9ca5fe8dedec6556`

## 结论与原始红条

原始用户会话里的失败请求和后端原因仍是 **UNKNOWN**。不能据现有证据把它归因到 AI、Nominatim、Overpass、认证或某个 HTTP 状态。

本次独立签名会话中，“连城”请求实际返回 HTTP 200 / `CITY_NO_RESULTS`，没有出现用户所述红条。随后用受控样例地点走通了保存和 GO。503 恢复截图是人为注入的错误，只验证界面如何显示和恢复，不是原始故障证据。

已把万能错误文案改为按操作阶段和 HTTP 状态显示中文原因与一个恢复动作。技术详情只保留脱敏的 method/path/status 和 allowlisted reason code，不显示原始响应、访问令牌、trace 或完整 Journey ID。重复提交相同两站时，后端现在会重新投影当前成员的 GO 进度，避免把正在前往第一站的状态返回成 `NOT_STARTED`。

## 验收分档

| 闸门 | 状态 | 证据或限制 |
| --- | --- | --- |
| COMPILE_PASS | PASS | `npm run typecheck:all`、`npm run build`、Python 3.13 `py_compile` 通过。 |
| UI_FIXTURE_PASS | PASS | UI fixture 2 passed；错误矩阵 10 passed，含 401/403/404/409/422/429/502/503/timeout 和脱敏断言。 |
| SIGNED_BACKEND_PASS | PASS | 独立测试数据库和真实签名会话；真实后端完成创建、搜索、发现、双站保存、GO、刷新恢复。Provider 是 TEST_PROVIDER。 |
| REAL_PROVIDER_PASS | BLOCKED | 本次没有请求真实 Nominatim / Overpass；本机没有本任务授权的 Nominatim 联系配置。 |
| MODEL_TOOL_PASS | NOT_VERIFIED | AI 保持关闭，没有发起可能计费的 Hermes 请求。 |
| HUMAN_USABILITY_PASS | NOT_VERIFIED | 自动化浏览器跑通；真实用户尚未亲自确认。 |
| FULL_OPERATOR_PASS | NOT_VERIFIED | 没有伪造 ACTIVE PlanVersion、AgentRun、GPS 到场或正式 Operator 结果。 |

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

npm run typecheck:all
# passed

npm run build
# passed；Vite 输出既有的大 chunk 提示
```

连续浏览器复跑视口是精确的 1440×900 和 390×844。后端 Network 只记录脱敏路径与状态：创建 traveler/journey 为 201；两次 city search 为 200；discovery、Pocket Walk 保存、GO 为 200；刷新后从服务器恢复进度；地图瓦片请求数为 0。连城无结果后，测试显式改用受控 Shanghai 样例，地点卡片标为 SAMPLE ONLY / TEST_PROVIDER。

- [桌面 1440×900](../../frontend/output/playwright/20261015-first-human-desktop.png)
- [手机 390×844](../../frontend/output/playwright/20261015-first-human-mobile.png)
- [注入 503 的恢复提示 390×844](../../frontend/output/playwright/20261015-first-human-error-mobile.png)

环境使用 Node 24.14.0；没有找到 Node 22。`npm ci` 因现有 lockfile 与 package.json 不一致失败，依赖只在隔离 worktree 用 `npm install --no-save --no-package-lock` 安装，`package-lock.json` 未修改。

## 明早一次性更新并启动

先在原本服务所在终端按 Ctrl+C 停止旧 Uvicorn（用户原来的 :14173 / :18201）。以下命令只创建新的隔离 worktree；若目标目录已存在就停止，不触碰原 checkout、原数据库、lockfile 或密钥。命令不带 `--agent`，所以不会发 AI 请求；默认 Provider 是 LIVE，启动器需要联系邮箱时只在本机终端输入。

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
py -3.13 trial\try_revolution.py --fresh
```
