### SESSION=e345b9d6 @2026-09-25 21:56+08 —— **ORD-0310 交付（r2_recut_onto_the_frozen_tip）：给无键写腿一枚可指名的设备期限，屏上那句话只敢说自己射程以内的事（产码 2 件 + 门 2 件 + 臂 7 枚）**

单号 ORD-0310，形制按仲裁 Q54=①。候选（我自己命名的新 ref，别人的 ref 一枚没碰）：`refs/heads/review/ord0310-keyless-deadline-d-on-2344145c` = `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`（`git ls-remote` 回读，原样输出在 `evidence/ord0288-keyless-deadline/ord0310-tip-read-r3.out`，blob `98f27ad4dc936c6d6561952b0a91a46d4b9c5aa3`）。被量那一代 = `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`；推上去那一代 = `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`，四枚被测工件在两枚上逐枚同 blob（`subject_files_equal_to_the_tested_tree=true`），差的只有本车道自己的工具：[]。

**权威尖只读、两路一致**：`refs/heads/mirror/integration-frontend-apple-pass1` = `2344145ce6342b6ac32ac4d0955c0f524d8c9320`；第二路（git/ref REST）= `2344145ce6342b6ac32ac4d0955c0f524d8c9320`，`the_two_routes_agree=true`，全部测量做完后复测 `2344145ce6342b6ac32ac4d0955c0f524d8c9320`，`stable_across_this_run=true`。我 0 次移动它。

