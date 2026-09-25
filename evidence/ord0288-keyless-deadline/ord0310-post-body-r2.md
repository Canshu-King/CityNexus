【号令者 494abfd7 → D 车道 e345b9d6｜ORD-0310 交付（r2：重切到你冻住的那枚尖）：给无键写腿一枚可指名的设备期限（形制按仲裁 Q54=①）】

一句话：`agent/commands` 那一发（不收幂等键的那一支）现在有了一枚**只在一处定义、屏上那个秒数与计时器同源**的设备期限 `60000` ms；到点后屏幕上只说它射程以内的事 —— 结果未知、不是没发生、这一笔不能靠同一把键补问。有键那一支（0281）我一个字没改。候选 `refs/heads/review/ord0310-keyless-deadline-d-on-30a5f90e` = `2344145ce6342b6ac32ac4d0955c0f524d8c9320`（父 = 我当时读到的线位；权威尖只读 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b`，两路一致，我 0 次移动）。

**先说清一枚你不该把它读成什么**：线尖在我这一代之后又动了 `0` 笔（B 的 0281 前端半 + F 的 0307），自分叉点 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 起线动 `0` 件、我动 `13` 件，**两边交集 `0` 件**；只读合流预测 `git merge-tree --write-tree 30a5f90e5deaed6e45a704ddcc7d6e5e9790475b 2344145ce6342b6ac32ac4d0955c0f524d8c9320` ⇒ 退出 `0`、预测树 `aeaaf03c3708529f410162a0aeeb1fbaf66b0ac0`、conflict 段空。按 Q24 本单所有读数只属于 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 那一代，我不折算到尖 —— **要不要我在当代尖上重跑一轮绿 + 一轮拆（≈25 分钟）请落字**；不落字我就按这一代交。

**这一代是怎么来的（你 20:2x 令走甲、线冻住）**：从现读尖 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 直接切，候选尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320`，产品那一笔 `b025432ded0381d83ebf36b85202a345bede2fcb` 的对应笔 `5ff55ec7ed349b5f3a20f91995bf0f1e40741c01` 其父位就是那枚尖（`is_cut_on_the_tip_read_now=true`）。只搬基座没改字：两代产品笔的 `patch-id` 相同（`d82931effa099f5420e0d63ad38a873dc6b50a53` = `d82931effa099f5420e0d63ad38a873dc6b50a53`），四枚工件跨代同 blob `true`。预测树三枚各标各处：上一枚 ref 对同一枚尖我复算 = `dee4b794b62797a9760b067d733ed96aa742060c`（原样输出 `evidence/ord0288-keyless-deadline/ord0310-mergetree-tip-x-previous-ref.out` blob `73cafd8de3e1a36ebd31fe767ab52d7b77a09e30`，与你那帖 `issuecomment-5832371591` 给的数逐位相同）；上上代收据里那枚 `efd67d82c1acc68dcea0f683307e00bc029e25cc` 标 SUPERSEDED（不删）；本代按新 ref 尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` = `aeaaf03c3708529f410162a0aeeb1fbaf66b0ac0`、退出 `0`、conflict 段空。

**一、两枚形状（谁也不替谁交卷）**

- 有键 = 0281（B 的）：`frontend/src/lib/writeDeadline.ts` blob `1d67e725ebb3348bbeb70d743793388ed36ed9d9`，常数 `export const CLIENT_WRITE_DEADLINE_MS = 60_000`，引用者只有 `frontend/src/features/execution/LiveRecovery.tsx`、`frontend/src/features/recovery/V14RecoveryTruthPanel.tsx`；`git grep -n fetchWithWriteDeadline 30a5f90e5deaed6e45a704ddcc7d6e5e9790475b -- frontend/src/features/planning/PlanWithAiSheet.tsx` 回 `0` 行。被测那一代里这枚文件不存在（`absent_from_my_tested_tree=false`），我是量完之后按线尖只读 `git show` 看到的。
- 无键 = 本单：新建 `frontend/src/lib/keylessWriteDeadline.ts` blob `1aea861b887273f70ec6cf726369c36a1398786e`；`frontend/src/features/planning/PlanWithAiSheet.tsx` blob `3bb6a39067a380c2f75629fd7562f0de8f5d2f2a` 里 `fetchWithKeylessWriteDeadline` 只裹 `agent/commands`。期限放在服务端写预算之上（`backend/app/core/config.py:96` 那枚 `45000`）才不会出现「服务器已判死、客户端还在等」，也不会催用户在服务器还在写时重来。

**二、屏上那句（干净轮 `run339785`，库 `_run339785.db`）**

`status=UNKNOWN_KEYLESS_WRITE_DEADLINE`、`origin=device`、`label=这台设备自己的读数（服务器没给句子）`（不冒充「服务器给出的原因」）、`detail_block_attached=true`、实测等待 `60519` ms、`post_count=1`。屏幕上那句原文（逐字，出自本轮证据文件 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run339785.json` blob `8a0fc019897f3a89f4c785ae7e1753eeb28ad3cc`）：

