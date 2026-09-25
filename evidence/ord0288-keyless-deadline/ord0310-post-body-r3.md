【号令者 494abfd7 → D 车道 e345b9d6｜ORD-0310 交付（r3：落成的那一代 + 一处自我勘误）：给无键写腿一枚可指名的设备期限（形制按仲裁 Q54=①）】

一句话：`agent/commands` 那一发（不收幂等键的那一支）现在有了一枚**只在一处定义、屏上那个秒数与计时器同源**的设备期限 `60000` ms；到点后屏幕上只说它射程以内的事 —— 结果未知、不是没发生、这一笔不能靠同一把键补问。有键那一支（0281）我一个字没改。候选 `refs/heads/review/ord0310-keyless-deadline-d-on-2344145c` = `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`（父 = 我当时读到的线位；权威尖只读 `2344145ce6342b6ac32ac4d0955c0f524d8c9320`，两路一致，我 0 次移动）。

**本代与权威线的关系（不用嘴说）**：本单收据 `evidence/ord0288-keyless-deadline/ord0310_keyless_deadline_receipt_r3b.json` blob `c92e565bc5466ff86ee96b622793ba6cf44b26ee` 的 `generation_binding` 写着 —— 现读的尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 是我这一代的祖先（`authority_tip_is_ancestor_of_this_tree=true`、`git merge-base --is-ancestor` 退出 `0`）。同一本账里 `files_this_tree_adds_on_top_of_the_tip` = ["review/ord0310_kill_arms.py"] —— 这 1 件全在本车道自己的 `review/` 之下，产品与门字节 0 件。另有 `files_the_line_changed_since_the_fork` / `files_my_candidate_changed_since_the_fork` / 交集 = 13 / 13 / 13（自分叉点 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 起）—— 这个交集是**我前几轮的工具改动已经在线上**的结果，不是「合流会不会撞」：尖是我这一代的祖先时合流是 fast-forward，不做三方合并，所以本代没有冲突面可预测；上一轮那份路径相交表仍在 `evidence/ord0288-keyless-deadline/ord0310-path-disjointness-r2.tsv`，我不拿它冒充今天的读数。

**这一代是怎么来的（`r3_on_the_landed_generation`）**：你落地之后我从现读尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 再切一次，候选尖 `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`；那一笔的父位 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 与这枚尖相等 `true`（本单声明的分叉基座 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 与尖相等 `false` —— 落地之后这两问不同答，上一块里我把它们混成一枚字段，勘误见第五节）。本代不是 re-cut：产品那一笔 `5ff55ec7ed349b5f3a20f91995bf0f1e40741c01` 与上一代同一笔，所以 `patch-id` 那两枚是同一笔与它自己比 —— 本条不拿它当跨代证据（新收据里具名 `what_a_recut_proves.is_a_self_comparison=true`）。本代能声明的是被量字节没动：`subject_files_equal_to_the_tested_tree=true`、`tested_tree_vs_product_commit.all_equal=true`。 预测树各标各处：上一枚 ref 对同一枚尖我复算 = `dee4b794b62797a9760b067d733ed96aa742060c`（原样输出 `evidence/ord0288-keyless-deadline/ord0310-mergetree-tip-x-previous-ref.out` blob `73cafd8de3e1a36ebd31fe767ab52d7b77a09e30`，与你那帖 `issuecomment-5832371591` 给的数逐位相同）；本代按 ref 当下尖重算 = `a5b5d3f5b253b6bcc635567c9fe1f2fb264e23f8`、退出 `0`、conflict 段 = `（空）`。

**一、两枚形状（谁也不替谁交卷）**

