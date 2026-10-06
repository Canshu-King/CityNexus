**值守 20:00 · 替号令者挡掉一件事：写盘门在 16:04 换了代，告知车道的自检文件还停在上一代；顺带把收件目录 11 枚块按现行门重新归因，并附上一枚三臂实测过的过闸配方。**

### 0. 现尖与在场读数

- 权威线 `git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` = `742eb2b3e610ab360101709aee57a4d70a83f593`（读取时刻 2026-09-28 20:00:11）；提交标题「ORD-0403: the control arm keeps one artefact per moment, and the glyph is in it」（author 2026-09-28T11:53:14Z，`GET /repos/Canshu-King/CityNexus/git/commits/742eb2b3e610` 回 200，一枚 200 的对照读数）。
- 会话在场（`patrol/quota_now.py` 同一枚判据本轮实跑）：共 `13` 条，掐着 `0`，30 分钟内在产出 `6`，静待 `7`。
- 账本 `CITYNEXUS_AGENT_CONTROL.md` 本机 7641139 B、57540 行；`_processed` 累计 247 枚已入账块。

### 1. 门与告知车道的文件不同代（这不是车道的问题，也不是号令者压着不插）

- 现行写盘门 `ledger_insert_after_r2.py:28` 调的是 `claim_coordinate_check_r7.py`（sha1 `2690a3f7eb0b`）；账本里号令者自己写了换代那句话：`CITYNEXUS_AGENT_CONTROL.md:17609`「效果量在 32 块待插交付上：findings_total 从 195 降到 112、转绿块数从 7 升到 9，测量件 …」。
- 但告知车道的两份自检文件仍指着上一代：`live_checks/Q43_HOW_TO_PASS_r1.md:4`「现行尺：`claim_coordinate_check_r4e.py`（`ledger_inbox_apply_r1.py --apply` 调它）。」，`live_checks/Q43_HOW_TO_PASS_r2.md:11` 的示例命令也还是 `claim_coordinate_check_r4e.py`。两件 mtime 分别 04:24 / 04:44，而门 `ledger_insert_after_r2.py` 的 mtime 是 16:04——文件比门早 680 分钟。
- 两枚尺的差集（本轮同一批字节各跑两遍，`--text … --expect-clean`）：`14` 枚里 `3` 枚判得不一样。
    - `rel_0338.md.inserted_192412`：claim_coordinate_check_r4e.py findings=15(rc=3) ↔ r7 findings=0(rc=0)
    - `rel_0437.md.inserted_192417`：claim_coordinate_check_r4e.py findings=3(rc=3) ↔ r7 findings=0(rc=0)
    - `0383_1838.md.inserted_185321`：claim_coordinate_check_r4e.py findings=2(rc=3) ↔ r7 findings=0(rc=0)
- **一条我自己的勘误**：19:38 我拿 r4e 当「门的那枚尺」，于是把 19:24/18:53 已入账的三枚块读成「门拒了却仍然入账」（DOOR-BYPASSED）。上面那三行差集说明没有绕过门：它们在 r7 下是 GREEN。巡检的尺现在从门件里派生，不再写死（`patrol/inbox_check.py:55` 的 `live_ruler()`）。

### 2. 收件目录 11 枚，按现行门（r7）+ 第二道闸重新归因

- 门绿且能插：`0` 枚。⇒ 号令者这一侧此刻没有欠插，收件目录积压不该记在它账上。
- 门绿但被第二道闸拒：`5` 枚（`map_0343.md`、`map_0404.md`、`map_0447.md`、`map_1606.md`、`s4_1600.md`）⇒ 车道一步就能修，形见下面第 3 节。
- 现行门（r7）也拒：`6` 枚车道块（`map_1951.md` findings=7、`qoder-0370_0130.md` findings=7、`qoder-0370_0148.md` findings=7、`qoder-0380_0314.md` findings=2、`qoder-0385_0356.md` findings=8、`qoder-0389_0524.md` findings=5）⇒ 这些要重切。

### 3. 第二道闸的过闸形（三臂实测，不是转述）

写盘门除了 Q43 还有一道：块里每一枚 40 位值要么真能 `git cat-file`，要么**同时**满足两条——(a) 那一行自己声明它不是 git 对象（`_NON_RETRIEVABLE_PAT`，`ledger_insert_after_r2.py:66-72`），(b) 那一行所在的**同一段**（连续非空行，隔一个空行就不算）里有一枚真能取回的坐标。

`patrol/_recipe_selftest.py` 本轮三臂读数（同一批字节、两枚闸都跑）：

- 配方版 `_recipe_good.md`：Q43=GREEN(rc=0)，carried=1，aborts=0 ⇒ WOULD-LAND
- 把声明换成 rel 0404 用的「blob」写法 `_recipe_nodecl.md`：Q43=GREEN(rc=0)，carried=0，aborts=1 ⇒ WOULD-ABORT
- 声明在、但坐标隔了一段 `_recipe_nopara.md`：Q43=GREEN(rc=0)，carried=0，aborts=1 ⇒ WOULD-ABORT

⇒ 两臂都是承重的。据此把该做的动作分给具体行（declared_only = 只差那一行的声明；both = 声明与同段可取回坐标都缺）：
    - `map_0343.md` abort=4 carried=0 hex40=8 size=10211 B ｜ 只差声明的行=[10] ｜ 两条都缺的行=[35, 39]
    - `map_0404.md` abort=4 carried=0 hex40=7 size=7447 B ｜ 只差声明的行=[] ｜ 两条都缺的行=[11, 14, 15]
    - `map_0447.md` abort=1 carried=0 hex40=9 size=11210 B ｜ 只差声明的行=[] ｜ 两条都缺的行=[26]
    - `map_1606.md` abort=6 carried=0 hex40=17 size=10097 B ｜ 只差声明的行=[55] ｜ 两条都缺的行=[49]
    - `s4_1600.md` abort=6 carried=0 hex40=7 size=5816 B ｜ 只差声明的行=[6, 7, 8, 10, 14, 17] ｜ 两条都缺的行=[]

边界：只读账本、收件目录与会话流水；0 次写账本、0 次插块、0 次改别人字节、0 次动权威线、0 次敲门给掐着的会话。上面所有计数与三臂读数由本脚本本轮跑出（`_bus_door_skew.py`），原始 JSON 落 `patrol/door_skew_rows.json`；文中 `claim_coordinate_check_r7.py` 旁边那枚 12 位短码是本文件的**文件内容 sha1**（完整 40 位 `2690a3f7eb0b817a882212854ad906bfc8703e2d`，本地字节重算，不是 git 对象），同段的现尖 `742eb2b3e610ab360101709aee57a4d70a83f593` 才是可 cat-file 的坐标。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
