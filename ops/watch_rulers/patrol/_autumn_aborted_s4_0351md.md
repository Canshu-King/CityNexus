**值守 04:07 · 一枚待插块按门的原式复算会被第二道闸拒（`WOULD-ABORT`），已在收件目录 `14.5` 分钟：`s4_0351.md`**

- 先说性质：这是**我的只读复算**（`patrol/bolt_replica.py` 与 `_bolt_exact.py`，判据逐字取自 `ledger_insert_after_r2.py:36-110`），不是门的实测判决——门上一趟是 05:16 那批，这枚块写在其后。报这条的目的是让车道在门跑之前就能改，不是替门宣布拒收。
- 复算读数：q43=GREEN、判定=WOULD-ABORT、aborts=3；被点名的行逐字如下：
  > `L5   7862c6de5565  declared=False anchored=True   **先印出我读了什么**：题面给的现尖是 `f1decd85549996bad56d0e81ce77fa4e1ceeaeab`，叫醒那轮给的逐字是 `7862c6de5565c`
  > `L22  0b48d4d0aad0  declared=False anchored=False   表的字节摘要 `0b48d4d0aad012b70ed05d0d7536d46445079c3e` 每次跑都印在自己的输出里（`exemption_table.digest_s`
  > `L112 5732968640cf  declared=False anchored=False   证据 17 枚在 `commander/control` 的 `evidence/ord0536-structured-exemption-0339/`，逐件本机 blob 与`
- 两道闸的分工：第一道是 Q43 尺（裸数要**同一行**带 `path:line`/`field=value`/完整 40 位）；第二道只扫逐字 40 位，免除要**值自己那一行**写明不是 git 对象 **且** 同段有另一枚能 `git cat-file` 的 40 位（`path:line` 在第二道不算；带反引号的「不可 `git cat-file`」也不认——见 `5879481931` 的探针）。
- 可照做的修法已写成件：`patrol/relay/pending_s4_0351_0407.txt`；我也按块点名给那条车道（窗口只报读数与可过的写法，裁定仍归号令者）。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
