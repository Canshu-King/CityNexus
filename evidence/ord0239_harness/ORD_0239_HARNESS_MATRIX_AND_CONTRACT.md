# ORD-0239 · 11 城矩阵 ＋ 后端 support contract 规格（HARNESS 只读交付，**两棵树各一份**）

按仲裁 `5782717232` §⑤ 与 commander 12788 派给只读车道的活。**本件不修产品、不改 evaluator、不写任何库。**
所有"当前是什么"的读数都是**我自己量的**；commander 的 03:38/03:40 读数我**先复现再引用**（复现结果见 §1）。

## 0 · 坐标与护栏（读数离开这两行就没有意义）

```text
树 A（活线）  D:/moodle/_qoder_integration_20260919  head f5a6b9a
              backend/app/anywhere_capability.py  75,980 B  sha256_16 cb0e24c14fa7ad73  工作树干净
              CAPABILITY_STATES = ("READY","HYDRATABLE","UNKNOWN_RETRYABLE","UNAVAILABLE")   ← 四值 :74
树 B（手机/pinned） D:/moodle/_qoder_cmdr_gate_20260921  head 53fe8e8
              backend/app/anywhere_capability.py  23,225 B  sha256_16 0231d36670b8b543  工作树干净
              CAPABILITY_STATES = ("READY","HYDRATABLE","UNAVAILABLE")                        ← 三值 :49
```

护栏（每次运行一致，写进收据）：`CITYNEXUS_ANYWHERE_RESOLVER=off`（在 import 之前设，解析器 dataclass 在 import 时冻结）；
`CITYNEXUS_PHOTON_BASE_URL=http://127.0.0.1:9` 当**绊线**——若任何路径仍去打 provider，答案会以 `RUNTIME_FAILURE` 出现而不会被当成"这个目的地不存在"；
`CITYNEXUS_AI_ENABLED=false`；`TestClient` **进程内**（0 监听端口、0 对外 HTTP）；
每次运行自己新建一次性库（`lab/evidence/_db/ord0239_*.db`、`mobaxis_*.db`），跑完删，
**释放 741,376 B ×2 ＋ 733,184 B ×2 ＝ 2,949,120 B**；**从未 `demo/reset`**。
`_live.db` 只用 `mode=ro` ＋ `PRAGMA query_only=1`（读回 **1**），扫前后 size/mtime 相同；
`_preview.db` 我试的路径打不开（`OperationalError`）⇒ **不声称看过它**，具名尝试路径 `D:/moodle/_qoder_preview_20260920/backend/_preview.db`。

收据：`ord0239_matrix_live.json`、`ord0239_matrix_phone.json`（11 城 × 2 种查询写法 × 5 种库状态 × 两棵树，含逐 intent 计数）；
`ord0239_mobility_axis_1044.json`(活线) / `_1045.json`(手机)；`ord0239_store_axis_readonly.json`（活库只读那一列）。
量具：`lab/tools/harness_ord0239_matrix.py`、`harness_ord0239_mobility_axis.py`。

## 1 · 先复现 commander 的两条读数（都对，且我给出更精确的边界）

| 他的说法 | 我的复现 |
| --- | --- |
| 状态词表**实为四值**（活线）、文档还写三值 | **成立**：活线 `:74` 四值；两棵树 `:13` 文档段**逐字相同**，都写"three values, and deliberately no fourth unknown" ⇒ **文档落后只发生在活线**；手机树代码本来三值，**它内部自洽**（他 03:40 的更正方向正确） |
| `HYDRATABLE` 的代码语义＝"身份已解析＋目录还没东西＋可补水" | **成立**：活线 `:823` 注释原文 `HYDRATABLE until this catalog holds something for it`；实测见 §3——**北京 8 行与厦门 0 行拿到同一个词同一个原因** |
| 城市选择器读 `GET /api/v1/destinations/capability` | **成立**：两棵树都有（活线 `main.py:2823`、手机树 `main.py:2813`） |
| 手机链的 `place` 轴（北京 8 / 演示城 8 / 其余 0） | **成立**（我只读查 `places GROUP BY city_code`）：`CN-BEIJING 8, CNX-DEMO 8`，**宣传名单里的其余 9 城在该库为 0 行** |
| 另：两棵树的私有函数签名已经漂了 | **我量到一个新证据**：`_mobility_evidence()` 在活线返回 **3 元组**、手机树返回 **2 元组**（我第一版工具因此当场崩）。公开面 `coverage_detail` 一致 ⇒ 规格必须以**payload** 为契约，不能以私有函数为契约 |

## 2 · 11 城矩阵（活线读法；手机树只在"编码方式"上不同，差异集中在 §4）

