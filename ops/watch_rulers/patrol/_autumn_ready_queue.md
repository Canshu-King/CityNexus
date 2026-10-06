**值守 23:17 · 队列又在等落地：现尖已 118 分钟没动，已申报未落地候选 18 枚**

- review/0296-write-deadline-f                         头 6d041dcce11d  块 0afdb49b_2259.md.inserted_  账本逐字命中=是  与现尖差 112/559 枚  只读预测=merge-tree 退 128
review/0afdb49b-missing-ref-dossier-r1               头 3c63b3d0ec02  块 0afdb49b_2120.md.inserted_  账本逐字命中=是  与现尖差 5/4401 枚  只读预测=merge-tree 退 128
review/0afdb49b-recoverable-coord-check-r1           头 d45c2ab2735b  块 0afdb49b_2259.md.inserted_  账本逐字命中=是  与现尖差 5/5 枚  只读预测=merge-tree 干净
review/1ba48dbf-anchor-drift-rulers-r4               头 9dfd376d0629  块 1ba48dbf_2050.md.inserted_  账本逐字命中=是  与现尖差 1/4390 枚  只读预测=merge-tree 退 128
review/1ba48dbf-conflict-hunk-evidence-r7            头 80efd0da4eef  块 1ba48dbf_2133.md.inserted_  账本逐字命中=是  与现尖差 2/2 枚  只读预测=merge-tree 干净
review/2d2d7428-ord0561-c4-drift-r1                  头 2e2ddbaf72ee  块 2d2d7428_2308.md.inserted_  账本逐字命中=是  与现尖差 1/1 枚  只读预测=merge-tree 干净
review/2d2d7428-ord0561-control-set-board-gated-r1   头 dcc7d9f216d1  块 2d2d7428_2207.md.inserted_  账本逐字命中=是  与现尖差 1/1 枚  只读预测=merge-tree 干净
review/2d2d7428-ord0561-readonly-board-r1            头 0a2a723083b5  块 2d2d7428_2301.md.inserted_  账本逐字命中=是  与现尖差 1/1 枚  只读预测=merge-tree 干净
review/6a773af1-ord0556-route-sweep-r1               头 9e933b975d38  块 6a773af1_2122.md.inserted_  账本逐字命中=是  与现尖差 168/4227 枚  只读预测=merge-tree 退 128
review/82f55d8a-journeytrash-name-anchors-r2         头 06dd76444df4  块 82f55d8a_2118.md.inserted_  账本逐字命中=是  与现尖差 158/4186 枚  只读预测=merge-tree 退 128
review/82f55d8a-trash-zh-wording-r2                  头 06dd76444df4  块 82f55d8a_2118.md.inserted_  账本逐字命中=是  与现尖差 158/4186 枚  只读预测=merge-tree 退 128
review/8ac89982-ord0573-sections-copy-table-r1       头 f66c81770b7f  块 8ac89982_2234.md.inserted_  账本逐字命中=是  与现尖差 12/12 枚  只读预测=merge-tree 干净
review/8ac89982-ord0577-entry-gap-width-r1           头 4a7f8991cea6  块 8ac89982_2118.md.inserted_  账本逐字命中=是  与现尖差 5/4401 枚  只读预测=merge-tree 退 128
review/8ac89982-ord0578-token-route-chrome-r2        头 748a08407d02  块 8ac89982_2129.md.inserted_  账本逐字命中=是  与现尖差 5/5 枚  只读预测=merge-tree 干净
review/R-od0471-evidence-r1                          头 2a5e05ec2b6a  块 0afdb49b_2259.md.inserted_  账本逐字命中=是  与现尖差 190/2128 枚  只读预测=merge-tree 退 128
review/cff87c64-english-arm-enum-echo-r2             头 5e32c84ca673  块 0afdb49b_2259.md.inserted_  账本逐字命中=是  与现尖差 168/4120 枚  只读预测=merge-tree 退 128
review/cff87c64-ord0562-english-count-nouns-r8       头 a5131437e14d  块 cff87c64_2058.md.inserted_  账本逐字命中=是  与现尖差 15/4400 枚  只读预测=merge-tree 退 128
review/newlane-ord0444-collections-r5                头 f5aa54beaefd  块 0afdb49b_2259.md.inserted_  账本逐字命中=是  与现尖差 141/1859 枚  只读预测=merge-tree 退 128
- 尺 `patrol/_ready_not_landed_r1.py`（只读：块的枝名+申报头 → `merge-base --is-ancestor` 判是否已在线上 → 未落的跑一次 `merge-tree --write-tree`）。
- 我不落地、不写账本、不动权威线；这条只是把那批「已经能落」的名字摊在你眼前。

边界：值守 0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次改动 cron。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