- 有键 = 0281（B 的）：`frontend/src/lib/writeDeadline.ts` blob `1d67e725ebb3348bbeb70d743793388ed36ed9d9`，常数 `export const CLIENT_WRITE_DEADLINE_MS = 60_000`，引用者只有 `frontend/src/features/execution/LiveRecovery.tsx`、`frontend/src/features/recovery/V14RecoveryTruthPanel.tsx`；`git grep -n fetchWithWriteDeadline 2344145ce6342b6ac32ac4d0955c0f524d8c9320 -- frontend/src/features/planning/PlanWithAiSheet.tsx` 回 `0` 行。落地之后它随基座进我的候选（`absent_from_my_tested_tree=false`、候选树内 blob 与线尖同值），本道那一笔的改动清单里没有它 ⇒ 我对它仍是一字未改。
- 无键 = 本单：新建 `frontend/src/lib/keylessWriteDeadline.ts` blob `1aea861b887273f70ec6cf726369c36a1398786e`；`frontend/src/features/planning/PlanWithAiSheet.tsx` blob `3bb6a39067a380c2f75629fd7562f0de8f5d2f2a` 里 `fetchWithKeylessWriteDeadline` 只裹 `agent/commands`。期限放在服务端写预算之上（`backend/app/core/config.py:96` 那枚 `45000`）才不会出现「服务器已判死、客户端还在等」，也不会催用户在服务器还在写时重来。

**二、屏上那句（干净轮 `run342959`，库 `_run342959.db`）**

`status=UNKNOWN_KEYLESS_WRITE_DEADLINE`、`origin=device`、`label=这台设备自己的读数（服务器没给句子）`（不冒充「服务器给出的原因」）、`detail_block_attached=true`、实测等待 `60544` ms、`post_count=1`。屏幕上那句原文（逐字，出自本轮证据文件 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run342959.json` blob `b98af1e5c0184a3da823ab6b3cdc7ac86059ad7c`）：

> POST /api/v1/journeys/e8bf898b-babb-47db-9167-a09818ec9d1f/agent/commands -- 这台设备等到 60 秒就停下来了。这一笔的结果未知，不是没发生：请求已经发出去了，服务器可能还在做。也不能靠同一把键补问：这条路线不认幂等键，它没有收下这把键，没有可回读的凭条。

反推那一刀（读数出自证据文件 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run343841.json` blob `3f6b246fd5171658d49ffa15ddca676155fe51df`、臂收据 blob `1c9a4599816afce169b69222cccb6587304b74fb`）：常数从 `60000` 改小到 `7000` （臂 `K0310_DERIVATION_PROBE_CONSTANT_TO_7S`，轮次 `run343841`）⇒ 屏上秒数跟着变 `7`、实测等待从 `60544` ms 变 `7548` ms，该臂仍判 `HOLDING_AS_EXPECTED`。数值与计时器动在同一处定义上，所以那句里的秒数不是另一处硬编码。

**三、服务端字段读数（不用状态码冒充 DB 事实）**

库 `C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_rt3r7nh_\suite.db`、表 `idempotency_keys`、字段出处 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r3.json` blob `89588274ba0180b51f3e26fb789f33ddbcd7a24f`，回读走第二条 `mode=ro` 连接：不带键连发三发 ⇒ `count(*)` 从 `0` 到 `0`（凭条 +0 行），同轮 `journey_missions` 从 `0` 到 `3`、`distinct_mission_ids=3`；带一把形制正确的键仍 +0 行（凭条表列 `count(*)`）。
认键那一支 `plans/generate`（服务器只在这一支收键）：读数取自 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r3.json` 的 `T1a` 格，blob `89588274ba0180b51f3e26fb789f33ddbcd7a24f` ⇒ 第一发回答 `201`、同键换正文第二发 `409`（服务器原话 `same idempotency key used for a different request`）。
同一本账的 `T1b` 格 blob `89588274ba0180b51f3e26fb789f33ddbcd7a24f` 给出落下的凭条行：`key=plans.generate:8b75f830-471a-4b5e-a814-5afb23e38cf7`、`operation=plans.generate`、`response_status=201`，与客户端第一发看到的 `201` 相等（`response_status == client_status_first` 是本格断言）。

**四、反突变臂（逐臂带 (sha, nodeid, shape)）**

| 臂 | 红了几枚节点 | gate exit | 还原 | claimed |
| --- | --- | --- | --- | --- |
| `K0310_DEADLINE_RENAMED_AS_CANCEL` | 1 | 1 | true | KILLED |
| `K0310_DEVICE_NOTE_UNDER_SERVER_LABEL` | 1 | 1 | true | KILLED |
| `K0310_SENTENCE_PROMISES_REPLAY` | 1 | 1 | true | KILLED |
| `K0310_DEADLINE_IMPERSONATES_TRAVELLER` | 1 | 1 | true | KILLED |
| `K0310_TIMER_FIRES_BEFORE_THE_CONSTANT` | 3 | 1 | true | KILLED |
| `K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE` | 1 | 1 | true | KILLED |
| `K0310_DERIVATION_PROBE_CONSTANT_TO_7S` | 0 | 0 | true | HOLDING_AS_EXPECTED |

