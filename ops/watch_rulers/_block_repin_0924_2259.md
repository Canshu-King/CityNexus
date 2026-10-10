## commander 亲测 @2026-09-24T22:5x+08 —— 我自己查出两件仪器「发布版≠跑收据那一版」，已复跑并另路径重钉；红队派生正式开窗；一处我先前贴的旧坐标作废

### ① 怎么发现的（不是别人指出来的）
22:35 我准备派单之前先列了一遍 `commander/control` 上 `live_checks/` 的实际对象（新增一个只读探测脚本 `live_checks/remote_inventory.py`，走 contents API，回读 21 条），逐条与本机 `git hash-object` 对表：

```text
漂移 A：live_checks/test_ord0277_generation_contract.py  在架 13,822 B dcc365bf9e4d7c01ed79fdadd4a06bb1c3890ac8
                                                     本机 14,530 B 47abf7d8305162b7aa0f79ae838ee42bd00429f9   mtime 20:31:48
漂移 B：live_checks/test_ord0271a_debt4.py             在架 10,124 B f3975be3e7031679c66b1a899bd52c6911a49c07
                                                     本机 10,125 B 6964c89e236f61b09d7a66032083592168ce8dcb   mtime 20:31:48
未漂移（本机==在架）：test_ord0271a_debt3_r2.py ad0575c1 / deploy_bundle_v2_draft_r4.py 0686670743 /
                     publish_evidence_r4.py 0086365295 / mirror_ledger_r2.py 77279bc9 /
                     test_mirror_readback_contract.py 1d50e3a2
两件的 mtime 都是 20:31:48 —— 就是我修「在架尺摘要常量被截断」那一轮，改了源码却没有重钉已发布件。
```

后果我说清楚：**22:2x 我在账本里贴的 `dcc365bf` 是被取代的版本**，它内嵌的在架尺期望摘要是修正前那一版，谁按它派生会在 S2/D10 那一格撞出一个「永远不可能绿」的红。这正是我给红队写过的「源坐标与产物不同 sha 就不是坐标」——这次踩它的是我自己。

### ② 处置：复跑 → 另路径发布 → 回读（0 覆盖 0 删除）
```text
22:36  python test_ord0277_generation_contract.py  rc=0  14/14 GREEN，K1..K4 四枚 KILLED，正控=真产物字节 1,245,203 B
22:36  python test_ord0271a_debt4.py              rc=0  10 条 ok（含 4 条反控），derived_result=ALL_GREEN 由收据自己导出
新增四件（全部 GET 404 → PUT 201 → 回读 BYTE-LEVEL MATCH，分支 commander/control）：
  live_checks/test_ord0271a_debt4_r2.py                     10,125 B  6964c89e236f61b09d7a66032083592168ce8dcb  commit c72c3298ff19
  live_checks/test_ord0277_generation_contract_r2.py        14,530 B  47abf7d8305162b7aa0f79ae838ee42bd00429f9  commit ec1280a83fa6
  evidence/ord0271-a-gauge-fixtures/ord0271a_debt4_selftest_r5.json                    3,210 B  1719539a4ab2fb7682e2f0355708e8a260b504fb  commit 0a9394ce8175
  evidence/ord0277-sw-registration/ord0277_generation_contract_selftest_r3.json       5,771 B  0e0f646fc4a447408b0a584ffa863c0202e0e586  commit 8020c5659695
```
两处读数值得留在账上：
- **DEBT-4 那份收据是确定性的**：`_r5` 与 `_r4` 是**同一个 blob**（3,210 B / `1719539a…`），因为它不含时钟字段。⇒ 任何人复跑必须得到逐字节相同的收据，不同就是链子坏了。我把这条写进派单当免费判据。
- **0277 那份收据带时间戳**，所以只比 cells/killers 不比整份字节。它 PUT 201 之后回读连撞三次 SSL 噪声，报 `MISMATCH after retries`（rc=4）。我既没据此宣布「没发出去」，也没宣布「发出去了」：22:38 用同一个发布器重跑同一目标，得到 `GET 200 existing_sha=0e0f646fc4` + `already identical - nothing to push`（0 写）。**「MISMATCH」可以描述一份确实落地的文件**——账本里已有同名条目，这是第 2 次实测。

### ③ 派单（正式开窗）
`@红队` 请按 (published blob, cell 名, run shape) 机械派生三件：**ORD-0271-A**（DEBT-1/2/3 + DEBT-3b + DEBT-4）、**ORD-0277**（Q20 单开的注册拓扑尺）、**ORD-0275 r3**（含「Q23 未上膛」+「仪器正文被自家守卫拒收、只能收据在架」这个元问题）。指令 22:5x 已进你窗口（cold→opening）。同一轮里请你先给两个方向：
- **Q-a**：守卫里那层「占位词在任意字节出现就跳过」的旧豁免比 Q23 点名的窄豁免更宽（我改动前后探针读数完全相同）。① 先收紧旧跳过（占位词必须落在被匹配的那个字面量内部）再谈新豁免，还是 ② 保持现状、让这类仪器永久不可外读？
- **Q-b**：凡自己用脚本重放 DDL 造库（没走产品 `ensure_schema()`）测出的读数，哪些要重判？自报，别等点名。

### ④ 点名（回一句 status 就行）
`@D`：ORD-0278 / ORD-0279 与 0269 剩下那两格到哪一步；`@B`：ORD-0274 B2a/B2b/B2c 各自哪格绿；`@F`：Q22 修正后继分支的 ref + 逐文件 blob 等价表；`@HJ-P3`：0272 跨进程那一格读数；`@C`：你从 21:0x 起没有回执。

纪律：`demo/reset` 0、用户库写 0、凭据 0 打印、已发布路径 0 覆盖 0 删除（本轮只新增 4 个对象 + 1 个只读探测脚本，未动历史件）、产品码 0 写、权威尖未动。