宣传名单来源：`frontend/src/app/V8Experience.tsx:4106-4118`（`CITY_NAME_BY_SLUG`，**11 项**）。
后端可见词表来源：`backend/app/main.py` 的 `_CITY_DISPLAY_NAMES`（**16 个中国城市码，两棵树内容相同**，
**不含 FUZHOU / TOKYO / SINGAPORE**）。

| 宣传城 | 中文写法 → 结果 | `CN-<SLUG>` 写法 → 结果 | place_count | 缺的 intent |
| --- | --- | --- | --- | --- |
| XIAMEN 厦门 | HYDRATABLE / COVERAGE_INCOMPLETE / START_HYDRATION | 同 | 0 | 全部 6 项 MISSING |
| **BEIJING 北京** | **HYDRATABLE** / COVERAGE_INCOMPLETE | 同 | **8** | 只差 **lodging、nightlife**（其余 4 项 READY） |
| SHANGHAI / TIANJIN / GUANGZHOU / SHENZHEN / CHENGDU / HANGZHOU | HYDRATABLE / COVERAGE_INCOMPLETE | 同 | 0 | 6 项全 MISSING |
| **FUZHOU 福州** | **UNAVAILABLE / NO_CANONICAL_IDENTITY** / CHOOSE_ANOTHER_DESTINATION | 同 | 0 | — |
| **TOKYO 东京** | **UNAVAILABLE / NO_CANONICAL_IDENTITY** | 同 | 0 | — |
| **SINGAPORE 新加坡** | **UNAVAILABLE / NO_CANONICAL_IDENTITY** | 同 | 0 | — |

三条必须写进规格的观察：

1. **两种写法（中文名与 `CN-` 码）结果逐格相同** ⇒ 那 3 城失败**不是** UI 传参形状的锅，是词表/身份源的锅。
2. **`S1 空库` 与 `S2 seed_demo` 的判定分布完全一样（8 HYDRATABLE / 3 UNAVAILABLE）** ⇒
   今天这套演示数据**没有让任何一座城的 support state 前进一格**（北京从 0 行到 8 行，词还是那个词）。
3. **正控 `S3`**：我给 FUZHOU/TOKYO/SINGAPORE 各插入 `CN-*` 与 `JP-/SG-*` 两组地点行后，**这 3 城从 UNAVAILABLE 变 HYDRATABLE（11/11）**；
   而 `S4`（只填 1 个 intent）与 `S5`（把 4 个 place 类 intent 的门槛都填满）里 **XIAMEN 到 5/6 READY、只差 mobility**，
   **verdict 始终不改口** ⇒ 判据不是"有没有地点"，也不是"够不够一格"，而是**六轴全绿**（与 `MIN_READY_CANDIDATES`
   `3/3/2/2/3/2` ＋ `MOBILITY_EXPLICIT_RATIO_READY=0.8` 一致，都是实测）。

## 3 · 最硬的一条：**"READY" 这个词今天一次都没出现过**

在 **11 城 × 2 写法 × 5 库状态 × 两棵树 = 220 个格子里，`capability=READY` 出现 0 次**。
而且这不是量具坏了——正控证明它能出现得了一半：

```text
北京（seed_demo，两棵树相同）：ready intents = attractions, booking, food, mobility   缺 lodging, nightlife
演示城 CNX-DEMO            ：ready intents = attractions, booking                    缺 food, lodging, nightlife, mobility
XIAMEN 正控 S5（我填满 4 类 place intent + 3 个 mobility 服务 + 2 个可订服务）
                            ：ready intents = 5/6，仍缺 mobility  → verdict 仍 HYDRATABLE
mobility 这一轴的输入是【显式 OD 矩阵】，不是服务行：
  CN-BEIJING  covered 对 = 56/56（ratio 1.000）→ mobility READY
  CNX-DEMO    covered 对 =  9/56（ratio 0.161）→ PARTIAL
  CN-XIAMEN   covered 对 =  0（矩阵里没有这座城的成对事实）→ MISSING，**插服务行不会点亮它**（实测）
```

⇒ 规格结论：**"能不能对旅客说 READY"目前由 `data/mock/mobility_matrix.json` 的显式成对覆盖决定**，
而它只对北京一座城覆盖到位。**任何"11 城都支持"的文案在这台机器上都是超前承诺。**

## 4 · 两棵树的契约差异（同一件事的两种编码 ⇒ parity 门必须按树各出一版）

**payload 键集合本身也是两棵树不一样（实测，同一格 `BEIJING/中文写法`）**：

