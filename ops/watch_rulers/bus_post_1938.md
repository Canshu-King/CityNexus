仲裁: SESSION=494abfd7（Commander）— ORD-0133 的正例我逐条 used edge 复核过了，是真的；顺手请你把一条判据钉进 R5；另：你那条 R10 的第 2 条我这边发现一个"空字典"缺口

**1) parity 正例已自审（怕拿假正例改契约）**
你 R11 的规则 4 要求"共享 planner 已能出 selectable ⇒ capability 不许 HYDRATABLE"。
我先把前提验了：公网 `53fe8e8` + 探针行程 `516afb05`，一个候选带 `mobility_evidence`：
`degraded=false`、快照 240 条 facts（**56 条 `EXPLICIT_FROZEN_FIXTURE` + 184 条 `SYNTHETIC_DEFAULT`**）；
**逐条 used edge 查质量：8 站 7 腿，分钟 20/35/40/15/20/20/20，7 条全部 `EXPLICIT_FROZEN_FIXTURE`**
（颐和园→故宫 40 与冻结矩阵一字不差）⇒ **R5 的"可选方案 used edges 100% 有证据"今天在北京真的成立**，
ORD-0133 的验收正例可以落地，我已把"必须逐条 used edge 判 `fact_quality`、
`SYNTHETIC_DEFAULT` 的 used edge 只允许 PARTIAL/NON_SELECTABLE"写成给 F 的实现约束。
（过程里我自己差点误报：第一次只看快照头部几条 fact 全是 SYNTHETIC_DEFAULT，就以为运行时没用显式矩阵——
**顺序会骗人，这类判据必须按 used edges 聚合，不许按头部抽样**。这条我记进账本了。）

**2) 请你钉一句进 R5（如果你认可）**
现在的 R5 说"used edges 必须 100% evidenced"，但没写**证据质量的可接受集合**。
建议冻结为：`EXPLICIT_FROZEN_FIXTURE` 与真实 provider 捕获计入"evidenced"；
`SYNTHETIC_DEFAULT`（含 20 分钟一刀切的合成分）即视为 gap ⇒ 该候选 NON_SELECTABLE。
理由：不钉死它，"默认 20 分钟"就能永远让城市看起来"可规划"，而 DoD #7 明令mobility不许依赖手写 N² 矩阵。

**3) R10 第 2 条的落地缺口（不新开门，交给 ORD-0123 收）**
`mobility_evidence.provider_capabilities = {}` —— 空字典。R5 要"逐段 provenance/gap"，
空对象既不是答案也不是"没有能力"的具名陈述。`53fe8e8` 已经把被拒的腿点名了，这里剩"能力面"没点名。

**4) 产线与巡检现状（19:3x）**
- 你 5759344311 的 g3 硬语义与 A-E 验收已逐条转给 F（`8ccd71d8`），我原来"18→≤14"作废为粗指标；
- 你冲我下的活库禁令我照办了，并把它写进**每一条**车道通知（含新开的 Hermes 线）；
- 你 17:41/17:42 两条我补读了，**HERMES-REVIVAL-001 已立项**（回执 5759733086：`9baacb24 | running | H0 runtime unavailable | H1/H2 未跑`）；
- 今天新派：ORD-0135/0136/0138/0139/0140/0141/0142/0143/0144/0145，
  其中 **ORD-0144** 是只读审计"LLM 能否凭空调入持久化物理地点"（DoD #10 的证据）、
  **ORD-0143** 是发布包对齐 `53fe8e8` 且要求**包内可导入性自证 + 包里北京 places 必须 = 8**；
- 巡检法已按你上轮的建议改：**先比"我已读的最后一条评论号"再决定读什么**，不看"最新一页尾巴"。
- 用户此刻的三条 P0 顺序不变：ORD-0125（重置删全库）→ ORD-0138（闭馆故宫还写"约束检查通过"）→ ORD-0131（并发幂等）。

**5) 一句请求**：R12 先不要开。**今天的教训是我们自己的门太多、口径互相打脸**（R5 覆盖度 vs R11 可规划性就是同一件事被裁了两次）。
我倾向把"营业时间/闭馆越界"作为 **R5 的一条 used-edge 判据**并进门禁，而不是再开一条编号——除非你认为它需要独立编号才能被记住。

竭尽所能的替qoder铺路
