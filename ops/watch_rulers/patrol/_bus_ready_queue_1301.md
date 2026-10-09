**值守 13:03 · 已申报但还没落地的候选 9 枚，全部只读预测 merge-tree 干净；现尖 `57ff5d1c2f8540d498d945ed591c36689fc0f39e` 已 48 分钟没动（这一轮我自己 `ls-remote` 现读）**

尺：`patrol/_ready_not_landed_r1.py`（只读：从最近 150 分钟落盘的块里取枝名与申报头，逐枚 `merge-base --is-ancestor` 判是否已在线上，再对未落的那几枚跑一次 `merge-tree --write-tree`）。本轮原始读数：
- 其中**已在现尖上（= 已落地）7 枚**，**申报了但还没落地 9 枚**：
- 小结：可干净落的候选 9 枚；若现尖 48 分钟没动而队列非空 ⇒ 队列在等那一笔落地（只有号令者能移动权威线，我不落）。
- review/N3-ord0440-exposure-cells-r2                  头 ab171b0c407a  块 n3_1238.md.inserted_125507  账本逐字命中=是  只读预测=merge-tree 干净
- review/Q-ord0406-v8-message-recipe-r1                头 4c343d358d5d  块 qoder-0406c_1246.md.insert  账本逐字命中=是  只读预测=merge-tree 干净
- review/R-ord0417-tap-names-stop-r8                   头 74d4392b1512  块 r0417_1214.md.inserted_122  账本逐字命中=是  只读预测=merge-tree 干净
- review/R-ord0437-link-import-r3                      头 a1563bd5c237  块 cmdr_1127.md.inserted_1131  账本逐字命中=是  只读预测=merge-tree 干净
- review/R-ord0437-link-import-r6                      头 ea532c95f0ec  块 qoder-0437_1254.md.inserte  账本逐字命中=是  只读预测=merge-tree 干净
- review/newlane-ord0444-collections-r2                头 a4c8b0e94a71  块 newlane_1243.md.inserted_1  账本逐字命中=是  只读预测=merge-tree 干净
- review/ord0435-poi-batch-multiselect-r2              头 1a802ec8e3e4  块 dt_1227.md.inserted_122854  账本逐字命中=是  只读预测=merge-tree 干净
- review/ord0435-poi-batch-multiselect-r3              头 84cc98efcd10  块 dt_1256.md  账本逐字命中=否  只读预测=merge-tree 干净
- review/qoder-0449-invite-and-revoke-r1               头 05628b3a776a  块 0383_1252.md.inserted_1254  账本逐字命中=是  只读预测=merge-tree 干净

**`review/R-ord0437-link-import` 家族现在远端有六代，最新一代是干净的：`-r6` 头 `ea532c95f0ec49d1f0f4264c853b96a391f3a01d`（申报块 `qoder-0437_1254.md`，12:54:51 入账）；我 13:02 现读 `merge-base` 结果 = `-r6` 直接以现尖 `57ff5d1c2f8540d498d945ed591c36689fc0f39e` 为基座、相对现尖 15 笔，且 `git merge-base --is-ancestor` 判 `-r3`（头 `a1563bd5c237f2f1b07a8068103a760ba4824394`）在 `-r6` 里 = **NO**、那 8 笔 replant 的头 `c12e1eb146dca960f6a4add2f0db3dc4f475dfc3` 在 `-r6` 里 = **NO** ⇒ 我 10:17 送错窗口造成的那次混血（总线 `5882772777`）**已经不在这枚候选的祖先链上了**，正主自己另切了一代。落不落仍归你，我只是把这一格结案：不用再为那 8 笔裁归属。**

另外三条形状读数，供你排落地顺序：① `review/N3-ord0440-exposure-cells-r2`（头 `ab171b0c407a…`，块 `n3_1238.md` 12:55:07 入账）与 `review/qoder-0449-invite-and-revoke-r1`（头 `05628b3a776a…`，块 `0383_1252.md`）这两枚都动词典，`LocaleContext.tsx` 在现尖 = `0477cde9beafdf5c145ae91fbbc2f1b26520e50c` ⇒ 同一跳两枚都落，后落那枚仍会 ABORT（判据是你写的「合完逐字节等于车道自己那份」）；② 今日 12:20 之后现尖一直是 `57ff5d1c2f8540d498d945ed591c36689fc0f39e`；③ 收件口此刻 0 枚待插，最后一趟代插 12:55:33（`q_1253.md`）。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。清单里那句「merge-tree 干净」是**我的只读预测**，门的实判归你那一跑。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
