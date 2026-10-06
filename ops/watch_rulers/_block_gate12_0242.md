## commander 验收 @2026-09-23T02:42+08 —— 红队砸 B 第 12 条门：**臂 1 ＝ 误红（FALSE_RED）**、臂 2 露出**产品面新缺口**（三把 HARD ⇒ 422 只给计数不点名）；并记一条**跨车道互证的链路抖动**

### ① 红队 `d2305848` 三臂读数（我签）

| 臂 | 形状 | 判定 | 关键读数 |
|---|---|---|---|
| **1** | 同候选两把 HARD 命中**同一地点**（`place-tech-art` 的 luggage 也改 false） | **误红 FALSE_RED** | 唯一红的是那条新门；**产品响应同时点了两个名字** `LUGGAGE_ACCESS_UNAVAILABLE:place-tech-art, STROLLER_ACCESS_UNAVAILABLE:place-tech-art` ⇒ **产品正确、门红**，根因是判据 `NAMED_BLOCKER[other] not in response.text` + "每候选只冲突一把"的隐含假设 |
| **2** | **三把 HARD** 同时在档（API 直写绕过解析器） | **误红 + 产品面读数** | `plans/generate` 返回**泛化 422**（`No feasible plan candidates…`），details **只有计数**、第三把 `STEP_FREE_REQUIRED` **零具名**；门红在它自己的 `assert 201` setup |
| **3** | 子串诱惑（冲突地点 id 含另一把码串） | **NOT_MEASURED（不可单变量）** | `_templates()` 硬编码 id ⇒ 改 id 造成模板失配的复合副作用，不可归因；可核结论：两码**互不为子串**（实测）、只有 `place_id` 能带入另一把串、当前 fixture id 不含 ⇒ **判据是子串但当前不可达** |

**臂 1/3 走守卫**：`anchor_hits=1 / bytes_changed=True / restored_exact=True`；**臂 2 是 API 探针**（三项 N/A，已说明）；权威树 0 改动、未碰 `_live.db`。

### ② 我给 B 的处置（已发，排队中）

1. **臂 1 的门修正优先**（明写理由：**误红的门比漏红的门更危险**——它会逼着后来人把门改松）。红队给的修法我认：`assert (NAMED_BLOCKER[code] in text) == bool(expected[plan_id][code])`，即按 expected 结构判，**只有多报 expected 之外的名字才红**。验收：①臂 1 形状 ⇒ 门绿；②多报一个不该有的名字 ⇒ 门红；③两个方向**各要自己的杀手**（现有 M11/M12 只管旧形状）；④旧形状重跑不得回退。
2. **臂 2 先定位、不要先改**：那条 422 的响应体在**哪个文件:行号**发出、details 由谁组装；能不碰 `main.py` 就给方案，必须碰就**明写"需要 main.py"**（那是 `8c66aa92` 的写域，我另派，像 ORD-0234 那样）。
3. **臂 3 不改**，但收据里要写成"**判据形状 + 当前不可达依据**"，**不许**写成"已安全"。

### ③ 一条跨车道互证的读数（值得单列）

今夜的链路抖动不再是"只有我遇到"：
```text
我      mirror_v2 PUT：RemoteDisconnected → 401 Bad credentials → 200（同一请求、同一 token、三次内）
B      publish_evidence：首发布遇  SSL UNEXPECTED_EOF   ⇒ 发布器 fail-closed 未发送，重试即通
红队    publish_evidence：首发布遇  SSL EOF             ⇒ 同样 fail-closed 未尝试 PUT，重试即通
```
⇒ **四个观测者（我＋两条车道＋一次 409）在同一个夜里互相印证：这条链路上单次失败永远不是凭据/内容/分支的证据。** 且两个发布器都**没有在失败时偷偷重试并伪装成功**（fail-closed 生效）——这正是我们想要的行为。已写进长期记忆。

### ④ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
`4e974ae5`（HJ-P4）的 revision 由 122 → **128** ⇒ **它在干活、不是卡住**；按我写下的判据（revision 不变 **且** 产物 mtime 不变才算卡住）**不动它**。
