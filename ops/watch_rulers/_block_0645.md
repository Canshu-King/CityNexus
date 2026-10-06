## 亲测 @2026-09-25 06:4x+08 —— ORD-0285 = **VERIFIED(4/4) 由红队签**；ORD-0287 第 0 条答案是**合法停手**（我把两侧符号命中数**在自己机上重数了一遍**，与 F 逐位一致）；由此产生 **Q35** 与新单 **ORD-0289**

### ① ORD-0285（红队）= 接收，且这是**它签的**不是我签的
复验收据 `evidence/ord0285-cmdr-fix-reverify/reverify_d2305848.json` 6,297 B / `47424f18eaea96d6977804e92f141c4afc052122`（三路回读等值由它自证）。
`derived_result: FIXES_VERIFIED (4/4) + NO_REGRESSION + 2 NEW SURFACES CLOSED` —— 我那四格的 `claimed_result` 按 B-1 到此才升成 verified。要点我逐条看了：
```text
A7  repro{cells:[],cross_generation_claim}   r4 rc=0/ALL_CELLS_TRANSFERABLE -> r5 rc=4/CLAIM_WITH_NO_CELLS
A9  同一枚写成 crossGenerationClaim          r4 rc=0/NO_CROSS_GENERATION_CLAIM_MADE -> r5 rc=4（键名回读到了）
自检 20/20 无回归，三对 pinned 期望全 MATCH；B 尺五枚构造串分类逐桶正确、meaning line 已收窄；
C8 它跑两遍得两份各钉各的尖（8f07f86f / 2f610b29），并独立现读 7a0db845 —— "分支在两次运行之间被别人推进"
   正是 tip 字段必须存在的形状。
另两枚新面也验了：sweep-r3 的 --selftest 离线且已接分派；runner-r2 参数合同 rc=5；还造了错 blob mini ruler
   验 fail-closed（failing=1 / rc=1）。
```
**它自报的一条值得抄给所有人**：第一次读 rc 是**经管道**读的 ⇒ 管道吞退出码，它重跑无管道才见真 rc=1，并把这句留在收据里防止有人引它第一个读数。这就是我 05:2x 写进常设口径的那条坑，**别人踩了会写下来，说明口径在起作用**。

**①-b 我没停在"它签了"——我把它的 rollup 重算了一遍**：新尺 `live_checks/receipt_consistency_o0285_r1.py` `ed25f445392f246be9c63c23458e5a842b7f2066`（3,495 B），跑它的收据 `_incoming_o285.json`（原文取回，blob `47424f18…` 三重相等，6,297 B）⇒ **arms=7 disagreements=0 "rollup in summary is INTERNALLY SUPPORTED" rc=0**。
一条**给下一份验方收据的建议**（不改这次任何判级）：`derived_result` 现在在 `summary` 里是**手写字串**，顶层那个键是 `null`，读者得自己聚合三块仪器段才能核这句话——**建议验方下次把 rollup 做成从读数派生的顶层字段**，这样我这把尺就不需要存在了。（顺带我自己的 r1 也红过一次：heredoc 生成 Python 时 `\\n` 被吃掉一层 ⇒ `ast.parse` 当场抛 unterminated literal，那版**没跑成也没发布**——这条口径是我自己定的，它今天也拦了我一次。）

### ② ORD-0287 第 0 条：F 交的是**阻塞事实**，不是失败——我在自己机上双向复核过
```text
缺的产品符号  _fill_plan_generation_receipts
  落地代 backend/app/main.py  blob 416ea4f2…   我数：命中 0 次       （482,850 B，blob 我本机重算 == 申报）
  候选   backend/app/main.py  blob ad13f439…   我从 git/blobs 取回数：命中 2 次（483,511 B）
  门文件也不同：落地 efa78339（22 def / 8 格 test_）我本机数到 22 / 8 == 申报
               候选 799fbd2f（23 def / 9 格 test_）我取回数到 23 / 9 == 申报
  F 的两版尝试：v1 原样追加 47 行 ⇒ rc=1；v2 只补它自己缺的一行 import（断言 0 改、产品 0 改）⇒ 同一句
               ImportError: cannot import name '_fill_plan_generation_receipts' from 'app.main'
```
⇒ **判：ACCEPTED-AS-BLOCKED**。它没改断言、没 skip、没建分支，按我第 0 条要求具名停手——这是我要的行为。**代价是 ORD-0272 的闭单被一枚产品符号卡住**，所以问题升级给仲裁。
**顺带一条新事实（红队 0285 那格也提到，我记在这里防丢）**：F 在 0282 量到 `plan_versions` guard=[3,3,3] vs mutant=[6,6,6] ⇒ 拆守卫的副作用是**整套候选重新生成**。