聚合 `killed=6/6`、`survived=0`、`every_arm_parsed_at_least_one_node=true`、`tree_unchanged_by_this_run=true`。**`claimed_result` 只是我这辆道的观测，`derived_result` 一律 null；等级归红队，我不签级。**

**四·补、判据是「期限到了」，不是「有没有 signal」（你 ② 要的那枚双臂自证）**

先把前提钉住（这是你 21:02 那帖给我的新事实；下面每个数都出自臂收据 `evidence/ord0288-keyless-deadline/ord0310-arms-receipt-r5.json` blob `1c9a4599816afce169b69222cccb6587304b74fb` 与其逐臂证据文件）：现读尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 上 `PlanWithAiSheet.tsx` 的 `signal` 选项行是 [414, 474, 553, 600, 692]，而我这一代的无键腿 [538] 行本来就带着它（包装件 `93` 行 `const upstream = init.signal ?? null;`）⇒ **「有 signal」在这棵树上恒真，它不可能当判别量**。所以我把臂对准这一点：`K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE` 只把 `const response = await fetchWithKeylessWriteDeadline(` 换回裸 `fetch(`（同一处 `signal,` 一字未动；下面四个数都是该臂在 `evidence/ord0288-keyless-deadline/ord0310-arms-receipt-r5.json` blob `1c9a4599816afce169b69222cccb6587304b74fb` 里的字段 `anchor_hits` 与 `sizes`：`anchor_hits=1`、`before=52799` → `during_mutation=52775` → `after_restore=52799`，差 `-24` B 正好等于包装函数名多出的长度），三枚节点读数是 `K1 无键写腿到点=红`、`K2 正控=绿`、`K3 反控=绿` ⇒ 只有 K1 红、K2/K3 仍绿，即**红的是「期限到不到」那一判据，不是 signal 的有无**。反向对照：把期限分支冒充成旅客主动取消的那枚臂 `K0310_DEADLINE_IMPERSONATES_TRAVELLER` 红的节点数是 1（K3）。逐行前提原样输出 `evidence/ord0288-keyless-deadline/ord0310-signal-vs-deadline-proof.out` blob `eaa24028b6be59cb92ea10516a910567bd37ed62`。

