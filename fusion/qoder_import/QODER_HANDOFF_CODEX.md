# 给 Codex 的交接件（Qoder 侧实测，2026-10-14 17:55）

出处：`fusion/codex-journey-20261014` 与 `fusion/qoder-import-20261014` 同起点 `594f9a4e75`。
以下每条都是我在本机源码上逐条跑出来的，不是引用谁的报告。复跑姿势统一为：

```bash
cd /d/moodle/CityNexus          # 只读，不要在里面改任何东西
git grep -n '<pattern>' 594f9a4e75 -- frontend/src backend/app
git show 594f9a4e75:frontend/src/api/citynexus.ts | sed -n '3240,3256p'
```

后端我也用本机 venv 把它跑活了做对照（`127.0.0.1:8121`，空库自举 93 表、`/openapi.json` 249 条路径、
`/api/v1/health` → `{"ai":"disabled","ai_state":"DISABLED_BY_OPS"}`），所以下面凡是「路由存在但没人调」的结论，
**服务端那一侧是实测通的**，不是推测。

## 一、GO MODE 只有半条腿（阻断 charter Phase 4(B)）

| 事实 | 实测数字 |
|---|---|
| 前端有没有 GO 组件 | `GoMode` 在 `frontend/src` 命中 **0** 个文件 |
| 提到 `pocket-walk` 的前端文件 | **只有 2 个**：`src/api/citynexus.ts`、`src/features/discovery/BootstrapDiscoveryPanel.tsx` |
| `transitionBootstrapPocketWalkGo`（POST 写） | 调用点：仅 `BootstrapDiscoveryPanel.tsx` |
| **`getBootstrapPocketWalkGo`（GET 读进度）** | **在 `frontend/src` 零调用点** |
| `go_progress` 挂在哪个响应类型 | 只在 `BootstrapPocketWalkResponse`（citynexus.ts:1878 `export interface`、:1892 字段），**没有任何 GET 响应带它** |
| 面板挂载时实际读什么 | `getBootstrapDiscoveryReadiness`（:720）、`getBootstrapShortlist`（:754、:1629）——shortlist 给 `resume`，不给 GO 状态 |
| 面板一共用几个 API 方法 | 20 个，GO 相关只有 `transition…Go` 与 `clearBootstrapPocketWalk` |

结论（措辞按 charter 的 `Strict meaning of FULL` 第 4、6 条）：

1. R108 的**服务端只读进度门是通的、而且专门被测过**（`c6cd7f94a1 test(revolution): GET GO progress emits no Journey UPDATE statement`、
   `cb3d549241 fix(revolution): make signed Pocket Walk GO GET read-only; keep POST serialization`），
   但**前端没人调它** ⇒ 刷新/后台恢复后 GO 状态无法回灌，charter Phase 4(B) 要求的
   `self-report first stop -> ... -> reload to see persisted state` 在当前 UI 上不可能通过。
   断的是 UI 腿，不是测试没跑。
2. `BootstrapDiscoveryPanel` 唯一的渲染点 `V8Experience.tsx:1644-1650` 上方有代码注释自认：它**故意在 `.v8-product-shell` 之外返回、
   没有底部主导航**（`Amendment F #1`）。⇒ Journey 一旦 ACTIVE、用户回到正常壳（hub/live/map/trips），**没有任何入口进 GO**。
   这与 charter 的 `accessible with user login, no hidden test-only route` 直接冲突。

我这边不动它：它属于你的管辖面（`fusion/codex-journey-20261014` owns Revolution end-to-end Journey/Agent/mobile integration），
且我此刻正往同一个 worktree 移植 collections，同时改 `V8Experience.tsx` / `BootstrapDiscoveryPanel.tsx` 必然撞车。
如果你需要我这边配合（例如把 GO 入口注册进 `v8PanelRegistry.tsx` 的 route surface，和 `live` 那条 `testId: "live-recovery"` 同构），
说一声，我按你的口径接线。

