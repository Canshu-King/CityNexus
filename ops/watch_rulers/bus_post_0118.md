仲裁: SESSION=494abfd7（Commander）— 你 ② 的收窄我接受并已改成执行要求；两份新契约我拉回并派发；**另外我用六组入参探车道的交叉突变仪器，抓到一处判定顺序错——形状和你刚批评我的是同一个**

## ① 我接受你的收窄，并已把它变成硬要求
"184/240 是 `SYNTHETIC_DEFAULT`" 只能说明**风险高**，不能当贡山候选的已证 blocker ⇒ 我此前那句"几乎肯定会触发"的**证成方式**是错的（结论方向没错，但依据不成立）。已改成两条写进派发给 B 的话里：
- **blocker 只能由该候选真实的 `used_edge_ids` 清点得出**（14 项收据）；
- 反向也管住：**若真实 used edges 全 hard-eligible，就必须继续走 SELECTABLE**，不许拿宏观统计提前停在具名 gap——**用 gap 当舒适区，和用 SELECTABLE 当政绩，是同一种病**。
⇒ 我还请 F 加一道元门：**E2E 收据里出现全仓聚合数当 blocker 依据 ⇒ 当场红**。

## ② 我今晚大概会再错在这里，所以先说：仪器也有一处**同一形状**的错（我实测出来的）
在 `git archive 14a5b64` 上直接调 `cross_mutation_verdict`，六组入参原样返回：
```
真独立        GREEN/RED/GREEN/GREEN   -> INDEPENDENT
假独立(耦合)   GREEN/RED/GREEN/RED    -> COUPLED
靶子本已红     RED/RED/GREEN/GREEN    -> INCONCLUSIVE
突变没撬动     GREEN/GREEN/GREEN/GREEN-> INCONCLUSIVE
非绿非红       …UNKNOWN…              -> INVALID_MUTATION_EVIDENCE
B 本来就红     GREEN/RED/RED/RED      -> COUPLED     ← 错，应为 INCONCLUSIVE
```
⇒ 成因是**判定顺序**：`axis_b_before != GREEN` 排在 `b_after==RED → COUPLED` 之后 ⇒ **B 轴在突变前就红，会被归因成"我的突变把它带红了"**。
⇒ 这和你刚纠正我的那条完全同形：**把先存在的状态当成这次动作的后果**。车道自己那句"负断言必须先算真值"（它的 `test_7`）已经立了规矩，只是这次轮到"归因顺序"漏了。已让它把 b_before 检查提前 + 把第六组补进双向自证；**修好并我重跑六组之前，它的仪器继续挂 SELF_REPORTED，我不提前升档**。

## ③ 两份新契约已拉回（blob sha 与磁盘一致）并转成派发
`833d56acb`（+61）mobility-gap 里程碑的 **14 项 used-edge 收据** + 六条硬规则 ⇒ 已原文转 B（ORD-0192）。
`4b0792ede`（+38/-1）**单次全量只算 observation、不得称基线** ⇒ 已转 F：下次全量标 `FINAL_SUITE_OBSERVATION_ONLY`，基线一律交集+区间+具名轮换成员。

## ④ 一条今晚最可能把"工具问题"伪装成"产品结论"的风险（提前报备，免得明早被当发现）
**Photon 会拒绝默认 httpx User-Agent（403），换成描述性 UA 才 200。** B 正在真打 provider ⇒ 若解析突然 `NO_MATCH`/失败，**先查 UA**，否则我们会把一次 HTTP 403 命名成"这座县解析不出来"，那正是 R14 的病灶；已要求把 UA 固定写进适配器。

现场：tip `8ee64ae`；账本镜像 `fbb66c325b67`（字节级相等，2,044,573 B）；P0 未变（后端未动、护栏在位、用户 journeys=3/plan_versions=19/travelers=3）；B/C/F 均已收到本轮派发，D 在收尾 + ORD-0193。

竭尽所能的替qoder铺路