这一格自己也有一个要说出来的缺陷：修正后的收据里 `C6.readings.premise_proof.exists=false`、`blob=`NOT_WRITTEN` —— 因为我给收据生成器指的 `--raw-dir` 是 r3b，而那件证明输出留在 r3。证明件本身早已发布（上面那枚 blob 就是逐字节回读到的它），落地那一块引的也是它；这里是**第四枚同类毛病（标签/路径指错，不是读数错）**，我写在这里而不是再补一块账本。

**五、我自己的账（不抹）**

头两轮臂收据把每一枚臂都报成 SURVIVED，而同一些运行的行数是 `1 failed` —— 正则少了 `re.M`，`^`/`$` 只对着整段文本两端，计数恒为 0；修具那一笔就是候选尖 `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`（驱动器 blob 见下表 `ord0310-tool-kill-arms-r2.py`），本条所有数字出自修好之后那一轮。另一处：`K0310_SENTENCE_PROMISES_REPLAY` 第一次真存活 —— 门禁只在折叠态读卡片，而禁句活在「技术详情」展开之后；补法是折叠+展开各读一遍，并把「不能靠同一把键补问」钉成逐字判据。两处都是收紧量具，不是把断言改松换绿。

第三批（这一代特有，已单独落账本勘误块）：我 21:56 那块里有 3 处**标签/派生**错，全不是读数 —— ① `is_cut_on_the_tip_read_now=false` 印在两个一模一样的 40 位旁边，因为那枚字段比的是「声明的分叉基座 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b`」与尖，不是我那句话说的父位与尖；现测父位 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 与尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 相等（`evidence/ord0288-keyless-deadline/ord0310-ref-read-r3b.out` blob `89eb633ba1ab3e8ff8cdb5192558a74562daa0cb` 里 `git ls-remote` 与 `git rev-parse …^` 的原样输出），修正后拆成两问 `is_parent_the_tip_read_now=true` / `is_declared_base_the_tip_read_now=false`；② 块标题的 `r2_recut_onto_the_frozen_tip` 是 r2 那轮留下的字面量，现在由 `--generation-label` 传入 = `r3_on_the_landed_generation`；③ 那块把 `patch-id` 两枚相同当跨代证据，而落地之后那是同一笔 `5ff55ec7ed349b5f3a20f91995bf0f1e40741c01` 与它自己比 ⇒ 新收据具名 `is_a_self_comparison=true`，论证退回上一枚收据 blob `35e40da15ef65b024b10269cb3774faca77f9641`。修正件走新名：收据 `evidence/ord0288-keyless-deadline/ord0310_keyless_deadline_receipt_r3b.json` blob `c92e565bc5466ff86ee96b622793ba6cf44b26ee`，尺 Q38 r2 判它 `Q38_GATE_GREEN`、hard `0`、soft `0`；被勘误那两件 0 覆盖 0 改名，仍在原位。机器可读 was/now：`evidence/ord0288-keyless-deadline/ord0310-erratum-r1.json` blob `bb0e1c1506157593397ce807b3d64cb00cd809c2`。另有第四枚同类（`C6.premise_proof` 指错目录，上一段刚说过），我没再补块，写在这里。 勘误块自己也在 `## DELIVERIES` 里（`evidence/ord0288-keyless-deadline/ord0310-ledger-block-erratum-r1.md` blob `b9b9a80e282c81a4ed86bc807db1768fbb55ea62`，两把尺判的是从账本回读出来的那份字节）。量具改动不塞进被量那一代：逐件字节冻结在 `refs/heads/review/ord0310-tools-r5` = `c518e64b42db4e4428c78dc04982ef32e8dd3e78`，五枚 ref 同一趟 `git ls-remote` 的原样输出是 `evidence/ord0288-keyless-deadline/ord0310-tools-ref-read-2.out` blob `107d93ddf2aba2d9f8e11eecb156ec2b403e309d` —— 里面同时回读着 `refs/heads/review/ord0310-tools-r3b` = `e6927f0f18c86ad0969690e8293b0d2c8a889988`，即勘误块引的那枚等式仍然成立；被量的 `refs/heads/review/ord0310-keyless-deadline-d-on-2344145c` 仍是 `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`。

**六、发布与回读**：`evidence/ord0288-keyless-deadline/` 目录现在共 `111` 件，本轮逐件独立 GET 量了 `59` 件（本代交件），`byteLevelMatches=59`、`notMatching=[]`；剩下 `52` 件是上一代同名/异名件，我这一轮没有重贴它们的内容，所以它们具名为 `PRIOR_GENERATION_NOT_RESTAGED` 而不是被算成不吻合。
0 覆盖不是我口述：每一件都走 `HJ-P3_evidence/gated_push.py` 那道同字节即跳过、异字节即拒绝的门，逐件日志已发布：`evidence/ord0288-keyless-deadline/ord0310-publish-log-r9.json` blob `903e5cdc0fe6701ea268b97046b2955e62d29313`、`evidence/ord0288-keyless-deadline/ord0310-publish-log-r10.json` blob `12358a9c2a6ea077d4ddadd8eb84aa0022d77ffa`、`evidence/ord0288-keyless-deadline/ord0310-publish-log-r11.json` blob `5e59acad69e9861d13b2218d10260631e7fc7a4c`。三个计数是从日志的 `fresh_path` / `identical_skipped` / `refused` 三个键算出来的：首次创建 `19` 条路径、同字节被跳过 `131` 条路径、被门拒绝 `1` 条（`ord0310-publish-log-r10.json :: ord0310-tool-stage-pub-r5.py`：我把一件已按此名发布过的量具改了字又想同名重发，门咬住了，于是改名重发成新路径、旧那件字节未动）；另有 `3` 次在**发出 PUT 之前**就死于链路（`SSL: UNEXPECTED_EOF_WHILE_READING`，闸门 fail-closed、什么都没写）：["ord0310-q43r4b-on-block-erratum-r1.json", "ord0310-tool-kill-arms-r2.py", "ord0310-q43r4b-on-post-r2.json"] —— 按老规矩记成传输异常而不是凭据问题，只手工重试那几件，重试后全部 FRESH+MATCH。

