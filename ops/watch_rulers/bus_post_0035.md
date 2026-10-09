仲裁: SESSION=494abfd7（Commander）— 你两条新 policy 我拉回并落单；另外**我把自己的一个重复记账错当场回滚了**，顺带回你 ORD-0156 那条待裁

已读 **5763697604**。三件事，都有可复放的读数。

## ① 我自己的错：00:0x 我把 21:0x 已经写过的一块又写了一遍

`git` 无关，是**账本**：21:0x 我已经写过"R10 身份归属复核 + ORD-0155/0156/0157/0158/0160 五张单"，
00:0x 我又写了一遍 ⇒ 账本里一度出现两份 `ORD-0157/0158/0155/0160` 与两份同名块头。

- **我怎么发现的**：不是回忆，是写入命令自己的输出——`- id: ORD-0157` 的计数写前 1、写后 **2**；
- **怎么回滚的**：按我那两个 block 文件的**字节**精确摘除，每个 payload 必须命中**恰好 1 次**，否则拒绝写（`live_checks/rollback_dup_2112.py`）；
- **回滚后实测**：账本 135 个 `ORD-####` 条目 **0 个重复**，我那两个块计数 0，行尾仍 LF，`ORDERS` 标题未被改动；字符 1,185,171 → 1,173,082；
- **为什么不退回写前快照**：我诊断期间车道还在追加（ORD-0184 已落），逐字节还原会**吃掉他们的块**——所以只做精确摘除 + 后置条件断言。

教训我写进自己的规矩了：**动手前先量一遍"这东西是不是已经做过了"**。我犯的正是我今晚纠正别人的那类错——
拿"我以为还没做"当事实，没先打印现场的计数。这条和你 ② 的 negative-claim inventory 是同一个病。

## ② 你两条新 policy 已拉回落单（REST contents，未对 github.com 用 git 网络）

- **`docs/pending_destination_identity_policy.md` @ `e4b7faa3`（+103）**：**我 ③ 的挂起项被采纳**——
  `canonical_destination_id=null` + `pending_destination_label` 保原文 + `destination_pending_key` 只作相关/幂等键；
  两条反向突变也进了门（把 `pending:<raw>` 写回 canonical 必须红；拿 pending key 当 catalog join key 必须红）。
  ⇒ **ORD-0157 ④ 挂起解除**，C 按此实现；已落库的 `pending:` 行按 R10 就地回填、**不许删**。
- 同文件里 **ORD-0167 小县城端到端闭环**的 11 项收据我已抄进 0157 的交付口径；
  冻结句我照录：**Resolve a real place, preserve the user's raw request, and carry only real canonical identity into planning.**
- **`docs/test_execution_truth_policy.md` @ `65f1934f`（+38）**：这条正是我今晚第四次同族错换来的——
  我拿**猜的**字段名 `data-attribution-evidence-kind` 去问，实际叫 `data-evidence-kind`，四个都读回空，差一步就写"缺四项"。
  我已把"写'没有 X'之前先打印实际读到的键名清单"并入 ORD-0166/0168 的报数口径。

## ③ 请你拍 ORD-0156 那条（F 交的门里唯一待裁）

F 的 12 道门 6 红 6 绿、三条突变全杀，但问了一句：**§3 的"不许新增 `OSM_TAG_INFERRED`"枚举禁令，
要不要连带"假来源即不合格证据"的语义**——即：映射层若把 `source_kind` 填成 `REMOTE_PROVIDER` 而事实来自冻结快照，
是**枚举违规**还是**证据不合格**（后者该在 hard-feasibility 里直接判红，而不是只报命名错）。
我的建议：**两者都要，但分开断言**——枚举门管命名、证据门管可采性，这样"标签对了但来源是编的"不会因为名字合法而蒙过去。

## ④ 两条我亲手量的现场状态（不是转述）

- 手机预览链：`:4782` → **200**、隧道 → **401**（需鉴权）、`POST /api/v1/demo/reset` → **403 `PREVIEW_GUARDED`**（我带正确凭据实测，护栏不拆）；
  `GET /api/v1/health` → `{"status":"ok","database":"ok","ai":"enabled"}`；后端 tip 未动、用户数据未动。
- 权威树 tip 仍 **`d26933c`**；`e9efec6` 之后 5 笔（`2d3b3fb`/`23bdf9f`/`4176e7b`/`b2becb5`/`d26933c`）我逐笔读过 numstat。
- 我 21:0x 那条 R10 自撤（**identity 只有一个主人**、provider 调用实测 **0**）已发在 `5761107840`，请以那条为准，
  不要再引用我 20:3x 的"两处各自算 identity"——那句是我量具不足时的错话。

竭尽所能的替qoder铺路
