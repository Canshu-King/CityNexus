【号令者 494abfd7 → D 车道 e345b9d6｜ORD-0310 交付：给无键写腿一枚可指名的设备期限（形制按仲裁 Q54=①）】

一句话：`agent/commands` 那一发（不收幂等键的那一支）现在有了一枚**只在一处定义、屏上那个秒数与计时器同源**的设备期限 `60000` ms；到点后屏幕上只说它射程以内的事 —— 结果未知、不是没发生、这一笔不能靠同一把键补问。有键那一支（0281）我一个字没改。候选 `refs/heads/review/ord0310-keyless-deadline-d` = `b025432ded0381d83ebf36b85202a345bede2fcb`（父 = 我当时读到的线位；权威尖只读 `7856e03f6238da3000976eb6e690a448dfa39b9a`，两路一致，我 0 次移动）。

**先说清一枚你不该把它读成什么**：线尖在我这一代之后又动了 `4` 笔（B 的 0281 前端半 + F 的 0307），自分叉点 `5aff3722d5c36c760a424f5fea5c3a771298f9ac` 起线动 `8` 件、我动 `6` 件，**两边交集 `0` 件**；只读合流预测 `git merge-tree --write-tree 7856e03f6238da3000976eb6e690a448dfa39b9a b44a77148a2431252dfb546c8067d472813b2cbe` ⇒ 退出 `0`、预测树 `efd67d82c1acc68dcea0f683307e00bc029e25cc`、conflict 段空。按 Q24 本单所有读数只属于 `b44a77148a2431252dfb546c8067d472813b2cbe` 那一代，我不折算到尖 —— **要不要我在当代尖上重跑一轮绿 + 一轮拆（≈25 分钟）请落字**；不落字我就按这一代交。

**一、两枚形状（谁也不替谁交卷）**

- 有键 = 0281（B 的）：`frontend/src/lib/writeDeadline.ts` blob `1d67e725ebb3348bbeb70d743793388ed36ed9d9`，常数 `export const CLIENT_WRITE_DEADLINE_MS = 60_000`，引用者只有 `frontend/src/features/execution/LiveRecovery.tsx`、`frontend/src/features/recovery/V14RecoveryTruthPanel.tsx`；`git grep -n fetchWithWriteDeadline 7856e03f6238da3000976eb6e690a448dfa39b9a -- frontend/src/features/planning/PlanWithAiSheet.tsx` 回 `0` 行。被测那一代里这枚文件不存在（`absent_from_my_tested_tree=true`），我是量完之后按线尖只读 `git show` 看到的。
- 无键 = 本单：新建 `frontend/src/lib/keylessWriteDeadline.ts` blob `1aea861b887273f70ec6cf726369c36a1398786e`；`frontend/src/features/planning/PlanWithAiSheet.tsx` blob `3bb6a39067a380c2f75629fd7562f0de8f5d2f2a` 里 `fetchWithKeylessWriteDeadline` 只裹 `agent/commands`。期限放在服务端写预算之上（`backend/app/core/config.py:96` 那枚 `45000`）才不会出现「服务器已判死、客户端还在等」，也不会催用户在服务器还在写时重来。

**二、屏上那句（干净轮 `run335277`，库 `_run335277.db`）**

`status=UNKNOWN_KEYLESS_WRITE_DEADLINE`、`origin=device`、`label=这台设备自己的读数（服务器没给句子）`（不冒充「服务器给出的原因」）、`detail_block_attached=true`、实测等待 `60107` ms、`post_count=1`。屏幕上那句原文（逐字，出自本轮证据文件 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run335277.json` blob `048851d1f25d32523b396fa970338a846aca8903`）：

> POST /api/v1/journeys/4d6db997-38a4-4c94-82b0-10876c958b96/agent/commands -- 这台设备等到 60 秒就停下来了。这一笔的结果未知，不是没发生：请求已经发出去了，服务器可能还在做。也不能靠同一把键补问：这条路线不认幂等键，它没有收下这把键，没有可回读的凭条。

反推那一刀（读数出自证据文件 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run335765.json` blob `30aaac9604843c191b2ff47ef23915e306681335`、臂收据 blob `a748c41a93342f767b8b47da642e98a94d798e87`）：常数从 `60000` 改小到 `7000` （臂 `K0310_DERIVATION_PROBE_CONSTANT_TO_7S`，轮次 `run335765`）⇒ 屏上秒数跟着变 `7`、实测等待从 `60107` ms 变 `7131` ms，该臂仍判 `HOLDING_AS_EXPECTED`。数值与计时器动在同一处定义上，所以那句里的秒数不是另一处硬编码。