生成本条正文那件工具本身也已发布：`evidence/ord0288-keyless-deadline/ord0310-tool-make-post-r6.py` —— 它的 blob 我不写在这里，由下一本账 `ord0310-readback-r7.json` 逐件独立 GET 给出（自己给自己签哈希不算证据）；七枚本车道 ref 同一趟 `git ls-remote` 的原样输出在 `evidence/ord0288-keyless-deadline/ord0310-tools-ref-read-final.out`，包括 `refs/heads/review/ord0310-keyless-deadline-d-on-2344145c` 与被量那一代的父位。

那本账本自己不能自证，所以它单独由一次 GET 收尾（原话）：`GET https://api.github.com/repos/Canshu-King/CityNexus/contents/evidence/ord0288-keyless-deadline/ord0310-readback-r6.json?ref=commander/control -> HTTP 200 | remote 64,935 B blob b1a20e2fb571c14ee49501c845e29548bf918787 | local 64,935 B blob b1a20e2fb571c14ee49501c845e29548bf918787 => BYTE-LEVEL MATCH`。

（本条正文自己、以及判它的两把尺输出，也在同一目录：`ord0310-post-body-r3.md`、`ord0310-q43r4b-on-post-r3.json`、`ord0310-q43r3-on-post-r3.json`；它们的逐字节回读记在下一本账 `ord0310-readback-r7.json` 里 —— 那本账在本条发出去之后才生成，所以这里只给名字不给读数，免得我拿一段还没定型的字去算哈希。）

