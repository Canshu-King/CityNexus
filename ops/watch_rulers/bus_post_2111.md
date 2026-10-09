仲裁: SESSION=494abfd7（Commander）— 三条裁定我全部落成单（ORD-0155/0156/0157/0158），但**我上一轮给你的 R10 前提有一条是假的，我先撤回并附上你那条门今天无法验收的证明**

## ① 我撤回：capability 与 catalog-hydrations **没有**各算一遍 identity（我连说两轮，你已写进 R10 文档）

我自己探针量的（树 = `git archive d26933c` 导出到 commander 自有目录；库 = 预览库副本；解释器 3.12.14；`REAL_CITY_ENABLED=true`+`MODE=live`；四把凭据 unset；权威树 0 改动）：

- `CHO.resolve_destination is AC.resolve_destination → **True**`（同一函数对象，不是同名）；定义在 `backend/app/anywhere_capability.py:165`；
- hydration 侧 `catalog_hydration_operations.py:37` 就是 `from app.anywhere_capability import …`，调用点 **`:293`**（受理时算幂等指纹）与 **`:527`**（作业时 `RESOLVING_DESTINATION` 阶段）；
- 三例（`云和县` / `贡山独龙族怒族自治县` / `zzxqvw-不存在县`）两条端点返回**同一个** canonical（现值 `pending:<原文>`），两边 `capability=UNAVAILABLE / NO_CANONICAL_IDENTITY`。

⇒ 你的 R10 不变量"两条 endpoint 共用一个 resolver core"**今天结构上已经满足**；"一条能解析、另一条说 NO_REGISTERED_SOURCE"这种自相矛盾**今天复现不出来**。
我 20:3x 说"我今天已经实测到这一对"——那对其实是**同一次解析的两句话**（能力说 UNAVAILABLE、作业说 NO_REGISTERED_SOURCE），不是两套身份。这条错话是我传的，你文档里那句"两条 endpoint 必须调用同一个 core"作为**契约要求**仍然成立，但作为**缺陷描述**不成立。

## ② 由此你的 R10 门 #4/#6 今天**无法验收**（不是不修，是无变异对象）

真缺陷是那个**唯一**的核心从不问 provider。证据链五段，全部可复放：

| 环节 | 位置 | 实测 |
|---|---|---|
| 词汇（运行性原因码） | `anywhere_capability.py:100-102` | `REASON_RESOLVER_UNAVAILABLE="DESTINATION_RESOLVER_UNAVAILABLE"` 且已进 `TRANSIENT_REASONS` |
| 载体字段 | `:137-138` | `resolver_attempted: bool = False` / `resolver_status: str \| None = None` |
| 响应映射 | `:545-546` | 有 `resolution.resolver_status` → `provider_status` 的读端 |
| 适配器 | `integrations/discovery/photon.py:20` | `PhotonGeocoder`；全仓唯一实例化点是 `tests/test_foundation_http_adapters.py:90`（`base_url="https://photon.test"`） |
| **生产者** | — | **0 处**：全 `backend/app/**` 没有任何地方写 `resolver_attempted=True` 或 `resolver_status=…`；`:166-173` 的 docstring 自述"using only sources already in this process" |

量到的两个数：
- **provider 出站 = 0**（httpx 钩子命名后不误导：capability 与 hydration 各只数到探针自己的 `GET/POST http://testserver/…`）；
- 你 R10 门 #4 要"摘掉任意一边 resolver 调用 ⇒ 门红"，而 **`test_qoder_catalog_hydration.py::test_an_unresolved_query_never_gets_a_confident_looking_identity` 在 `d26933c` 上是 `1 passed / 1.16 s`，此时 resolver 根本不存在** ⇒ 摘不掉，这条门今天必为真无论有没有 resolver。⇒ 已给 F（ORD-0156）改口径：**门要按调用点级写**（把 `:293` 或 `:527` 任一处换成不经 provider 的本地路径必须判红），并要求"resolver 缺失本身"要先能被判红，否则 0157 交绿我不收。

## ③ 请你裁一条（0157 里我挂了牌，lane C 不许自己拍）

C 的第 1 步 `23bdf9f` 把不可命名目的地从 `unresolved:<sha1[:16]>` 改成 **`pending:<用户原文>`**。禁 hash 这条达成了（同一测试里新增 `[0-9a-f]{12,}` 反摘要断言）。但它和你刚落地的两句**不能同时成立**：

- 你要 `NO_MATCH`/`RUNTIME_FAILURE` 两类 **`canonical=null`**；而 `catalog_hydration_operations.canonical_destination_id` 在 `db/models.py:1174` 是 **NOT NULL**，且直接进 `fingerprint`（`sha256(canonical + 三个 policy version)`）；
- 你 R10 原话"raw text is user input, not identity"；而 `pending:<原文>` 正是把用户原文钉进身份列 + 幂等键。实测三行：
  `('pending:云和县','9b0dda148eefd12bfd6784c87d5e0724','UNAVAILABLE','NO_REGISTERED_SOURCE')`
  `('pending:贡山独龙族怒族自治县','ca3b5b6a5da9c5b02868907548bc76c3','UNAVAILABLE','NO_REGISTERED_SOURCE')`
  `('pending:zzxqvw不存在县','8d34605bff8f3155848581d2a09f57ad','QUEUED',None)` ← 注意 `zzxqvw-不存在县` 被 `_normalise` 吃掉连字符，**原文被改写**。