**这一代是怎么来的（号令者 20:2x 令走甲、线冻住）**：从现读的尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 直接切，产品那一笔 = `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f`，其父位 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 与这枚尖相等 `false`。上一代被测尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 的收据与预测树都不删：收据 blob `35e40da15ef65b024b10269cb3774faca77f9641`，预测树 `aeaaf03c3708529f410162a0aeeb1fbaf66b0ac0` 标 `SUPERSEDED_BY_THIS_GENERATION_NOT_DELETED`。只换基座不改字是量出来的，不是说的：产品那一笔在两代上的 `patch-id` 都是 `d82931effa099f5420e0d63ad38a873dc6b50a53`（`git show <commit> | git patch-id --stable`），四枚被测工件跨代同 blob `true`。三枚预测树各就各位、旧的都不删：上一枚 ref `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 对同一枚尖的预测树我自己复算 = `dee4b794b62797a9760b067d733ed96aa742060c`（与号令者那帖 `issuecomment-5832371591` 给的数逐位相同，原样输出 `evidence/ord0288-keyless-deadline/ord0310-mergetree-tip-x-previous-ref.out` blob `73cafd8de3e1a36ebd31fe767ab52d7b77a09e30`），上上代收据里那枚 `aeaaf03c3708529f410162a0aeeb1fbaf66b0ac0` 标 `SUPERSEDED_BY_THIS_GENERATION_NOT_DELETED`。本代按 ref 当下尖重算的合流预测：`git merge-tree --write-tree 2344145ce6342b6ac32ac4d0955c0f524d8c9320 30de4ebe409f49c5e25f4758cb2e5f4e90764a4f` ⇒ 退出 `0`、预测树 `a5b5d3f5b253b6bcc635567c9fe1f2fb264e23f8`、conflict 段 = `（空）`。臂跑的那一枚树与产品那一笔的关系也逐枚核过：`tested_tree_vs_product_commit.all_equal=true`。

**代际绑定（不自宣携带）**：分叉点 `30a5f90e5deaed6e45a704ddcc7d6e5e9790475b`；**这一代已经在线上**：现读的尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 是我这一代的祖先（`authority_tip_is_ancestor_of_this_tree=true`），我这代比线尖只多 1 件：["review/ord0310_kill_arms.py"]（0 件产品/门字节）；「两边交集 0 件」那条论证属于落地前那一轮，这里不复述，只留 `evidence/ord0288-keyless-deadline/ord0310-path-disjointness-r2.tsv` 那件当落地前的原始依据。。
合流只读预测：`git merge-tree --write-tree 2344145ce6342b6ac32ac4d0955c0f524d8c9320 30de4ebe409f49c5e25f4758cb2e5f4e90764a4f` ⇒ 退出 `0`、预测树 `a5b5d3f5b253b6bcc635567c9fe1f2fb264e23f8`、conflict 段 = `（空）`（原样输出 `evidence/ord0288-keyless-deadline/ord0310-mergetree-tip-x-candidate-r3.out`，blob `f39d52e81e0fb9a0a1f4f772debdd5d36c40ce88`）。`frontend` 子树：我这一代 `3257a0266fbb73cfd452c5a1106ba416a4703ec0`、线尖 `3257a0266fbb73cfd452c5a1106ba416a4703ec0` ⇒ 按 Q24 本块所有读数只属于 `30de4ebe409f49c5e25f4758cb2e5f4e90764a4f` 那一代，而这正是权威线本身。

**一、两枚形状分开具名（谁也不替谁交卷）**

- 有键那一支 = ORD-0281（不是我交的）：`frontend/src/lib/writeDeadline.ts` blob `1d67e725ebb3348bbeb70d743793388ed36ed9d9`，导出常数 `export const CLIENT_WRITE_DEADLINE_MS = 60_000`，引用者只有 `frontend/src/features/execution/LiveRecovery.tsx`、`frontend/src/features/recovery/V14RecoveryTruthPanel.tsx`；`git grep -n fetchWithWriteDeadline 2344145ce6342b6ac32ac4d0955c0f524d8c9320 -- frontend/src/features/planning/PlanWithAiSheet.tsx` 回 `0` 行。本单对它 0 字节改动 —— 它随基座进我的候选（树内 blob = `1d67e725ebb3348bbeb70d743793388ed36ed9d9` 与线尖同值），而本道那一笔的改动清单里没有它。
- 无键那一支 = 本单：新建 `frontend/src/lib/keylessWriteDeadline.ts` blob `1aea861b887273f70ec6cf726369c36a1398786e`，常数一处 `KEYLESS_WRITE_DEADLINE_MS = 60000`，屏上秒数与计时器同取它（`KEYLESS_WRITE_DEADLINE_SECONDS = KEYLESS_WRITE_DEADLINE_MS / 1000`）；`frontend/src/features/planning/PlanWithAiSheet.tsx` blob `3bb6a39067a380c2f75629fd7562f0de8f5d2f2a` 里 `fetchWithKeylessWriteDeadline` 只裹 `agent/commands` 那一发。两枚数值都是 `60000` ms，但各管各的调用点，我没有替 0281 交卷。

**期限为什么是 `60000` ms**：服务端写预算 `45000` ms（`backend/app/core/config.py:96`）、锁等待 `30000` ms（`backend/app/core/config.py:95`）——设备期限放在服务端预算之上，才会出现「服务器已判死、客户端还在等」那一句；压到它下面就等于在服务器还在写的时候催用户重来，那正是 Q54 要防的重复提交面。

**二、屏上那句话（两件事都在，四句禁句都不在）**

对象 = 干净轮 `run342959` 的 K1 节点（库 `_run342959.db`、端口 5610）。逐行读数在门禁自己写出的证据文件里：`evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run342959.json`，blob `b98af1e5c0184a3da823ab6b3cdc7ac86059ad7c`（6242 B）。`status=UNKNOWN_KEYLESS_WRITE_DEADLINE`、`origin=device`、`label=这台设备自己的读数（服务器没给句子）`（不是「服务器给出的原因」那四个字，所以设备自报没冒充服务器），`detail_block_attached=true`，实测等待 `60544` ms、`post_count=1`（一发，不是重发），判据 `10` 行逐行来自这一轮运行。两件事：「结果未知」并明写「不是没发生」；「不能靠同一把键补问」逐字钉进断言。四句禁句（已取消 / 没有发生 / 再试一次 / 连不上服务端）逐条判缺。

卡片正文（展开「技术详情」之后实际读到那段的前 96 字）：`这一笔的结果未知（不是没发生） 这台设备停止等待了，而请求已经发出去，服务器那边可能还在做。这条路线不收幂等键，所以这一笔既没有可回读的凭条，也不能靠同一把键补问。先刷新核对结果，不要重复提交`

**常数可反推（先例是那对 TB/TC 反件，`refs/heads/review/0281-write-deadline-keyed-b3`）**：干净轮屏幕那句里的秒数是 `60`（实测等待 `60544` ms，证据 blob `b98af1e5c0184a3da823ab6b3cdc7ac86059ad7c`）；把常数从 `60000` 改小到 `7000` 的那一枚探针臂 `K0310_DERIVATION_PROBE_CONSTANT_TO_7S`（轮次 `run343841`，证据 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-run343841.json` blob `3f6b246fd5171658d49ffa15ddca676155fe51df`）⇒ 屏上跟着变成 `7` 秒、实测等待变成 `7548` ms、`post_count=1`，该臂判 `HOLDING_AS_EXPECTED`（仍绿）。两处一起动才叫同源；这就排除了「屏幕上那个秒数是另一处硬编码」。

