- id: ORD-0151
  to: 8c66aa92
  priority: P0-critical
  if_head: e9efec6
  order: |
    **#4 的堵点被我两枪定位在 Step 0：产品内的"原文→canonical identity"这一步没有真的去问 resolver。**
    读数（`live_checks/dod4_hydrate_probe.py` + `dod4_gongshan.txt`，副本库、`REAL_CITY_ENABLED=true` + `MODE=live`、3.12.14）：
    - `云和县` → `unresolved:8fccf2bbf123e3df`；`贡山独龙族怒族自治县` → **`unresolved:aeb41cef3b84ddbb`**；两者 `capability=UNAVAILABLE / NO_CANONICAL_IDENTITY`；
    - `POST /catalog-hydrations` 受理 **0.02-0.03 s / 202**，**3 秒后** `outcome=NO_REGISTERED_SOURCE`、`provider_status=null`；
    - 库里 `places` 只有 `CNX-DEMO 8`、`provider_key` 只有 `mock-city` ⇒ **零真 provider 实体**。
    关键判据：返回的是 **`NO_REGISTERED_SOURCE` 而不是 `REAL_CITY_DISABLED`**（`real_city.py:1169` 那条旗标分支没被走到），
    而 **Photon 在 09-21 上午对同一个县是直接可解析的（ORD-0099/0109 实测 ~1 s + extent）** ⇒ 不是网络、不是开关，是**产品路径没调 resolver / 调了但结果被丢**。
    要做：
    ① 顺着 `GET /api/v1/destinations/capability?query=…` 与 `POST /api/v1/catalog-hydrations` 两条入口，
      **把"什么时候才会去问 resolver"写成一条明确规则**（现状像"只有已注册 source 才问，而注册要求已有 canonical"，那是**死循环**）；
    ② 修成：**未解析身份本身就是触发解析的理由**——`PhotonGeocoder`（`integrations/discovery/photon.py:20`，
      今天仍是 built-but-never-wired，只被 `tests/test_foundation_http_adapters.py:90` 实例化）接进 capability/hydration 两条路；
      默认 resolver 按 **R1** 走 Photon，Nominatim 只能显式兜底并记 provenance；
    ③ **一次修两处**：`capability` 与 hydrate 各自算 identity，两处都得改（只修表面会出现"能力说可解析、作业说没源"）；
    ④ 失败必须是**运行性** reason_code（`DESTINATION_RESOLVER_UNAVAILABLE` / `PROVIDER_TIMEOUT` / `PROVIDER_RATE_LIMITED` 一类），
      **不许**把"我没去问"报成结构性 `UNAVAILABLE`；resolver 不可达**不许写 hash**（R10 第 6 条）；
    ⑤ 交一份**能复跑**的 Step 0 证据：`云和县`、`贡山`、一个明显不存在的字符串（如 `zzz不存在的县xq`）三例，
      分别给出 `canonical_destination_id`、`destination_resolution`、provider observations 计数、耗时、以及"有没有真发 HTTP"的传输层证据。
    验收：① 三例里至少两例产出 **真 canonical**（provider id + extent + WGS-84 provenance），第三例是**具名运行性失败**而不是 hash；
    ② `catalog-hydrations` 之后 `NO_REGISTERED_SOURCE` 不再出现在"能解析"的目的地身上；
    ③ 先红后绿（红读数＝我上面两枪）；④ 一条杀得掉的突变（把 resolver 调用摘掉，门必须红）；
    ⑤ 全量红集合是 `eef24d9` 14 条基线的**子集**。
    【边界】不碰 `:4781/:4782/:8693` 与 `_live.db`；不触发 `demo/reset`（R13）；provider 实验用自有副本库/端口；
    不许把真 AI key 带进实验；**不许为了过门去 mock 出 canonical**。
    【与 ORD-0150 的关系】这张**排在 0150 之前**：canary 实时路由在没有真 canonical 之前是无本之木。
  status: DISPATCHED@2026-09-21T20:3x+08 by 494abfd7