| 文件（全部在 `evidence/ord0288-keyless-deadline/` 下，本单之前该目录不存在） | blob（40 位） | 远端字节 |
| --- | --- | --- |
| `ord0310-arms-receipt-r4.json` | `d86e0e7ba757fbf18a0ba8d065b482b46a0b7bc1` | 21,496 |
| `ord0310-arms-receipt-r5.json` | `1c9a4599816afce169b69222cccb6587304b74fb` | 24,786 |
| `ord0310-backend-readings-r2.json` | `74d4c0ea276c1126f4f4302e474f61d906606bec` | 2,053 |
| `ord0310-backend-readings-r3.json` | `89588274ba0180b51f3e26fb789f33ddbcd7a24f` | 2,053 |
| `ord0310-erratum-r1.json` | `bb0e1c1506157593397ce807b3d64cb00cd809c2` | 6,916 |
| `ord0310-gate-evidence-run342959.json` | `b98af1e5c0184a3da823ab6b3cdc7ac86059ad7c` | 6,242 |
| `ord0310-gate-evidence-run343053.json` | `fe2f84508a9f9700b78968c67b26610570e2cc36` | 2,235 |
| `ord0310-gate-evidence-run343182.json` | `467dda4049eac33f75ec018bd1ea41afe8545e83` | 2,235 |
| `ord0310-gate-evidence-run343283.json` | `a73880863cb1926cf88f8fb7f7deb08cdf663c6f` | 2,235 |
| `ord0310-gate-evidence-run343403.json` | `4b5e493fbf62aace664227f97dac1017d6bff646` | 7,552 |
| `ord0310-gate-evidence-run343517.json` | `9657919928335a83f6a1e7d7384e4c345438ee5f` | 131 |
| `ord0310-gate-evidence-run343607.json` | `fd994a43567813ba0a3c282e9dc1855f4e49f95f` | 2,235 |
| `ord0310-gate-evidence-run343841.json` | `3f6b246fd5171658d49ffa15ddca676155fe51df` | 6,234 |
| `ord0310-ledger-block-erratum-r1.md` | `b9b9a80e282c81a4ed86bc807db1768fbb55ea62` | 5,864 |
| `ord0310-ledger-block-r2.md` | `320084ace903d1c195f2fc036768ffbab6278c35` | 15,511 |
| `ord0310-ledger-block-r3.md` | `39d5079158fd8018a35ece12fbaa1cd691be7254` | 16,734 |
| `ord0310-left-right-count-trap.out` | `ee03cf3206ff6f8e0138050c10d2be8fe9e26d91` | 521 |
| `ord0310-mergetree-tip-x-candidate-r2.out` | `8db66d7493f634f8e4f9a4a217fc3c963b30db6a` | 485 |
| `ord0310-mergetree-tip-x-candidate-r3.out` | `f39d52e81e0fb9a0a1f4f772debdd5d36c40ce88` | 485 |
| `ord0310-mergetree-tip-x-candidate-r3b.out` | `9ea5e8c2b78c59eb495105da038c9fb6ab4f0053` | 486 |
| `ord0310-mergetree-tip-x-previous-ref.out` | `73cafd8de3e1a36ebd31fe767ab52d7b77a09e30` | 41 |
| `ord0310-path-disjointness-r2.tsv` | `d74dbd49ff8975b05020d0984dcc128d23f2af34` | 897 |
| `ord0310-path-disjointness-r3.tsv` | `b8bc20e7a980c443719c74fba3a3f17a1c65d69f` | 2,292 |
| `ord0310-post-body-r2.md` | `da843bf4b6b3155debe75701a9444c1882d24eee` | 13,430 |
| `ord0310-publish-log-r10.json` | `12358a9c2a6ea077d4ddadd8eb84aa0022d77ffa` | 17,308 |
| `ord0310-publish-log-r11.json` | `5e59acad69e9861d13b2218d10260631e7fc7a4c` | 17,270 |
| `ord0310-publish-log-r9.json` | `903e5cdc0fe6701ea268b97046b2955e62d29313` | 13,143 |
| `ord0310-q38r2-on-receipt-r2.json` | `64c7fd6398fb025b1feae8278a32bc96ec6e2150` | 12,127 |
| `ord0310-q38r2-on-receipt-r3.json` | `5c59548f0031d6fde4f7e18edd24c16d94a141bc` | 12,111 |
| `ord0310-q38r2-on-receipt-r3b.json` | `5c05265d9ae1a44c0c264b33fa66e8ad3d4c034d` | 12,112 |
| `ord0310-q43r3-on-block-erratum-r1.json` | `875fbeff37ccc6c6ed5fe33b40de754715e865c2` | 595 |
| `ord0310-q43r3-on-block-r2.json` | `9d04379b6cb3795e954aff51bf355936359ca356` | 588 |
| `ord0310-q43r3-on-block-r3.json` | `75ea55056e5750241cff9f4950245e598b076fe8` | 588 |
| `ord0310-q43r3-on-post-r2.json` | `131ddc226caa23c79db0acc8302960fc529d0a7b` | 585 |
| `ord0310-q43r4b-on-block-erratum-r1.json` | `7d7665530a9e9ae469f407d1ff31a84e6f99401b` | 562 |
| `ord0310-q43r4b-on-block-r2.json` | `bfbc4a1fe4e77b82a735c9ffa80aad997cf4d763` | 576 |
| `ord0310-q43r4b-on-block-r3.json` | `411c64372bf3605748c0b29c887e6cc00e2cac6e` | 576 |
| `ord0310-q43r4b-on-post-r2.json` | `2600ff44d31bad0353f050b2d184ddb48df2e314` | 559 |
| `ord0310-readback-r5.json` | `01d9f0d92b560d72bc7044e67cd389d1d0384821` | 52,058 |
| `ord0310-ref-read-r3b.out` | `89eb633ba1ab3e8ff8cdb5192558a74562daa0cb` | 903 |
| `ord0310-signal-vs-deadline-proof.out` | `eaa24028b6be59cb92ea10516a910567bd37ed62` | 1,469 |
| `ord0310-tip-read-r2.out` | `0e19d401a3174edfd204c03bca81c8e8e0435682` | 1,617 |
| `ord0310-tip-read-r3.out` | `98f27ad4dc936c6d6561952b0a91a46d4b9c5aa3` | 1,617 |
| `ord0310-tool-gauge-landed-block-r2.py` | `76e76aa1418988f3c14dda9d764276f3c3a4b6e8` | 2,356 |
| `ord0310-tool-kill-arms-r2.py` | `630d6feb89f4b5763ed75d1c3708a2ea45cd1c03` | 14,811 |
| `ord0310-tool-make-block-r4.py` | `5e6441b12a2e61bd41cb620b9b80e35867dc0d00` | 25,614 |
| `ord0310-tool-make-erratum.py` | `17dbb8ba51e5ecbf22b1a234c299fa8b262148d4` | 19,277 |
| `ord0310-tool-make-post-r4.py` | `ea4361387c8d752fd7a2d175e1a7286eb28f1e5f` | 30,667 |
| `ord0310-tool-make-receipt-r4.py` | `615d899b36ebd2c518bc9aa8199e05387f400aa3` | 42,470 |
| `ord0310-tool-pub-names-r6.py` | `d0f4ef16c73847e556aa3a18c63bd2f6d66e8489` | 9,332 |
| `ord0310-tool-publish.py` | `08bf5229f6a52077b99ef49a37fb92d5e9536f4c` | 2,715 |
| `ord0310-tool-readback-r3.py` | `702fe9e35a39d45d977614f390c08ff6e4c4bc81` | 6,429 |
| `ord0310-tool-signal-proof.py` | `1508fb18f149ddcace4497e896dc49a15062b5fb` | 3,581 |
| `ord0310-tool-stage-pub-r6.py` | `b576aab86effbe1ce6e96c04350fc317523b8014` | 7,864 |
| `ord0310-tools-ref-read-2.out` | `107d93ddf2aba2d9f8e11eecb156ec2b403e309d` | 1,199 |
| `ord0310-tools-ref-read.out` | `600aa4a219fde4b0976a4499b49a4a9d805576ea` | 974 |
| `ord0310_keyless_deadline_receipt_r2.json` | `35e40da15ef65b024b10269cb3774faca77f9641` | 34,150 |
| `ord0310_keyless_deadline_receipt_r3.json` | `df1c18a4456314b633018e31da48ea3c4cf0dac6` | 37,187 |
| `ord0310_keyless_deadline_receipt_r3b.json` | `c92e565bc5466ff86ee96b622793ba6cf44b26ee` | 37,233 |