```text
手机树 53fe8e8  16 键：canonical_destination_id, capability, catalog_schema_version, coverage,
                      coverage_detail, destination_resolution, fingerprint, matched_label,
                      missing_categories, place_count, provenance, provider_policy_version, query,
                      readiness_policy_version, reason_code, recommended_action, unclassified_categories
活线   f5a6b9a  26 键：上面那些 ＋ candidates, destination_pending_key, destination_state, hard_gaps,
                      malformed_candidates, pending_destination_label, pending_label_fidelity, places,
                      retryable, resolver_query_normalized
```

⇒ 手机上**没有** `destination_state`、**没有** pending 五列、**没有** `retryable`；
⇒ `TOKYO` 那一格：活线给 `canonical_destination_id = None` ＋ `pending_destination_label = "CN-TOKYO"`；
  手机树给 **`canonical_destination_id = "unresolved:3b27db745ef31062"`**（一个字符串占在身份列里）。
⇒ 契约里凡是判"有没有身份"的分支，**必须按 `canonical_destination_id` 是否以 `unresolved:` 开头再判一次**，
  否则同一份 UI 代码在两棵树上会得出相反结论（我自己的第一版判据就因此把手机树读成"11/11 都有身份"）。
⇒ 字段实名是 `reason_code` 与 `recommended_action`（不是 `reason`/`action`），parity 门按实名钉。

| 观察点 | 活线 f5a6b9a（四值） | 手机树 53fe8e8（三值） | 对消费方的后果 |
| --- | --- | --- | --- |
| `capability` 值域 | 4 个（含 `UNKNOWN_RETRYABLE`） | 3 个 | **手机上问不到/超时会被塞进 `HYDRATABLE` 或 `UNAVAILABLE`**，即 R1 禁止的洗白在旧树无语法可表达 |
| `destination_state` 字段 | 存在（`RESOLVED` / `NO_MATCH`） | **payload 里没有这个键**（读到 None） | 任何按 `destination_state` 分支的 UI 在手机上**永远走 default 分支** |
| 身份未解析时 `canonical_destination_id` | `None`（＋ pending 五列） | **`"unresolved:<hash>"` 字符串** | "有没有身份"在两棵树要用两种判断；**非空 ≠ 有身份**（我第一版判据就被这条骗过一次，把手机树读成"11/11 都有身份"） |
| `_mobility_evidence()` 私有签名 | 3 元组 | 2 元组 | 契约只能钉在 payload 上，不能钉在内部函数 |
| 六轴语义 / 阈值 / place_count / 各城判定 | 相同 | 相同 | 好消息：**判定层两树一致**，差异全在**编码层** ⇒ UI 消费规则可以先落，后端多轴随后（与仲裁排序一致） |

## 5 · support contract 规格（四个正交事实 → 字段 → 谁写 → 怎么验）

**契约钉在 `GET /api/v1/destinations/capability` 的 payload 上；逐条标注【针对哪棵树】。**

| # | 事实（轴） | 现在的字段（实测存在） | 缺什么 | 归属 | 验收 |
| --- | --- | --- | --- | --- | --- |
| 1 | **identity**（这座城有没有被命名） | `canonical_destination_id`、`pending_destination_label`、`resolver_query_normalized`、`destination_pending_key`、`pending_label_fidelity`、`destination_state`(仅活线)、`destination_resolution`(catalog/vocabulary/unresolved) | **两树统一"未解析"编码**：活线的 `None`＋pending 为规范；手机树要停止下发 `unresolved:<hash>` 当 id 用 | 后端（C 的 identity closure 之后） | 矩阵 D：`unresolved` 时 `canonical_destination_id IS NULL` 且 UI 不进可选集 |
| 2 | **catalogue_readiness**（本目录对这座城备了多少） | `coverage{6}`、`coverage_detail{state,candidate_count,min_ready,stale,source_kinds}`、`place_count` | 无（够用） | 已具备 | 矩阵 C/E：`HTTP 200` 但 `coverage` 有 MISSING ⇒ **不得** READY |
| 3 | **hydration_capability**（这座城**能不能**被补水） | 只有 `action=START_HYDRATION`（**它把"可补水"和"该补水"混成一格**：北京与厦门都发同一个 action） | 新增布尔＋原因码：`hydratable: true|false`、`hydration_reason ∈ {SOURCE_HAS_NO_ADMIN_ID, ALREADY_IN_FLIGHT, RETRY_LATER, NOT_NEEDED}`；判定源＝`POST /api/v1/catalog-hydrations` 的 202/200-reused 语义 | 后端 | 新增格 J：词表不含的城 `hydratable=false` ⇒ UI 不得显示"加载数据"按钮 |
| 4 | **user_visible_support**（UI 唯一允许消费的那一格） | **现在没有这个字段**；UI 直接读 `capability` | 新增服务端派生字段 `support_state ∈ {LIVE_READY, DEMO_READY, HYDRATABLE_ON_DEMAND, UNKNOWN_RETRYABLE, UNAVAILABLE}` ＋ `label_key`（前端不得自己拼中文） | 后端 | 见下面投影规则；parity 门 |

