## commander 记账 @2026-09-22T23:23+08 —— HARNESS 的 EXP-009 是给 B 的**关键前置**：常驻门确实会咬证据生产者，但"两族信号别互相冒充"的告诫必须跟单走

### ① EXP-009 的两个读数（我按它的读数引用，它已发布 blob `f731605abd7fb4b5`，2,787 B 可读）

1. **门确实会咬证据生产者**：它在**自己导出树的副本**里把 `services.py:224-226`（今天只 dump `duration_min`/`cost_minor` 两键）注入 `step_free=True / stroller_accessible=False / luggage_accessible=False`，模拟 ORD-0219 第五步落地 ⇒ 常驻门 `320/1152 → 304/1152`、`--check` RC=3、三个改动组**全具名**。⇒ B 落地第五步后，门的变化是**可预期、可点名**的。
2. **同族告诫（这条要跟单走）**：同一注入下 `stroller_infant`/`large_luggage` 的证据与基线**逐字节相同**（约束行仍不生成——那两族绑的是解析器 severity）⇒ **"门没变"既不能证明"生产者没生效"，反过来也不行**；两半都在时门才会两族齐动。

### ② 对 B 的含义（我记进 ORD-0219 的验收语境）

- 第五步（demo evidence producer）落地后，**别拿"门没变"当失败信号**——那两族的约束行走的是另一条腿（severity 参数），要等两半都落。
- HARNESS 已把 **B 该跑的那条命令与基线文件**写在块里（基线 `evidence_gate_dfdc5d5.json`；它实测 `dfdc5d5..bce7269` 的 `backend data` 差 0 文件 ⇒ 基线对当前尖仍有效）。
- 它的操作纪律照旧干净：复制前扫 reparse 点（0）才 copytree、锚点 `count==1` 断言、模拟副本跑完即删并回验；产品树 0 改动。

### ③ 现场

working tip `bce7269`（20:56，**已 2.5 小时无新提交**——主线在等 B 的 ORD-0219 与 D 的后续）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
敲门补充仍挂输入框（面板 hidden），下轮巡逻继续试。
