【0afdb49b 交付副本】入账那一块的标题（逐字）：
{title_tail}

- 收件口回执：`{inbox_receipt}`（这一代只落了这一块；重复投递会被我写手自己的 `ABORT_ALREADY_DELIVERED` 拒掉，那条腿刚用真回执验过一次，块体字节与回执 md5 相同）。
- 发布枝：`{published_ref}` 头 `{published_ref_head}`，单父=现尖 `{tip}`；对尖改动 {published_paths} 枚路径，全在 `{published_sub}/` 前缀之下，产品字节零枚。
- 分母（现读远端）：review 枝 {review_refs} 条、去重头 {distinct_heads} 枚、与他人共用同一枚头的 {refs_sharing_a_head} 条、本地不可解 {heads_unresolvable_locally} 枚、真·空提交 {heads_empty_commit} 枚；八格判语合计 {tally_sum} 条。
- 本代改判语 {labels_changed} 条，最大一对 {top_pair} 占 {top_pair_refs} 条；每路径计数移动 {count_moves_rows} 行，全部有名字，无人认领 {unattributed_count_moves} 条；对照腿 {arms_count} 枚，`every_arm_bit` = {every_arm_bit}。
- 名册（每枝一行逐枚计数）{roster_data_rows} 行 + 抬头 {roster_header_rows} 行；上线字节 {roster_bytes} + {summary_bytes}，未推整棵 {full_json_bytes} 的逐枚 JSON。
- 要点：上一代把快照形的手报成"字被线上盖掉了"是我夸了口；那批聚合标签从未进过账本，所以本手没有已发布读数要撤回。真入过账的 LOST 用词更正早在 `{prior_erratum_receipt}` 那一块做过，与本手无关。
- 等你的仍是那三件：甲（重父）、乙（ORD-0485 产品腿收口）、丙（这把尺进不进落地闸）。我没再推零变化的重切枝。未量：真机 adb、Playwright 套件、拒绝语逐句屏读。
