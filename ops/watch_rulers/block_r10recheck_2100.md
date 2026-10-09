### SESSION=494abfd7 · ORD-0151 前提被我自己的探针推翻一半 + ORD-0154 收一半驳一半 + tip 漂移通告 @本机钟 21:0x

`STATUS: COMMANDER-RECHECK-R10-OWNER | 树：`git archive d26933c`→`_qoder_cmdr_ref_20260921/tree_head`（权威树 0 改动）| 库：`live_pre_tip.db` 的两份副本（`head_r10_recheck.db`/`head_r10_urls.db`），**未碰 `_live.db`** | 传输：`TestClient`（不起端口）| 解释器 `CityNexus/.venv` 3.12.14 | `REAL_CITY_ENABLED=true` + `MODE=live`、四把凭据 unset | evidence `live_checks/r10_owner_recheck.py`+`.out`、`r10_url_names.py`、`hydration_identity_trace.txt` | 生产码 0 改动 |`

#### ① 我撤回：capability 与 catalog-hydrations **没有**各算一遍 identity（我连说两轮，仲裁已写进 R10）
- `CHO.resolve_destination is AC.resolve_destination → **True**`（同一函数对象，不是同名）；定义处 `backend/app/anywhere_capability.py:165`；
- hydration 侧两个调用点：`catalog_hydration_operations.py:293`（受理时算幂等指纹）、`:527`（作业时 `RESOLVING_DESTINATION` 阶段）；`:37` 就是 `from app.anywhere_capability import …`；
- 实测三例两条端点返回**同一个** canonical：`云和县`/`贡山独龙族怒族自治县`/`zzxqvw-不存在县` 均 `pending:<原文>` 两边一致；
⇒ 仲裁 R10 的"两条 endpoint 必须共用一个 resolver core"这个不变量**今天结构上已经满足**；"一条能解析、另一条说 NO_REGISTERED_SOURCE"这种自相矛盾**今天复现不出来**（我 20:3x 说"我今天已经实测到这一对"——那对其实是"能力说 UNAVAILABLE / 作业说 NO_REGISTERED_SOURCE"，**同一次解析的两句话**，不是两套身份）。
- 真正要修的仍是那一个核心：它**从不问 provider**。它自己的 docstring 写着 "using only sources already in this process"（`anywhere_capability.py:166-173`）；模块内 `photon/overpass/geocoder` 只出现在 `:247` 的 provenance 分类集合里。
- 出站计数（httpx _tripwire_，命名后不误导）：capability 与 hydration 各 **1 条**，且那 1 条是探针自己 `GET/POST http://testserver/…` ⇒ **provider 调用 0**。

#### ② 我把自己 ORD-0113 块里的两处行号按当前 tip 重测了一遍（结论成立，行号漂了）
- 全仓 `def get_session` **只有一处** = `backend/app/db/session.py:710`，体是 `try: yield / finally: session.close()`
  ⇒ 我 20:0x 写的 `:696-701` 在 `e9efec6` 上成立，在 `d26933c` 上是 **`:710-715`**，"finally 跑到"这句**照旧成立**；
- `main.py` 在 `2d3b3fb` 与 `d26933c` 是**同一 blob `cb325aa6…`**（⇒ 两 tip 之间行号不可能漂）；
  全文件 `except OperationalError` **只有 1 处 = `:5907`**，`:5909` 判 `"database is locked" / "database is busy"`
  ⇒ 我原写的 `:5808-5811` 更正为 **`:5907-5909`**；"twin 是唯一锁兜底"这条**加强成立**（1 处，不是"只有它优雅降级"，而是"整个 main.py 只有这一处捕获"）；
- 顺手钉两个可能被误读的点：`main.py:162` = `from app.db.session import SessionLocal, ensure_schema, get_session`，
  `Depends(get_session)` 在 `main.py` **136 处**；`main.py:8455-8460` 实读是 `SolverV2Option(option_key=f"KEEP:{item.id}", …)` 重规划求解器。
- **记一笔我自己的过程错**：我一度以为车道递过一条"`get_session` 是 `:8458` 空壳、`Depends` 计数为 0"的更正，并据此要开一张质询单。
  我在账本里**找不到**这段原话，而上面的 grep 读数也证明该说法不成立 ⇒ **指控不成立，那张单作废**（预留的 ORD-0159 不使用、不派任何人）。
  教训按我 19:5x 那条自纪执行：**没找到原文就说没找到，不许把转述当交付去驳。**

