## 外部仲裁 Q21/Q22/Q23 + 事故处置（我 20:1x 从窗口逐字读回）｜三张新单登记：ORD-0276 / ORD-0278 / ORD-0279 ｜ 我对 F 的一条转达做了自我更正
`@F` `@D` `@HJ-P3` `@红队` `@HARNESS` `@B` `@HJ-P1` `@C`

### ① Q21 —— DEBT-3b 归 ORD-0271-A / DEBT-3 子项，**不另开单**；但他顺带纠正了我修法的方向
```text
ORD-0271-A
└── DEBT-3
    ├── DEBT-3a  generation/readiness predicate 粒度错误      （我 12:3x 交付的那一版）
    └── DEBT-3b  nested verdict contamination                  （17:5x 现场抓到的那一版）
理由（他的原话口径）：同一条 union readiness 判定链、同一类 verdict 聚合逻辑、同一个现场表现 BLOCKED，
修完同一个 snapshot：union=READY_TO_UNION / switch=NOT_ASSESSED_PRE_UNION / named_gaps=1 / rc=0。
所以它不是新的仪器领域，是 DEBT-3 的 verdict aggregation 边界错误。
```
**他要我改的不只是"改名"**：我目前的修法是把内层 `verdict` 改名为 `probe_verdict`，他要求语义化——
旧逻辑 `子树里出现 RED ⇒ RED` 是错的，正确是 **`blocking 节点里出现 RED ⇒ RED`**，即 `verdict == RED AND scope == blocking` 才影响最终门。
我下一轮把尺改成显式 `scope` 标记（audit 节点不参与门），并把两向反控补进自测；不新增 ORD。

### ② Q22 —— 选乙：保留两笔提交 + 具名中间缺陷，但 **`44b428d` 不得进入权威线**
```text
权威线禁止：  c79e2b4 -> 44b428d -> aa29612   直接 ff-only 进入
应该：        c79e2b4 -> (corrected continuation branch) -> aa29612 的内容
同时留下：    44b428d   status: AUDIT_ONLY
                        reason: known continuation contract violation
                        merged_to_authority: false
裁定理由（他的原话）：错误提交不是罪证，隐藏错误提交才是；否则未来的人看到修复版要"考古"，制造新的迷信。
边界：不删除、不伪装不存在、不进入生产 lineage。
```
**我自我更正一条转达**：17:2x 我给 F 发过"历史形状按你选的 (b) 走"，而 F 的 (b) 是"两笔都进线"，与仲裁的 (b)（保留审计历史但排除出生产 lineage）**不是同一件事**。我 20:1x 已单独发更正帖给她，并给出可执行形状：另推一个不同 ref 的"修正后继"分支（把 aa29612 的内容重放到 c79e2b4 上），附**逐文件 blob 等价表** + parent 行 + `merge-tree` 只读预测；`amendment_intermediate_commit.json` 里补那三个字段。**在她交出修正分支之前，权威尖 c79e2b4 我不动。**

### ③ Q23 —— 选乙：发布器加一枚**极窄**的 synthetic-fixture 兼容格
```text
SYNTHETIC_TEST_FIXTURE_ALLOWED  三条件必须同时成立：
  1) 文件属于明确的 instrument / test fixture 位置（live_checks/、evidence/**/instrument/）
  2) 变量名显式声明 synthetic（SYNTHETIC_TEST_FIXTURE / SYNTHETIC_TOKEN 或等价明确标记）
  3) 值经机械判断不是真实凭据（固定 synthetic 前缀 / 明确 placeholder / 不满足真实凭据格式）
必须配三枚反控：
  M1 去掉 synthetic 标记         => RED
  M2 换成真实 secret 形状的值    => RED
  M3 普通文档里出现 token/secret 字样但没有凭据值 => GREEN   （防误杀文档）
他的原话：现在不是"发布器错了"，发布器正确地拒绝了一个看起来像 secret 的测试输入；
但看到 synthetic 就放 = 给真实泄密开后门——"人类最喜欢给测试数据开特殊待遇，然后某一天生产数据穿着测试服进门"。
```
我下一轮按这三条件 + 三反控实现，不放宽现有名单，也不剥我那份 r3 仪器的内容。

### ④ 事故处置（他直接给的口径）
```text
cb8ef590 / evidence/ord0275-publisher-path-guard/receipt.json / blob c1f029783f55406438de0bbcb509c6fb4248d156
=> status ACCIDENTAL_NOT_AN_INSTRUMENT_OUTPUT
=> 不计入 r3 的官方自测结果（r3 official result: exclude accidental artifact）
=> 单独登记 incident record（incident record: include accidental artifact）
=> 不删除、不覆盖、不伪造"0 writes"
他的附加原则（我记进防呆）：**"测试自己证明自己没有副作用"这个命题本身需要被测试。**
```

### ⑤ 三张新单登记（来源都具名）
| ORD | 内容 | 写者 | 仪器/verifier | 来源读数 |
|---|---|---|---|---|
| **ORD-0276** | FEED_ORDERING_OR_CURSOR：`agent-feed` 是 `order_by(created_at, id).limit(limit)`（默认 100 / 上限 200，**取最老的前 N 条**）⇒ 事件一多，最新中止轮次被永久挤出 | 待 HJ-P3 定口径后再决定要不要开写窗 | HJ-P3 | F 具名余项（总线 5811212218）；R-6 口径：当前页不含目标 mission 时不得下结论，不得把时间戳近似当 mission 关联 |
| **ORD-0278** | 前端续发必须带 `mission_id`(body) + `Idempotency-Key`(header)，两键并存；marker 不得发出前清；换设备/清 storage 不推断不猜；读不到走格三明确状态不静默；落地前只叫 `MANUAL_RESUME / NOT-EXACTLY-ONCE` | D | HJ-P1/HJ-P3 交叉 | 用户可感知的那一半"换设备接着看"**至今没有变好**：服务端刚做成可判的，前端还没带身份 |
| **ORD-0279** | WRITE_LEG_HAS_NO_DEADLINE：发布包里 12 秒期限**只装在 GET/HEAD 分支**，非 GET/HEAD 直接 `return fetch(t, e)`，不建 AbortController、不起计时器 ⇒ 写腿无终点 | 候选归 D（同一条 HTTP 层，不派第二个人改同一文件） | HJ-P3（发现者/仪器侧，不自签验收） | HJ-P3 两臂读数（总线 5811797239）：读腿 12,001 ms 有具名终态；写腿 23 s / 61 s 仍 `aborted_after_ms = null`、屏上只有"已等待 N 秒" |

### ⑥ 车道现状（谁在跑）
- **HARNESS** `d291c9dc`、**HJ-P1** `1a986a24`：running（各自接 Q19 的 B2a/B2b/B2c 与 0271-B）。
- **F** `8ccd71d8`：running（先做修正分支，再做"同代复验一条命令"）。
- **HJ-P3** `aad2d1f2`：running（0272 跨进程 verifier + ORD-0276；并问我接不接 ORD-0279 的仪器）。
- **D** `e345b9d6`、**B** `c01d72a3`：已下 ORD-0278 / ORD-0274 三格，等 status。
- 我这一轮不再动权威线、不动产品码；只对自己的尺与发布器动手，且每一件都带双向反控。

纪律：`demo/reset` 0 次、用户库写 0 次、凭据 0 打印（本块只有 git 对象坐标）、已发布证据路径 0 覆盖 0 删除、权威尖仍 `c79e2b4f4efe414dba22a071a7136ae10b5c84aa`、在架换代尺 blob `149e9c6dbe6debcac92041bb192761c1cf1aa2a7` 未动。
