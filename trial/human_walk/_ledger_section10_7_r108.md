### 10.7 上膛后的两处补账：门禁 step 级读数，以及这条尺本来根本不会被触发

（本节把 §10.6 末尾那句「GitHub Actions 的 step 级成功读数本轮没有回读」结掉，并记一笔新发现的形制缺陷。）

**step 级读数（现取，非推断）**。推送 `5263da08da` 触发的 run `40738615975` 已回读，作业
「A refused request must never reach the screen verbatim」结论 `success`，九步逐一出声：
`Set up job:success`、`Run actions/checkout@v4:success`、`Run actions/setup-python@v5:success`、
`Scan every screen setter for a raw client error string:success`、
`Prove the ruler still catches the leak that really reached a traveller:success`、
**`Prove no two walk arms drive one browser or write one receipt:success`**、两条 Post 步 `success`、
`Complete job:success`。同一次 run 里另两枚作业 `Backend signed journey and classroom integration` 与
`Frontend typecheck and Vite build` 也都是 `success`。这一步是 `success` 而不是 `skipped`，所以 §10.6 里那条
未证的事现在证到了；尺的本地重放与 CI 的命令行逐字相同（三条命令，退出码都是 `0`）。

**新发现的形制缺陷：这条尺挂在门禁里，但门禁不看走查臂**。`v3-rescue-release-gate.yml` 的
`on.push.paths` 原本只列 `backend/**`、`frontend/**`、`contracts/**` 与工作流自身，没有 `trial/**`。
也就是说：一次「新增一支共用别人 profile 或别人收据的臂」的推送，恰好不会触发那把专门查这种事的尺——它只在
产品代码变动时跑，而那正是它不可能出错的情形。上面两枚尺的提交本身能绿，是因为它们同时改了工作流文件，
属于「改了门才开门」，不是门本来会开。修法是把 `trial/**` 也加进 paths（`.github/workflows/v3-rescue-release-gate.yml:14`），
提交 `95f8277180`，推送后 run `40739418148` 结论 `success`。
代价说清：`trial/**` 的推送此后也会跑后端与前端两枚作业，多花几分钟 CI；没有加按路径分流的作业级 `if:`，
因为那会给「本该跑的腿被静默跳过」再开一扇门，而顶部已有的 `concurrency` + `cancel-in-progress: true`
（同文件 `:23`）会把连发的臂推送压成一趟运行。

**尺又长了一条腿：截图名**。第一版只管 profile 与收据，而真正吃掉一张图的正是同名截图（aq3 那张被后一轮覆盖），
所以那条已声明的缺口当时仍然开着。现在 `scan()` 同一枚函数也收字面量截图名——`shot("x")`、
`path: "${DIR}/x.png"` 两种写法（`trial/human_walk/_arm_collision_ruler_r108.py:30`），并且**只**收字面量：
实测若把 `shot(\`${name}\`)` 这类由调用方传参、或带 `${TAG}` 前缀的名字一起算，39 组同名会被当成冲突，
把两枚真的埋在里面。负对照同步长这条腿：合成臂现在共用 profile、收据与一枚字面截图名，`control()`
不仅要求三组冲突各恰好一枚，还点名抓到的必须是 `shared-screen-before` 那枚（同文件 `:100`）——少一条就
`SELFTEST_RED` 退出 `2`，不会报树干净。第一次跑这条新腿报 `SHOT_CLASH half-day-430-before` 与
`SHOT_CLASH half-day-430-after`，主人都同为 `_half_day_r33.mjs` 与 `_half_day_r34.mjs`；改法是给后者自己的
帧名 `half-day-430-r34-before` / `half-day-430-r34-after`（`trial/human_walk/_half_day_r34.mjs:91` 与 `:126`），
替换同样先数命中各恰好一次再改，改后 `node --check` 通过。改名后尺现读
`ARMS files=306 declaring_profile_or_receipt=86 profiles=33 receipts=85 literal_screenshots=220`、`COLLISIONS 0`。
盘上那两张 `half-day-430-before.png`（142727 字节）与 `half-day-430-after.png`（141757 字节，时间戳 10-26 15:24／15:25）
与它们的收据 `half-day-430.txt` 是同一对不可分离的运行，帧内容同样不能归给某一次运行；已在
`trial/results/20261026_gozero/arm_collision_disclosure_r108.txt` 逐条写明，没有复制也没有改名。
提交 `b0e43ab75f`。

**没有第二把尺**。这条腿加在原文件里，没有另起一枚 `_arm_collision_ruler_r109.py`——上一班我因为「补充腿重复造」
被点名两次，两把相邻的尺必然一把先烂掉。
