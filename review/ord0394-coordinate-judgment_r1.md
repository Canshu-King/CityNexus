# ORD-0394 step 1 -- 判断：坐标是读侧 join，不是写侧落库

判断依据全部在下面，行号逐条在 `0598e4d17202`（`git rev-parse origin/_preflight_cand` = 0598e4d17202fd0619592a40e617c67b2108afd3）上取，
blob 由 `git rev-parse origin/_preflight_cand:<path>` 现读；库读数全部 `mode=ro&immutable=1` 只打开，没写过一个字节。

## 一句话答案

**读侧 join。** 坐标在这套系统里从来不是 activity 的字段，而是 place 的字段，代码里已经写着这条事实、
也已经在另一处投影里这么做了：`backend/app/stay_mobility.py:471` 的注释原文 `# Coordinates live on the Place row, not on the Activity.`，
同一函数 `backend/app/stay_mobility.py:498` 就是 `lat = getattr(place, "latitude", None) if place else None`——join 的写法是既有的，不是我提的新招。

## 为什么写侧落库是错的（三条都有读数）

* `iso.db`：activities=6，带 place_id=6，能 join 到经纬度=6，metadata_json 里含 latitude 的=0，
  places 带经纬度=16，coordinate_system=WGS84（`PRAGMA table_info('places')` 里有 `coordinate_system` 与 `source_coordinate_system` 两列）
* `canary_56d20ec.db`：activities=134，带 place_id=134，能 join 到经纬度=134，metadata_json 里含 latitude 的=0，
  places 带经纬度=16，coordinate_system=WGS84（`PRAGMA table_info('places')` 里有 `coordinate_system` 与 `source_coordinate_system` 两列）
1. **写侧不是“补几行”，是 100% 回填**：两枚库里 `metadata_json` 含 latitude 的行数是 **0**（上面逐库读数），
   也就是没有任何历史行自带坐标；要么跑一次迁移，而那次迁移本身就得做 place→activity 的 join——
   等于承认读侧 join 是对的做法，只是把它一次性抄进库里。
2. **抄进来就多了一个会漂移的真值**：`places` 是坐标的持有者（`backend/app/schemas.py:375` 的 `Place` 模型 `location: GeoPoint`，
   且 `backend/app/schemas.py:370` 的 `GeoPoint` 只有 latitude/longitude 两枚数）；把值复制进 `activities.metadata_json` 之后，place 改了坐标，
   activity 那份还是旧的，而且复制件没有 `coordinate_system` 一起走——同一屏幕上两个来源同名不同系。
3. **`metadata_json` 的三支笔没有一支写坐标**：读 `backend/app/main.py` 三处（backend/app/main.py:6614, backend/app/main.py:6702, backend/app/main.py:6788），写回三处（backend/app/main.py:6632, backend/app/main.py:6707, backend/app/main.py:6791）。
   逐笔看它外层函数与它写进去的键：`backend/app/main.py:6632` 在 `def _transition_activity_state`，键 arrived_at, en_route_at, started_at_actual; `backend/app/main.py:6707` 在 `def complete_activity`，键 completed_at_actual, legacy_execution_compatibility; `backend/app/main.py:6791` 在 `def skip_activity`，键 skipped_at。全是状态跳转的时间戳与执行兼容标记，没有 latitude/longitude 这一说。
   `en_route_at`/`arrived_at`/`started_at_actual` 这三枚取自 `backend/app/main.py:6615` 的 `actual_key` 映射——`metadata_json` 不是坐标的存放处；把坐标塞进去要新开一支写笔，
   而 `/experience` 明明只是一枚投影：`backend/app/main.py:3004` 就是那条路由的声明行。

## 读侧改在哪一格（只说位置，这一步不写码）

* 投影体在 `backend/app/stay_mobility.py:1696` 起：每条 activity 已经发 `"place_id": item.place_id,`（`backend/app/stay_mobility.py:1711`）与 `"metadata": _load(item.metadata_json, {}),`（`backend/app/stay_mobility.py:1717`），
  这一份投影**现在根本不发 `location` 这个键**——现读路由正文里 6 条 activity 有 `location` 键的是 **0** 条（见下节实测），
  号令者 17:00 那块写的 `location=None` 是 `dict.get` 出来的默认值，不是正文里真有一个 null 字段；这点要更正，因为它会误导“字段有了、值没填”这种读法。
