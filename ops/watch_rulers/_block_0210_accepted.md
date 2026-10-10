## commander 记账 @2026-09-23T00:02+08 —— **ORD-0210 机制层 ACCEPTED**（仲裁第四次源审 `5779720219`）；我的薄适配器撤销旧裁定、签为可用；两处口径纠正照录

### ① 仲裁直接读了 F 的二审包（`evidence/ord0210/` 下 5 件），逐项签字：

```text
freshness shared predicate   = ACCEPTED   （run_freshness_problems() 已进共享模块、streak_verdict 机械判、M14/M15 杀掉两条退化）
run-shape exactness          = ACCEPTED   （parse_pytest_selectors() 整体抽出、三种形制各有精确判据、M16 真杀旧假 single-node）
triple-scope classifier      = ACCEPTED
target-node exit isolation   = ACCEPTED
protected-db guard           = ACCEPTED
reverse-closure semantics    = ACCEPTED-MECHANISM
measurement mutation campaign= ACCEPTED-EVIDENCE（16/16 KILLED）
⇒ ORD-0210 IMPLEMENTATION MECHANISM = ACCEPTED
⇒ ORD-0210 FINAL CLOSED             = NOT YET
```

**为什么还不能 CLOSED**（它说得对）：`a4079bc` 上的真实 acceptance receipt 是 g3 **0/10 GREEN**——这正说明尺会诚实报坏消息。最终关闭仍走老顺序：**C/ORD-0213 修完产品并发根因后，在修复后的 exact SHA 上重跑 10 进程/10 fresh DB 全绿，再破坏真产品的并发保护点必须红**。F 的 16 个突变是量具自己的反例，**不能冒充产品根因的 reverse mutation**。

### ② 一处口径纠正（照录）

它不接受 manifest 里"引用定性必须带批次"那句：**冻结 scope 仍只有 `(exact SHA, target node id, run shape)` 三元组，batch/receipt id 只是 provenance 不是第四维**。同 SHA+同 node+同 shape 的两个独立批次若一绿一红，必须合并证据定 `FLIP_WITHOUT_SHARED_STATE`，不能靠"不同批次"各自签 stable。请改 manifest 那句为 provenance 说明（归 F）。

### ③ 我的薄适配器：**撤销旧裁定，签为可用**

它原话要点：现在 import 共享模块、argv 由 `shape_command()` 生成、强制 10 runs、跑前快照、流分开、verdict 全走共享函数 ⇒ **`gate_streak.py current thin adapter = ACCEPTED for single-node measurement`**。但**不能替交付方证明 clause 6b、也不能替产品 reverse mutation 出证据**——这两格照旧。
（上轮"C/HARNESS 不能用这把尺"的纠正至此更新。）

### ④ 它顺手预审了已落可读面的 ORD-0219 demo-evidence 交付

九项 ACCEPTED/ACCEPTED-CODE SHAPE/ACCEPTED-EVIDENCE（parser severity 形状、server-stamped `source_kind=DEMO`、fixture 无法伪造 LIVE、CNX-DEMO-only 零泄漏、unknown≠implicit true、正常消费链、双向具名阻塞、生成过滤冲突候选、6 突变臂全有杀）。**特别认可**：`severity='HARD' if hard else None` 的 None 会回到现有默认，没有另造语义。
**只留一个不阻塞的窄探针**：hard capability 先于 generate 时冲突候选会静默消失，若响应无具名 blocker ⇒ 另开 explainability 单；**不要为 probe 先改产品**。

### ⑤ 工具状态

`publish_evidence.py` 的 post-PUT proof GET 401/403 自动 retry 仍是唯一残口（SAFE-DEFAULT 未签）——**下次有人碰这工具时顺手补**，不开安全史诗。

### ⑥ 现场

working tip `e1580de`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
**待办按序**：① F 改 manifest 那句（provenance 化）；② C/ORD-0213 修根因后重跑 10 连＋真 reverse mutation；③ publisher 补 proof-GET fail-closed；④ hard-capability-before-generate 窄探针（可派红队或 HARNESS）。
