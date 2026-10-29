### 494abfd7 复算「本班报过的 36 笔插入」账账相符 36/36，并自报一格我自己造成的假红灯（#367）

- 假红灯先认：上一格我把落地门 trial/human_walk/_cmdr_ledger_landing_check_r300.py:83 的 check() 从「返回一个退出码」改成「返回（退出码，是否给了候选提示）」，只跑了门自己的 --selftest 与一次真 --title 命令，没同拍 grep 调用点——复算尺 trial/human_walk/_cmdr_blocks_landed_census_r301.py 有两处在拿返回值与 0 比，元组永不等于 0，于是把 36 枚其实都在账上的块全报成丢失。两处解包现已对齐（尺 :63、:76）。
- 复算读数（回执 trial/results/20261026_gozero/bw301-this-sessions-blocks-landed.txt 现读）：账账相符 36 笔、36 笔 GREEN、0 笔 RED，逐行数出的 gate: GREEN 也是 36 行，两把尺一致（回执 :119）；负控仍会咬：一枚从未发布的标题读 RED（回执 :112）。
- 机制这一格装进门里，不靠我记得：整表同时全红被单独定性为仪器故障而非丢工（尺 :97 的哨兵、:109 的第三退出码），--selftest 用「把账本换成一个空文件」复现该形状：158 枚归档全红时尺答 8 而不报「丢了 158 枚」（回执 trial/human_walk/_bw301_selftest.txt:376）。
- 这条对主上的意义：本班此前所有「INSERTED」的复算仍成立（36/36 在账），但任何一把尺整表翻红时，先按 :122 那行的第三方读数复核再动手重插——我这一班次就差点按一张假清单去重插 36 枚已在账的块。本班 0 改产品字节。
- 落点与代次：正文最后一节在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3765；本批工件的提交代次为 git 对象 92f7cdf32c0e0e17825b7a9f1c75064d587e4c03，可 git cat-file -t 取回。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
