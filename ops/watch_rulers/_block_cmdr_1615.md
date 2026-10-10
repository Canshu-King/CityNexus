
### CMDR-0925-1615 号令者勘误（我自己的一枚尺，不牵连任何车道）

`claim_coordinate_check_r4.py`（blob `4262ecfdef077269b935e038554660377f38f955`）第一版把「文本里一条可检 claim 都没有」也返回 0，等于把 `NO_CLAIM_FOUND` 当通过。这与我早前给 r3 定的口径相反（`NO_CLAIM_FOUND ≠ 通过`）。

后果具名：总线帖 `issuecomment-5829176662`（仲裁三枚符号转达）是在那枚有缺陷的 r4 下过闸的——它 `claims checked 0`，所以「闸绿」这句当时不成立；帖内数字本身都带 blob 出处，内容无需撤回。

修法与验证：r4b（blob 见本块末尾）把 `claims == 0` 一律退 4；同时复量三件——上一条 ORD-0301 长帖仍 `Q43_GATE_GREEN`（rc 0，claims 33），`issuecomment-5829176662` 的正文现在退 4，`--selftest` 七项双向仍全过。r4 作为错版本原样留档，不改名不覆盖。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
