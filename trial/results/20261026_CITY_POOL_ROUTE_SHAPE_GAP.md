# 城市池的第二个缺口：冻结到的公交事实没有折线，预检却只认带折线的路线

关联 `20261025_CODEX_CITY_IDENTITY_ADCODE_GAP.md` 与勘误二。城市身份这一关已经过了；这一件是它后面那一道。

## 现场（课堂库，05:05 本地）

用课堂栈的 presenter 会话、对该 journey 的 goal task 真调了一次产品自己的冻结门：

```
POST /api/v1/journeys/2e9cd67d-…/agent/goal-tasks/1690b9ed-…/plans/cc543b16-…/freeze-routes
-> HTTP 200（7 秒内返回）
edges: 2 条，status=MEASURED_NOW
  · 天安门广场 → 故宫博物院：77 分钟 / 6006 m / mode=TRANSIT / 8 号线 / source_url=uri.amap.com…
  · 故宫博物院 → 天坛公园：64 分钟 / 7509 m / mode=TRANSIT / 8 号线 / spans_night=true
```

冻结后计划的快照 id 确实换新并对齐：

```
plan_versions.mobility_snapshot_id = 20dc440c-18a1-4e48-a6dd-51464cb5deda
mobility_evidence_json.snapshot_id = 20dc440c-18a1-4e48-a6dd-51464cb5deda
facts = 2，fact_quality = LIVE_PROVIDER_CAPTURE
```

## 但城市池的 routes 仍是 0

同一会话随即读 `GET /simulation/cities?seed=17`：

```
status=BLOCKED  required=3  eligible=0
city CN-RV-3507014DDE2C  missing=['AT_LEAST_3_CAPTURED_ROUTES_REQUIRED']
poi=40  routes=0  provider_city_adcode=110000
```

原因在一条事实的完整字段里：

```
mode=TRANSIT  route_geometry=[]  geometry_provider=null  provider=amap_walking
minutes=78  distance_m=6006  walking_distance_m=3326  captured_at=2026-10-25T21:05:32Z
```

预检把「计划里的路线」算作可计路线，必须同时满足：`fact_quality=LIVE_PROVIDER_CAPTURE`、未降级、**`route_geometry` 非空**、有 `captured_at`（`backend/app/simulation/preflight.py:108` 那一行就是 `or not fact.route_geometry`）。这次冻结出来的是公共交通段：线路、时长、距离都有，**折线为空**，于是两条都不计。

## 这不是「没采集」

`freeze-routes` 真的调了高德：返回了 8 号线的线路名、真实分钟数与 `uri.amap.com` 的请求地址，`MEASURED_NOW` 也说明了它是当场量的。问题在**产出形状与门槛不匹配**：公交测量这条产品路径不落折线，而预检只认折线。

## 两条解决路，需一句裁语

1. **让 TRANSIT 也带折线**（数据域）：冻结时把公交段的 polyline（或起终点折线）写进 `route_geometry`，`geometry_provider` 记来源。门槛不动，语义最干净。
2. **改门槛语义**（产品裁语）：把「有 provider 线路 + 时长 + 捕获时刻的 LIVE 事实」也算可计路线，折线只作可选证据；这与 `preflight.py:108` 现在的写法相反，必须有人明确点头。

我没有为凑演示手写任何路线，也没有改后端；第 3 条仍缺（2 < 3），所以即便形状修好，北京也还差一条边。

## 给课堂的一句话

控制台那句「随机城市池：可用 0 座，需要 3 座；这趟演示用行程自己的城市，仍可开演」在课堂上仍然成立；本件只影响「随机城市池」这条路，不影响主线的开演、守护、接受与完成。
