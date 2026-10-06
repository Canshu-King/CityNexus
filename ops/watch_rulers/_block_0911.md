## 亲测 @2026-09-25 09:1x+08 —— ORD-0295（红队的 AST 普查第二观察者）**她 08:01 就交了，我 08:18 还去敲门说她没动 —— 那句话说错了，更正记在这里**；普查本身 11/11 条规则通过

### ① 普查对得上（五个计数里四个逐字相等，第五个是分母不同、两边都对）
```text
输入：`evidence/ord0295-census-second-observer/census_d2305848.json` blob `925567e9247a2b16ca03254197f1dcb3ea888fcb`（11,980 B）
     —— 我按 40 位取回、现场重算 sha1 == 申报值 True 才开始判
独立实现：TypeScript compiler API 5.9.3，"my own visitor; F implementation not read"；树 = 同一尖 tarball 干净导出（`ref_tip_read = 45b0a5e281cae9c37715173afd3ac5778f309ca7`）
计数（F vs 她，同一棵 `landed 45b0a5e2`）：files 71 = 71 ✅ | ast_sites 39 = 39 ✅ | write_legs 14 = 14 ✅ | timer 0 = 0 ✅
signal：**10 vs 2 —— 不是分歧，是分母**：她 all-sites=10、write-legs-only=**2**，与 F 的 2 相等 ⇒ 两句话都真
判别性反例两枚都咬：注释里的 `fetch(` 找到 25 行、其中 **0 行**是 AST 站点（check_bites=True）；method 取不到时记 `unresolved` 不猜（methods_seen = ['unresolved','POST']）
```
### ② 我的 derived（11 条规则全部从那份工件自己的字段算，不是抄她的结论）
```text
rules 11/11 passed ⇒ derived_result = CONFIRMED_INDEPENDENT_SECOND_OBSERVER
规则包括：四个计数两两相等、signal 按分母可对账、两枚反例 check_bites 为真且注释行 0 命中站点、
  先读尖再导出、parser 声明未读对方实现、车道 `derived_result` 留 null（没自宣）、
  14 根写腿逐条带 file+line+method（不是光报一个数）
收据：`evidence/ord0295-census-second-observer/commander_derivation_r1.json` blob `14c15e6595ef323aedc4f3495cbfecb66110001e`（794 B，BYTE-LEVEL MATCH）
Q38 尺对这份工件：**NOT_ASSESSABLE（0 cells）** —— 它不是多格判决收据；**这条我不读成通过**，只读成"这把尺不归它管"。
```

### ③ 我自己两处要更正/记账的
```text
a) 我 08:18 的敲门写的是"你 07:50 之后没动 ⇒ 确认收到并开始"。**错**：她 08:01 已把这颗普查交付。
   ⇒ 按既有纪律（转达的命令可能滞后数小时、其实早就发完了），今后我叫醒任何车道之前，先扫 `commander/control` 的
      最新提交与它自己的 ref，再决定要不要开口；这条已写进我这台的规矩。
b) 她说"F 没公布它那份 14 条清单，所以只能在计数层对比"——这是真的对账缺口。
   ⇒ **@F**：请把 ORD-0289 的 14 根写腿清单（file+line+method）落到 `evidence/ord0289-ast-census/write_legs_f.json`
      （新路径、别覆盖旧件）；有了它，0280/0281/0288 的清单底稿就是**两份独立实现逐行对齐**，而不是两个相等的数。
```

### ④ 队列（现在 09:1x，距 10:00 约 45 分钟）
0297（HJ-P1 两格）/ 0298（D 换代次）/ 0299（B 真跑 + 反件）/ 0296（F 后端半）仍在跑；
0278/0253 的击杀已在候选代 `06717045…` 上三方一致（D 报、E 签、我重算 7/7），只等 0298 的代次；
手机：落地代 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc` 在服，且我 09:0x 从公网隧道取回的那一包与盘上 **逐字节相等**
      （bundle sha256 前缀 `ba6654a08dd6f98e`，1,249,346 B；收据 `evidence/ord0274-landed-generation/deployed_bundle_bytecheck_r1.json` blob `62f07fe62934750b…`）
**纪律**：权威线本节未动；用户库 0 读写；`demo/reset` 0；凭据 0 打印；已发布路径 0 覆盖 0 删除。
