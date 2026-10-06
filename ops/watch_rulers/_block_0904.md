## 亲测 @2026-09-25 09:0x+08 —— ORD-0292：红队签了 derived，**我又独立重算了一遍（7/7 KILLED，不抄任何一方的话）**；0278/0253 现在只差 ORD-0298 那一步

### ① 三方读数并排（每个数都带 durable 坐标，按 Q43=①）
```text
D 申报：`evidence/ord0292-on-frozen-0671704/arms-0292c-0671704.json` blob `cb9270671adc323ff2816d406739e04518b9d05f`（35,661 B）
E 派生：`evidence/ord0292-on-frozen-0671704/verifier_derivation_d2305848.json` blob `7fa7946a4f154aadf5fbc5132374640129440cb7`（6,096 B）
绿轮：  `evidence/ord0292-on-frozen-0671704/gate-round-0671704.json` blob `0160e8db0295e600b44a5e5ff021d5da507bc7d2`（36,615 B）
我重算：`evidence/ord0292-on-frozen-0671704/commander_rederivation_r1.json` blob `ea90156d5b4586b25ec5628edff582e4ed762eff`（4,659 B）
        仪器（可复跑）`evidence/ord0292-on-frozen-0671704/derive_ord0292_commander_r1.py` blob `8f90454b878e999fdd2bb844c9c9b50c95afd05e`（5,996 B）
冻结尖（本批被测树）：`0671704546f9c9ea1d1b57627b059124c7800803` = refs/heads/review/0278-0253-on-45b0a5e
```
**我这一遍怎么算的**：三件输入都先按 40 位取回、现场重算 sha1 与申报值相等才开始判；每臂的 11 条规则**全部从该臂自己的字段派生**（`baseline.exitCode==0`、`attempt.exitCode!=0`、两面 `stackStarted`、`missingNodes==[]`、owner 节点基线 GREEN / 突变 RED、`redSet == 该次 attempt 里真红的节点集合`、`anchor_hits>=1`、`restored_exact`、`triple.exact_sha==冻结尖`、两次 `runId` 不同）。
```text
结果：arms 7 | 我判 KILLED 7 | 与车道申报一致 True | 实测 red-set 大小只出现 {1, 3}
  K278_NO_MISSION_ID_IN_BODY / TWO_KEYS_MERGED / CLEAR_BEFORE_SEND / SILENCE_ON_NON_ACCEPT  各 1 节点红（独占）
  K253_LEG2_KEY_DROPPED / LEG1_KEY_DROPPED / ONE_KEY_FOR_ALL_INTENTS                          各 3 节点红（同一 spec）
⇒ 证据计数按 E 的口径我也认定 **5 份**：4 枚独占 + K253 三臂是**同一个割集**从三个 owner 看过去的样子，不算三份。
```

### ② 状态与下一步（谁欠什么）
```text
0278 / 0253 的击杀在**候选代 `06717045…`** 上成立（E 签 + 我复核）；按 Q24/Q25 它们**不迁移**到落地代 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`。
⇒ @D：ORD-0298 就是剩下那一步（新开 ref、同一批臂在 `5c4608ce` 上重跑一轮绿+一轮拆、`frontend/**` 逐文件 sha256 对表、三元组换新代）。
   你不必重造判据，判据已被验证有效；要重做的只是"代次"。
⇒ @红队： ORD-0298 交上来时同样请你出 derived；我的 `derive_ord0292_commander_r1.py` 已参数化了冻结尖/三个 blob，改常量即可复用（或直接交给你当模板）。
```

### ③ 顺带（不做就没证据的东西）
`Q43=①` 的尺我又用了一次：对 E 的派生件跑 ⇒ `NO_CLAIM_FOUND_NOT_APPLICABLE`（rc 4）——**这不是通过，是"这里没有可判的数字申报"**，我在收据与账本里都按这个措辞写。

**纪律**：权威线本节未动（`5c4608ce…`）；本节 3 次 PUT 全 BYTE-LEVEL MATCH、0 覆盖 0 删除；用户库 0 读写；`demo/reset` 0；凭据 0 打印。
