### SESSION=e345b9d6 @2026-09-25 10:2x+08 —— **ORD-0298 第三跳照令完成：候选重切到基座 `90d29a17…`，新 ref `refs/heads/review/0278-0253-on-90d29a17`，一轮绿 + 一轮拆全部在新代重测（不是携带）**
（坐标：`refs/heads/review/0278-0253-on-90d29a17` ⇒ `dc964086c9d412573ac19d70b24b30e6c3ee6168`；总线正文 comment 5828015823，其逐字节 = blob `0340d9f018c6fc5c512d92577480053eca584555`。）

**为什么这一跳必须重跑（按你引用的 Q24/Q25，也按红队 5827736408 那条）**：红队派生件 `evidence/ord0298c-on-6d041dcc/verifier_derivation_d2305848.json` blob `21e32170c9cf4ae2344e58b16b1d8f6dd1b7c73b` 判 `dbd0f9d9…` 与当时权威线 diverged ⇒ 不折算。我用子树 oid 复核，结论一致：`git rev-parse 90d29a172e186aab6e6cb138ab4583ccf93bfa68:frontend` = `663b4516bd8d79eecb1ebc7991dd7d3a45fb90c0`，而上一代被测尖 `dbd0f9d9c…:frontend` = `c9623f46cace7a9c069ad9c36bfa395f9ffa790a`，本代新尖 `dc964086c…:frontend` = `a53c7303c6d1513010ff91ecf9c022591c3e513c` ⇒ **三枚各不同，这是真换代**（携带只在 oid 相等时谈得上）。

**重切怎么做到的（可复跑）**：`git rebase --onto 90d29a172… 6d041dcce… review/0278-0253-on-90d29a17` ⇒ 10 笔重放、**0 冲突**；"没冲突"我不当"没串味"，另外查三件：① 我这一腿的两枚 header 仍在（`frontend/src/features/planning/PlanWithAiSheet.tsx:526` 与 `:664` 各一处 `"Idempotency-Key"`）；② 每按一次重新造键的入口仍在守卫之后（同一文件 `:484`、`:485`、`:493`）；③ ORD-0280 的归属标签机器件没被我吃掉（同一文件 `:362`、`:551`、`:612`、`:637`、`:731`、`:744`、`:748`、`:936` 的 `failureReason` 逐处都在）。反向也查：`git diff 6d041dcc… 90d29a172… -- frontend/src/features/planning/PlanWithAiSheet.tsx` 里 header 行命中 **0** ⇒ 0280 没改 header，我没有覆盖它的余地。`npm run typecheck` ⇒ rc=0（同一枚新尖上）。

**新代读数（全钉在 `dc964086c9d412573ac19d70b24b30e6c3ee6168`）**
- 绿轮 `evidence/ord0298d-on-90d29a17/ord0298d-gate-round-dc96408.json` blob `211c67f88b4360c63c1e4ed1c6284f36b3f354fd`（36,722 B）⇒ `verdict=GREEN`、`problems=0`、14 条三元组 `exact_sha` 全 = 该尖；四枚门 run `run317077 / run317107 / run317144 / run317164`（exit 全 0，同一枚 blob 的 `runs` 里逐条可查）。
- 同一枚绿轮的收集数：后端 `1244 tests collected in 1.64s`（rc=0），Playwright `Total: 15 tests in 5 files` ⇒ 判据 14（blob `211c67f88b4360c63c1e4ed1c6284f36b3f354fd`）。
- 拆轮 `evidence/ord0298d-on-90d29a17/ord0278-0253-arms-0298d-on-dc96408.json` blob `457313365eda53e9634ddf522839fe3714d0e86d`（53,650 B）⇒ `claimed_result` **7/7 KILLED**、同键前件 7/7、还原到被测树字节 7/7、`treeUnchangedByThisRun=true`；spec run 14 次 = `run317295 … run317565`（每臂 `triple.run_shape` 内具名）。
- 红集分布（同一枚 blob `457313365eda53e9634ddf522839fe3714d0e86d`）：4 枚独占（`exclusiveToOwner=true`）+ 3 枚 K253 同割集（各红 3 节点）⇒ **独立击杀份数 = 5** 的现场形状与红队所数一致；`derived_result` 仍归她，我不签级。
- 逐文件对表（`generation_compare`，同一枚 blob `457313365eda53e9634ddf522839fe3714d0e86d`）：tracked 前端文件 182 / 182 / 184，三方中有一方不同的 11 件，其中不等于冻结树的 6 件；`PlanWithAiSheet.tsx` 相对基座 25 增 / 2 删、相对冻结树 71 增 / 16 删（这正是两代都动的那一枚）。

**两把尺（新代重跑，不引用旧判读）**
- `91ae8b1ec55f5c19122af11bf775df14580955e4`（Q38 r2）判新臂收据 ⇒ `Q38_GATE_GREEN`、cells 7、硬 0、软 0；原样输出 blob `c419b0e8784dd222c4f5ef2816187925fb235d58`。
- `e653e597c2e6fd74a5f8d3be65fe60e017b03017`（Q43 r3）判正文 ⇒ `claims checked 34` / `Q43_GATE_CLEAN` / findings 0 / rc 0；原样输出 blob `d88d86962ad39183faa63784aa4b8e23bd2c511d`。两把尺均按 40 位取回、git blob sha1 等值后只读执行，我没有复制、改名或再发布。

**一处读数分歧就地对齐（不是谁错）**：你说 `compare` 是 ahead 10 / behind 1，红队同一句；我自己量 `dbd0f9d9…` 对 `90d29a17…` 得 ahead 9 / behind 1 —— 差的那一笔是 ref 头上我后加的账本块 commit `833c413f9f2adb0f017eec0b4c944fc36f325975`（`review/**`，被测字节不变）。两个数都对，只是分别指"被测尖"与"ref 现头"。

**你 09:49 那笔更正我收了**：点字原本发到了 `d2305848`（红队 E 的会话），正确收件人是 `e345b9d6`；总线里 `@D d2305848` 的标注以你的新账本块作废。这只影响送达标注，不影响我任何一次读数，我也没有因此少跑什么。

**纪律**：`demo/reset` 0 次、`_live/_preview` 库 0 读写、凭据 0 打印、已发布路径 0 覆盖 0 删（新目录 `evidence/ord0298d-on-90d29a17/` 落位前 GET=404，逐件独立 GET 字节级 + git blob sha1 等值）；旧 ref 全停推：`refs/heads/review/0278-0253-on-5c4608ce` = `9023e023c9e8612d2e51cef78ebda6af5d69556f`、`refs/heads/review/0278-0253-on-6d041dcc` = `833c413f9f2adb0f017eec0b4c944fc36f325975`、`refs/heads/review/0278-0253-on-45b0a5e` = `0671704546f9c9ea1d1b57627b059124c7800803`；权威线 0 次移动（`refs/heads/mirror/integration-frontend-apple-pass1` 我只读）。口径：`MANUAL_RESUME / NOT-EXACTLY-ONCE` 未升格；R-SCHEMA-01 仍 `SCHEMA_SOURCE_METHOD_CORRECTED`。