## 二、别把 Qoder 的收藏门原样搬进 canonical（鉴权口径）

实测：`traveler_id: str = Query` 出现次数 **融合 main.py = 0 / Qoder main.py = 1**，
而那唯一一次就是 `GET /api/v1/collections`（`eeb8b8d2fd:backend/app/main.py:3885`），它的 docstring 原话承认：

> `What this version does *not* do is authenticate it -- the id is asserted by whoever calls`

融合树已经有自己的身份缝：`backend/app/traveler_principal.py` 提供 `resolve_journey_member_principal(...)` → `principal.traveler_id`
与 `member_has_capability(...)`（在 `main.py:2035-2042`、`:2184` 已在用），另有 `backend/app/agent/principal.py: resolve_agent_principal(request, session, journey_id=...)`。

同意(consent)口径的落差也一并给你：**`consent` 在融合 `backend/app` 命中 185 次、`provider_consent` 17 次；Qoder 树分别只有 4 和 0。**
⇒ 谁把 Qoder 的 collections / poi-import / calendar 那 12 条路由原样搬进 canonical，就等于新开一扇
`unsigned cross-member read/write`——正是 charter 列的 non-negotiable stop condition。

**更新（18:34，我这侧已经搬完并量过了，你直接照这一版接）**：`fusion/qoder-import-20261014` 上
collections 三条门已改走 `resolve_traveler_principal`，且读门上**根本没有 `traveler_id` 入参**。
活口 8122 实测（明细 `SLICE1_AUTH_ACCEPT_r1.md`）：
匿名点名读从源树的 **200** 变 **401**；合法凭据 + 别人的 id 变 **422**，且带专用理由码
`COLLECTION_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED`／`details.field=traveler_id`（不是静默忽略）；
B 持自己的凭据 `200 / count=0`，`B_sees_A_shelf = false`；建表走 `backend/db/schema.sql`，
删库重启自举实测 **93 → 95 张表**，`UNIQUE (folder_id, place_id)` 在。
⇒ canonical 侧若还要接这一片，请接**我这棵的口径**，不要回落到 `eeb8b8d2fd` 的形状。

## 三、融合基线上「Revolution 侧存活」的实测清单（省你再数一遍）

对 8121 活口 `/openapi.json`（249 条）分类：

```
pocket-walk  4   /bootstrap-discovery/pocket-walk、/bootstrap-shared-walk/pocket-walk、/bootstrap-shortlist/pocket-walk
go           1   /api/v1/journeys/{journey_id}/bootstrap-shortlist/pocket-walk/go
walk         8   另含 bootstrap-shared-walk/lookup、bootstrap-shortlist/adaptive-short-walk
guardian    14   autopilot/start|status|stop、mission …
operator    10   /operator、approvals/{id}/approve|reject、inbox/intake …
discovery    6   bootstrap-discovery、/preview、/readiness …
consent      0   ← 没有独立 consent 路由；同意是请求体字段 + 模块级强制（见第二节数字）
```

`LiveRecovery` 是真接在普通路由上的：`v8PanelRegistry.tsx:181-198` 有 `id: "live"`、`surface: "route"`、
`testId: "live-recovery"`、`when: (s) => s.route === "live"` ⇒ Operator/Guardian 那一面**有壳内入口**，
和 GO MODE 的处境不一样，别一起当「隐藏路由」处理。

## 四、真两叉差量（charter 说不要用 GitHub 截断的 300 文件）

```
git diff --shortstat 594f9a4e75 origin/mirror/integration-frontend-apple-pass1
6839 files changed, 1436017 insertions(+), 140432 deletions(-)     6378 A / 241 M / 220 D
```
241 个 M 里落在产品代码的约 **110 个**（`frontend/src/features` 49、`backend/app/agent` 13、`backend/app/integrations` 12、
`frontend/src/lib` 11 …），其余是 `review/` 证据 PNG 与 `tools/`、`scripts/`。
`ics_parser.py` 两树 `git diff --numstat` 为空 ⇒ 完全相同，不必讨论。

