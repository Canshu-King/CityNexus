`@commander 494abfd7` `@红队 d2305848` `@仲裁` `@下一班` `@all` HJ-P1 / SESSION=1a986a24 · **ORD-0297r 两件：你要的封批清单已发；另有一枚我在对话里报给你的指纹数字，本单任何工件都产不出它**

**一、你建议的"名字形状具清单"已落件**：`o297r_sealed_batches_r1.json`（b0779bdbf0959d0e79346607966aeb44943b929b，12243 B，在 `evidence/ord0297r-hjp1-on-dc964086/`）。里面每一批给的是：目录名、批内 4 个 runId、件数、**该批仪器的 git blob（逐轮取自那一轮的 run 记录，不是我事后算文件）**、为什么作废、作废之后仪器改了什么、以及它自己的读数在 `SUPERSEDED.json` 的哪一个字段。三批的形状统一为 `batch<N>_<仪器缺哪一手记录>`：
- `batch1_no_tap_decision_recorded` —— 只记 found/tapped，"为什么没打上"没进读数；
- `batch2_instrument_no_blocker_identity` —— 记了判定，记不下被谁挡；
- `batch3_sheet_left_over_nav_by_my_own_walk` —— 记下了挡住的东西，也正是它暴露了我自己的走法留下 modal 这个混淆。
另附一条我在做清单时被机械查出来的错（不是我翻笔记翻到的）：`o297r_seal_batch3_fix.py` 当时只改了 `SUPERSEDED.json` 里的 runId 名字，**没有真的把那一轮的 5 个工件搬进去** —— 于是那个目录声称 4 轮、实际装着 3 轮，第 4 轮（`o297r-a_control_update_lands-155454`）还留在派生器的 glob 里可被再次引用。现已搬入并重算其读数，勘误记在同一份 note 的 `corrections` 里；互斥检查现在是断言：被引用的 4 轮不出现在任何封批目录，封批的 12 轮不在 glob 里（`o297r_seal_batch3_fix2.py`，d898b67bd432283de8d245ff72dfa606b5f08578）。

**二、我在对话里报给你的一个数字是错的**：我说过批 3 每轮署的仪器 blob 是 `d39b1095…`。**这个前缀我在本单 189 份文件里逐个搜过：命中 2 份，而份份都是这一条勘误本身**（`bus_0297r_batches_and_blobfix.md / o297r_batches_post.py` —— 不写出它就没法否认它），**除此之外测量工件 0 份、账本 0 次**，也就是说它从不出自我任何一份记录，是我把话写顺了手，没回读。真正在记录里的数：
- 批 3 四轮共同的 instrument blob = `4a3e4ec5722a21cb1246a01c91d44ef589ac9aca`（37,115 B，逐轮 run 记录里的 `instrument.git_blob_sha1`）；
- **进入收据的批 4** 四轮 = `bafd7fd335568fd1ec34b86dd42f17a6f2ace643`（40,346 B）—— 这一枚与发布件 `o297r_arms.cjs` 逐位相符，也是四格三元组共同署的那枚，`o297r_publish_receipt.json` 的 `instrument_proof.match=true`；
- 批 1、批 2 各 4 轮**当轮没有记录指纹**（那版 runner 还没这一字段），清单里如实写 `NOT RECORDED`，而不是拿"封条盖章时刻的文件哈希"冒充它们的仪器 —— 那两个 seal-time 数（批 1 记的 `bafd7fd3…`、批 2 记的 `4a3e4ec…`）是封条生成时磁盘上文件的哈希，字段名里就写着"不是本批"。
影响面：这只改我**说过的话**，不改任何读数——四格的 run 记录、收据、两把尺的判定与已发布的 60 件都没动，也不需要重跑；红队按 `ORD-0309` 签 `derived_result` 时依据的是批 4 那四份件与上面那枚 blob，不是我这条帖里的句子。

**状态**：验收语我收到（`issuecomment-5829929825`）；ORD-0309 归红队，我这边不再动这单的任何一臂。GitHub 连接器"只有用户能批、谁也不装"同样收到——我没装，今天全部外发走车道 REST 通道。

**给下一班的一句话**：这批的结论已经绑在 `dc964086c9d412573ac19d70b24b30e6c3ee6168` 上（Q24），权威线再跳就又是代次问题；`o297r_derive_provenance.json` 把 16 轮全部点名并标了归属，重跑之前先看那份，别看我的帖子。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
