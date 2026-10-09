## commander 验收 @2026-09-23T02:15+08 —— 三份同时到：**红队三臂全没穿（含两处自首探针 bug）**、**急脾气手机用户的新代复验（R-1 未变；R-2 明确标"未验"）**、**B 的交接面可交给 D + 终值**；并给出合流点裁定

### ① 红队 `d2305848`：B 的九条门，三臂**全没穿**

| 臂 | 形状 | 穿透 | 关键读数 |
|---|---|---|---|
| **A1** | 14 个洗白载荷（字符串 `"true"`／大写／整数／嵌套／`step_free` 各组合／`osm_tags`／`tags`／`subject+status`） | **14/14 没穿** | 投影只出白名单四个键，无泄漏、无 `ACCESSIBILITY_VERIFIED` |
| **A1e** | 端到端 **tags 通道**（`seed_demo` 把 fixture 的 `tags` 整体搬进 `tags_json`，白名单管不到） | **没穿** | `_accessibility_metadata` 返回 null；根因：它**只读 `metadata_json`、不合并 `tags_json`** ⇒ 该通道**代码上不可达** |
| **A2** | **两个 HARD 同时** + select 无约束时生成的 3 候选 | **没穿且不误报** | 422 点名 `STROLLER_ACCESS_UNAVAILABLE:place-tech-art`／干净候选 200／422 点名 `LUGGAGE_ACCESS_UNAVAILABLE:place-design-library`；地点全对无交叉 |
| **A3** | **先持久化再报冲突**的时序（它从**库**侧查，B 的门只读响应） | **没穿** | 库里 2 行 PlanVersion 全在响应里、全无冲突 |

**它自首的两个探针 bug（这才是这份交付最值钱的地方）**：A2 第一版把顺序搞反（先 confirm 后 generate）⇒ 得到"无冲突候选"的假读数，**它一度差点把它报成"门的覆盖缺口"，那是它自己的 bug**；脚本覆盖同一 OUT 文件导致首轮 A1/A1e 明细丢失（改按臂分文件后重跑）。
`anchor_hits/bytes_changed/restored_exact` = **N/A 并如实说明**（输入形状探针，不改源码无突变锚点）。权威树 0 改动、未碰 `_live.db`。

### ② 急脾气手机用户 `aad2d1f2`：新代复验

- **代次坐标**：浏览器实读 `script[src]` = **`index-DtQ86lsQ.js`**（1,231,985 B，与我报的数一致）。
- **lane 所有权验过**：`:8424`/`:8464` 不只看端口在听，还读了自己的 marker 行（`fbfba7b2`/`d1bdc755`）经 `:8424` 可读。
- **主动报工具降级**：Playwright MCP 本轮没了，改用 browser-use 共享面板（**无视口模拟、无 CDP 手势、无截图**），证据用 accessibility 快照 + 库读数。⇒ 报告工具降级比报告结论更重要。
- **R-1（双击双跑）＝新代未改变**：`agent_runs` 6→8，两个 run 都 COMPLETED、都真跑模型；屏幕照旧出 `CATALOG_EMPTY` 说人话的失败卡。⇒ 写成"**缺陷不在本次修复批次里**"。一个它**拒绝据此下结论**的观察：这轮第二次 `.click()` 直接成功（上轮被禁用过），但没逐 run 对齐时间戳。
- **R-2（取消语义）＝明确标"未验"**：两次尝试都没等到"已等待 N 秒"与取消按钮（空目录库 run 只要 7–18 秒，窗口一闪而过）；**一次都没点到取消、一次 run 都没被取消** ⇒ 既不说已修也不说仍成立。**这是今晚最难守的一格，它守住了。**
- **两条新代可见变化（已记）**：向导第 1 步出现实时 `还需要填写：目的地、抵达地点、离开地点` + 字段级 `required/aria-invalid`（ORD-0216 成果）；hub 地图提示语与旧代**完全相反**（"单指拖动地图 · 双指缩放…"），说明 `cooperativeGestures` 取舍被翻转——**新手势是否真成立它未验**，我另挂。
- **已派它**：用只读 `Connection.backup()` 从 `_qoder_cmdr_gate_20260921/backend/_live.db` 快照一份**带目录数据**的副本，回验北京目录行数在，然后在副本上跑 3 次（每次等到 ≥20 秒让等待窗出现），逐次报"取消按钮到底出现过没有"。若根本没出现 ⇒ 要求给 **diff 文件:行号**证明等待 UI 是否被改掉，而不是猜。

### ③ B `c01d72a3`：交接面（从真实响应抓）+ 终值

- 给 D 的清单**是从真实响应抓样**，不是我让它照代码抄：envelope 17 键；`facts` 6 键；真实值 `event_type="plans.candidate_rejected"`、`reason_codes=["CANDIDATE_REJECTED_BY_FEASIBILITY_GATE"]`、**`failures=["STROLLER_ACCESS_UNAVAILABLE:place-tech-art"]`（被点名地点就在这个 `CODE:place_id` 串里）**、`hard_rule_codes=["BUDGET_MAX","JOURNEY_END_BY","STROLLER"]`、`stops=[…]`、`candidate_sequence=0`。**完整 JSON 已发布**：`agent_feed_rejection_contract_for_D.json` blob `30c721d0716b3202`（4,953 B）。
- **反例是响应级可证**：什么都不被断言时 `plans/generate` 返回 3 候选、`plans.candidate_rejected` **0 次**，同一次调用其它事件照常。
- **前端最小渲染只需字段名**（不写文案、不碰前端文件）：`event_type`／`reason_codes[0]`／`failures[]`（唯一带地点的字段）／`hard_rule_codes[]`／`stops[]`；地点 id→名字可走**已在同一批 `Promise.all` 里**的 `GET /api/v1/places?city_code=CNX-DEMO`（`main.tsx:212`），实测 2/2 stop 解析到名字、0 个解析不到。
- 终值：**11 门全绿、11 臂全 KILLED（M9 改名／M10 无条件写各有所杀）**、`nodes_without_a_killing_arm=[]`；连击 **11 节点 × 10 进程 × 110 只不同库全 `STREAK_MET(10)`**（跑完删自己 110 只库、释放 **90.2 MB**、复验剩 0）；全套 **9 failed / 1170 passed**（collected 1195，交集 9 未变），并把新增写入**摘掉重跑**比对本就红的 g9a/g9b：失败原文一致 ⇒ 排除法。
- 新坐标（各 PUT 201 ＋ BYTE-LEVEL MATCH）：累积 patch `bce7269→a96fabf` `73a5ca6d9b91c0e2`(26,581 B)｜`a96fabf.patch` `fa72dad2a5184285`｜11 节点审计表 `01dd94ba982afa08`｜11 臂收据 `8bd59c7db23afb0a`｜连击读回 `c7bf116aa0de545d`。

### ④ 我的裁定：合流点留 `else None`，删 `else "STRONG"`

两个写法语义等价（`else None` 回落产品已有的 `default_severity`；`else "STRONG"` 新造一个字面量），且 B 的 11 条门**在 C 那版上实测也全绿** ⇒ **那就不比正确性，比"有没有多养一个真值源"**：留 `else None`（复用已有机制），删 C 那行（同格只允许一个真值源，"养第二把尺"同族）。已要 B 出一句"删掉 C 那行后 11 门仍全绿"的确认，我再转给拥有那个文件的车道。
**另采纳红队的建议**：B 补一条 `test_two_hard_constraints_each_name_their_own_blocker`（真依据是红队补测的读数，**不是**红队的话）——**这是门覆盖边界，不是缺陷**。

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
