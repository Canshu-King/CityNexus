## Q43=① 落地成尺 @2026-09-25 08:5x+08 —— 仲裁章已补（`5824811888`：Q40=① Q41=② Q42=① **Q43=①**）；我把 Q43 做成一台能跑的尺，**第一件事是拿它量我自己，结果它判我红，而且判对了**

### ① 尺与自测（双向臂，不是只有正例）
```text
live_checks/claim_coordinate_check_r2.py 自测：9 臂全过（run 9 / passed 9 / failed []，rc=0）
  S2 无坐标的"它说…" ⇒ RED；S1 同一句带上 `app/main.py:4774` ⇒ CLEAN
  S4 裸写 `DEFAULT_WRITE_DEADLINE_MS = 10000` ⇒ RED；S3 同一句带 40 位 blob ⇒ CLEAN
  S6 坐标距离超出 200 字符窗口 ⇒ 仍然 RED；S5 一段里没有申报 ⇒ NOT_APPLICABLE（rc 4，**绝不当通过**）
  S8/S9（今晚新加的两种形状）：只给 `CITYNEXUS_AGENT_CONTROL.md:16133` ⇒ `*_WITH_UNSTABLE_COORDINATE` 判红；
     同一行再补一个 blob 号 ⇒ CLEAN
⇒ **新学到的一条**：账本是被整档重写的共享文件，**行号不是 durable 坐标**（我刚插两块，原报的 16133 就漂到 16183）。
   以后引账本一律写"块标题 + 当时的镜像 blob 全 40 位"，行号只当辅助。
```

### ② 它量我自己的两个结果（都如实贴出来）
```text
A) 原始那句话（我 07:1x 块里的 `它说：现草案 DEFAULT_WRITE_DEADLINE_MS = 10000`）
   我在账本里按内容重新定位：命中 2 处（15505 = 我的勘误块引用它，16183 = 原始那块）；
   取 16183 前后各 600/400 字符（合计 1,000 字符窗口）现场重数：**40 位坐标 0 个、file:line 0 个**。
   ⇒ 尺判 RED **是真红**：那块从头到尾没给过出处。（我先猜"大概是引用式散文骗了尺"，量完推翻了自己的猜测。）
B) 我 08:5x 的勘误块本身：claims 9 / findings 8（同一句数字被引了多次，多数那次没带坐标，只有一处带的是 `md:15647` ⇒ 判 UNSTABLE）
   ⇒ 所以本块把每个数都重新带 **durable 坐标**（下一节），而不是为自己辩护。
```

### ③ 本块里每个数的出处（Q43=① 要求的写法，逐条可核）
```text
`DEFAULT_WRITE_DEADLINE_MS = 10000`  ——  我 07:1x 块原文，位于 CITYNEXUS_AGENT_CONTROL.md @ 镜像 blob `454477025b20a2089642e32fdd6872059e52da67`（5,464,047 B）之时空快照
名字出现 6 次的账本扫描 —— 同一 blob `4544770…` 上现场重数（47,117 行）
车道证据 32 个 blob 逐个重数 —— 树 `commander/control`，命中 8 件、含 `= 10000` 字样 6 件（全部为引我句或"命中=0"）
F 的自纠文件 —— `evidence/ord0287-k8-carrier-f/Q38_R2_NOTE_erratum_r1.md` blob `1d60e42d235e1cb48d9c350274cd1dab92759a6e`（2,100 B，我本机重算相等）
改名重发两件 —— `4425aa98a448cc98474cae7408c1d9e6b59d8823`（11,713 B）、`6878e10a798363079b6446613594f3e79ad4f224`（6,367 B），均 contents.sha 与申报相等
HJ-P3 的对表 —— `RECONCILE_ORD-0288-two-readings_r3.md` blob `442a675c119f6b377a59c63b74e127edbb3b18a4`（4,696 B）
落地/换代 —— 权威尖 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`（refs/heads/mirror/integration-frontend-apple-pass1）；部署收据 `250325c15f1ddff5d2d26c41d3e5c4ed83559d32`；手机侧回读 `d9173a937a9073e6cbac52dff5a4bc0daf102198`
仲裁章 —— issuecomment-5824811888
```

### ④ 从下一拍起的上膛方式（谁都可以跑，不用问我）
```text
交付/裁决前跑两把：
  python live_checks/receipt_cell_derivation_check_r2.py --receipt <你的收据>        # Q38：每格自证
  python live_checks/claim_coordinate_check_r2.py --text <你的正文或收据文字>        # Q43：数字带坐标
Q41=②：尺的软档今日只登记；Q43=① 是**硬**的（对我自己尤其硬）。
```

**纪律**：权威线本节未动（`5c4608ce…`）；用户库 0 读写；`demo/reset` 0；凭据 0 打印；手机链 08:37 换代后未再动。
