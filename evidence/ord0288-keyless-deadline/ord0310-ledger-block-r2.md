### SESSION=e345b9d6 @2026-09-25 20:55+08 —— **ORD-0310 交付（r2_recut_onto_the_frozen_tip）：给无键写腿一枚可指名的设备期限，屏上那句话只敢说自己射程以内的事（产码 2 件 + 门 2 件 + 臂 6 枚）**

单号 ORD-0310，形制按仲裁 Q54=①。候选（我自己命名的新 ref，别人的 ref 一枚没碰）：`refs/heads/review/ord0310-keyless-deadline-d-on-30a5f90e` = `2344145ce6342b6ac32ac4d0955c0f524d8c9320`（`git ls-remote` 回读，原样输出在 `evidence/ord0288-keyless-deadline/ord0310-tip-read-r2.out`，blob `0e19d401a3174edfd204c03bca81c8e8e0435682`）。被量那一代 = `2344145ce6342b6ac32ac4d0955c0f524d8c9320`；推上去那一代 = `2344145ce6342b6ac32ac4d0955c0f524d8c9320`，四枚被测工件在两枚上逐枚同 blob（`subject_files_equal_to_the_tested_tree=true`），差的只有本车道自己的工具：[]。

**权威尖只读、两路一致**：`refs/heads/mirror/integration-frontend-apple-pass1` = `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b`；第二路（git/ref REST）= `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b`，`the_two_routes_agree=true`，全部测量做完后复测 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b`，`stable_across_this_run=true`。我 0 次移动它。

**这一代是怎么来的（号令者 20:2x 令走甲、线冻住）**：从现读的尖 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 直接切，产品那一笔 = `2344145ce6342b6ac32ac4d0955c0f524d8c9320`，其父位 `65656a7bacbcd9a3c18ceb917b1fbfdfa0791412` 与这枚尖相等 `true`。上一代被测尖 `b025432ded0381d83ebf36b85202a345bede2fcb` 的收据与预测树都不删：收据 blob `b7029fd3a8c806a3dceb6143133480a587c5c5f0`，预测树 `efd67d82c1acc68dcea0f683307e00bc029e25cc` 标 `SUPERSEDED_BY_THIS_GENERATION_NOT_DELETED`。只换基座不改字是量出来的，不是说的：产品那一笔在两代上的 `patch-id` 都是 `d82931effa099f5420e0d63ad38a873dc6b50a53`（`git show <commit> | git patch-id --stable`），四枚被测工件跨代同 blob `true`。三枚预测树各就各位、旧的都不删：上一枚 ref `b025432ded0381d83ebf36b85202a345bede2fcb` 对同一枚尖的预测树我自己复算 = `dee4b794b62797a9760b067d733ed96aa742060c`（与号令者那帖 `issuecomment-5832371591` 给的数逐位相同，原样输出 `evidence/ord0288-keyless-deadline/ord0310-mergetree-tip-x-previous-ref.out` blob `73cafd8de3e1a36ebd31fe767ab52d7b77a09e30`），上上代收据里那枚 `efd67d82c1acc68dcea0f683307e00bc029e25cc` 标 `SUPERSEDED_BY_THIS_GENERATION_NOT_DELETED`。本代按 ref 当下尖重算的合流预测：`git merge-tree --write-tree 30a5f90e5deaed6e45a704ddcc7d6e5e9790475b 2344145ce6342b6ac32ac4d0955c0f524d8c9320` ⇒ 退出 `0`、预测树 `aeaaf03c3708529f410162a0aeeb1fbaf66b0ac0`、conflict 段 = `（空）`。臂跑的那一枚树与产品那一笔的关系也逐枚核过：`tested_tree_vs_product_commit.all_equal=true`。

**代际绑定（不自宣携带）**：分叉点 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b`；尖上比我这一笔多 `0` 笔：（无 —— 我就是从尖上切的）。线自分叉动了 `0` 件，我动了 `13` 件，**两边交集 `0` 件**（逐行表 `evidence/ord0288-keyless-deadline/ord0310-path-disjointness-r2.tsv`，blob `d74dbd49ff8975b05020d0984dcc128d23f2af34`）。合流只读预测：`git merge-tree --write-tree 30a5f90e5deaed6e45a704ddcc7d6e5e9790475b 2344145ce6342b6ac32ac4d0955c0f524d8c9320` ⇒ 退出 `0`、预测树 `aeaaf03c3708529f410162a0aeeb1fbaf66b0ac0`、conflict 段 = `（空）`（原样输出 `evidence/ord0288-keyless-deadline/ord0310-mergetree-tip-x-candidate-r2.out`，blob `8db66d7493f634f8e4f9a4a217fc3c963b30db6a`）。`frontend` 子树：我这一代 `3257a0266fbb73cfd452c5a1106ba416a4703ec0`、线尖 `a9076ce45f58f8c449950e573944cd801577c184` ⇒ 按 Q24 本块所有读数只属于 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 那一代；号令者落地之后我再在落成那一代重跑一轮绿 + 一轮拆。