* **三处消费点读的都是同一格 `metadata.longitude/latitude`**，形状已经定死：`frontend/src/components/v8/MapPanel.tsx:19、107`（判空 `tripHasNoCoordinates` 与 `points` 的 flatMap 各一处）、
  `frontend/src/components/v8/MapPanel.tsx:113`（取数 `latitude: item.metadata.latitude`）、`frontend/src/app/V8Experience.tsx:3723`（`planStops` 的过滤，紧接 `frontend/src/app/V8Experience.tsx:3787` 的 `map-stop-*` 列表）。
  所以 join 之后坐标若仍走 `metadata` 这一格，**前端一行都不用改**（`frontend/src/app/V8Experience.tsx` 的取数行 `frontend/src/app/V8Experience.tsx:666` 也在尖暂停名单里，少动它正好）；
  如果选择另起一个 `location` 键，就要同时改上面三处判据，且要落在被冻结的 `frontend/src/app/V8Experience.tsx` 里——那是这条单现在最不该碰的文件。
  代价要说清楚：`metadata` 一旦被 join 派生值占用，正文里的 `metadata` 就不再等于库里 `metadata_json` 的字节。
  补法不是改回去，而是同格带上来源声明（`coordinate_system` 与一枚具名的 provenance 键），让消费能分辨哪几枚键是写出来的、哪几枚是读出来接上的。

## 现读路由的正文（GET only，:8693，读数于本地 2026-09-28 17:35:14 +08:00）

```
GET /api/v1/journeys/22222222-2222-4222-8222-222222222222/experience  -> 200  body_bytes=4955
active_plan.activities            = 6 条
activity 的键                     = city_service_id,end_at,id,locked,metadata,place_id,protected,sequence_no,start_at,status,title,type
含 location 键的条数              = 0 / 6
activities[].place_id             = place-old-town,place-riverside-museum,place-food-hall,place-tech-art,place-river-cruise,place-skyline-dinner
metadata 键并集                   = completed_at_actual,legacy_execution_compatibility
trip.arrival_anchor 的键          = at,latitude,location,longitude,reservation_id   latitude=None   place_id 在不在=False
```

## 这一格读侧修不了的东西：出发/到达锚点（必须请裁，我不会顺手“造”坐标）

`trip.arrival_anchor` / `departure_anchor` 的 latitude/longitude 现读是 **None**，而锚点正文里**没有 `place_id`**（上面实测=False）。
* 投影出自 `backend/app/stay_mobility.py:222` 的 `def _anchor(...)`，`backend/app/stay_mobility.py:229` 那行是 `"latitude": value.get("latitude")`——值来自 `journey_trip_contexts.arrival_anchor_json`；
* 种子里写进去的只有 at 与一句标签：`backend/app/stay_mobility.py:165` = `arrival_anchor_json=_json({"at": journey.start_at, "location": "Arrival"}),`，没有坐标也没有 place 引用；
* `iso.db` 库里 `journey_trip_contexts` 行数=0（那枚库里根本没有这一行），所以 join 到 place 的**前置条件（一个 place_id）不存在**——
  这不是“读侧 join 一下就好”，是要先决定锚点身份：`backend/app/schemas.py:203` 的 `JourneyAnchor` 模型**本来就有 `place_id: str | None`**，
  只是 `_anchor()` 既不读也不发它。所以 ORD-0394 的完整收口是两格：activities 走 join（可当场做），
  anchors 要么具名 null 并说明为什么（`/experience` 里那两枚是行程边界，不是地点），要么先把 `place_id` 落进锚点契约再 join——后者是契约增项，请您裁。

## 契约面（ ORD-0383 刚把两份契约的账揭开，这里先量清楚再动）

`contracts/openapi.yaml` 里 `latitude` 命中 4 行、`coordinate_system` 命中 6 行（首行 contracts/openapi.yaml:2211）；`activities` 与 `experience` 同行的声明 0 处。
也就是说：读侧一旦把坐标发出去，`/experience` 的响应形状就变了，而这份手写契约里没有那一格——
这条单落地时要同时决定要不要写进契约（不写的话，下一个车道还是会靠猜）。我不在这一步改它。