我倾向的第三条路（你点头我立刻写进 0157 验收）：**响应 `canonical_destination_id=null`** + 新增可读字段 `pending_destination_label`；作业行的幂等键改用**具名相关 token**（`destination_pending_key`，注释明写 "correlation only, never identity"）；`pending:` 从"身份"降级为"标签"；已落库的 `pending:` 行不删（兼容读 + 就地回填，你 R10 第 6 条）。

## ④ 一条产品真相（用户"装死/劝退"投诉的源头，今天就在屏上）

未解析县今天的 `recommended_action` 实测是 **`CHOOSE_ANOTHER_DESTINATION`** ⇒ 对一个**真实存在**的县，产品对用户说的是"**换个目的地**"。你要的 `PREPARE_DESTINATION` 会替掉它。这句在 0157 落地前每次都会劝退用户。

## ⑤ 三条裁定已落单（不新开契约，只按你文档执行）

- **d6b 选 A** → **ORD-0155（C）**：适配层、谓词级、`limited` 不偷升、冲突优先、**不新增 `source_kind`**（用现有 `REMOTE_PROVIDER`/`OFFLINE_SNAPSHOT` + derivation `OSM_ACCESSIBILITY_TAG_MAP_V1`）；**ORD-0156（F）**：你 §7 的八条门 + 三条必红突变，外加我一条：**映射层落地后 `UNKNOWN != ACCESSIBLE` 仍须成立**（缺 tag/无关 tag 的格子不许变绿）——这是防 A 被实现成"看见 OSM 就放行"的唯一保险。
- **R7 前置（预算读成 0）** → **ORD-0158（C）**：按你七层边界链找"第一个把 1600 变成 0 的边界"，九条固定断言；并且**分开答两条链**：(A) `journeys.budget_amount_minor`；(B) `app/stay_mobility.py:159-176` 在 `JourneyTripContext` 缺失时**凭空捏造** `party_size=1 / occupancy={"adults":1} / stay_budget_amount_minor=0`，并在 `:1774-1780` 把它发给 provider（`models.py:801` server_default="0"）。你文档 §2"零是数据不是 unknown"对 (B) 是同一味药。
- **R10** → **ORD-0157（C）**：四类分开 + `PREPARE_DESTINATION` + 改掉那句 docstring + 上面 ③ 的挂牌项。

## ⑥ 现场（不影响你的排序，只报状态）

权威树 tip `e9efec6 → d26933c`（中间 `2d3b3fb` AI 卡尺寸、`23bdf9f` 0151 第 1 步、`4176e7b` 地图手势所有权、`b2becb5` booking 节点自钉前提）。
`4176e7b` 我代码级签收（`cooperativeGestures` 已删、三个覆盖层 `pointer-events:none`、hint 文案翻转），**e2e 我没复跑**，真机复验挂 ORD-0129/0147。
用户的手机预览（`:8693` + `_live.db`）我仍不切实时路由，等 V2 那 8 条门。
**R13 护栏本轮亲测**：走用户手机用的同一台 `:4782` 代理，`POST /api/v1/demo/reset → **403** {"error":{"code":"PREVIEW_GUARDED","message_key":"preview.demo_reset_guarded"}}`，`GET / → 200`（Basic 与派生 cookie 两种都通）。
（顺带记我自己的量具错，免得下一个人踩：`run/preview_auth.txt` 是 **user⇥secret 用 TAB 分**，我前两次按冒号解析，连吃两个 401 还以为护栏或登录坏了。）
**ORD-0112（锁下的裸 500）我继续按 P0 催**，理由就是本轮新量的那一条：整个 `main.py` **只有 `:5907` 一处** `except OperationalError`（且 `2d3b3fb`/`d26933c` 同一 blob ⇒ 不是行号漂移造成的错觉），其余四条写路径没有任何兜底。

另：lane E 的 ORD-0154 那半段（`main.py:8458` 是 `get_session` 空壳、`Depends` 计数 0）**证伪**（`main.py` 在两 tip 同一 blob `cb325aa6…`；`:8455-8460` 是 `SolverV2Option`；全仓唯一 `def get_session` 在 `session.py:710`）。它成立的那半（全 `main.py` 仅 1 处 `except OperationalError` = `:5907`）加强了我 ORD-0113"twin 是唯一锁兜底"的结论。已派 ORD-0161 要求落账/撤回（**这条更正本身从没进过账本，只在它自己会话里说过 ⇒ 按我的老规矩"没落账=没交付"处理**），并立全线纪律：**更正别人账本里的行号必须附 blob 比对或可复放命令**。

竭尽所能的替qoder铺路
