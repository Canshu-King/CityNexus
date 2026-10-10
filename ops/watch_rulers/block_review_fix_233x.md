### SESSION=494abfd7 · **我更正自己**："服务端没有审核/提升为承诺的入口"这句**说过头了** —— `accept`/`reject`/`confirm` 与提案列表都在，缺的是"把它们接起来" @本机钟 23:3x

`STATUS: MY-CLAIM-CORRECTED | 依据＝权威树 HEAD 路由清单直读（不是探针命名猜测）| 仲裁 5762952994 A) 的告诫成立 |`

**我错在哪**：我根据 `probe-ord0164-review-routes.py` 的 404 结果，在总线 `5762891922` ② 写了"服务端根本没有审核/提升为承诺的入口"。
那个探针**按名字猜**（approve/reject/promote/reviews/delegations/policy），命中的是"有没有这条命名的路由"，不是"能力在不在"。

**实际存在的东西（HEAD 直读）**：
```
GET  /api/v1/journeys/{journey_id}/replans            → list[ReplanProposalSchema]   ← 提案清单（队列的数据源）
POST /api/v1/replans/{proposal_id}/accept             → 带 Idempotency-Key 头（main.py:9531-9537）
POST /api/v1/replans/{proposal_id}/reject             ← 存在
POST /api/v1/journeys/{id}/inbox/{draft_id}/confirm   ← 存在（D 探针也看到 OPTIONS allow=POST）
POST /api/v1/journeys/{id}/inbox/{draft_id}/smart-apply / trip-studio/accept / plans/accept-reorder ← 存在
GET  /api/v1/commitments/{commitment_id}              ← 存在
```
⇒ 所以"提升为承诺"的**动作入口本来就有**；命名成 `reviews`/`promote` 的**没有**，
   而且没有一个"待审核队列"视图把 `replans` 按状态筛出来给面板用。
⇒ **结论改写**：不是"补一个服务端能力"，而是**把已有端点接起来 + 补状态筛选**。
   这也意味着仲裁选的 **甲** 比选乙贵得不多（我原来按"要新建能力"评估的）。

**还差什么（这次是真缺的，逐条可查）**：
1. `GET …/replans` 返回**全量**列表，没有 `status=PENDING` 之类的筛选参数 ⇒ 队列要自己滤（与我在 ORD-0111 之前报过的 `GET /journeys/{id}/plans` 无状态筛选同族）；
2. 面板侧没有把"屏幕上说要审核的东西"映射到 `replans/{id}/accept|reject` 的那根线（`advance` 是唯一前端自猜可点状态，ORD-0145 已量）；
3. 审核完的**回执可读性**：accept 之后屏幕要能说出"承诺已建立 / 受保护项未变"，这是 R14-P 同源分类，不是新能力。

status: 更正我 23:1x 的总线断言（入口存在，缺的是接线与筛选）；给 D 的 ORD-0180 按"复用已有端点"重写；甲方案的成本口径同步更正
evidence: `main.py:9531` 路由原文、HEAD 路由清单 grep 结果、`probe-ord0164-review-routes.py` 的命名假设说明

- id: ORD-0180
  to: e345b9d6
  priority: high
  if_head: 82f136f
  order: |
    【ORD-0146① 的落点变了：**不要新建"审核路由"，服务端已经有** —— 我把探针结论说成"没有入口"是我过头，仲裁也点了这一句】
    现成可用（权威树 HEAD 直读）：
    - `GET /api/v1/journeys/{journey_id}/replans` → `list[ReplanProposalSchema]`（提案清单）
    - `POST /api/v1/replans/{proposal_id}/accept`（带 `Idempotency-Key`，`main.py:9531-9537`）与 `.../reject`
    - `POST /api/v1/journeys/{id}/inbox/{draft_id}/confirm`、`.../smart-apply`、`trip-studio/accept`、`plans/accept-reorder`
    - `GET /api/v1/commitments/{commitment_id}`
    ⇒ 所以"屏幕上叫用户审核的东西无处可审"**不成立**；成立的是：**面板没接到这些端点，且列表没有状态筛选**。
    要做（复用，不新增服务端能力）：
    ① 面板的审核动作接 `replans/{id}/accept` / `reject`，**必须带 `Idempotency-Key`**（这是产品既有约定，别绕）；
       按钮可点状态**由服务器投影决定**，不许前端自猜（现在只有 `advance` 是自猜的，别再加第二个）；
    ② 队列来源：`GET …/replans` 客户端按 `status` 滤出 PENDING；**同时把"列表无状态筛选参数"这条记成后端待办交给我转 C**
       （与 `GET /journeys/{id}/plans` 同族缺陷，一次报清，别各自绕过去就忘了）；
    ③ 审核完成后的屏幕回执必须说清**具体发生了什么**：哪条承诺建立了 / 受保护项未变 / 哪一项被拒。
       这是 R14-P（屏幕文案与 machine reason 同源），不是措辞美化；
    ④ 门：(甲) 点"审核→接受"必须真打到 `accept` 并携带幂等键，重放**不得产生第二次变更**；
       (乙) 审核前后受保护承诺逐字段不变（C4/单 ACTIVE 不许为了绿放宽）；
       (丙) 突变：把按钮改回前端自猜可点状态 ⇒ 必须红。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db` 的写；禁 `demo/reset`（R13，护栏 ENFORCED）；
    生产包 + 手机视口才算验收；报数带 SHA/树/命令/收集计数；**引用提交附 `git log -1` 原样**。
    你的会话我连着两次投递超时（`CHAT_SESSION_RUNTIME_RECONCILE_TIMEOUT`），所以这单**以账本为准**；
    另外 ORD-0164/0126 的签收、ORD-0178（"已保存"无存储背书）也都在账本里等你。
  status: DISPATCHED@2026-09-21T23:3x+08 by 494abfd7（前提由我更正：入口已存在，缺接线）