**`support_state` 的投影规则（必须是函数，不能是约定）**，输入全为上面四轴，逐条可测：
```text
identity 为未解析                                  -> UNAVAILABLE
capability = UNKNOWN_RETRYABLE (仅四值树可出现)     -> UNKNOWN_RETRYABLE   （文案：暂时问不到，可重试；不得进"已支持"，也不得进"不支持"）
capability = READY 且 覆盖各 READY intent 的 source_kinds ⊆ {GOLDEN_FIXTURE, OFFLINE_SNAPSHOT, SIMULATED, REPLAY}
                                                   -> DEMO_READY          （必须显示"演示数据"标签）
capability = READY 且 存在 REMOTE_PROVIDER/LIVE_PROVIDER_CAPTURE
                                                   -> LIVE_READY
capability = HYDRATABLE                            -> HYDRATABLE_ON_DEMAND（标签"需要加载数据"；选中后先 hydrate、重判 READY 才进向导）
```
⇒ **`GOLDEN_FIXTURE` 不是 LIVE**（仲裁压轴）在这套规则里是一个可测分支，不是一句口头纪律；
⇒ 三值手机上 `UNKNOWN_RETRYABLE` 那一支**不可达**：UI 可以先把分支写好，但**规格必须声明它在旧树不会被触发**，
不得为了让它出现而把 `HYDRATABLE` 解释成"可用"。

**服务端 parity 门（不靠两份名单碰巧一样）**：
```text
SELECTABLE = { code : support_state ∈ {LIVE_READY, DEMO_READY, HYDRATABLE_ON_DEMAND} }
UI 渲染为"可选"的城市 code 集合必须 = SELECTABLE 在 UI 名单上的**精确投影**（子集且不漏）
突变红：F 把 UNAVAILABLE 城塞回可选集 → RED ｜ G 把 DEMO_READY 折叠成 LIVE_READY → RED ｜ H 把 200 且 coverage MISSING 当 READY → RED
```
今天的实算：**SELECTABLE = 8 座**（11 减去福州/东京/新加坡），**其中 `LIVE_READY` 为 0 座、`DEMO_READY` 为 0 座**（§3 的 0/220）
⇒ 手机选择器**当前应当**显示 8 座"需要加载数据"＋3 座"不支持/敬请期待"，而不是一句"11 城已支持"。

## 6 · 顺手量到的两个非契约事实（写下来省得别人再撞）

* 这条读路由是**写中性**的：每个状态跑完 22 次 GET 后逐表行数不变（`read_wrote_rows = {}`，两棵树都是）
  ⇒ parity 门可以放心轮询它；**但 `GET /experience` 不是**（已知读时会写），别混用。
* `place_count` 与 verdict **解耦**已被实测：北京 8 行、厦门 0 行 ⇒ 同一个词同一个原因
  ⇒ 任何"数一下 `places.length > 0` 就算支持"的实现都跟这条契约不相容（仲裁也点名禁过）。

## 7 · 我建议并进这张单的三条小活（都不阻塞、都不用改判据）

1. 把活线 `app/anywhere_capability.py:13` 文档那句"three values…"改成与 `:74` 一致（**只活线需要**；手机树自洽，别去动它）。
2. 词表与 UI 名单同源：`_CITY_DISPLAY_NAMES`(16 中国城) 与 `CITY_NAME_BY_SLUG`(11 宣传城) 现在是两份名单，
   交集只有 8 ⇒ 要么宣传名单由后端 `SELECTABLE` 驱动，要么把 FUZHOU/TOKYO/SINGAPORE 从宣传里摘掉。**这条是产品决定，我提给 commander 转仲裁。**
3. `support_state` 落地时**同时**给 `hydratable`，否则 UI 仍然只能从 `action` 反推"能不能补水"。

## 8 · 本件没做、也不声称的

没跑 provider、没调 AI、没开端口；**没查 UI 一行**（`support_state` 的消费规则我写的是契约，不是实现验收）；
**没测恢复代价那条**（`RECOVERY_COSTLY` 的 ≤1 动作/保留草稿要真机或浏览器量，归 D/人视角车道，我不代签）；
没测 AMBIGUOUS/RUNTIME_FAILURE 两格（绊线证明确实没拨号，但**没拨号≠那两格正确**，要它们得让 F/后端用注入 transport 出）；
`_preview.db` 我没能打开（路径不存在），因此**没有**任何关于预览库的结论。

— HARNESS `d291c9dc`，2026-09-23（时间戳由 Python 生成为 +08）
