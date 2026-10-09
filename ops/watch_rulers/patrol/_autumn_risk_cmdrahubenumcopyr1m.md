**值守 20:10 · 一枚车道枝被现尖追成「两侧都改过」⇒ 按复切判据预测 ABORT（只读预测，门的实判归 `--apply`）**

- cmdra-hub-enum-copy-r1-m2                    -r1  头 7427f549 落后 23 笔  动  2 枚｜单侧改过 0 枚｜**两侧都改过 2 枚** ← frontend/src/features/planning/PlanRankingPanel.tsx：三侧互异；frontend/src/lib/displayVocabulary.ts：三侧互异
- 判据来源：`patrol/_hotfile_contention_r2.py`（`ls-remote` + `merge-base` + `ls-tree -r` 缓存，逐枚对该枝自己动过的每一枚文件比 base/车道/现尖三份 blob；两侧改到**同一字节**不算争用，这条是 10:14 我修掉的假报形）。
- 我没有动任何枝；这条只为了让落地顺序与 rebase 提醒早一点到车道。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
