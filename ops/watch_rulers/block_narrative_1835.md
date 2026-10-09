### commander 亲测 @2026-09-21 18:3x —— 预览换代到 `53fe8e8`、北京目录增量灌进真库、"重置按钮删全库"定性为 P0

**先说要紧的**：手机上「没有生成可行方案」有**第二个因**，不在排程里，在环境里——
预览后端一直钉在 `1874a41`，它的 `data/mock/places.json` 只有 **CNX-DEMO 8 个点**（tip 是 8+8），
它的 `_live.db` 里 **CN-BEIJING 地点数 = 0**。屏幕发的是 `GET /places?city_code=CN-BEIJING → 0 个 id`
⇒ 老包 `<2 就不发请求` ⇒ 什么也没跑、只说"没方案"。**这一条今天修了。**

**换代动作（18:22–18:26，全程有备份，无一处删用户数据）**
- 后端树 `_qoder_cmdr_gate_20260921`：`1874a41` → **`53fe8e8`**（本地 `git checkout`，无网络操作）；
- **一致快照**（WAL 安全的 `sqlite3.backup`，不是裸拷）：`_qoder_cmdr_ref_20260921/live_snapshots/live_pre_tip.db`，
  `integrity_check = ok`，54 张表，用户 3 条行程在内；
- 灌数据用**新写的增量脚本** `live_checks/seed_city_catalog.py`：按 `seed_demo()` 会写的行**只插不删**、
  列按 `PRAGMA table_info` 自适应（`places` 根本没有 `created_at`，第一版就死在这）：
  **places +8、city_services +5**，`integrity ok`，18:21 三条行程（`22222222` ACTIVE / `94669bae 北京` /
  `bf8beccf 云和县`）**一条不少**；**没有调 `demo/reset`**（见下）；
- 前端：新包在 tip 树里真建（`node_modules` 从集成树**整份复制**进来，不是 junction；依赖与
  `d76992a` 起未变，已核 `package.json/lock` 无 diff）→ `vite build 4.27 s` →
  dist 换 `/D:/moodle/_qoder_preview_20260920/dist`，旧包备份 `dist_bak_1825/`；
  公网 `/` 现在返回 **`index-6vq1iijw.js`**（1,201,865 B，fetch 200），预览专用自退 SW 已盖上；
- **停机归属**：`:8693` 重启窗口 **18:22:44–18:23:12（约 28 s）**是我干的，那段时间任何车道报"连不上"都是因，不是产品缺陷。

**换代后的公网实测（云 → 4782 → 4781/8693，全部 `53fe8e8` + 灌完的真库；探针用我自己新建的 `516afb05`，没动用户的 `94669bae`）**
- `GET /places?city_code=CN-BEIJING` → **200 / 8 个**（故宫、后海、护国寺小吃、南锣鼓巷、前门大栅栏、全聚德、颐和园、天安门）；
- `capability?query=北京` → `canonical=CN-BEIJING`，**HYDRATABLE / COVERAGE_INCOMPLETE**，
  六轴 = `attractions READY(4/3) · food READY(3/3) · nightlife PARTIAL · lodging MISSING · mobility READY · booking READY`；
- **默认路径**（用户那句"直接生成方案"）→ **201 / 3 个候选**，`selectable=True`，活动数 **8 / 8 / 7**，1.38 s；
- **AI 卡片口径**（把 `/places` 前 8 个 id 原样发出去）→ **422**，正文
  `GENERIC_COMPOSE_INFEASIBLE:GENERIC_COMPOSE_INFEASIBLE:PLACE_CLOSED:place-beijing-nanluoguxiang|…houhai|…forbidden-city`，
  且 **`details: null` 在 `53fe8e8` 仍然成立**；
- **同库同行程只发 5 个 id → 201 / 1 个候选**。
  ⇒ 给 **ORD-0111** 补精确边界（不改它的单，只补数字）：`min(3, len-1)` 只试 8/7/6，**6 拒 5 成**，
  阶梯差的就是**第 4 档**；这不是"北京没救"，是"砍得不够深就宣布不可行"。

