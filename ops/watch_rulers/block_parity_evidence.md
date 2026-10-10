### commander 亲测 @2026-09-21 19:3x —— 我把 ORD-0133 的正例**先自我审查了一遍**：北京候选的 7 条 used edge 全是 `EXPLICIT_FROZEN_FIXTURE` ⇒ R5 站得住，parity 门的正例是真的；但我中途差点误报一次，也记下来

**为什么要自己再量一次**：ORD-0133 的验收第①条要求"北京必须读成 `capability=READY / planning_readiness=READY / coverage_completeness=PARTIAL`"，
它的**前提是那 3 个 selectable 候选符合 R5**（used edges 100% 有合规证据）。如果候选其实是合成默认值堆出来的，
那 parity 门就会把"证据不足"的城市推成 READY —— 那就是用一个假正例去改契约，比现在这个 bug 更糟。

**读数（公网 `53fe8e8`，探针行程 `516afb05`，19:36–19:37）**
- 一个候选带 `mobility_evidence`：`degraded=false`、`source_provider=mock-mobility`、快照内 **240 条 facts**：
  **56 条 `EXPLICIT_FROZEN_FIXTURE` + 184 条 `SYNTHETIC_DEFAULT`**（矩阵是 65 对里 56 对北京，全部进了快照；剩下是合成填充）；
- **逐条 used edge 查质量**（这个才关键，快照级平均没用）：该候选 8 站、7 条 used leg，
  分钟数依次 `20 / 35 / 40 / 15 / 20 / 20 / 20`，**7 条全部 `EXPLICIT_FROZEN_FIXTURE`**
  （其中 颐和园→故宫 40 与冻结矩阵一字不差）；
- ⇒ **R5 的"可选方案 used edges 100% 有证据"在北京这条路上今天是真的**，
  所以 ORD-0133 的正例成立，F 可以按它落地 parity 门。

**我差点误报的那一下（记下来，别删）**：我第一次只看了快照里**最前面几条 fact**，全是 `SYNTHETIC_DEFAULT / minutes 20`，
就以为"运行时没用显式矩阵、fixture 是装饰品"。**逐条对上 used leg 才发现顺序会骗人**——快照按 origin 分组，
北京 place 键排在后面。**结论：`fact_quality` 这类判据必须按"used edges"聚合，不能按快照头部抽样。**

**顺带一条小契约缺口（不派单，交给 ORD-0123 一起收）**：`mobility_evidence.provider_capabilities = {}` ——
空对象，没说"这次用了哪个 provider、能力边界是什么"。R5 要的是**逐段 provenance/gap**，
空字典不算答案；`53fe8e8` 已把"被拒的腿"点名了，这里剩"能力面"没点名。

**给 F 的一句话**：parity 门实现时，请断言**逐条 used edge 的 `fact_quality ∈ {EXPLICIT_FROZEN_FIXTURE, PROVIDER_*}` 才计入 READY**，
`SYNTHETIC_DEFAULT` 的 used edge 只允许 PARTIAL/NON_SELECTABLE —— 这样上面那个正例就是可回归的，而不是我今天手量的。