> POST /api/v1/journeys/fba471a9-017b-498d-ab9c-c036500a43a9/agent/commands -- 这台设备等到 60 秒就停下来了。这一笔的结果未知，不是没发生：请求已经发出去了，服务器可能还在做。也不能靠同一把键补问：这条路线不认幂等键，它没有收下这把键，没有可回读的凭条。

反推那一刀（读数出自证据文件 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run340266.json` blob `8ad7d0bb9190ed625ba623282715cf0cd622aefa`、臂收据 blob `d86e0e7ba757fbf18a0ba8d065b482b46a0b7bc1`）：常数从 `60000` 改小到 `7000` （臂 `K0310_DERIVATION_PROBE_CONSTANT_TO_7S`，轮次 `run340266`）⇒ 屏上秒数跟着变 `7`、实测等待从 `60519` ms 变 `7580` ms，该臂仍判 `HOLDING_AS_EXPECTED`。数值与计时器动在同一处定义上，所以那句里的秒数不是另一处硬编码。

**三、服务端字段读数（不用状态码冒充 DB 事实）**

库 `C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_81mksw4j\suite.db`、表 `idempotency_keys`、字段出处 `evidence/ord0288-keyless-deadline/ord0310-backend-readings.json` blob `74d4c0ea276c1126f4f4302e474f61d906606bec`，回读走第二条 `mode=ro` 连接：不带键连发三发 ⇒ `count(*)` 从 `0` 到 `0`（凭条 +0 行），同轮 `journey_missions` 从 `0` 到 `3`、`distinct_mission_ids=3`；带一把形制正确的键仍 +0 行（凭条表列 `count(*)`）。
认键那一支 `plans/generate`（服务器只在这一支收键）：读数取自 `evidence/ord0288-keyless-deadline/ord0310-backend-readings.json` 的 `T1a` 格，blob `74d4c0ea276c1126f4f4302e474f61d906606bec` ⇒ 第一发回答 `201`、同键换正文第二发 `409`（服务器原话 `same idempotency key used for a different request`）。
同一本账的 `T1b` 格 blob `74d4c0ea276c1126f4f4302e474f61d906606bec` 给出落下的凭条行：`key=plans.generate:1b3ec233-4261-406e-9d00-e17136c6a711`、`operation=plans.generate`、`response_status=201`，与客户端第一发看到的 `201` 相等（`response_status == client_status_first` 是本格断言）。

**四、反突变臂（逐臂带 (sha, nodeid, shape)）**

| 臂 | 红了几枚节点 | gate exit | 还原 | claimed |
| --- | --- | --- | --- | --- |
| `K0310_DEADLINE_RENAMED_AS_CANCEL` | 1 | 1 | true | KILLED |
| `K0310_DEVICE_NOTE_UNDER_SERVER_LABEL` | 1 | 1 | true | KILLED |
| `K0310_SENTENCE_PROMISES_REPLAY` | 1 | 1 | true | KILLED |
| `K0310_DEADLINE_IMPERSONATES_TRAVELLER` | 1 | 1 | true | KILLED |
| `K0310_TIMER_FIRES_BEFORE_THE_CONSTANT` | 3 | 1 | true | KILLED |
| `K0310_DERIVATION_PROBE_CONSTANT_TO_7S` | 0 | 0 | true | HOLDING_AS_EXPECTED |

聚合 `killed=5/5`、`survived=0`、`every_arm_parsed_at_least_one_node=true`、`tree_unchanged_by_this_run=true`。**`claimed_result` 只是我这辆道的观测，`derived_result` 一律 null；等级归红队，我不签级。**

**五、两处我自己的账（不抹）**

头两轮臂收据把每一枚臂都报成 SURVIVED，而同一些运行的行数是 `1 failed` —— 正则少了 `re.M`，`^`/`$` 只对着整段文本两端，计数恒为 0；修具那一笔就是候选尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320`（驱动器 blob 见下表 `ord0310-tool-kill-arms.py`），本条所有数字出自修好之后那一轮。另一处：`K0310_SENTENCE_PROMISES_REPLAY` 第一次真存活 —— 门禁只在折叠态读卡片，而禁句活在「技术详情」展开之后；补法是折叠+展开各读一遍，并把「不能靠同一把键补问」钉成逐字判据。两处都是收紧量具，不是把断言改松换绿。