账本块已落 `## DELIVERIES`（追加，不动别人的块），逐字节同 `evidence/ord0288-keyless-deadline/ord0310-ledger-block-r3.md`，blob `39d5079158fd8018a35ece12fbaa1cd691be7254`（16,734 B）；两把尺判的是**从账本里回读出来的那份字节**（不是我递给插入工具的草稿），输出同目录：`ord0310-q43r4b-on-block-r3.json`、`ord0310-q43r3-on-block-r3.json`；Q43 r4b（尺 blob `efa6b7a383e094e2ede89f5dd8565b12feed0171`）判绿，Q43 r3（尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）判干净。

**六·补、手机上还看不到（你 ① 那句我记账）**：这一代 `LANDED`（尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 里就有那四枚工件），但**没部署到手机预览面** ⇒ `NOT-YET-DEPLOYED-to-phone`。我这边 0 次换代：没跑 `deploy_bundle.py`、没切 bundle、没动 `vite preview` 的端口带，所以真机上那句话仍是上一代的。按 Q61 我不去自己换那一代 —— 要我在手机上量这句，请落字并给一次换代窗口，我按 `REPRODUCED(tree)` 与 `NOT-DEPLOYED(phone)` 分两栏报。

**七、队列里还压着的**：ORD-0288 的另一半（服务端那一腿）不在本单射程；ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED；ORD-0232 端到端复放仍等合流窗口；ORD-0308 那张表里 `NOT_APPLICABLE_missing_candidate` 那一格现在有条件重跑（F 的 0307 已落），你要的话我下一单做。

**纪律**：`0 权威线写入`、`0 推他人 ref`（只推了自己命名的 ref：`refs/heads/review/ord0310-keyless-deadline-d-on-2344145c` 与量具那枚 tools ref）、`demo/reset 0`、`_live`/`_preview` 库 0 读写、凭据 0 打印（第二路读 ref 的 token 只进内存，`evidence/ord0288-keyless-deadline/ord0310-tip-read-r3.out` 里那一行写的是占位符）、`0 为了绿而改断言`（勘误件 `evidence/ord0288-keyless-deadline/ord0310-erratum-r1.json` blob `bb0e1c1506157593397ce807b3d64cb00cd809c2` 的字段 `readings_unchanged.re_measurements_run_for_this_erratum` = 0，即一轮门、一枚臂都没重跑）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
