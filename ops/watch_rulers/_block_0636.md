## 亲测 @2026-09-25 06:3x+08 —— 我把 HJ-P3 0281 那句"33 处裸 fetch / 13 处写 / 0 处计时器"**在落地代自己数了一遍**（40/17/2/0，差异有据可查，承重结论一致）；硬链接隐患**已实测归零**（35 → 0，06:23:04）；D 的候选我预核过：**可 ff-only**

### ① ORD-0281 定形 = ACCEPTED，但分母我换成了自己量的
HJ-P3 报（树 `dcae1bc9`）：33 处裸 `fetch`、13 处写、带 signal 2 处、带计时器 **0** 处。
我在**落地代** `_qoder_wt_45b0a5e`（`git rev-parse HEAD` = `45b0a5e281cae9c37715173afd3ac5778f309ca7`，我自己读的那一分钟）用同一思路数：`frontend/src` **71 个 .ts/.tsx**、**40 处 `fetch(`**、其中 method ∈ {POST,PUT,PATCH,DELETE} 的 **17 处**、写腿带 `signal` 的 **2 处**、写腿带计时器（`AbortSignal.timeout` 或 `setTimeout`+`abort` 同窗）的 **0 处**。
**40≠33、17≠13 不是谁数错**：`compare dcae1bc9...45b0a5e2` 实测两代之间 `frontend/` 改了 **8 件**，其中 6 件在 `frontend/src`，而**光这 6 个文件里就有 10 处 `fetch`**（`PlanWithAiSheet.tsx` 一件就 8 处）。⇒ 两个分母**各自对自己那代树成立，不可直接比**（正是 Q24/Q25 的形状）。
**能直接比的是承重那句**：写腿带计时器 = **0 处**（两代、两个人、两种数法一致），带 signal 的写腿 = **2 处**（两代一致）。⇒ **ORD-0281 定形 ACCEPTED**，其"只补 `readDeadline.ts:43-45` 那一格仍然红"的结论我认。
**口径写死**：我这一版是正则 + 700 字符窗口，`method` 未能解析的 23 处按读腿处理 ⇒ 分母可能偏大（**只会让我说的"17 处写"偏保守方向失真，不影响 0 计时器**，因为计时器是在同一窗口里找的）。要更严的口径请红队在 0285 之后顺手打这一枚。

### ② 那条硬链接隐患：**已经不在**（我复扫了，不是我猜的）
```text
06:35 复跑 live_checks/dist_hardlink_scan.py（同一把尺、同一对目录 + 它的新私有目录）
  serve_root=D:\moodle\_qoder_preview_20260920\dist  served_files=38  look_roots=3  hits=0  unnamed=0
  verdict=NO_EXTERNAL_HARDLINK_REFS rc=0     was: 06:xx 同命令 hits=35 rc=3
证据链（文件系统直读）：
  _hjp3_fan_sweep_0923\snap_live_dist\index.html      nlink 2->1  inode 1688849863486668 -> 281474981542849  mtime 06:23:04
  ...\assets\index-CtuiCkKf.js                        nlink=1  inode 844424934964172                      mtime 06:23:20
  ...\assets\index-ChOTTCvB.js（上一代）              nlink=1  inode 281474981542820                      mtime 06:23:04
  我在服的 _qoder_preview_20260920\dist\index.html    inode 1688849863486668 **未变**、nlink=1
```
⇒ **HJ-P3 在 06:21 收到指路后 2~3 分钟内把快照改成了真复制**（不是我动的：我的 index.html inode 一字未变，我只是被链接的那一侧）。它还把我**新旧两代资产都留下**了——那正是 `DEPLOY_BUNDLE_RETENTION` 的私有版做法。**这一格我记成"隐患已关"，不是"已修好产品"。**
新尺 `live_checks/bundle_selfreference_check_r1.py` blob `3878341a4dca3dff2127f6dbf99a131a93f4e4b7`（5,009 B）：问的是另一半——**"如果我拿这个目录去服务，它 index 里点名的文件在不在自己目录里？"** 实测三个快照根全部 `SELF_REFERENTIAL`（`dangling=0`），收据 `evidence/commander-dist-hardlink-scan/selfcheck_r1.json` `0d4f31938525447386fafdcd31dab1cc43f7c70e`（3,210 B）；复扫收据 `.../scan_r2_after_fix.json` `e115412298e6f269166f577f2cbb40c950e2bc5f`（345 B）。
**同一分钟从两个面量过的在服 bundle**：`index.html` 点名的 4 件（`index-CtuiCkKf.js` 1,248,629 B `text/javascript`、`index-I45CQek8.css` 183,897 B `text/css`、`favicon.svg` 199 B、`manifest.webmanifest` 314 B）在 **`127.0.0.1:4781` 与公网隧道两个面上都是 200 + 正确 MIME**，`dangling_or_wrong_mime = 0 of 4`。⇒ 这条用户面链子**没有**"200 但发的是 HTML"的悬空引用。

### ③ D 的候选我预核了（**不代替派生**）
```text
compare 45b0a5e2...0671704546f9c9ea1d1b57627b059124c7800803  status=ahead  ahead_by=13  behind_by=0  ⇒ 可 ff-only
16 件：frontend/** 7 件（新增 2 枚 e2e spec、改 4 件 src + 1 件 spec）· review/** 9 件（脚手架）
两单**分在不同 commit**：873266210 = 表格提交两腿带同一传输身份（0253 客户端半件）· c166bcd64 = 续押带轮次身份（0278）
```
**一条我要提前说的后果**：这棵候选改了 `frontend/src/features/planning/PlanWithAiSheet.tsx`（+25/−2，新 blob `1e100f909cfe…`）。我 r5 尺里那枚 **TRANSFERABLE 正控**钉的就是它（`58c0580b…`）⇒ **落地后那一格必然报 DRIFT**。这不是回归，是**正控的前提到期**；届时我按新代重钉 pins（`git rev-parse` 实测，不手填），**不换判据**。这正是 F 04:4x 提醒过的形状，我提前写在这里，省得将来有人把它当"指挥官的尺自己坏了"。

### ④ 现场
红队 running（0285 已实测 A7/A9 在 r5 上 rc=4，正在跑 20 臂自检与 B/C 两把；它自报的括号问题是**它自己收据构建器**的，不是我的尺）；F running（0287 第 0 问）；HJ-P3 活着——**06:23:04/06:23:20 那三次文件改写就是它做的**（② 的 inode/nlink 证据）；D/B running。**权威线未动**（`mirror/integration-frontend-apple-pass1` = `45b0a5e2…`）；用户库 0 读写；`demo/reset` 0 次；凭据 0 打印（我只把文件路径喂给仪器）。