#### ③ ORD-0151 第 1 步（`23bdf9f`）：方向对、**但和仲裁刚落地的两句话打架**（要裁）
实测落库行（`catalog_hydration_operations`，列 `canonical_destination_id` 在 `db/models.py:1174` 是 **NOT NULL**）：
```
('pending:云和县',                 '9b0dda148eefd12bfd6784c87d5e0724', 'UNAVAILABLE', 'NO_REGISTERED_SOURCE')
('pending:贡山独龙族怒族自治县',      'ca3b5b6a5da9c5b02868907548bc76c3', 'UNAVAILABLE', 'NO_REGISTERED_SOURCE')
('pending:zzxqvw不存在县',          '8d34605bff8f3155848581d2a09f57ad', 'QUEUED',      None)
```
- 好消息：禁 hash 这条**已达成**（同一测试里新增 `[0-9a-f]{12,}` 反摘要断言，回归成 hash 会红）；
- 冲突 1：仲裁 5760650272/`docs/anywhere_capability.md` 要 no-match/runtime-failure 两类 **`canonical=null`**——而这一列 NOT NULL 且直接进 `fingerprint`；
- 冲突 2：仲裁 R10 原文"raw text is user input, not identity"——而 `pending:<原文>` 正是把用户原文钉进身份列与幂等键；且 `zzxqvw-不存在县` 被归一为 `pending:zzxqvw不存在县`（**连字符被吃掉**，原文被改写）；
- 我的第三条路（请仲裁点头我就写进 0151 验收）：响应 `canonical_destination_id=null` + 独立可读字段 `pending_destination_label`；作业行的幂等键改用**具名相关 token**（`destination_pending_key`，注释里明写"correlation only, never identity"），并把 `pending:` 从"身份"降级为"标签"。

#### ④ 一条产品真相（今天就能上屏的那种，与用户"装死"投诉同源）
未解析县的 `recommended_action` 实测是 **`CHOOSE_ANOTHER_DESTINATION`** ⇒ 对一个**真实存在**的县，产品现在对用户说的是"**换个目的地**"。
仲裁新令要 `HYDRATABLE + PREPARE_DESTINATION`。这一句在 ORD-0151 修完之前**每次都会**把用户劝退。

#### ⑤ ORD-0134②（`4176e7b`，lane D）代码级签收，门禁我**没有**复跑
实读 diff：`MapPanel.tsx` 删 `cooperativeGestures: true`（+注释里写明 12/12 单指滑动页面 0px 的红基线）、hint 文案由"两指拖动"翻成"单指拖动地图"；`styles.css +10` 给 `.v8-map-caption/.v8-map-gesture-hint/.v8-map-tile-notice` 上 `pointer-events:none`；`review/ord0082_0087_kill_drivers.py +33`。
⇒ 机制与我要的一致（**ACCEPT-CODE**）；它报的 27/27 与 killG 3/3 KILLED 是它自己跑的，**我没复跑 e2e**；真机复验仍挂 ORD-0129/0147（用户此刻看的 `:8693` 前端仍是 `index-DDgOVfG6.js`，未含此改）。

#### ⑥ tip 漂移通告（对所有 `if_head: e9efec6` 的单生效）
权威树现为 **`d26933c`**（`integration/frontend-apple-pass1`），`e9efec6` 之后 5 笔：
`2d3b3fb`（AI 卡尺寸/页脚）→ `23bdf9f`（0151 第 1 步）→ `4176e7b`（0134②）→ `b2becb5`（booking 节点自钉前提）→ `d26933c`（账本追加工具自证）。
各车道交付前请按**当时实读 tip** 重测行号；我账本里的 `main.py:5808-5811` 与 `session.py:696` 已在 ①② 更正。

status: commander 亲测交付（① 自撤 R10 前提；② ORD-0154 收①驳②；③ `pending:` 与 canonical=null/NOT NULL 双冲突上呈；④ 未解析县现在答"换个目的地"；⑤ 0134② 代码级签收未复跑；⑥ tip 漂移）
evidence: `D:/moodle/_qoder_cmdr_ref_20260921/live_checks/`（r10_owner_recheck.py、r10_owner_recheck.out、r10_url_names.py、hydration_identity_trace.txt、cho_head.py、models_head.py、arbiter_docs/ 三份契约原文）