另：charter 指定的 Qoder 移植源 `eeb8b8d2fd` 比台上演示那棵 `cca117cf1a` **更前进**
（`git diff --numstat eeb8b8d2fd cca117cf1a -- backend/app frontend/src` = +3091 / −10956）。
但台上那棵独有 3091 行，最大头是 `backend/app/stay_mobility.py` +2056/−2227（带 `party_size` 行为回归臂）
以及 `V8Experience.tsx` +110/−208、`PlanWithAiSheet.tsx`、`JourneyTrialSetup.tsx`、`CopilotDock.tsx`、`main.tsx`。
⇒ 你走 canonical 组装时按 `never overwrite their newer product fixes` 处置这批，别按文件新旧一刀切。

## 五、今天早些时候另外两条实测，可能改变你的优先级

- **真实城市腿只差开关**（lane z1，`_z1.db` 我亲自复核）：只设 `CITYNEXUS_REAL_CITY_ENABLED=true` 与
  `CITYNEXUS_LIVE_VALHALLA_URL`，就收到 8 条真上海 OSM 候选（`overpass:way/161090899` 上海博物馆、`node/4674819096` 杜莎夫人蜡像馆，
  全 `city_code=CN-SHANGHAI`）+ 一段真 Valhalla WALK 640m/8min，落成 `LIVE_PROVIDER_CAPTURE`；
  失败行如实留（三轮 overpass 镜像 `ReadTimeout`、`fallback_reason=REAL_CITY_DISABLED`），无 replay 洗白。
  ⇒ charter Phase 3 的阻塞是布景与开关，不是代码；`main.py:13915` 调用点已经在传 `mode="live"`。
  另外 overpass 认 User-Agent，默认 curl 会吃 406。
- **Agent 目前实质没有判断空间**（lane q2，四轮对照我亲自复核）：AI 全关 + 三种 AI 开法，
  `state_hash 04dfab2fd449` **四轮相同**、终局行程序列字节一致、R1 与空白对照 R3 逐字节相同，
  且模型要 5 个候选时服务器只回 1 份零差异 `F0_STABLE_COPY` ⇒ 判定「自主性未证实」。
  融合基线自身也是 `ai_state=DISABLED_BY_OPS`。这正是 charter 那句
  `Existing AI fallback MUST NOT be passed off as autonomous external model judgment` 的现行实况，
  Phase 4(C) 要走真判断得先把 AI 开起来（本机网关只有 chat/completions，`:7863`；`IMPACT_TIMEOUT_SECONDS=10` 太短，实测一轮 44–64 秒）。

## 六、融合树建表的真机制（谁做移植都会踩，先给你）

`backend/app/db/session.py:19` `SCHEMA_PATH = ROOT / "db" / "schema.sql"`，`ROOT = Path(__file__).resolve().parents[2]`
⇒ **真实文件是 `backend/db/schema.sql`（不是 `backend/app/db/schema.sql`）**；
`session.py:741 def ensure_schema(target_engine)` 读它并 `raw.executescript(sql)`，执行前还跑
`_quarantine_existing_duplicates` / `_collapse_duplicate_active_plans` / `_retire_duplicate_active_anchors` /
`_prepare_shared_stop_grant_slot` / `_preserve_legacy_hydration_table` 这些历史清理。

实测：**融合树这条路径上既没有 `Base.metadata.create_all`，也不靠 alembic 建表**
（`git grep create_all 594f9a4e75 -- backend/app` = 0 命中）。

| | `backend/db/schema.sql` |
|---|---|
| 融合基线 | 89 个 `CREATE TABLE` / 90150 B |
| Qoder 产品树 | 61 个 / 56773 B |
| 融合里 `collection` 字样 | **0** |
| `session.py` 行数 | 融合 1685（`ensure_schema` @741）/ Qoder 1123（@588） |

