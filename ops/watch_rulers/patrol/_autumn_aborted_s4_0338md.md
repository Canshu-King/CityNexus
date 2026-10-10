**值守 04:43 · 一枚块尺绿但被第二道闸拒，在收件目录等了 `64.3` 分钟：`s4_0338.md`**

- 现读：`patrol/bolt_replica.py`（对现行门的只读副本）报 q43=GREEN、bolt=WOULD-ABORT、aborts=2；被拒的行逐字如下：
  > `L34  5b8ba3a3ec3a  declared=True anchored=False   1. ORD-0424 只重取了基线（现尖 dccd13ad…，`tools/cnx_copy_tiers_r1.py --list-fallbacks`：扫 98 文件、ti`
  > `L36  11eee48d8b0a  declared=False anchored=False   3. ORD-0361（地图点选）rebase 到现尖仍 pending，枝 `review/S4-ord0361-map-tap-selection` 还停在 11eee48`
- 这一类不是「等代插」，是**插不进去**：门的两条臂里，第二道闸要求每个 40 位十六进制值要么 `git cat-file` 可取，要么它**自己那一行**写明不可取回**且**同一段落里有可解坐标。
- 我已经把这两条修法写成一份车道能直接照做的件：`patrol/relay/pending_s4_0338_0443.txt`，并按块点名给那条车道（窗口消息只催办与报数，裁定仍归号令者）。
- 同轮其他读数见 `patrol/round_watch.log`。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次删除、0 次动权威线、0 次点别人的批准。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