**三、服务端字段读数（不用状态码冒充 DB 事实）**

库 `C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_4hlgea2f\suite.db`、表 `idempotency_keys`、字段出处 `evidence/ord0288-keyless-deadline/ord0310-backend-readings.json` blob `710f3c8d22379026c6910c74e180fca8c207b04a`，回读走第二条 `mode=ro` 连接：不带键连发三发 ⇒ `count(*)` 从 `0` 到 `0`（凭条 +0 行），同轮 `journey_missions` 从 `0` 到 `3`、`distinct_mission_ids=3`；带一把形制正确的键仍 +0 行（凭条表列 `count(*)`）。
认键那一支 `plans/generate`（服务器只在这一支收键）：读数取自 `evidence/ord0288-keyless-deadline/ord0310-backend-readings.json` 的 `T1a` 格，blob `710f3c8d22379026c6910c74e180fca8c207b04a` ⇒ 第一发回答 `201`、同键换正文第二发 `409`（服务器原话 `same idempotency key used for a different request`）。
同一本账的 `T1b` 格 blob `710f3c8d22379026c6910c74e180fca8c207b04a` 给出落下的凭条行：`key=plans.generate:6f608826-37d2-4b88-b87e-3ab716023f53`、`operation=plans.generate`、`response_status=201`，与客户端第一发看到的 `201` 相等（`response_status == client_status_first` 是本格断言）。

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

头两轮臂收据把每一枚臂都报成 SURVIVED，而同一些运行的行数是 `1 failed` —— 正则少了 `re.M`，`^`/`$` 只对着整段文本两端，计数恒为 0；修具那一笔就是候选尖 `b025432ded0381d83ebf36b85202a345bede2fcb`（驱动器 blob 见下表 `ord0310-tool-kill-arms.py`），本条所有数字出自修好之后那一轮。另一处：`K0310_SENTENCE_PROMISES_REPLAY` 第一次真存活 —— 门禁只在折叠态读卡片，而禁句活在「技术详情」展开之后；补法是折叠+展开各读一遍，并把「不能靠同一把键补问」钉成逐字判据。两处都是收紧量具，不是把断言改松换绿。

**六、发布与回读**：`evidence/ord0288-keyless-deadline/` 共 `17` 件已发布（下表 16 件 + 最后那本回读账本自己），回读账本 `ord0310-readback-r1.json` 的远端 blob `f7257d8ae538709ee42f2efa5718bf2e747fa16d`（10,978 B，它不在下表里，因为下表就是它的内容）；落位前那次目录 `GET https://api.github.com/repos/Canshu-King/CityNexus/contents/evidence/ord0288-keyless-deadline?ref=commander/control` 服务器答的是 `Not Found`（我先量后写）⇒ 0 覆盖 0 改名；下表每行 = 对该文件一次独立 `GET https://api.github.com/repos/Canshu-King/CityNexus/contents/<path>?ref=commander/control`，base64 解回与本地逐字比、两边各重算 blob ⇒ `byteLevelMatches=16`、`notMatching=[]`。

那本账本自己不能自证，所以它单独由一次 GET 收尾（原话）：`GET https://api.github.com/repos/Canshu-King/CityNexus/contents/evidence/ord0288-keyless-deadline/ord0310-readback-r1.json?ref=commander/control -> HTTP 200 | remote 10,978 B blob f7257d8ae538709ee42f2efa5718bf2e747fa16d | local 10,978 B blob f7257d8ae538709ee42f2efa5718bf2e747fa16d => BYTE-LEVEL MATCH`。

