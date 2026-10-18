# 手机探索：按地点名称查找

## 本次产品增量

现在可以在选好公开地图区域后，展开「已经有想去的地方？」，输入想去的博物馆、公园等地点名称，再点击「查找这个地点」。原有按类别搜索保留。

- 输入或展开面板不会联网；点击按钮或输入框 Enter 才提交一次查询。
- 按名称查找使用 Photon `/api/`，携带名称、所选公开区域与类别过滤。服务端仍核对公开地点类别、OSM 身份、距离和访问限制。
- 查询范围仍为所选区域附近 2.5 公里，最多返回 3 处。不会自动改用其他 provider 或重试。
- 搜索结果继续走本人签名收据；刷新恢复不发起新的地点查询。
- 营业时间、费用和正式方案选用条件沿用现有规则。名称匹配本身不补造营业或费用。

入口：Revolution → 探索 → 选择地图区域 →「已经有想去的地方？」。

## 验证记录

本次没有新增真实 Photon、OSM 或模型请求。以下均为本地测试，不增加真实来源证据：

| 检查 | 结果 | 覆盖 |
| --- | --- | --- |
| `pytest tests/test_photon_poi_adapter.py tests/test_bootstrap_photon_provider_selection.py` | 40/40，exit 0 | 新名称查询参数、bbox、结果类别/距离过滤、单请求失败记录，兼容原类别路径 |
| `pytest tests/test_bootstrap_place_facts.py::test_signed_named_search_dispatches_once_and_restores_private_receipt` | 1/1，exit 0 | 独立临时 SQLite、正常签名用户、无同意/非成员拒绝、实际路由分发、收据落库/本人恢复；HTTP 使用 MockTransport |
| `playwright test --config playwright.mobile-trial.config.ts e2e/revolution-place-card-facts.spec.ts` | 2/2，exit 0 | 390×844 Chromium UI 夹具；名称 Enter 一次提交、输入不请求、44px 按钮、无横向溢出；原详情/刷新路径仍通过 |
| `npm.cmd run typecheck:all` | exit 0 | TypeScript |
| `npm.cmd run build` | exit 0 | Vite；仍有既存大分包提示 |
| `git diff --check` | exit 0 | 本次路径 |

签名 API 测试初次因测试替身未接受位置参数失败，修正该替身签名后通过；不是产品 provider 故障。测试产物位于本机 `AppData/Local/CityNexus/QA/named-place-20261018`。未改用户数据库，也未重放南京/台北旧查询。

手机组件来自本组既有 Hermes 工人提交 `3eb4bbf3fd95ef63514e96674e94298b08889593`，仅集成两个新增组件文件；没有导入其旧分支上的其他内容。

## 下一项真实闭环

使用一个新的、用户确实想去的地点名称，通过这个入口查找并读取公开来源详情。若真实来源给出营业/费用，再继续正式 PlanVersion → 选用 → 确认启动。当前新增名称入口尚未有真实 provider 验证；既有台北/南京结果仍缺营业和费用，真实正式 PlanVersion → ACTIVE → Hermes 持久化工具轨迹仍未完成。

当前已运行试玩服务仍为上一产品 SHA `cb86b7689a` 的后端；不要把本报告的名称输入夹具算成该服务已经完成真实查询。