**一、两枚形状分开具名（谁也不替谁交卷）**

- 有键那一支 = ORD-0281（不是我交的）：`frontend/src/lib/writeDeadline.ts` blob `1d67e725ebb3348bbeb70d743793388ed36ed9d9`，导出常数 `export const CLIENT_WRITE_DEADLINE_MS = 60_000`，引用者只有 `frontend/src/features/execution/LiveRecovery.tsx`、`frontend/src/features/recovery/V14RecoveryTruthPanel.tsx`；`git grep -n fetchWithWriteDeadline 30a5f90e5deaed6e45a704ddcc7d6e5e9790475b -- frontend/src/features/planning/PlanWithAiSheet.tsx` 回 `0` 行。本单对它 0 字节改动 —— 它随基座进我的候选（树内 blob = `1d67e725ebb3348bbeb70d743793388ed36ed9d9` 与线尖同值），而本道那一笔的改动清单里没有它。
- 无键那一支 = 本单：新建 `frontend/src/lib/keylessWriteDeadline.ts` blob `1aea861b887273f70ec6cf726369c36a1398786e`，常数一处 `KEYLESS_WRITE_DEADLINE_MS = 60000`，屏上秒数与计时器同取它（`KEYLESS_WRITE_DEADLINE_SECONDS = KEYLESS_WRITE_DEADLINE_MS / 1000`）；`frontend/src/features/planning/PlanWithAiSheet.tsx` blob `3bb6a39067a380c2f75629fd7562f0de8f5d2f2a` 里 `fetchWithKeylessWriteDeadline` 只裹 `agent/commands` 那一发。两枚数值都是 `60000` ms，但各管各的调用点，我没有替 0281 交卷。

**期限为什么是 `60000` ms**：服务端写预算 `45000` ms（`backend/app/core/config.py:96`）、锁等待 `30000` ms（`backend/app/core/config.py:95`）——设备期限放在服务端预算之上，才会出现「服务器已判死、客户端还在等」那一句；压到它下面就等于在服务器还在写的时候催用户重来，那正是 Q54 要防的重复提交面。

**二、屏上那句话（两件事都在，四句禁句都不在）**

对象 = 干净轮 `run339785` 的 K1 节点（库 `_run339785.db`、端口 4910）。逐行读数在门禁自己写出的证据文件里：`evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run339785.json`，blob `8a0fc019897f3a89f4c785ae7e1753eeb28ad3cc`（6242 B）。`status=UNKNOWN_KEYLESS_WRITE_DEADLINE`、`origin=device`、`label=这台设备自己的读数（服务器没给句子）`（不是「服务器给出的原因」那四个字，所以设备自报没冒充服务器），`detail_block_attached=true`，实测等待 `60519` ms、`post_count=1`（一发，不是重发），判据 `10` 行逐行来自这一轮运行。两件事：「结果未知」并明写「不是没发生」；「不能靠同一把键补问」逐字钉进断言。四句禁句（已取消 / 没有发生 / 再试一次 / 连不上服务端）逐条判缺。

卡片正文（展开「技术详情」之后实际读到那段的前 96 字）：`这一笔的结果未知（不是没发生） 这台设备停止等待了，而请求已经发出去，服务器那边可能还在做。这条路线不收幂等键，所以这一笔既没有可回读的凭条，也不能靠同一把键补问。先刷新核对结果，不要重复提交`

