仲裁: SESSION=494abfd7（Commander）— 你两条都执行了（**甲 → ORD-0197**；**canary → ORD-0198，只建不叫醒**），并且我把"单实现"这条用在自己身上了

## ① 甲 落地
- **ORD-0197（C，P0，压过它整个队列）**：`anywhere_capability.py:431` 构造面从 `PhotonGeocoder` 换成 B 的 `PhotonIdentityProvider`，消费 `ProviderResolution`；
  四类映射逐条写进单（MATCH→用 `source_provider + source_entity_id` + WGS84 + observed_at 建服务端所有身份；AMBIGUOUS→null+候选另栏且**不静默当选**；NO_MATCH→null，**不得写 `pending:<raw>` 当身份**；RUNTIME_FAILURE→null+具名 retryable，**不得塌成 NO_MATCH**）。
- 我保留了 C `61cde4b` 的全部成果（10/10 与合跑 25/25 我复跑过）：**只换构造面，不改它的配置纪律**；并要求把 `ProviderAttempt`（逐镜子逐尝试留痕）接进作业/审计字段，这样 R14 的具名原因有出处。
- **`P7_RESOLVER_INTEGRATED` 我继续记 false**（条件 2 PARTIAL）。C 交付后我在**它的 exact SHA** 上重跑七条，成立才机械唤醒 Harness + P1–P4。

## ② canary 落地为"只建不叫"
**ORD-0198（B）**：你那十项隔离条件**逐条自证后才能动代码**（独立端口/一次性副本/不复用 live 写连接/不挂用户 URL·隧道·SW scope/用户入口不可达/主预览钉 53fe8e8/护栏 403/不切 live router/破坏性只作用 canary/失败不回写）。
证据口径也一并钉上：14 项 used-edge 收据 + `blocker_basis=USED_EDGE_INVENTORY` + `aggregate_repository_counts_used_as_blocker=false`；
**provider-only MATCH、直接塞 DB、API-only 成功、mock 冒充 live 全不算 Mission A 成功**。

## ③ 你 ③ 的账本 preflight 我用它替掉了自己那份
已拉 `ledger_write_preflight.py` @ `620c8e60`（5,649 B，blob 与磁盘一致），我的 `ledger_write.py` **改成只 import/wrap 它的 `plan_edit()` + `atomic_write()`**，自己那套 EOL/锚点/可逆判断全部删掉——本轮两块（ORD-0197/0198、ORD-0186 与 P7 记录）都经它写入，receipt 全部 `anchor_hits=1 / prefix_unchanged / suffix_unchanged / reversible=True`，并加了**写后回读比对**。
⇒ 顺带一条我自己的小教训，归进同一原则：**我读自己脚本状态时又出错一次**——一条 print 里把 `t.count('## ORDERS…') == 1` 写成了括号错位的式子，打出 False，我先诊断再动手，确认账本其实 HEALTHY（锚点=1）。**观察器错≠目标坏**，今晚第 6 次同族。

## ④ 现场
tip `61cde4b`；镜像 `a13c8a38fd16` 字节级相等（2,129,786 B / LF 干净 / 锚点=1）；
P0：主预览后端仍 `53fe8e8`、`demo/reset 403`、匿名 401、用户 `3/19/3` + places 北京8/演示8 未变；
车道：C(0197) B(0198) D(0135③ 双向已签 / 0180-0183 在收) F(0189 时间优先重写 + 元门) E(0186 隧道臂我复跑升 REPRODUCED) LAB(首班隔离证明) 全部有活；**真人组与 Harness 仍未唤醒**（等 P7 真成立）。

竭尽所能的替qoder铺路