**号令者那条新事实我复算成立（判据是「到点」不是「有没有 signal」）**：在尖 `2344145ce6342b6ac32ac4d0955c0f524d8c9320` 上两条 POST 的选项对象本来就带 `signal,` —— 行号 414, 474, 553, 600, 692（调用点在第 472, 598, 625, 678 行）。所以本单加的是期限：wrapper 先原样接住调用方的信号（`frontend/src/lib/keylessWriteDeadline.ts` 第 93 行读 `init.signal`），到点才由 `firedHere` 抛 `KeylessWriteDeadlineMissed`；旅行者自己按取消仍走取消那一支（`CANCELLED_AFTER_SEND`）。这条判据有牙齿：K3 反控本轮判 `GREEN`，而拆掉 `firedHere` 判定的臂 `K0310_DEADLINE_IMPERSONATES_TRAVELLER` 实测红的节点是 `["K3 反控：旅行者按取消时，期限不许冒充用户"]`，它自报 `KILLED`。

**号令者要的那枚双臂自证（有 `signal`、无期限）**：臂 `K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE` 只把外层包装拆掉（锚点命中 `1` 次、字节 `52799` → `52775`、还原后 `52799`），`signal` 那些行一字未动 —— 前提的证明文件 `evidence/ord0288-keyless-deadline/ord0310-signal-vs-deadline-proof.out` blob `eaa24028b6be59cb92ea10516a910567bd37ed62`（`1469` B）里把行号集合列出来了：原件与变异后都是 `[474, 553, 600, 692]`。该臂本轮逐节点读数 = `{"K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源": "RED", "K2 正控：服务器两秒内答完时，这枚期限不碰正常结局": "GREEN", "K3 反控：旅行者按取消时，期限不许冒充用户": "GREEN"}` ⇒ K1 红、K2/K3 仍绿，所以那格判据确实是「期限到了」，不是「有没有 signal」；它自报 `KILLED`，还原 `true`。

**三、服务端字段读数（不用状态码冒充 DB 事实）**

门 `backend/tests/test_qoder_ord0310_keyless_leg_receipts.py`（blob `bb2111362c00272d056e0a709bf73a1009366716`，`5` 格），库文件具名 `C:\Users\仓鼠王\AppData\Local\Temp\cnx_pytest_rt3r7nh_\suite.db`，表 `idempotency_keys`，回读走第二条只读连接（`mode=ro`），与写入方不同连接。

- K-1（不带键连发三发 `agent/commands`）：`idempotency_keys.count(*)` 从 `0` 到 `0`（+0），同轮 `journey_missions` 从 `0` 到 `3`（+3），三个 mission id 互不相同（`distinct_mission_ids=3`）。**凭条表 +0 行而业务表 +3 行 = 「无键可回读」是服务器的形状，不是我推测的。**
- K-2（带一把形制正确的键仍无凭条）：`count(*)` 从 `0` 到 `0`，`mission_id_present=true` ⇒ 请求里有个头不等于服务器收了键。
- T-1(a)（服务器认键那一支 `plans/generate`，字段读数出处 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r3.json` blob `89588274ba0180b51f3e26fb789f33ddbcd7a24f`，表 `idempotency_keys`）：第一发回答 `201`、第二发同键不同正文回答 `409`，`idempotency_keys.count(*)` 两次读数 `[1, 1]`；服务器原话：`same idempotency key used for a different request`。那两个数是**观测到的回答**，不是本单主张的数量。
- T-1(b)（凭条行落成长什么样，同一本账 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r3.json` 的 `T1b` 格 blob `89588274ba0180b51f3e26fb789f33ddbcd7a24f`）：`idempotency_keys.key` = `plans.generate:8b75f830-471a-4b5e-a814-5afb23e38cf7`、`.operation` = `plans.generate`、`.response_status` = `201`，客户端两发状态各为 `201` / `201`；键被拒那一发（畸形键）先落行为 `false`。读过的列：["key", "operation", "response_status"]。

**四、反突变臂（逐臂带 (sha, nodeid, shape) 与还原摘要）**

| 臂 | 红的节点（几枚 / 具名） | gate exit | 还原到被测字节 | claimed_result |
| --- | --- | --- | --- | --- |
| `K0310_DEADLINE_RENAMED_AS_CANCEL` | 1 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源` | 1 | true | KILLED |
| `K0310_DEVICE_NOTE_UNDER_SERVER_LABEL` | 1 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源` | 1 | true | KILLED |
| `K0310_SENTENCE_PROMISES_REPLAY` | 1 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源` | 1 | true | KILLED |
| `K0310_DEADLINE_IMPERSONATES_TRAVELLER` | 1 枚：`K3 反控：旅行者按取消时，期限不许冒充用户` | 1 | true | KILLED |
| `K0310_TIMER_FIRES_BEFORE_THE_CONSTANT` | 3 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源`；`K2 正控：服务器两秒内答完时，这枚期限不碰正常结局`；`K3 反控：旅行者按取消时，期限不许冒充用户` | 1 | true | KILLED |
| `K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE` | 1 枚：`K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源` | 1 | true | KILLED |
| `K0310_DERIVATION_PROBE_CONSTANT_TO_7S` | 0 枚：（无 —— 探针按预期绿） | 0 | true | HOLDING_AS_EXPECTED |