**常数可反推（先例是那对 TB/TC 反件，`refs/heads/review/0281-write-deadline-keyed-b3`）**：干净轮屏幕那句里的秒数是 `60`（实测等待 `60519` ms，证据 blob `8a0fc019897f3a89f4c785ae7e1753eeb28ad3cc`）；把常数从 `60000` 改小到 `7000` 的那一枚探针臂 `K0310_DERIVATION_PROBE_CONSTANT_TO_7S`（轮次 `run340266`，证据 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run340266.json` blob `8ad7d0bb9190ed625ba623282715cf0cd622aefa`）⇒ 屏上跟着变成 `7` 秒、实测等待变成 `7580` ms、`post_count=1`，该臂判 `HOLDING_AS_EXPECTED`（仍绿）。两处一起动才叫同源；这就排除了「屏幕上那个秒数是另一处硬编码」。

**号令者那条新事实我复算成立（判据是「到点」不是「有没有 signal」）**：在尖 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b` 上两条 POST 的选项对象本来就带 `signal,` —— 行号 394, 454, 529, 575, 667（调用点在第 452, 518, 573, 600, 653 行）。所以本单加的是期限：wrapper 先原样接住调用方的信号（`frontend/src/lib/keylessWriteDeadline.ts` 第 93 行读 `init.signal`），到点才由 `firedHere` 抛 `KeylessWriteDeadlineMissed`；旅行者自己按取消仍走取消那一支（`CANCELLED_AFTER_SEND`）。这条判据有牙齿：K3 反控本轮判 `GREEN`，而拆掉 `firedHere` 判定的臂 `K0310_DEADLINE_IMPERSONATES_TRAVELLER` 实测红的节点是 `["K3 反控：旅行者按取消时，期限不许冒充用户"]`，它自报 `KILLED`。

**三、服务端字段读数（不用状态码冒充 DB 事实）**

门 `backend/tests/test_qoder_ord0310_keyless_leg_receipts.py`（blob `bb2111362c00272d056e0a709bf73a1009366716`，`5` 格），库文件具名 `C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_81mksw4j\suite.db`，表 `idempotency_keys`，回读走第二条只读连接（`mode=ro`），与写入方不同连接。

- K-1（不带键连发三发 `agent/commands`）：`idempotency_keys.count(*)` 从 `0` 到 `0`（+0），同轮 `journey_missions` 从 `0` 到 `3`（+3），三个 mission id 互不相同（`distinct_mission_ids=3`）。**凭条表 +0 行而业务表 +3 行 = 「无键可回读」是服务器的形状，不是我推测的。**
- K-2（带一把形制正确的键仍无凭条）：`count(*)` 从 `0` 到 `0`，`mission_id_present=true` ⇒ 请求里有个头不等于服务器收了键。
- T-1(a)（服务器认键那一支 `plans/generate`，字段读数出处 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r2.json` blob `74d4c0ea276c1126f4f4302e474f61d906606bec`，表 `idempotency_keys`）：第一发回答 `201`、第二发同键不同正文回答 `409`，`idempotency_keys.count(*)` 两次读数 `[1, 1]`；服务器原话：`same idempotency key used for a different request`。那两个数是**观测到的回答**，不是本单主张的数量。
- T-1(b)（凭条行落成长什么样，同一本账 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r2.json` 的 `T1b` 格 blob `74d4c0ea276c1126f4f4302e474f61d906606bec`）：`idempotency_keys.key` = `plans.generate:1b3ec233-4261-406e-9d00-e17136c6a711`、`.operation` = `plans.generate`、`.response_status` = `201`，客户端两发状态各为 `201` / `201`；键被拒那一发（畸形键）先落行为 `false`。读过的列：["key", "operation", "response_status"]。

**四、反突变臂（逐臂带 (sha, nodeid, shape) 与还原摘要）**

| 臂 | 红的节点（几枚 / 具名） | gate exit | 还原到被测字节 | claimed_result |
| --- | --- | --- | --- | --- |
| `K0310_DEADLINE_RENAMED_AS_CANCEL` | 1 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源` | 1 | true | KILLED |
| `K0310_DEVICE_NOTE_UNDER_SERVER_LABEL` | 1 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源` | 1 | true | KILLED |
| `K0310_SENTENCE_PROMISES_REPLAY` | 1 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源` | 1 | true | KILLED |
| `K0310_DEADLINE_IMPERSONATES_TRAVELLER` | 1 枚：`K3 反控：旅行者按取消时，期限不许冒充用户` | 1 | true | KILLED |
| `K0310_TIMER_FIRES_BEFORE_THE_CONSTANT` | 3 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源`；`K2 正控：服务器两秒内答完时，这枚期限不碰正常结局`；`K3 反控：旅行者按取消时，期限不许冒充用户` | 1 | true | KILLED |
| `K0310_DERIVATION_PROBE_CONSTANT_TO_7S` | 0 枚：（无 —— 探针按预期绿） | 0 | true | HOLDING_AS_EXPECTED |