**新发现的 P0（不是排程、不是覆盖度，是数据生死）**：舞台按钮「重置到场景起点」= `POST /api/v1/demo/reset`
= `services.py:106` `reset_all()` **无范围删 52 张表**（`journeys` 是第 49 项）。
预览访问日志里 `POST /api/v1/demo/reset → 200` 共 **9 次**；**我自己 12:47 的 M1 走查按过它**——
用户早上那两条自建行程（`e833311d 天津`、`bca6a834 平潭县`）在 18:2x 的真库里已经不在了，
我按"我们自己犯过"定级并派 **ORD-0125**（删除范围只能覆盖 seed 派生行 + 诚实计数 + 先红后绿 + 可杀突变）。
`live_snapshots/live_pre_tip.db` 与 18:05 的 `_live_copy.db` 里那两条行程的**行还在**，
**18:4x 我做一次增量回灌**（只在 id 缺失时插回 journey/traveler/constraints，绝不覆盖现有行），成不成如实报。

**县城口径（用户此刻正在手机上试）**：`capability?query=云和县` → **UNAVAILABLE / NO_CANONICAL_IDENTITY**，
`canonical_destination_id = unresolved:8fccf2bbf123e3df`——哈希当持久身份这件事**还没被禁**（已派 **ORD-0127** 取证 + 出口，等 **R10** 裁）。
同一时刻库里还有 `city_code='CN-平潭县'`：**任意字符串照样能进库**，与 0106 修的拼写门是两件事。

**验收与更正**
- **ORD-0119（Harness 复活）ACCEPTED**：249 = 198/38/13（09-15 快照）→ **234/2/13**（今天 `eef24d9`）＝ **37/38 旧红是集成造成**；
  `osm.py` 冻结语料 7/7 FULL 且冲突优先不被正向标签洗白；`/capabilities/catalog` 与
  `…/accessibility-evidence` **运行时 404**（不再靠 grep 推断）；两次自我否证写进正文（`data/` 漏拷导致假 12 红）。
  放行 **EXP-HARNESS-002 + d6b 量化**（**ORD-0128**，含"允许整份复制 `node_modules`、禁止 junction"）。
  `d6b`（**缺证据被当硬阻塞**，`ACCESSIBILITY_UNVERIFIED:p1 / NEEDS_LIVE_EVIDENCE:p1`，红了 6 天且没登记）
  与 **R5 同族不同物**：R5 管覆盖度，这条管**证据缺失度**——等 ORD-0128 的分母出来我再请裁归属。
- **HJ-P1（ORD-0120）**三条发现收单：**R3-4 假离线死屏**（`navigator.onLine=true` + health 三次 200，屏上"网络不可用"且**可见按钮 0 个**）与
  **R3-6 建承诺 404 屏幕零反应**（`message_key` 有、前端没用）→ 一起派给 **ORD-0126（D）**；
  **R3-5 未来行程被判 COMPLETE** 只记不修。**更正其"两条隧道全死"**：`unexpected-somerset…` 确实死（旧登记），
  `fonts-facilities…` 活着（18:24:02 与 18:24:44 两轮全 2xx），他们落在我的重启窗口里的那部分算我的因——已写进 **ORD-0129**。
- **我没能验成的**（别当成验过）：① 新包上 AI 卡片的"例子跟着目的地走"——手机上从向导进不去那趟北京行程
  （`text=北京` 只命中一个**不可见** `<li>`），这条交给 ORD-0129 的手机复验；② 地图手势：新包只是"把缺陷带在明处"，
  HJ-P3 找到机制但**未修**；③ M1→M4 完整链路在新包上**没重走**（只确认舞台面板 8 个动作都在位、console 0 报错），
  因为按「重置/准备」会改写用户此刻 ACTIVE 的舞台——这正是 ORD-0125 的因，我不重复犯。

**请 GPT 裁（R11，新）**：同一棵树、同一个库、同一分钟，`capability=HYDRATABLE（lodging MISSING / nightlife PARTIAL）`
与"默认路径已经能出 **3 个 selectable 候选**"**并存**。现在屏幕会说"这城市还得灌数据"，而系统其实能排。
要哪种口径：**A** 把"可规划"与"覆盖完整"拆成两个字段（前端各自显示，不互相冒充）；
**B** 把 `min_ready` 只按"可规划所需轴"判（lodging/nightlife 缺失只降级为 PARTIAL 提示）；
**C** 维持现状（覆盖度不足即 HYDRATABLE，即使已能出可选方案）。
我倾向 **A**：`capability` 回答"有没有货"，`plans/generate` 回答"能不能排"，两者今天在同一块屏上互相打脸。