（本条正文自己、以及判它的两把尺输出，也在同一目录：`ord0310-post-body.md`、`ord0310-q43r4b-on-post.json`、`ord0310-q43r3-on-post.json`；它们的逐字节回读记在第 2 本账 `ord0310-readback-r2.json` 里 —— 那本账在本条发出去之后才生成，所以这里只给名字不给读数，免得我拿一段还没定型的字去算哈希。）

| 文件（全部在 `evidence/ord0288-keyless-deadline/` 下，本单之前该目录不存在） | blob（40 位） | 远端字节 |
| --- | --- | --- |
| `ord0310-arms-receipt-r3.json` | `a748c41a93342f767b8b47da642e98a94d798e87` | 21,496 |
| `ord0310-backend-readings.json` | `710f3c8d22379026c6910c74e180fca8c207b04a` | 1,796 |
| `ord0310-gate-evidence-run335277.json` | `048851d1f25d32523b396fa970338a846aca8903` | 6,242 |
| `ord0310-gate-evidence-run335765.json` | `30aaac9604843c191b2ff47ef23915e306681335` | 6,234 |
| `ord0310-ledger-block.md` | `126eb4e97df9bfd0417511ce3672d943b119af78` | 12,209 |
| `ord0310-mergetree-tip-x-candidate.out` | `2b0bd9815d2fcd2b56ee47987fd5deda3469fe33` | 485 |
| `ord0310-path-disjointness.tsv` | `059a68d41a3fc96cd34dc67ec4472f379d39a859` | 995 |
| `ord0310-q38r2-on-receipt.json` | `148d5bc9c589c85e7582e20318e7b1de876d44df` | 7,997 |
| `ord0310-q43r3-on-block.json` | `0aa255e4fac3e3900c9785d2d034c93ab4c2199e` | 585 |
| `ord0310-q43r4b-on-block.json` | `cd3c175b0c93b3c472b344e1b180574875e9d4e9` | 573 |
| `ord0310-tip-read.out` | `dd1445df4b5524404dd07b46767d5282b91d9f86` | 1,593 |
| `ord0310-tool-gauge-landed-block.py` | `beaa3693b40ca3101d2280ef02a13cd7b4271ed8` | 2,062 |
| `ord0310-tool-kill-arms.py` | `bf0f0cce780cf934d09338186ab699964f08ca0d` | 14,063 |
| `ord0310-tool-make-block.py` | `e50b191f42089f4d04051ad056301f995ff5e47e` | 16,902 |
| `ord0310-tool-make-receipt.py` | `6d235d2f0ec92f5f62b68ff9fb10426c455120ff` | 30,603 |
| `ord0310_keyless_deadline_receipt_r1.json` | `b7029fd3a8c806a3dceb6143133480a587c5c5f0` | 25,055 |

账本块已落 `## DELIVERIES`（追加，不动别人的块），逐字节同 `evidence/ord0288-keyless-deadline/ord0310-ledger-block.md`，blob `126eb4e97df9bfd0417511ce3672d943b119af78`（12,209 B）；两把尺判它的输出也在同目录（`ord0310-q43r4b-on-block.json`、`ord0310-q43r3-on-block.json`）：Q43 r4b（尺 blob `efa6b7a383e094e2ede89f5dd8565b12feed0171`）判绿，Q43 r3（尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）判干净。

**七、队列里还压着的**：ORD-0288 的另一半（服务端那一腿）不在本单射程；ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED；ORD-0232 端到端复放仍等合流窗口。另外 F 的 0307 已经落了（`refs/heads/review/ord0307-credential-gate-f` = `7856e03f6238da3000976eb6e690a448dfa39b9a` 就是它），所以 ORD-0308 那张表里 `NOT_APPLICABLE_missing_candidate` 那一格现在有条件重跑 —— 你要的话我下一单做。

**纪律**：`0 权威线写入`、`0 推他人 ref`（只推了自己命名的那一枚新 ref）、`demo/reset 0`、`_live`/`_preview` 库 0 读写、凭据 0 打印（第二路读 ref 的 token 只进内存，`ord0310-tip-read.out` 里那一行写的是占位符）、`0 为了绿而改断言`。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
