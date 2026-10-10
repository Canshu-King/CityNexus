# Revolution R99 — Adaptive Short Walk Result

日期：2026-10-11  
分支：`codex/revolution-r63-planned-parallel-journey`

## 交付

R99 为 draft Journey 增加了“当前第二站 + 一个候选第二站”的自适应短步行比较：

- 只接受同一签名成员保存的三个 `SAVED`、WGS84、公共 OSM 身份；比较前要求选择 15/20/30/45 分钟之一并再次明确同意。
- 复用 Valhalla pedestrian 适配器，最多发出两次 `/route`。路由边界只收到两组公共起终点坐标，不包含 GPS、当前起点、查询中心、成员/旅客/Journey、receipt、私密意图或 arrival。
- 每条腿返回 provider、provenance、`observed_at`、时间/距离状态和 caveats。比较成功时使用 `WITHIN_MY_LEG_BUDGET` 或 `LONGER_THAN_REQUESTED`；任一腿不可用时使用 `ROUTE_UNVERIFIED`，不补造时长。
- “Choose this better second stop” 只改私有 draft 的 stop 2；它会失效旧路线、旧 fallback、旧比较和旧同意，要求对新公共路线重新同意。未写入 Place、PlanVersion、MobilityFact、RouteAcquisitionOperation、ProviderCall、AgentRun、GuardianRun、Booking。
- A/B 签名成员隔离保持有效；建议、比较数据和预算不会出现在协作者页面。

## 受控验收证据

一次独立 authoritative run（`r99-adaptive-20261011-06`，390×844 Chromium，新的 SQLite，`--project=chromium --no-deps`）通过：

- 受控 Overpass 返回 Museum、Gallery、Park 三个公共身份并保存 3/3。
- 受控 Valhalla 对 Museum→Gallery 返回 42 分钟、Museum→Park 返回 13 分钟；前端显示两条证据、`WITHIN_MY_LEG_BUDGET`、`TEST_PROVIDER_EMULATOR` 和观察时间。
- 路由请求恰好两次，每次仅两个坐标，`costing=pedestrian`；没有私密字段。
- 选择 13 分钟建议后只替换 stop 2，stop 1 保持不变，比较结果和旧同意被清除；新的 Museum→Park 外部 walking URL 要求 fresh consent。
- 受控路由切换为 503 后，新的比较显示 `ROUTE_UNVERIFIED`，不显示 42/13 分钟、不显示建议按钮，只显示两个公共地图选项。
- 协作者页面显示 `Saved 0 of 3`，不显示三个名称或 adaptive card；数据库 explore-only 计数保持全零。

## 检查命令

```text
py -3.13 -m pytest -q backend/tests/test_r98_two_stop_walkability.py backend/tests/test_r99_adaptive_short_walk.py
2 passed

py -3.13 -m compileall -q backend/app backend/tests/test_r99_adaptive_short_walk.py
git diff --check
cd frontend && npm run typecheck
cd frontend && npm run build
```

真实外部路由未作为验收依据；本轮证据仅来自明确标注的本地受控 provider emulator。
