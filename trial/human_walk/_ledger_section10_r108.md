## 10. 走查臂的浏览器档案与收据同名冲突：一把会咬人的尺（r108）

### 10.1 这一段是为什么存在

本轮最贵的三次教训都不是产品缺陷，而是量具自己污染了自己：

- `_ba_arm_switch_on_draft_430_r103.mjs` 与第一版 `_bb_arm_three_labels_430_r104.mjs` 是从 `_az_arm_layer_switch_430_r102.mjs` 复制出来的，只改了收据名和截图名，`launchPersistentContext` 里的 profile 目录仍是 `_chrome_gozero_az102`。结果 bb104 撞在 profile 锁上死掉，ba103 的读数来自一台 az102 仍在驱动的浏览器的第二个页面。那份读数看起来像一次独立走查，实际不是。
- `_aq_arm_clean_430_r92.mjs` 自己的 profile 早就改成了 `_chrome_gozero_aq99`，但同一条 cp 链后面五支臂还写着 `_chrome_gozero_aq92`。
- 三支收据文件被两支臂同名写入，谁后跑谁把谁的证据盖掉。

靠"我记得下次改名"不是一条规则，所以把它做成尺：`trial/human_walk/_arm_collision_ruler_r108.py`。它读 `trial/human_walk/*.mjs` 每一支臂自己声明的 profile 目录与收据路径，任何一枚被两支臂共用就是红。

### 10.2 尺的负对照跑的是真扫描，不是我手写的字典

`scan()` 是真正被 `main()` 使用的那个函数（`trial/human_walk/_arm_collision_ruler_r108.py:33`）。`control()`（同文件 `:61`）在临时目录里落下两支合成臂，让它们真的共用一个 profile 与一枚收据，再对那个目录跑同一个 `scan()`：

- 合成臂数必须数到两支、且两支都声明了 profile 或收据；
- 必须恰好抓到一枚 profile 冲突与一枚收据冲突；
- 抓到冲突还不够，必须把两个共用的主人一起点出来。

任何一条不满足，尺退出 `2` 并打印 `SELFTEST_RED`，不会把这棵树报成干净。这是为了避免上一条记忆里那种"吞掉判语的尺"——一把看不见冲突的尺如果自称绿，比没有尺更坏。树里找不到 `trial/human_walk` 或臂数为零同样退出 `4`，也不算通过。

### 10.3 修的是臂，不是尺（没有豁免名单）

尺第一次跑（同一枚扫描，改名之前）报 `COLLISIONS 7` groups、`RULER_RC=1`，7 组就是 10.1 里那些。我没有给旧臂留豁免名单，也没有把阈值调松，而是逐支改名，让每支臂真正只拥有一枚 profile 与一枚收据：

| 改名 | 支数 | 改动 |
| --- | --- | --- |
| profile 目录 | 9 处 | `_dinner_r43` → `_chrome_gozero_r43`、`_my_trips_r39` → `_chrome_gozero_r39`、`_ar_..._r93` → `_chrome_gozero_ar93`、`_as_..._r94` → `_chrome_gozero_as94`、`_at_..._r95` → `_chrome_gozero_at95`、`_au_..._r96` → `_chrome_gozero_au96`、`_av_..._r97` → `_chrome_gozero_av97`、`_ba_..._r103` → `_chrome_gozero_ba103`、`_bd_..._r106` → `_chrome_gozero_bd106` |
| 收据文件名 | 3 处 | `_go_to_active_chrome_r10` → `go-active-${TAG}-full-r10.txt`、`_go_continue_chrome_r9` → `go-active-${TAG}-r9.txt`、`_half_day_r34` → `half-day-430-r34.txt` |

每一对里编号较早的那支保留原名，所以从这一代起只有它还会写那个名字。改名只动了字符串字面量：替换前先数命中（12 处全部恰好一次，任何一处不是一次就整体 ABORT），替换后逐支 `node --check` 复跑，12 支全部无输出通过。磁盘上已有的收据与截图没有被移动、重命名或删除。

### 10.4 已经混在一起的那三份证据（交底，不假装修好）

`trial/results/20261026_gozero` 里现存三份文件的内容是两支臂里后跑那一支的，前一支的内容不可恢复。我没有在新名字下复制一份，因为一份换了名字的副本会被读成"另一次独立走查的收据"，而它不是：

- `go-active-390-full.txt`，`7079` 字节，sha1 前缀 `333b83508711` — 主人为 `_go_to_active_chrome_r7.mjs` 与 `_go_to_active_chrome_r10.mjs`
- `go-active-390.txt`，`1968` 字节，sha1 前缀 `782512970a67` — 主人为 `_go_to_active_chrome_r6.mjs` 与 `_go_continue_chrome_r9.mjs`
- `half-day-430.txt`，`1913` 字节，sha1 前缀 `fbf20bb34c13` — 主人为 `_half_day_r33.mjs` 与 `_half_day_r34.mjs`

凡引用这三份文件的旧结论，从现在起要读成"两次运行里的一次"，不能读成一次运行的收据。逐条写明在 `trial/results/20261026_gozero/arm_collision_disclosure_r108.txt`。

### 10.5 装上膛

尺挂进已有的门禁作业 `assistant-screen-text`，作为第三个测量步骤（`.github/workflows/v3-rescue-release-gate.yml:95`），那一步已经带 `fetch-depth: 0` 的检出，前两步（裸错误串尺与它的历史对照）在它前面。落地前按 CI 的命令行逐条本地重放：

- 裸错误串尺：`SELFTEST_OK negative=2 positive=0`、`RAW_ERROR_SINKS 0 files_checked=17`
- 历史对照：`CONTROL_OK old_caught=7 current=0`
- 同名冲突尺：`SELFTEST_OK synthetic pair sharing profile+receipt was caught by the same scan()`、`ARMS files=306 declaring_profile_or_receipt=86 profiles=33 receipts=85`、`COLLISIONS 0`

三条退出码都是 `0`。改名前那一次同样的尺给出 `COLLISIONS 7` groups 与非零退出，所以这一步不是恒绿。

### 10.6 坐标与没做到的事

提交 `5263da08da`（父提交 `a647818122`），可 `git cat-file -t` 取回；尺在 HEAD 的 blob 是 `2761bf8bf6195fba459c6f5d2a0aceefadf50602`。分支 `rescue/v3-final-departure-20261022` 推后 `git ls-remote` 回读到的枝尖就是这枚 40 位，逐位相同。本段只提交这一件事相关的 15 枚文件；`frontend/` 下别人在写的改动、`_bb_arm_three_labels_430_r104.mjs`、`_guardian_unavailable_r1.py` 一并未碰（工作树里仍有其余 49 处脏文件，都不归本笔）。

没做到的两条要说清：截图名不在尺的管辖范围内——`shot()` 的名字大量是参数化的，实测 39 组同名里绝大多数是 `${name}` 这类变量拼接，真正需要的是"每支臂自己的一套截图前缀"，这一步还没做，所以 aq3 那一张被后一轮覆盖的事故今后仍可能发生；GitHub Actions 上这一步的 step 级成功读数本轮没有回读（只在本地按同一条命令行重放了三步），要等下一次推送后按 run-id 读日志才算证到。