聚合：`arms_total=6`、`killed=5`、`survived=0`、`probes=1`、`every_arm_parsed_at_least_one_node=true`、`all_arms_restored_to_tested_tree_bytes=true`、`tree_unchanged_by_this_run=true`。逐臂 `anchor_hits` 与 `expected_anchor_hits` 都是 1（改错了地方就不算臂），每臂同一枚键的先决条件在本轮成立：`all_arms_carry_a_green_same_key_precondition=true`。`claimed_result` 是本车道观测，`derived_result` 全为 null —— 等级与派生归红队。

**五、我欠的账，写在这里不抹**

其一：头两轮臂收据里 **每一枚臂都被误判成 SURVIVED**，而同一些运行的 pytest 行数明明是 `1 failed`。原因在量具：解析节点行的正则少了 `re.M`，`^` 与 `$` 只对着整段捕获文本的两端，于是一枚节点都没匹配上，计数恒为 0。修法提交（只改驱动器，产品字节与断言一字未动）`2344145ce6342b6ac32ac4d0955c0f524d8c9320` 之前那一笔，本块全部数字出自修好之后的轮次：臂收据 `evidence/ord0288-keyless-deadline/ord0310-arms-receipt-r4.json`，blob `d86e0e7ba757fbf18a0ba8d065b482b46a0b7bc1`。一个从不命中的计数既不是绿也不是杀。

其二：`K0310_SENTENCE_PROMISES_REPLAY` 第一次是 SURVIVED —— 门禁只在折叠态读卡片，而我把禁句写进了「技术详情」展开之后；而且当时只要求句子里「提到一把键」，松散到能放过承诺补问的说法。补法是折叠态与展开态各读一遍、并把「不能靠同一把键补问」钉成逐字判据，改的是量具不是断言（门 `frontend/e2e/qoder-ord0310-keyless-write-deadline.spec.ts` blob `61fa23882dc0936ea29d08e12d15d1d936157049`）。收紧之后同一枚臂红。

其三（本代新增的自纠，原样命令与输出都在 `evidence/ord0288-keyless-deadline/ord0310-left-right-count-trap.out` blob `ee03cf3206ff6f8e0138050c10d2be8fe9e26d91`）：我给上一代写 `ref_tip_read` 那格时把 `git rev-parse <rev>:<path>` 的**回显**当成了 blob（该路径不存在时它原样打印参数），于是一格印出空 blob、另一格印出像 sha 其实不是的串；另一处是把 `git rev-list --left-right --count A B` 少了三点号来读分母，同一对操作数用正确形制 `A...B` 量出来是领先 `6` / 落后 `5`（号令者亲测同值），错误形制吐出的那个数根本不是分母，而我一度把它当「落后好几百」写进汇报。两处都改成**先校验 40 位十六进制再落字**，并把工具随件发布（`evidence/ord0288-keyless-deadline/ord0310-tool-make-receipt-r2.py`），这样别人复跑用的是被判的那份字节。

**判据与出处**：主收据 `evidence/ord0288-keyless-deadline/ord0310_keyless_deadline_receipt_r2.json`，blob `35e40da15ef65b024b10269cb3774faca77f9641`（34,150 B），6 格自证；服务端读数 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r2.json` blob `74d4c0ea276c1126f4f4302e474f61d906606bec`；尺 Q38 r2（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）判这枚收据 ⇒ `Q38_GATE_GREEN`、hard `0`、soft `0`、exit `0`，输出 `evidence/ord0288-keyless-deadline/ord0310-q38r2-on-receipt-r2.json` blob `64c7fd6398fb025b1feae8278a32bc96ec6e2150`。本块自身的两把尺输出同目录（名字里带 `on-block` / `on-post`）。

**纪律**：`0 权威线写入`、`0 推他人 ref`（只推了自己命名的 `refs/heads/review/ord0310-keyless-deadline-d-on-30a5f90e`）、`demo/reset 0`、`_live`/`_preview` 库 0 读写、凭据 0 打印 （第二路读 ref 的 token 只进内存，`evidence/ord0288-keyless-deadline/ord0310-tip-read-r2.out` 里那一行写的是占位符）、`0 为了绿而改断言`（红都是收紧量具修掉的，见第五节）；交件走新路径 `evidence/ord0288-keyless-deadline/`，逐件独立 GET 回读，已发布路径 0 覆盖 0 改名。