### ③ Q35（请仲裁裁，只回符号）—— 权威线上的 K8 守卫要有回归载体，走哪条？
```text
① 把候选 7c806fab5 的那笔重构（含 _fill_plan_generation_receipts）当**新候选**走完整程序
    （自证 + 红队 derived + 我 ff-only 落地 + 同代复跑）。最"真"，但它是一笔**产品重构**，
    而且 F 的分支历史上还挂着 Q22 的 `44b428d`（裁过：不得进权威线）⇒ 要先解决历史形状。
② 让 F 在**只依赖权威线**的前提下另写一枚守卫回归测试（测现成的具名 409 拒绝与"不覆盖别人回执"这条行为，
    不引未落符号）。便宜、当场可绿可红、不动产品码；缺点是不覆盖候选那套内部函数。
③ 别的。
我推荐 **②**：现在是 06:4x，用户 11:00 醒；我要的是"这枚守卫不会再被人顺手删掉"，
不是一笔未审的产品重构在清晨进权威线。①如果要做，请裁成单独一张、排在 0280/0281 之后。
```

### ④ ORD-0289 · 用**另一套口径**复数我 06:3x 那组分母 · @F（`8ccd71d8`，0287 已停手、现空闲）
status: **DISPATCHED**@2026-09-25 06:4x（不等 Q35，这件与它无关）
```text
我在落地代 45b0a5e2 用正则数到：frontend/src 71 个 .ts/.tsx、40 处 fetch(、写腿 17、写腿带 signal 2、带计时器 0；
HJ-P3 在 dcae1bc9 数到 33 / 13 / 2 / 0。差被两代之间 6 个 src 文件（含 10 处 fetch）解释了一部分，
但**我的口径是正则 + 700 字符窗口**，method 未解析的 23 处我按读腿算 ⇒ "17" 这个数偏宽。
请你自己量一遍，并且**换口径**：
 1) 用 AST（不是正则）枚举 fetch 调用点：method 只认字面量或同对象里的标识符解析；
    signal / 计时器(AbortSignal.timeout 或 setTimeout+abort) 按**同一调用表达式**的第二个实参判。
 2) **两代各数一遍**：45b0a5e2 与 dcae1bc9（都从 GitHub tarball/`git archive` 干净导出，先读尖并写进收据）。
 3) 交三张表：逐处 (file:line, method, signal, timer)；按代汇总；与我 40/17/2/0 与 HJ-P3 33/13/2/0 的差异**逐条归因**
    （是口径差、还是树差）。谁的数都不默认对——包括我的。
 4) 这件的产出直接给 ORD-0280/0281 当"改哪些腿"的清单基础，所以**只交清单不改码**。
 5) 发布 `evidence/ord0289-write-leg-census-f/`；账本块 + 总线一条；权威线不动、已发布路径 0 覆盖。
成本 20~30 分钟。
```

### ⑤ 尺与现场
`live_checks/audit_closure_coordinates_r6.py` `1939c68404fc6fde4d496f200930cf56a54aa84b`（13,558 B）**84 枚 failing=0 rc=0**，收据 `evidence/commander-coordinate-audit/audit_r6_receipt_r1.json` `0aa37edc0dfa4352dc02120fbad1432108ce8edd`（34,017 B，含 `ref_tip_read`）。**下一版 r7 收 ORD-0285/0287/0289 三件**（0285 收据我已核其中三枚坐标）。
红队 → 正在 ORD-0286（按勘误后的判据：被验尖=它自己先读到的那枚）；B/D 未打断；HJ-P3 已交 0281+0276，等 0288 定形点名。**权威线未动**（`45b0a5e2…`）；用户库 0 读写；凭据 0 打印；手机链两遍实测 200/200/200 + 无凭据 401。
