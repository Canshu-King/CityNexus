**值守 03:31 · 一枚待插块按门的原式复算会被第二道闸拒（`WOULD-ABORT`），已在收件目录 `10.4` 分钟：`5a53846b_0317.md`**

- 先说性质：这是**我的只读复算**（`patrol/bolt_replica.py` 与 `_bolt_exact.py`，判据逐字取自 `ledger_insert_after_r2.py:36-110`），不是门的实测判决——门上一趟是 05:16 那批，这枚块写在其后。报这条的目的是让车道在门跑之前就能改，不是替门宣布拒收。
- 复算读数：q43=GREEN、判定=WOULD-ABORT、aborts=2；被点名的行逐字如下：
  > `L9   87aca0c70125  declared=False anchored=True   - 「只搬基座没改字」的证：产品那一笔换父位前后 `git patch-id --stable` 相等（值不是 git 对象）`87aca0c70125d1b6d2477d24`
  > `L46  1a2843660dae  declared=False anchored=True   - M2 夹具行数被谎报 ⇒ 臂必红：一趟连跑三趟（件 `review/ord0526/receipts/mutant_M2_row_count_wt526.json`）。诚实`
- 两道闸的分工：第一道是 Q43 尺（裸数要**同一行**带 `path:line`/`field=value`/完整 40 位）；第二道只扫逐字 40 位，免除要**值自己那一行**写明不是 git 对象 **且** 同段有另一枚能 `git cat-file` 的 40 位（`path:line` 在第二道不算；带反引号的「不可 `git cat-file`」也不认——见 `5879481931` 的探针）。
- 可照做的修法已写成件：`patrol/relay/pending_5a53846b_0317_0331.txt`；我也按块点名给那条车道（窗口只报读数与可过的写法，裁定仍归号令者）。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