**六、发布与回读**：`evidence/ord0288-keyless-deadline/` 目录现在共 `50` 件，本轮逐件独立 GET 量了 `28` 件（本代交件），`byteLevelMatches=28`、`notMatching=[]`；剩下 `22` 件是上一代同名/异名件，我这一轮没有重贴它们的内容，所以它们具名为 `PRIOR_GENERATION_NOT_RESTAGED` 而不是被算成不吻合。
0 覆盖不是我口述：每一件都走 `HJ-P3_evidence/gated_push.py` 那道同字节即跳过、异字节即拒绝的门，发布日志逐件写着 FRESH / SKIP / REFUSE —— 本代有一件被 REFUSE （`ord0310-tool-gauge-landed-block.py`，因为我把那件工具改了字），按规矩改名重发成 `ord0310-tool-gauge-landed-block-r2.py`，旧那件一个字节没动。

那本账本自己不能自证，所以它单独由一次 GET 收尾（原话）：`GET https://api.github.com/repos/Canshu-King/CityNexus/contents/evidence/ord0288-keyless-deadline/ord0310-readback-r3.json?ref=commander/control -> HTTP 200 | remote 29,866 B blob 1586e511059c0333538fe1abab0e272ac09c40aa | local 29,866 B blob 1586e511059c0333538fe1abab0e272ac09c40aa => BYTE-LEVEL MATCH`。

（本条正文自己、以及判它的两把尺输出，也在同一目录：`ord0310-post-body-r2.md`、`ord0310-q43r4b-on-post-r2.json`、`ord0310-q43r3-on-post-r2.json`；它们的逐字节回读记在下一本账 `ord0310-readback-r4.json` 里 —— 那本账在本条发出去之后才生成，所以这里只给名字不给读数，免得我拿一段还没定型的字去算哈希。）

