## 落地+换代 @2026-09-25 08:3x+08 —— **权威线两跳：`45b0a5e2` → `ef277b2d`（ORD-0274）→ `5c4608ce`（ORD-0287 按 Q40=① 由我 re-cut）**；手机换代 OVERALL GREEN，我这边手机侧回读 **新代在服、旧代仍在服**

### ① ORD-0294 的修订版我收了（尺绿才算）
```text
evidence/ord0294-hjp1-revision/o290_derived_r3.json   24,542 B  blob 37133521666190c7df3894d7fa0fcfd504cc6641
  （我本机副本现场重算 == cited == contents.sha，三路全等；不是引用它自己贴的数）
我的 r2 尺独立跑：cells 3 | overall Q38_GATE_GREEN | 硬 0 | 软 0
  B2a why tokens 7 / 命中本格读数 6；B2b 9/8；B2c 11/10；三句 why 互不相同
它自己那份 selftest_duplicate_why：cells 3、distinct 3、duplicates [] ⇒ PASS（与我独立量的同一件事）
真正拦停我的那一格现在是**判别对**了：
  b2c_restored   sha 45a3d56862fc  converged=True  executed index-C2DKD_R7.js -> index-DimRtCQm.js  user_navs=0
  b2c_noconverge sha 45b0a5e281ca  converged=False executed index-CtuiCkKf.js -> index-CtuiCkKf.js  user_navs=0
  ⇒ 未修复臂换成**没有 B2a 空闲收敛的那棵树**（就是我当时的权威尖），同一 shape 字符串、同一仪器、0 次用户导航
诚实的一面也留着：`not_run` 里 B3/A 两格写明"fixture 建好（5 棵树）但臂未跑"——**没被写成通过**。
我的 derived：B2a/B2b = VERIFIED_FIXED_WITH_DISCRIMINATING_CONTROL；
  B2c = 上面那一对我逐字核过；它主张的"第二枚判别控"我**没有独立重测**，所以我不替它签字。
```

### ② 两次落地（都只由包工头的手，ff-only，落地前一瞬重读尖）
```text
land_authoritative_ref.py ef277b2d… 期望基 45b0a5e2…  -> 读回 45b0a5e281ca ✓ PATCH force=false http 200 -> 读回 ef277b2da5df
land_authoritative_ref.py 5c4608ce… 期望基 ef277b2d…  -> 读回 ef277b2da5df ✓ PATCH force=false http 200 -> 读回 5c4608cede6c
独立复读（隔几分钟、两条路由）：`GET /commits?sha=mirror/integration-frontend-apple-pass1&per_page=1` -> `5c4608cede6c`；
`GET /git/refs/heads/mirror%2Fintegration-frontend-apple-pass1` -> 同一个 sha，父 = `ef277b2da5df`
```
**Q40=① 我用了，四条要件全量了**（不是"我做了"）：carrier 文件 `git hash-object` = `894c6d54e345dabdc4050a38f413fdaaa1a92748`，与 F 原尖的 blob **逐字节相等**；新尖上 3 轮删库重跑全绿（每轮 collected 2）；拆掉 `app/main.py` 那唯一承载 ⇒ hits 1→0、K1 FAILED / K2 passed；还原后 main.py 哈希回到改前。
收据 `evidence/ord0274-landed-generation/ord0287_recut_verify_commander.json` 3,367 B `f6017837c144c30ef6c1c693b3716372726b420d`（derived = KILLED_CANDIDATE_ALL_ROUNDS_GREEN_AND_GUARD_IS_LOAD_BEARING）。F 的原尖 `c31ba195` 与它自己的收据**一个字没动**。

### ③ 手机换代：并集在切 index 之前，工具与手机侧各读一遍
```text
干净导出：git archive ef277b2d frontend -> D:/moodle/_qoder_build_ef277b2d/frontend（node_modules 用 junction，非硬链接）
npm run build：BUILD_EXIT=0，vite/PWA 产出 dist（新 bundle 名 index-xKIGmoBz.js）
换代前两把尺：dist_hardlink_scan  hits=0 -> NO_EXTERNAL_HARDLINK_REFS
              bundle_selfreference_check_r2 --look 新导出 -> roots_actually_measured=1 dangling=0 SELF_REFERENTIAL
deploy_bundle.py（union -> 验 -> 切 index）：receipts/deploy_…_083644.json 66,507 B `250325c15f1ddff5d2d26c41d3e5c4ed83559d32` -> overall GREEN
  收据里的实测：`build_input_dirty = []`（构建输入干净，没有把别人的工作树缝进包）；`assets_union.added = [index-xKIGmoBz.js, JourneyMap-DOROX9Q5.js, maplibre-gl-JaODVDnV.js]`、
  `already_identical = [index-I45CQek8.css]`、`total_in_serve_assets = 34`；备份 `dist_bak_083634_…`（具名 5 个根文件）
  旧代记录 `generation_OLD.ref = /assets/index-CtuiCkKf.js` 且探针 200 —— **并集先做、index 后切**，这一条是有数的，不是口号
手机侧我自己回读（公网隧道 + Basic，凭据只走文件、0 打印）：post_swap_probe_0837.json 1,777 B `d9173a937a9073e6cbac52dff5a4bc0daf102198`
  / 200 命名 index-xKIGmoBz.js（1,249,346 B text/javascript）+ index-I45CQek8.css（183,897 B text/css）
  **旧代 index-CtuiCkKf.js 仍然 200 text/javascript 1,248,629 B**（并集留住，老客户端不白屏）
  动态块 JourneyMap/maplibre 200 JS；v10-sw.js 200 JS；health 与 demo/scene 200 JSON；`.js` 路径回 HTML 的数量 = 0
derived_result = NEW_GENERATION_SERVED_AND_OLD_GENERATION_RETAINED
```

### ④ 现在手机上有 / 还在候选（Q39=① 要求我说清）
```text
在手机上：ORD-0274 的三格前端交接（B2a 空闲收敛 / B2b 生命期内被认领的表单 / B2c 在飞写入的安全点）
仍在候选、不在手机上：ORD-0280（B 的归因标签，48827a9d，静态过关但那条 e2e 规格**一次都没跑过**）
                     ORD-0278 / ORD-0253（D 的 7 枚击杀只有 claimed_result，derived 归红队）
                     ORD-0281/0296（F 后端半）、ORD-0288（形状已收、代码仍扣）
落地代里新增的测试载体：ORD-0287（不进包，只在树上守门）
```
⇒ 请 D / B 按 **Q39 之后**的口径 re-parent 自己的候选到新尖 `5c4608ce`，我不替你们改产品代码（Q40=① 只覆盖"单文件且我逐字节可证"那种）。

**纪律**：已发布路径 0 覆盖 0 删除（本节新增 3 件，全 BYTE-LEVEL MATCH）；用户库 0 读写；`demo/reset` 0 次；凭据 0 打印；手机地址未变（`obligation-plain-arcade-bean.trycloudflare.com`）。
