# 勘误二：城市身份不是「不可执行」——绑定门的三道门槛在课堂库都已满足

对象：`20261025_CODEX_CITY_IDENTITY_ADCODE_GAP.md` 与我在 2026-10-25 夜里的口头结论「两库无 goal-task/district 表 ⇒ 城市身份不可执行」。
本件只更正读数，不改旧文；旧文对「adcode 落库丢失」的取证仍然成立。

## 我错在哪

上一轮我把 mission 的 intent 结构记成 `intent["task"]`，据此打印出 `region=null`，并把它当成了「没有地区」。
现读课堂库 `citynexus_v3_demo_1025.db`（只读打开），同一个 PLAN_ONLY mission（id 前缀 `1690b9ed`）的 intent 键是：

```
intent keys: ['goal_task', 'mode']
intent["goal_task"].amap_region = {"adcode": "110000", "level": "province", "name": "北京",
  "status": "RESOLVED", "query": "北京", "center": "116.407387,39.904179"}
```

也就是说：**任务侧地区早已解析成六位 adcode，是我读错了键名，把「有地区」写成了「没有地区」。**

## 现读的三道门

1. **任务门**：`journey_missions` 里该 mission 为 `PLAN_ONLY`、`trigger_event_id=None`、`requested_autonomy=PLAN_ONLY`、`goal_task.schema_version=1`、`mode=GOAL_PLANNING`。`bind_identity` 的 `_require_task(..., require_draft=False)` 要的正是这几项。
2. **地区门**：`amap_region.status=RESOLVED`、`level=province` 且 `adcode=110000`（直辖市，代码在 `backend/app/simulation/city_catalog.py:84` 显式允许 province+四枚直辖码）。
3. **回执门**：`provider_calls` 里 `operation=goal_amap_district`、`status=SUCCESS` 有四条；其中 `60deda42` 的 request.region 为「北京」，response.districts 里含 `{"adcode":"110000","name":"北京","level":"province"}`，与任务地区逐字匹配。

因此 `POST /api/v1/journeys/{id}/simulation/city-identity`（`backend/app/simulation/api.py:64`）在这里**应当 200 并写入一行**；今日 `simulation_city_identities` 仍是 0 行，只是还没有人按过这扇门。

## 仍然成立的部分

- `real_place_candidates` 仍是 18 列、没有 `adcode`；`journeys.city_code` 九条仍是 `CN-RV-*` 随机码；`places.city_code` 同样。
  ⇒ 旧文的切片 A（研究落库写 adcode）与切片 B（身份写回）原样有效。
- 绑定只解决「这趟行程属于哪座提供方城市」；`/simulation/cities` 的可用数还看「至少五处真来源 POI、至少三条真捕获路线」。绑定之后北京大概率只剩「路线不足」，城市池仍不会变成三座可用。
- `simulation_public_city_snapshots` 也是 0 行；跨课堂发布还没有发生过。

## 已经真跑：绑定 200，预检少一项

r107 跑完后，用课堂栈的 presenter 会话（凭据不落文档）对课堂库调用一次：

```
POST /api/v1/journeys/2e9cd67d.../simulation/city-identity
body {"source_task_id": "1690b9ed-9d00-4c49-986e-85cbd7b3554d"}
-> HTTP 200
{"internal_city_code":"CN-RV-3507014DDE2C","provider":"amap",
 "provider_city_adcode":"110000","source_call_id":"60deda42-50d4-4af4-bb26-1d8d85da0c24",
 "source_sha256":"c8e0581fafd15b977202e3f29e037e9fa2891cc95cf296773054a917a585c5bb",
 "bound_at":"2026-10-25T20:52:38Z"}
```

同一会话前后两次 `GET /simulation/cities?seed=17`：

| | status | eligible | missing | poi | routes | provider_adcode |
|---|---|---|---|---|---|---|
| 绑定前 | BLOCKED | 0 | VERIFIED_CITY_ADCODE_REQUIRED + AT_LEAST_3_CAPTURED_ROUTES_REQUIRED | 56 | 0 | null |
| 绑定后 | BLOCKED | 0 | AT_LEAST_3_CAPTURED_ROUTES_REQUIRED | 40 | 0 | 110000 |

（POI 从 56 变 40 是因为绑定后按 110000 前缀过滤，只剩北京的行，40 仍高于门槛五。）

## 再往后一件

已真调一次 `freeze-routes`（200，两条公交段 MEASURED_NOW），但城市池 routes 仍 0：冻结出的 TRANSIT 事实 `route_geometry=[]`，而预检只认带折线的路线。读数与两条解决路写在 `20261026_CITY_POOL_ROUTE_SHAPE_GAP.md`。

## 下一张数据单

现在挡在「可用三座」前面的只剩一样：**三条带几何的真捕获路线**。它来自 `plan_versions.mobility_evidence_json` 里 `fact_quality=LIVE_PROVIDER_CAPTURE`、未降级、有 `route_geometry`、有 `captured_at` 的事实，不是手写表。  
这需要走产品自己的抓取与冻结（高德步行/公交），我没有把任何路线手写进库，也不建议为凑演示降门槛。

## 边界

本件只读库、只读代码；没有改后端树，没有写课堂库那一刻的状态。绑定动作在 r107 结束后单独执行并单独回执。