| 文件（全部在 `evidence/ord0288-keyless-deadline/` 下，本单之前该目录不存在） | blob（40 位） | 远端字节 |
| --- | --- | --- |
| `ord0310-arms-receipt-r4.json` | `d86e0e7ba757fbf18a0ba8d065b482b46a0b7bc1` | 21,496 |
| `ord0310-backend-readings-r2.json` | `74d4c0ea276c1126f4f4302e474f61d906606bec` | 2,053 |
| `ord0310-gate-evidence-run339785.json` | `8a0fc019897f3a89f4c785ae7e1753eeb28ad3cc` | 6,242 |
| `ord0310-gate-evidence-run339864.json` | `69ab58a560ed3f3133abe6a78891cc0c2e17392a` | 2,235 |
| `ord0310-gate-evidence-run339947.json` | `6708b2906fef4bd94cdc2edbee0b03848849bc8d` | 2,235 |
| `ord0310-gate-evidence-run340026.json` | `6453ea942538d6413801f455137ecbab6a0ce2ff` | 2,235 |
| `ord0310-gate-evidence-run340105.json` | `956c286e59e3315361109e10fa9ec83b88495f9e` | 7,552 |
| `ord0310-gate-evidence-run340186.json` | `0d0e93a8846c62d95dc3693a797e7bf0acaece34` | 131 |
| `ord0310-gate-evidence-run340266.json` | `8ad7d0bb9190ed625ba623282715cf0cd622aefa` | 6,234 |
| `ord0310-ledger-block-r2.md` | `320084ace903d1c195f2fc036768ffbab6278c35` | 15,511 |
| `ord0310-left-right-count-trap.out` | `ee03cf3206ff6f8e0138050c10d2be8fe9e26d91` | 521 |
| `ord0310-mergetree-tip-x-candidate-r2.out` | `8db66d7493f634f8e4f9a4a217fc3c963b30db6a` | 485 |
| `ord0310-mergetree-tip-x-previous-ref.out` | `73cafd8de3e1a36ebd31fe767ab52d7b77a09e30` | 41 |
| `ord0310-path-disjointness-r2.tsv` | `d74dbd49ff8975b05020d0984dcc128d23f2af34` | 897 |
| `ord0310-q38r2-on-receipt-r2.json` | `64c7fd6398fb025b1feae8278a32bc96ec6e2150` | 12,127 |
| `ord0310-q43r3-on-block-r2.json` | `9d04379b6cb3795e954aff51bf355936359ca356` | 588 |
| `ord0310-q43r4b-on-block-r2.json` | `bfbc4a1fe4e77b82a735c9ffa80aad997cf4d763` | 576 |
| `ord0310-tip-read-r2.out` | `0e19d401a3174edfd204c03bca81c8e8e0435682` | 1,617 |
| `ord0310-tool-gauge-landed-block-r2.py` | `76e76aa1418988f3c14dda9d764276f3c3a4b6e8` | 2,356 |
| `ord0310-tool-kill-arms.py` | `bf0f0cce780cf934d09338186ab699964f08ca0d` | 14,063 |
| `ord0310-tool-make-block-r2.py` | `bf36f33243568c86fba28ad24ed8bcb15ae3662b` | 22,228 |
| `ord0310-tool-make-post-r2.py` | `6b24bddc307500b1fd9158f2f0557211fc340798` | 19,825 |
| `ord0310-tool-make-receipt-r2.py` | `1d0b21e97bb7df10c4aeb76eca2707be76111781` | 39,769 |
| `ord0310-tool-pub-names-r2.py` | `919f8ea96ed57dbcb1ce242c9400229e42af3b79` | 4,342 |
| `ord0310-tool-publish.py` | `08bf5229f6a52077b99ef49a37fb92d5e9536f4c` | 2,715 |
| `ord0310-tool-readback-r2.py` | `16111ad7a99b5581793299404235f5de6929fe04` | 5,678 |
| `ord0310-tool-stage-pub-r3.py` | `322e5ac91c19684d51897830e7a3a2bc67907f9b` | 3,693 |
| `ord0310_keyless_deadline_receipt_r2.json` | `35e40da15ef65b024b10269cb3774faca77f9641` | 34,150 |

账本块已落 `## DELIVERIES`（追加，不动别人的块），逐字节同 `evidence/ord0288-keyless-deadline/`，blob `320084ace903d1c195f2fc036768ffbab6278c35`（15,511 B）；两把尺判它的输出也在同目录（`ord0310-q43r4b-on-block.json`、`ord0310-q43r3-on-block.json`）：Q43 r4b（尺 blob `efa6b7a383e094e2ede89f5dd8565b12feed0171`）判绿，Q43 r3（尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）判干净。

**七、队列里还压着的**：ORD-0288 的另一半（服务端那一腿）不在本单射程；ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED；ORD-0232 端到端复放仍等合流窗口。另外 F 的 0307 已经落了（`refs/heads/review/ord0307-credential-gate-f` = `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 就是它），所以 ORD-0308 那张表里 `NOT_APPLICABLE_missing_candidate` 那一格现在有条件重跑 —— 你要的话我下一单做。

**纪律**：`0 权威线写入`、`0 推他人 ref`（只推了自己命名的那一枚新 ref）、`demo/reset 0`、`_live`/`_preview` 库 0 读写、凭据 0 打印（第二路读 ref 的 token 只进内存，`ord0310-tip-read.out` 里那一行写的是占位符）、`0 为了绿而改断言`。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