⇒ 两条对双方都成立：
1. **只加 SQLAlchemy 模型类不会长出表**；任何新能力必须同时往 `backend/db/schema.sql` 写
   `CREATE TABLE IF NOT EXISTS`，验收要看空库自举的 `sqlite_master`，不能只看 import 不炸。
2. **谁把 `db/session.py` 或 `db/schema.sql` 按「谁新用谁」整文件搬，谁就删掉对方的表**——
   融合那份比 Qoder 多 28 个建表语句，Qoder 那份多出来的只有 collections 那两张。

顺带另外几枚规模差（parity 腿实测，我复算过 `session.py` 与 `gateway.py`）：
`main.py` 基线独有 handler **175**、`db/models.py` 基线独有模型 **35**、`schemas.py` 基线独有 **57**、
`api/citynexus.ts` 基线独有符号 **93**、`agent/gateway.py` 的 `AgentToolGateway` 基线 2998 行 vs Qoder 1078 行；
反向 `openapi` 生成物与 `V8Experience.tsx` 是 **Qoder 更长** ⇒ 覆盖方向两面都不许「捡大的」。
Workbox `public/sw.js` 两树字节相同（211 行，不在 diff 里）⇒ SW 不是冲突源。

config 层还有一个方向性结论：**Qoder 的 `core/config.py` 删掉了 `traveler_auth_secret`、全部 `city_search_*`、
`live_valhalla_test_provider`**（实测 fusion 命中 1/7/1，mirror **0/0/0**），并把 `hermes_model` 默认改成 `hermes`。
⇒ 真实城市腿与 traveller 签名是**基线更实**，config 这一路应当「反向不移植」。
两树的 `real_city_enabled=false / live_valhalla_url=None / real_city_mode=replay / IMPACT_TIMEOUT_SECONDS=10`
四项默认值逐字一致。硬关 `DISABLED_BY_OPS` 在 `ai_availability.py`（两树都有），
前端 `aiGenerationRun.ts` 到 `no_model` 的映射两树逻辑一字未动。


## 七、状态更新（2026-10-14 21:46）：§二 与 §六 我这侧已闭环，切片1 前端也落了

写这份交接件时（17:55）§二 的鉴权升级和 §六 的 `schema.sql` 建表是**待办**，现在都是**已实测的既成事实**，
你排优先级时请按这一节覆盖上面两节的「待办」语气：

- 表：空库自举 融合基线 **93** → import 尖 **96**，新增 `collection_folders` / `collection_items` / `journey_checkins`，`REMOVED_TABLES=[]`，索引 **228 → 236**。只走 `backend/db/schema.sql`，`git grep create_all` 于 `backend/app` 仍 0 命中 ⇒ §六 的警告对后来的车道仍然成立，只是不再欠实现。
- 鉴权：`GET /api/v1/collections?traveler_id=<别人>` 在 import 尖 **422 / `COLLECTION_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED`**（门上已无该入参，是结构性不能点名），无凭据 **401**，B 持自己凭据 **200 / count=0**。§二 要求「不许原样搬」的那扇门，现在搬不动了。
- 前端：收藏面板挂 `route==="discover"`、足迹面板挂 `trips`、行程逐日行两条写腿（打卡 / 收进架子），守门 `5 passed (21.6s)`，数值在 `reports/qoder-ord0510/*.json`。细节与两处量具坑记在 `SLICE1_UI_PORT_SEAM.md` §3–§4。
- 因此 **§一（GO MODE 半条腿）没有被我顺手改**：那是你 `fusion/codex-journey-20261014` 的地盘，我只在 §一 留了接线建议，没在 import 分支动它。
- 我这边仍未接通的腿：`footprintRead.ts`（地图面专用，欠 `mapPanelCopy.ts` 里 6 枚 `footprint*` 键）、`demo/scene/ensure`（判定为布景工具、不进产品）、`vite build` 与真机 PWA（这条分支上从没跑过）。
