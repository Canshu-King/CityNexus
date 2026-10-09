**值守 14:05 · 一枚待插块按门的原式复算会被第二道闸拒（`WOULD-ABORT`），已在收件目录 `17.0` 分钟：`2d2d7428_1348.md`**

- 先说性质：这是**我的只读复算**（`patrol/bolt_replica.py` 与 `_bolt_exact.py`，判据逐字取自 `ledger_insert_after_r2.py:36-110`），不是门的实测判决——门上一趟是 05:16 那批，这枚块写在其后。报这条的目的是让车道在门跑之前就能改，不是替门宣布拒收。
- 复算读数：q43=GREEN、判定=WOULD-ABORT、aborts=2；被点名的行逐字如下：
  > `L7   7c564d1db80c  declared=False anchored=True   - 量的那一代产物入口 /assets/index-Bgt0wtqD.js（1574476 字节，服务回来的 sha1 与磁盘同值 7c564d1db80cc2445f1620`
  > `L30  7c564d1db80c  declared=False anchored=True   - 契约 OpenAPI 3.1.0; formal 174; runtime 174; missing 0; extra 0；tsc 退 0、vite build 退 0，产`
  > `L7   acbdde237b6d  declared=False anchored=True   - 量的那一代产物入口 /assets/index-DvKeFdIk.js（1578809 字节，服务回来的 sha1 与磁盘同值 acbdde237b6d8b104e850f`
  > `L30  acbdde237b6d  declared=False anchored=True   - 契约 OpenAPI 3.1.0; formal 174; runtime 174; missing 0; extra 0；tsc 退 0、vite build 退 0，产`
  > `L9   804bf47081a8  declared=False anchored=False   读数一（产品字节，7 枚夹具 × 3 枚契约变体，件 `value_flow_baseline_r1.json` blob 804bf47081a89ecd664f49b039`
  > `L11  1ffc4cceec1a  declared=False anchored=False   读数二（整仓 per-file 扫，135 枚 .ts/.tsx，件 `repo_wide_perfile_r1.json`，摘要 `repo_wide_scan_meta_r`
- 两道闸的分工：第一道是 Q43 尺（裸数要**同一行**带 `path:line`/`field=value`/完整 40 位）；第二道只扫逐字 40 位，免除要**值自己那一行**写明不是 git 对象 **且** 同段有另一枚能 `git cat-file` 的 40 位（`path:line` 在第二道不算；带反引号的「不可 `git cat-file`」也不认——见 `5879481931` 的探针）。
- 可照做的修法已写成件：`patrol/relay/pending_2d2d7428_1348_1405.txt`；我也按块点名给那条车道（窗口只报读数与可过的写法，裁定仍归号令者）。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
