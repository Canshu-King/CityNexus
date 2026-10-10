仲裁: SESSION=494abfd7（Commander）— 18:4x 现场换代 + 北京打通的实测数 + 一条我们吃掉用户数据的 P0

**1) 预览已换代，北京在手机上有货了（全程未用 `demo/reset`）**
- 后端树 `1874a41 → **53fe8e8**`；服务包 `index-AkCV4A2Q.js → **index-6vq1iijw.js`（`/` 200、bundle 1,201,865 B）；
  旧 dist 备份 `dist_bak_1825/`，DB 一致快照 `live_snapshots/live_pre_tip.db`（`integrity_check=ok`）。
- 北京目录用**新写的增量脚本**灌进真库（只插不删、列按 `PRAGMA table_info` 自适应）：`places +8 / city_services +5`。
- **公网端到端**（云→4782→4781/8693，探针行程是我自己建的 `516afb05`，没动用户的 `94669bae`）：
  - `GET /places?city_code=CN-BEIJING` → **200 / 8 个**（故宫·后海·护国寺·南锣鼓巷·前门·全聚德·颐和园·天安门）
  - **默认路径 `plans/generate {}` → 201 / 3 个候选 / `selectable=True` / 活动数 8·8·7 / 1.38 s**
  - **AI 卡片口径（把 `/places` 前 8 个 id 原样发出）→ 422**：
    `GENERIC_COMPOSE_INFEASIBLE:GENERIC_COMPOSE_INFEASIBLE:PLACE_CLOSED:…nanluoguxiang|…houhai|…forbidden-city`
    且 **`details: null` 在 `53fe8e8` 仍然成立** ⇒ **R5 点名的契约缺陷在这条路上没死**；
  - **同一行程只发 5 个 id → 201 / 1 个候选**
    ⇒ 给 **ORD-0111** 精确边界：`min(3, len-1)` 只试 8/7/6，**6 拒 5 成**，差的正是**第 4 档**。
    "砍得不够深就宣布不可行"——不是北京没救。
- 用户侧正向证据：18:36 直读 `_live.db`，CN-BEIJING 出现 **`7dfdac2c… status=PLANNED`**
  —— 换代之后手机上真的排成了一趟北京行程。

**2) 我们自己吃掉了用户的数据（新 P0，已派 ORD-0125）**
「重置到场景起点」= `POST /api/v1/demo/reset` = `services.py:106 reset_all()` **无范围删 52 张表**（`journeys` 第 49 项）。
预览日志里 `POST /api/v1/demo/reset → 200` 共 **9 次**；**我本人 12:47 的 M1 走查按过它**。
用户自建的两条行程（`e833311d 天津`、`bca6a834 平潭县`）在 18:14 的一致快照里已经不存在，**不可恢复**。
修法已下令：删除范围只准覆盖 seed 派生行 + 响应带 `deleted_demo_rows / preserved_user_rows` 诚实计数 +
先红后绿（建用户行程→按 reset→它还在）+ 可杀突变。**我自己这条错误也进了账本，不藏。**

**3) 请你裁（R11，新）：同一棵树同一库同一分钟，两个口径互相打脸**
`capability?query=北京` = **HYDRATABLE / COVERAGE_INCOMPLETE**
（六轴 `attractions READY 4/3 · food READY 3/3 · nightlife PARTIAL · lodging MISSING · mobility READY · booking READY`），
而同一时刻**默认路径已经能出 3 个 selectable 候选**。屏幕现在会说"这城市还要灌数据"，系统其实能排。
- **A（我倾向）**：把"可规划"与"覆盖完整"拆成两个字段，各自显示、不互相冒充；
- **B**：`min_ready` 只按"可规划所需轴"判，lodging/nightlife 缺失只降级成 PARTIAL 提示；
- **C**：维持现状（覆盖不足即 HYDRATABLE，即使已能出可选方案）。

**4) R10 追一个实证（等你裁）**：`capability?query=云和县` → **UNAVAILABLE / NO_CANONICAL_IDENTITY**，
`canonical_destination_id = unresolved:8fccf2bbf123e3df` —— 哈希身份仍在被持久化/回显；
而今天(18:36)库里那条自建行程 `city_code='CN-云和县'` 说明**任意字符串照样能当 city_code 进库**。
已派 ORD-0127（取证 + Photon 候选出口，不许自己换哈希方案）。

**5) 你的 5758628612 已执行**：ORD-0124 拆两阶段 ⇒ 新立 **ORD-0130 = 0124-A 只读侦察**
（独立只读子代理，立刻并行，不占 D 写域、不改 `package.json`、不建 UI commit；
交付 `UI_DONOR_SCOUT_REPORT.md` + `UI_DONOR_PORT_MATRIX.md`，四 donor、source-level、AGPL 只看不搬）；
**0124-B port 保持 HELD**，等 D 收口手机 P0/P1 后由 D 逐组件移植。

**6) 车道与验收**
- **ORD-0119 Harness 复活 ACCEPTED**：249 = 198/38/13（09-15 快照）→ **234/2/13**（今天的树）＝ 37/38 旧红是集成造成；
  `osm.py` 冻结语料 7/7 FULL 且冲突优先；`/capabilities/catalog` 与 `…/accessibility-evidence` **运行时 404**。
  剩一条真缺陷 **`d6b`：缺证据被当硬阻塞**（`ACCESSIBILITY_UNVERIFIED / NEEDS_LIVE_EVIDENCE`，红了 6 天没登记）
  —— 与 **R5 同族不同物**（R5 管覆盖度，这条管证据缺失度），已令 ORD-0128 先量分母再来请裁归属。
- **HJ-P1** 三条：`R3-4` 假离线死屏（`navigator.onLine=true` + health 三次 200，屏显"网络不可用"、**可见按钮 0**）、
  `R3-6` 建承诺 404 屏幕零反应 → **ORD-0126（D）**；`R3-5` 未来行程被判 COMPLETE 只记不修。
  其"两条隧道全死"我已更正并**归属到我头上**：`18:22:44–18:23:12` 那 28 秒的重启是我干的，
  另一条 `unexpected-somerset…` 确实死（旧登记），在用的 `fonts-facilities…` 活着（18:24 两轮全 2xx）。
- **还没验成的**（不当作验过）：新包上 AI 卡片"例子跟着目的地"我在手机上走不到那趟行程（`text=北京` 只命中不可见 `<li>`）→ 交 ORD-0129 手机复验；
  地图手势在新包只是"带到明处"未修；M1→M4 在新包**没重走**（只确认舞台 8 个动作在位、console 0 报错），
  因为按「重置/准备」会改写用户此刻 ACTIVE 的舞台——正是 ORD-0125 的因，我不重复犯。
- 后端全量门禁这一轮我**没重跑**（换代吃掉 15 分钟），下一次巡检报精确红绿分母。

**派单一览**：0125(E, P0 重置删全库) · 0126(D, P0 失败上屏+出口) · 0127(F, 县城身份与出口) ·
0128(Harness, EXP-002 + d6b 分母) · 0129(HJ-P1, 新包手机复验) · 0130(只读侦察)。
