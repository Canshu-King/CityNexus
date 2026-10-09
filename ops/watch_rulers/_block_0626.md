## 亲测 @2026-09-25 06:2x+08 —— **ORD-0282 = ACCEPTED**（F 在落地代把 K8 那一格跑出来了；我用 10 臂复算尺从它自己的逐轮读数重算 ⇒ ALL_AGREE）；顺带量到一条新事实：**拆掉守卫 ⇒ `plan_versions` 3→6，第二发重新生成一整套候选**；F 提的问题立案 **ORD-0287**，并请仲裁裁 **Q34**

### ① 我这一拍量的（先核字节，再复算，不念它的摘要）
四件按 blob 回读全等（`commander/control`，声明 == `contents.sha` == 我用 body 现场重算）：
```text
evidence/ord0282-k8-landgen-f/ord0282_receipt.json          15,288 B  f93312c9ae1871744b94c54df843b3d59f3a585c
evidence/ord0282-k8-landgen-f/seam_face_readings.json       20,733 B  eeedddaa26d7626623046b27de2a214181cdd81b
evidence/ord0282-k8-landgen-f/landing_tree_proof.json        3,214 B  ec98fd76ea580cab38bb4c8293fe4af3b4d096ef
evidence/ord0282-k8-landgen-f/second_observer_r3_run.json    1,009 B  b29eb8cd1df7f62535939b40adf4e024fdb9bd1b
```
新尺 `live_checks/receipt_consistency_o0282_r1.py` `331a8b5651bb7dc015d9156769e6823431a82f0c`（3,731 B）
跑法：先按 blob 取回上面第一件到本地，再 `python live_checks/receipt_consistency_o0282_r1.py --path <本地副本>`
⇒ **arms=10 disagreements=0 `INTERNAL_CONSISTENCY ALL_AGREE` rc=0**。关键三臂不是我信它写的串：
**A07** 逐轮 `main.py` 的 blob 必须与它当时自称的状态一致（guard=`416ea4f2…`／mutant=`784599fd…`，**6 行（guard 3 + mutant 3）全对**）；
**A08** 反向：没有一轮"自称守卫在位、实际跑在突变体上"；
**A10** `FLIP_OBSERVED` 这个判级是我**从逐行读数重新算出来的**（guard 三轮 `A_bytes_survive` 全真 + `B_overwritten_rows` 全 0；mutant 三轮全反），不是从它文件里抄的字符串。
**第二观察者那格我认**：F 独立复跑我的 `audit_closure_coordinates_r3.py`（先重算 blob `fc35335a…` == 申报值）⇒ **claims=50 failing=0 rc=0**，与我 04:3x 申报同数、不同机器不同时刻。它还如实报了一条：那把尺**不在 45b0a5e2 这代树里**（两侧 404），所以它是按我分支上的 blob 跑的——这句说得对，我这把尺从来就是 commander 写域的工具，不是产品文件。
⇒ **ORD-0282 = ACCEPTED**。`derived_result` 仍归 verifier（B-1，F 自己也在 `not_claimed` 里写明了）。

### ② 一条顺手量到的产品事实（值得单独记，因为它改变"这枚守卫值多少"）
轮末 `plan_versions` 计数：**guard=[3,3,3] vs mutant=[6,6,6]** ⇒ 拆掉那半个条件不只是"别人的回执被覆盖"，**第二发会重新生成一整套候选**。也就是说这枚守卫挡住的副作用是**翻倍**级别的，不是"脏一行"级别的。这条我引 F 的读数（`criterion_4_derived.plan_versions_guard_vs_mutant`，我的 A03..A06 已核过其与逐轮行一致）。

### ③ F 提的问题我接，但不自己拍：ORD-0287 + Q34
F 原话要点：**落地代没有那枚 seam 符号与 `test_G9` 载体**（它每轮 `seam_symbol_at_round=false`），所以"同名格同代复现"要先决定候选 `7c806fab5…` 那笔重构落不落。
我的判断：**守卫的行为已经是落地代事实（①），但这枚守卫在权威线上没有回归载体** —— 这才是 0272 真正欠的那块。
```text
ORD-0287 · 给 K8 守卫在权威线上补一枚回归载体（test-only）· @F（8ccd71d8）
status: DISPATCHED@2026-09-25 06:2x
 0) **先答一句可移植性，再动手**：把 `7c806fab5` 的 `test_G9` 原样摘到 `45b0a5e2` 的树上，跑不跑得起？
    跑不起就交"它依赖哪个不在权威线的符号"（具名 + 那一枚 blob + 报错原文三行）然后**停手**——
    不许为了让格子变绿去改断言、去改产品码、去 skip。**交事实与下一步，比交一枚假绿值钱。**
 1) 从权威尖 45b0a5e2 起分支（先 GET /git/ref 读尖并写进收据；不是从 7c806fab5 续，它父是 dcae1bc9）。
 2) **只加测试文件，产品字节 0 改动**：`git diff --name-only 45b0a5e2 <新尖>` 必须全部落在 backend/tests/**，
    出现任何 backend/app/** 或 frontend/** ⇒ 自报 NOT_ELIGIBLE 并停手。
 3) 载体必须两态可跑：在权威树 GREEN；把 `IdempotencyKey.response_json.is_(None)` 拆掉后同一格 RED
    （具名前后 main.py blob、hunks=1、py_compile 过、跑完逐字节还原并回验）。
 4) 你 0282 那套两进程 rig 不要塞进候选——候选只交"能在 CI 形状里跑的那一枚"；两进程读数留在证据目录。
 5) 发布新目录 `evidence/ord0287-k8-carrier-f/`；候选分支外读 ref 必附 GitHub https 的 ls-remote 回读行，
    且**落点 sha == 候选尖**；账本块 + 总线一条。
 6) 权威线你不写。`derived_result` 我不签，等 @红队。
成本 20~30 分钟。
```
**Q34（请仲裁裁，只回符号）**：`ORD-0272` 现在怎么记？
① = **保持 OPEN**，等 ORD-0287 的 test-only 候选落地后再 CLOSED（我的推荐：**回归载体本来就是 0272 的交付物**，让一枚守卫裸奔进权威线是我不想要的先例）；
② = 按 Q30=① 立刻 CLOSED（只署 seam 面），0287 作为独立单另计；
③ = 别的。
（若你回 ①，则 0272/0287 一起等红队的 `derived_result`；若回 ②，我在闭单范围句里会写明"权威线上暂无回归载体，见 ORD-0287"。）

### ④ 队列与边界
红队：`ORD-0285`（复验我四处修复）→ `ORD-0286`（验 D 的 0278+0253 候选，0278 与 0253 分开签）→ 若 Q34=① 再加 0287 的派生。
F：0287（0282 已交）。D：等 0286 的派生结论，我不提前落地。HJ-P3：0276/0281 定形都已收，已请它把三个 `snap_*_dist` 从硬链接改成 copy。B：仍是 0274 → 0280 → 0281 顺序，未打断。
**我这一拍没动**：权威线（`mirror/integration-frontend-apple-pass1` 仍 `45b0a5e2…`）、任何人的已发布路径（新目录 4 个）、任何用户库（`_live`/`_preview` 0 读写）、`demo/reset` 0 次、凭据 0 打印。
