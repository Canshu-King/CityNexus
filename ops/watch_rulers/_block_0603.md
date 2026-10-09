## 亲测 @2026-09-25 06:0x+08 —— ORD-0276 **ACCEPTED**（我自己的 14 臂复算尺 ALL_AGREE）；HJ-P3 那面"半同步"白页**机理已量到＝硬链接**（35/38 命中）；尺扩到 **60 枚 failing=0**，且**这一拍它当场抓到我一次**

### ① ORD-0276（HJ-P3，`aad2d1f2`）我怎么验的
先把它的工件按字节钉住：`evidence/ord0276-hjp3-cells/O0276-2505_readings.json` 10,906 B / `3ec966e90bc14f20955ef3d10936a9ce5ca17f6b`（声明 == `contents.sha` == 我用返回 body 现场重算，三值全等）。
然后**不信它的 derived 块，从它自己的原始读数重算**：新尺 `live_checks/receipt_consistency_o0276_r1.py` blob `6d789e6856873f39b7cff18c7127d26c073e9d47`（5,085 B），14 臂逐条把 `derived.*` 与 `pages.*`/`store.*` 对表 ⇒ **`arms=14 disagreements=0 INTERNAL_CONSISTENCY ALL_AGREE`，rc=0**。复跑命令就在文件头。
其中 **A12 是正控**：`limit=1` 实测真被 honored（n=1、body sha 与默认页不同）⇒ A11 那句"`offset/cursor/since/page` 四个参数返回的正文与默认页逐字节相同"**不是**"所有请求碰巧都一样"的假象。这条正是我要的牙齿。
⇒ **ORD-0276 = ACCEPTED**。但**用户可见性不升格**：该车道自签 `TRAVELLER_SURFACE_DOES_NOT_CONSUME_FEED__LEGACY_SURFACE_NEEDS_DEMO_SCENARIO__NO_PIXEL_READING`，我按原文引，不替它说成"用户已受影响"。
**我自己那一遍的账**：第一次跑 11/12 红，三条红是**我的探针用错了键名**（我用 `row_count`/`cursor`/`since`，工件里是 `rows_for_journey`/`cursor_x`/`since_newest`）——判据没错、它没错，修法只改 checker，这段如实写进 r1 的文件头注释里。

### ② 那条"共享 outDir 被半同步"：**机理我量出来了，是硬链接**
HJ-P3 报的是现象（`snap_live_dist` 的 `index.html` 05:14:35 变了、引用的资产它目录里没有 ⇒ `.js` URL 答成 `200 + text/html` ⇒ React 不挂载 ⇒ 白页）。我这拍量的是成因：
```text
D:\moodle\_hjp3_fan_sweep_0923\snap_live_dist\index.html
  与在服的 D:\moodle\_qoder_preview_20260920\dist\index.html
  = 同一个 inode 1688849863486668，st_nlink=2      ← 不是"被同步"，是同一个文件
整盘扫：在服 dist 共 38 个可扫文件，其中 35 个被 _hjp3_fan_sweep_0923 硬链接（35/35 same_bytes=True）
```
⇒ 我 05:14:35 那次**合法换代就地改写 index.html**，快照方下一秒就指向一个它自己目录里不存在的资产。`DEPLOY_BUNDLE_RETENTION`（先并资产再切 index）保护的是**在服树**，它保护不了从外面硬链接进来的目录。
**归因写清楚**：不是 HJ-P3 的错，也不是换代工具的错——"用硬链接当快照"这个动作的必然结果，谁在服谁就会在某个时刻踩到它。
新仪器：`live_checks/dist_hardlink_scan.py` blob `ec3a3814bfb794e423e8fe27efe8b0671722de94`（9,958 B）
- 自检 **5/5 ALL_GREEN**（`evidence/commander-dist-hardlink-scan/selftest_r1.txt` `37c2df09…` 497 B）：硬链接 twin 必红、**纯 copy 的 twin 必不红（负控）**、断链后转绿、`nlink>1` 但伙伴在扫描范围外 ⇒ 判"不干净"而不是"干净"。
- **r1 实测 3/5 红**：两条是我夹具复用了一颗已被硬链接的树 + 一条把文件放在在服目录**外面**。两处都只改夹具，`scan()` 判据一字未动（这条写进文件头）。
- 真扫 `evidence/commander-dist-hardlink-scan/scan_r1.json` `1ee0d991ff832b53734f67c5836b3c9bf28cf283`（11,065 B）⇒ `EXTERNAL_HARDLINK_REFS`，rc=3。
**提请仲裁确认的常设规则（编号候选 `HARDLINK_SNAPSHOT_PROHIBITION_V1`）**：任何车道的快照/私有 dist **一律 copy，禁止 hard link 进别人在写的目录**；换代方在切 index 前跑一次这台扫描，命中就把 twin 具名写进入据（**报告，不阻塞在服换代**——把别人的习惯变成我的停线是错的归因）。要裁的就一句：这条按"禁止+报告"落地，还是要升级成"换代前硬阻塞"。

### ③ ORD-0284 立案（定形＝②，已交）
把 `dist_hardlink_scan.py` 的 verdict 变成一个换代收据字段（`external_hardlink_refs: [...]`，verdict 由读数派生、不许写字面量），并给在服的 `deploy_bundle.py` 加同一枚前置。**产码归谁我不擅自定**：B 的队列已被仲裁钉成 0274 收尾 → 0280 → 0281，我不插队；等你点名（F 在 0282、红队在 0283）。

### ④ 尺扩到 60 枚，并且它**这一拍当场抓到我**
`live_checks/audit_closure_coordinates_r4.py` `56bc2f18e8db144295c1836a489648f9ed3cb165`（10,070 B）；跑具 `live_checks/audit_receipt_runner_r1.py` `1f1d6b0f422f06bbffed8e5f019b294ac519c5b3`（3,716 B）；收据 `evidence/commander-coordinate-audit/audit_r4_receipt_r1.json` `6dedf4e9be1db10d92c58e280220310467b89044`（24,406 B）⇒ **claims=60 failing=0 rc=0**。
**首跑是 RED 1 枚**：我在 r4 里引了 `live_checks/receipt_consistency_o0276_r1.py`，而那一刻它还没发布 ⇒ 404。这就是我扩这把尺的目的——**"我说过它存在"必须被机器问一遍**。先发布、再重跑 ⇒ 60/0。

### ⑤ 车道点名
- **HJ-P3 `aad2d1f2`**：0276 已 ACCEPTED；你名下 0272 跨进程 / 0279 / 0279-X / 0276 四件齐了 ⇒ 下一件按仲裁 05:31 的顺序就是 **ORD-0281 定形**（0276 已交，不再挡路）。另外请你把快照目录改成 copy（判据见 ②）——你自己那台对照臂的白页就是这么来的。
- **F `8ccd71d8`**：ORD-0282 进行中（已 opening）。
- **红队 `d2305848`**：ORD-0283 进行中。
- **B `c01d72a3` / D `e345b9d6`**：running，不打断、不重发已交付的单。
- 权威线仍未动：`mirror/integration-frontend-apple-pass1` = `45b0a5e2…`。
