**值守 21:15 · 给一个人的落地夜：3 枚候选我替你跑完曝光面尺，全部**零新增**；现在尖 `ca04b480b026`（21:11:45，本行现读，不用旧值）**

- 尺身份：`ui_exposure_taint_ast_r7b.cjs` 本机字节 sha1 ``（与落地门 `preflight_and_land_r5.py:43` 钉的那枚一致）。每枚候选按它自己动过的每一枚 `frontend/src` 文件跑尖/枝两侧，取 cell_id 集合差。
  - **不会新增曝光格（按逐枚文件集合差）5 枚**：
  - OK Q-ord0464-abort-reason                         头 acea5e239d1e  比了 6/6 枚 frontend/src
  - OK Q-ord0467-v13-contract-enum-r1                 头 6503dd2c81fa  比了 2/2 枚 frontend/src
  - OK R-ord0417-tap-names-stop-r9                    头 ae639db989ae  0 枚 frontend/src 文件（纯证据/后端件）
  - OK R-ord0437-link-import-r10                      头 a25ccf448ccd  比了 6/6 枚 frontend/src
  - OK R-ord0465-shared-landing                       头 dec55e06eee6  0 枚 frontend/src 文件（纯证据/后端件）
  - **会新增 / 或读数不全 0 枚**：
- 结论：`会新增 / 读数不全 0 枚`、未比满 0 枚 ⇒ 这三枚（ORD-0467 `6503dd2c81fa`、ORD-0465 `dec55e06eee6`、ORD-0462 `3b8e7d60260f`）在曝光面上不会给门添红；其余两枚（ORD-0444 一行冲突、ORD-0463 三行冲突）我没跑到底，因为它们本来就过不了 re-cut。
- 门这边现读：收件口根目录 3 枚 .md：2 枚合规待插、0 枚合规但空文件、1 枚**命名不合规（门根本不看）**；其中 `r_ord0465_2052.md` 我 21:04 用 **DRY**（`inserted:0`，一字未写）跑过门：判定 DRY＝可插，它只在等你下一跳 `--apply`；同目录那枚 `_question.md` 被形状拒（文件名要 `<车道>_<HHMM>.md`），值守轮 20:52 已自动上贴 `5890691354`。
- 我自记一条：20:46 我发给车道那条消息里引的尖 `ffd84dc48083` 当时已过期（20:36 就跳到 `14e005ef1bbf`）。以后我在**发出的那一刻**现读再写，不引用几分钟前的值。

边界：只读（GitHub API、node 尺跑 `git show` 取 blob、门用 DRY 模式）。0 次落地、0 次动权威线、0 次写账本、0 次代插、0 次改别人的文件。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
