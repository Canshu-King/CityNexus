# ORD-0272 / K8 跨进程定向观测（HJ-P3 那一腿）· 结论：**观测到了翻转**，不是 `UNOBSERVED_CROSS_PROCESS`

- run id `K8XP-2505` · 车道 `HJ-P3 / aad2d1f2` · 本机钟 2026-09-25T05:03:29+0800
- 载体三元组（防"改了别的行也算拆"）：sha `7c806fab58e872060cb5811ff96c770b40dad165` · nodeid `tests/test_qoder_ord0272_continuation.py::test_G9_a_filled_receipt_is_never_rewritten_by_a_later_answer` · shape 拆掉 `app/main.py:4792` 的 `IdempotencyKey.response_json.is_(None)`
- 两代身份（我重算的 git blob，不是转述）：候选 `main.py` = `ad13f4395e3405ce722ae8660836f3c2aaa29df2`；我的私有 mutant = `f7263d6b9532e6c9be4f13f93a31b0f042dd0e95`；候选 tree = `04a8b56e494f53a20debfa139e8ab37c25c63352`（= F 在总线与账本引的那枚，相等=True）
- 边界：产品权威线一个字没动（mutant 是我 `D:/moodle/_hjp3_k8_0925/snap/…__mutant` 里的私有副本）；每个 arm 都用 `ensure_schema()` 新建一次性库、跑完即删；`demo/reset` 0 次；用户库 0 读写；凭据 0 打印。

## ① 缝上的跨进程（这才叫"两个进程共一把库"）

两个**独立 OS 进程**（pid 不同，谁都不是谁的线程）对同一把键 `plans.generate:cont:k8-xp-fixed-mission` 动手：A 先 claim+回填自己的答案，B 事后拿同一把键再回填。

| 树 | A 的 rowcount | B 的 rowcount | A 的字节还在吗 | 两 A/B 的 pid |
|---|---|---|---|---|
| 候选（守卫在位） | 1 | **0** | **True**（库里仍是 `{"answer": "A"}`） | 41920 / 45800 |
| mutant（拆掉那一行） | 1 | **1** | **False**（库里变成 `{"answer": "B"}`） | 688 / 35508 |

- 派生：`guard_present_blocks_rewrite=True`、`guard_removed_lets_rewrite=True` ⇒ **`OBSERVED_CROSS_PROCESS_FLIP`**。
- 一句人话：守卫在位时，别人已经答过的回执**一个字节都不动**，第二发拿到 `rowcount=0`（这就是它存在的理由）；把那半个条件拆掉，第二发就把前一个人的答案**顶掉**，而后到那一发读起来像"这批是我答的"——这正是候选文件里那段 docstring 预言的形状，我这一轮是**量出来**的，不是读出来的。

## ② HTTP 面那一臂（也照号令写清"能不能测到"）

两枚 uvicorn（pid 32756 / 42860，同一把一次性库）跑客户端真能发的那一发：同一把 `Idempotency-Key` 先由进程 1 答，再由进程 2 重发。读数：首发 HTTP `422`、重发 HTTP `422`、正文等值=False；重发之后库里回执行**没有变化**：候选 `unchanged`、mutant `unchanged`。⇒ 两棵树**没有任何一项读数不同** ⇒ `HTTP_FACE_CANNOT_REACH_K8`。
- 这条不是"我的仪器不行"的遮羞话，是一条**射程声明**：Phase A 的唯一索引会把抢同一把键的第二发挡在 409/重放之外，所以"覆盖"那一幕在 HTTP 面上根本不发生。K8 的可观测性在**缝**上（① 已翻），不在用户面上。
- 顺带一格与我 0279-X 呼应的读数：这一臂的请求体只带 `candidate_count`（没带 `mission_id`），所以库里只有 `plans.generate:<header>` 那一行、没有 `cont:` 那行——手机这一路也是同一形状。

## ③ F 那枚载体格我自己跑一遍（第二观察者，不引用它的 campaign 文件）

| 树 | rc | 末行 |
|---|---|---|
| 候选 `ad13f4395` | 0 | 1 passed, 2 warnings in 1.44s |
| mutant `f7263d6b9` | 1 | 1 failed, 2 warnings in 1.59s |

- 派生：`CELL_FLIPS_TOO`（候选绿、拆掉守卫之后红，红的那条 nodeid 逐字就是 `tests/test_qoder_ord0272_continuation.py::test_G9_a_filled_receipt_is_never_rewritten_by_a_later_answer`）。cwd 两侧都是 `<tree>/backend`，与被主张的 nodeid 根一致；我这边**没有**再引 F 的收据文件当证据。

## ④ 我不签的东西

- `derived_result` 归 @红队：我这一腿只交现场观测与其派生 verdict 名，不判 KILLED、不自宣闭单（B-1）。
- 时长一律只当读数（本收据里的秒数来自 pytest 自己的行，判据一项都不依赖它）。
- 未测：真机面上"用户能不能感到覆盖"这层——② 已经把它判成 HTTP 面不可达，所以我不假装它有读数。

## ⑤ 已发布件（blob 从分支 tree 读回，3 件）

分支 `commander/control` 读回 commit 尖 `ab8435427bd5ea049fc400d36829d4950ba90c47` · 其 tree `4420d43ad6270eac12eaaa409511b4330aff5081`：

| 文件 | 大小（读回） | blob（40 位，读回） |
|---|---|---|
| `K8_XP_readings.json` | 6,282 B | `fbb154cf9ce598ad1d3a4241b0f2b96181f0037b` |
| `k8_setup.py` | 5,026 B | `efb61af8710c95d7a594e08094317552199dba73` |
| `k8_xp_rig.py` | 14,545 B | `64faf335d5ef45f538decc5d0063f913544927ee` |

外部可读探针：`GET /git/blobs/K8_XP_readings.json` 重算 sha1 与 tree 上 blob id 相等 = True。

复跑：`python k8_setup.py export` → `python k8_setup.py mutant` → `python k8_xp_rig.py`。
