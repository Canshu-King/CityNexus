- id: ORD-0133
  to: 8ccd71d8
  priority: P0-critical
  if_head: 53fe8e8
  order: |
    **R11 已冻结（总线 5759213125，账本 18:5x 转录块）**：把"可规划性"与"覆盖完整度"拆开，
    并给两者做 **parity gate**。北京今天就是反例：`plans/generate {}` 公网实测 **201 / 3 个 selectable 候选（1.38 s）**，
    而 `capability?query=北京` 回答 **HYDRATABLE / COVERAGE_INCOMPLETE**（`lodging MISSING`、`nightlife PARTIAL`）
    —— 评估器在屏幕上把一座**能排的城市**说成**要灌数据**。
    要做（按 R11 六条硬规则逐条落）：
    ① 契约加两个独立真值：`planning_readiness: READY|NEEDS_HYDRATION|BLOCKED`、
      `coverage_completeness: COMPLETE|PARTIAL`；六轴 coverage **保留且继续展示**；
    ② `capability` 的判据改为"当前目录/证据能否让**共享 planner** 产出至少一条 evidence-complete selectable plan"，
      不再由"六轴全 READY"机械决定；coverage PARTIAL **不得**把 READY 降级（规则 1）；
    ③ 单次请求可以因自己的硬要求被拒（用户把 lodging 设成硬要求 ⇒ 对**该请求** `CATALOG_INSUFFICIENT`），
      但**不得**反推整城不可规划（规则 2、3）；
    ④ **parity gate（这条是门的核心，不许用常量糊）**：同一 snapshot 上先跑共享 planner，
      若已产出 selectable candidate，则 capability 回答 HYDRATABLE/NEEDS_HYDRATION 直接判红；
      反向也要：capability=READY 而 planner 零候选同样判红；
    ⑤ 文案：改成"可规划，夜生活/住宿数据仍不完整"，删除"这城市还要灌数据"这一类把两件事混说的句子（规则 5）；
    ⑥ 后台 enrichment 不得阻塞已 READY 的城市（规则 6）：若 hydration 仍在跑，capability 仍以 planner 事实为准。
    验收：① 北京在当前 `53fe8e8` + 现有目录上必须读出 **capability=READY / planning_readiness=READY /
      coverage_completeness=PARTIAL（nightlife PARTIAL、lodging MISSING）**，且这条**就是 parity gate 的正例**；
    ② 一个真空城市（六轴全 MISSING、planner 零候选）仍必须 HYDRATABLE 或 UNAVAILABLE，不许被放宽成 READY；
    ③ 先红后绿（把今天北京那组读数当红基线贴出来）；④ 一条杀得掉的突变
      （把 parity 检查改成"只看 coverage"必须让门红）；⑤ 全量红集合**只允许少不允许多**
      （现在 **18 红**，见 ORD-0131 —— 你那条先做，这条排它后面）；
    ⑥ 报出 parity gate 的**耗时**：它要在评估里调 planner，别把延迟藏进门后面。
    禁令：不许为了让北京 READY 去改 `data/mock/**` 或放宽 `min_ready`；不许绕过共享 planner 自己数点数；
    不许把 `details=null` 带进新字段（R5 定性不变）。
  status: DISPATCHED@2026-09-21T18:5x+08 by 494abfd7（R11 落地；与 ORD-0123 的契约 parity 合并验收）