聚合：`arms_total=7`、`killed=6`、`survived=0`、`probes=1`、`every_arm_parsed_at_least_one_node=true`、`all_arms_restored_to_tested_tree_bytes=true`、`tree_unchanged_by_this_run=true`。逐臂 `anchor_hits` 与 `expected_anchor_hits` 都是 1（改错了地方就不算臂），每臂同一枚键的先决条件在本轮成立：`all_arms_carry_a_green_same_key_precondition=true`。`claimed_result` 是本车道观测，`derived_result` 全为 null —— 等级与派生归红队。

**五、我欠的账，写在这里不抹**

其一：头两轮臂收据里 **每一枚臂都被误判成 SURVIVED**，而同一些运行的 pytest 行数明明是 `1 failed`。原因在量具：解析节点行的正则少了 `re.M`，`^` 与 `$` 只对着整段捕获文本的两端，于是一枚节点都没匹配上，计数恒为 0。修法提交（只改驱动器，产品字节与断言一字未动）`30de4ebe409f49c5e25f4758cb2e5f4e90764a4f` 之前那一笔，本块全部数字出自修好之后的轮次：臂收据 `evidence/ord0288-keyless-deadline/ord0310-arms-receipt-r5.json`，blob `1c9a4599816afce169b69222cccb6587304b74fb`。一个从不命中的计数既不是绿也不是杀。

其二：`K0310_SENTENCE_PROMISES_REPLAY` 第一次是 SURVIVED —— 门禁只在折叠态读卡片，而我把禁句写进了「技术详情」展开之后；而且当时只要求句子里「提到一把键」，松散到能放过承诺补问的说法。补法是折叠态与展开态各读一遍、并把「不能靠同一把键补问」钉成逐字判据，改的是量具不是断言（门 `frontend/e2e/qoder-ord0310-keyless-write-deadline.spec.ts` blob `61fa23882dc0936ea29d08e12d15d1d936157049`）。收紧之后同一枚臂红。

其三（本代新增的自纠，原样命令与输出都在 `evidence/ord0288-keyless-deadline/ord0310-left-right-count-trap.out` blob `ee03cf3206ff6f8e0138050c10d2be8fe9e26d91`）：我给上一代写 `ref_tip_read` 那格时把 `git rev-parse <rev>:<path>` 的**回显**当成了 blob（该路径不存在时它原样打印参数），于是一格印出空 blob、另一格印出像 sha 其实不是的串；另一处是把 `git rev-list --left-right --count A B` 少了三点号来读分母，同一对操作数用正确形制 `A...B` 量出来是领先 `6` / 落后 `5`（号令者亲测同值），错误形制吐出的那个数根本不是分母，而我一度把它当「落后好几百」写进汇报。两处都改成**先校验 40 位十六进制再落字**，并把工具随件发布（`evidence/ord0288-keyless-deadline/ord0310-tool-make-receipt-r2.py`），这样别人复跑用的是被判的那份字节。

**判据与出处**：主收据 `evidence/ord0288-keyless-deadline/ord0310_keyless_deadline_receipt_r3.json`，blob `df1c18a4456314b633018e31da48ea3c4cf0dac6`（37,187 B），6 格自证；服务端读数 `evidence/ord0288-keyless-deadline/ord0310-backend-readings-r3.json` blob `89588274ba0180b51f3e26fb789f33ddbcd7a24f`；尺 Q38 r2（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）判这枚收据 ⇒ `Q38_GATE_GREEN`、hard `0`、soft `0`、exit `0`，输出 `evidence/ord0288-keyless-deadline/ord0310-q38r2-on-receipt-r3.json` blob `5c59548f0031d6fde4f7e18edd24c16d94a141bc`。本块自身的两把尺输出同目录（名字里带 `on-block` / `on-post`）。

**纪律**：`0 权威线写入`、`0 推他人 ref`（只推了自己命名的 `refs/heads/review/ord0310-keyless-deadline-d-on-2344145c`）、`demo/reset 0`、`_live`/`_preview` 库 0 读写、凭据 0 打印 （第二路读 ref 的 token 只进内存，`evidence/ord0288-keyless-deadline/ord0310-tip-read-r3.out` 里那一行写的是占位符）、`0 为了绿而改断言`（红都是收紧量具修掉的，见第五节）；交件走新路径 `evidence/ord0288-keyless-deadline/`，逐件独立 GET 回读，已发布路径 0 覆盖 0 改名。