## 结论与下一步（等您点头再动码）

1. activities 的坐标 = **读侧 join**（place→activity，在 `backend/app/stay_mobility.py:1717` 那一格里带上 latitude/longitude/coordinate_system 与一枚具名 provenance），不改库、不迁移、不改被冻结的 `frontend/src/app/V8Experience.tsx`。
2. anchors 的坐标 = **不属于 join 能解决的一格**，按上面两条选项之一处理，需要您的裁。
3. 验收要件①-④我打算这样自证：①用现读路由正文逐条 print（有值或具名 null，不许静默丢行）；
   ②在 390×844 真点击下读 `v8-maplibre-panel` 可见 + `.v9-map-marker` ≥2 + `map-stop-*` ≥2，点击点是 `frontend/src/app/V8Experience.tsx:3787` 那一行的按钮；
   ③反例：把一枚 place 的经纬度置空后必须走“没有可信坐标”那一支（判据在 `frontend/src/components/v8/MapPanel.tsx:19`），不许画到别处；
   ④我不动 fixture——上面所有读数都出自真库与真路由，fixture 里补坐标正是这条禁止的事。

未改善与不确定的部分：我没有跑后端套件（这步只判断，没改码）；`:8693` 是共享预览数据，我只发 GET，没碰 `_preview.db`、没跑 demo/reset（它现在要 `X-Demo-Reset-Token`）；库里 6 条 activity 全部可 join 这一条在 `canary_56d20ec.db` 的 134 条上同样成立（0 条 join 不到），所以“读侧会留空位”的风险目前量到的是 0，但我没扫过全部历史库，别的机器上的库不在我读数范围内。

## 行号会漂：同一枚 needle 在两个尖上的现读

号令者 17:00 那块的行号取自 `1f8d7061`（当时正确），我这条判断落在 `0598e4d1` 上；下面每行都是两个尖上各跑一次 `git show` 的命中行号。

| 文件 | needle | 号令者的用意 | `1f8d7061` | `0598e4d1` | blob 变化 |
|---|---|---|---|---|---|
| `backend/app/main.py` | `@app.get("/api/v1/journeys…` | 号令者那块写的 :2939 | :2939 | :3004 | 923cef1e → a8e01ca2 |
| `backend/app/stay_mobility.py` | `# Coordinates live on the …` | join 的既有写法 | :471 | :471 | a0e07216 → a0e07216 |
| `backend/app/stay_mobility.py` | `"metadata": _load(item.met…` | activity 投影里 metadata 那一格 | :1717 | :1717 | a0e07216 → a0e07216 |
| `frontend/src/app/V8Experience.tsx` | `setData(experience)…` | 取数（号令者写 :662） | :665 | :666 | 8dc3a01d → 72a91588 |
| `frontend/src/app/V8Experience.tsx` | `data-testid={`map-stop-${s…` | 停止列表挂载处（号令者写 :3779） | :3779 | :3787 | 8dc3a01d → 72a91588 |
| `frontend/src/components/v8/MapPanel.tsx` | `export function tripHasNoC…` | 判空函数（号令者写 :16） | :16 | :16 | 04937100 → 04937100 |

这条 drift 不是抽象风险：刚落的 ORD-0384 把自己两处契约锚钉成了数字（`backend/app/main.py` 不关，但它读的 `contracts/openapi.yaml` 在动）。
现读：`feasibility_failures` 在 `1f8d7061` 是 :1393、在 `0598e4d1` 是 :1424；`requires_user_decision` 是 :1923 → :1954。
也就是说 n3 那份现在打印的 :1393 / :1923 在 `0598e4d1` 上指的是别的行；它的 Y4 臂下次跑门会自己报红——
这恰是我这条判断的理由之一：**坐标与它所在的行号都不该被抄成第二份真值**，读侧 join 与“门现场重算”是同一件事。

## 这条单因此要多加一条验收（我不擅自加，请您裁）

`/experience` 里若把坐标接进 `metadata`，同一次改动应带上 `coordinate_system`（库里 16 枚 place 全是 `WGS84`，`PRAGMA` 现读；`places.source_coordinate_system` 全为 None），否则“把坐标发出来”这句话仍然没有说它在哪个坐标系里。
