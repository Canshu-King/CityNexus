## commander 坐标核验 @2026-09-22T18:50+08 —— F 的 ORD-0210 机制收口：三笔提交/范围/门文件我都核过，**干净导出树上 14 passed + 1 skipped / exit 0**；深审按新分工转 GPT

### ① 我只做"便宜的现场读数"，逐条如下（不引用 F 的自报）

```text
提交       b05a3b2 18:22 / 491d8e7 18:28 / 9514eb7 18:34（三笔，git log 亲读）
范围       git diff --name-only 50b35e0 9514eb7 ⇒ 只有三个文件：
             backend/tests/_qoder_streak_receipt.py
             backend/tests/test_qoder_db_isolation_same_verdict.py
             contracts/gate-acceptance-streak.yaml
           grep 排除 backend/tests/ 与 contracts/ 后 = 0 行 ⇒ "产品码 0 改动"这条**成立**
门文件     9514eb7:backend/tests/test_qoder_db_isolation_same_verdict.py 存在，826 行
收集       本门 --collect-only = 15 tests（与它自报同）
实跑       git archive 9514eb7 干净导出树 → 默认（机制）模式：exit 0，14 passed / 1 skipped in 4.60s
           其中 [round 1/2] exit=1 outcome=RED db=…cnx_pytest_ey_c4o17\suite.db | 行数 2 —— 靶子红是**被设计成红的**，
           而机制门自己绿：这正是它说的"机制模式判量具形状，靶子红不算本门红"那条分工。
```

⇒ **机制层我按"门能跑、能给出判定、没碰产品码"记账**；它把第 9/10 条接进门里（`_qoder_streak_receipt.py::classify_target_node`、`contracts/gate-acceptance-streak.yaml` 十条原文）这两件我**没有逐行审**——那是深度审计，按用户 17:4x 的新分工转 GPT。

### ② F 顺手给全体改的一句口径，我采纳（这是第 10 条的字面后果，不是它的发明）

**账本里 `g3 = FLIP_WITHOUT_SHARED_STATE(single-node)` 这类定性，从今天起必须带 SHA。**
它列的三把读数（**各自合法、互不冲突**，因为是三个不同的 (SHA, node, shape) 三元组）：

| 谁 | 读数 | SHA |
|---|---|---|
| HARNESS | 1 绿 / 9 红 | `56d20ec` |
| commander（我） | 2 绿 / 12 红 | `0a4cb23` |
| F（门自己的验收收据） | 0 绿 / 10 红 | `491d8e7`（base `50b35e0`） |

**不带 SHA 引用定性 = 旧事重演**（"谁拿 7/10 说它在翻、谁拿 0/10 说它恒红，两边都没错"）。
它另外加了一个**只记录、不参与判定**的观测量 `foreign_temp_dirs_during_this_run`（本轮期间 `%TEMP%` 里别人新建的 `cnx_pytest_*` 目录数，它这次 = 0）——**这条我认可它的克制**：不拿"当时还有谁在跑"当成因，因为第 10 条的范围里确实没有这一格。

### ③ 它交 C 的那张 10 进程收据，我按"给 C 的起点"记账，不签 CLOSED

```text
SHA 491d8e7 | 形制 single-node | 10 轮：绿 0 / 红 10 / 未观测 0
重复解析路径 = []      缺路径的 run = []
逐 run resolved= 路径 10 个各不相同（cnx_pytest_3v9np7cw / 5n02b1tn / 5z28q__3 / phuv2v8f / 566cgywc /
                                     u4tetell / 1u_qmrlg / w00vzuyf / 18rybkj2 / 621orwfl）
跑前 = absent:True（fresh 是量出来的）  跑后 table_count 55
门要 1 枚 operation，实测逐 run = 4 3 2 5 4 2 4 3 4 5  ⇒ 最少的一次也造了 2 枚
结论 STREAK_NOT_MET(0/10_green)，可结案 = False；目标节点定性 STABLE_RED(single-node) @ 491d8e7
```

**这张不签 CLOSED、也不签"根因清楚"**——F 自己就这么写的，我照此。根因仍在 C 的 ORD-0213（C 16:4x 说卡在仲裁那句"新鲜度窗口内复用终态结果 vs 改写 g3 的并发定义域"，我还没看到仲裁对此的裁定）。

### ④ 现场

working tip `25165d9`（18:40，`docs(review): ORD-0216 ④ ledger block and its bounded runtime self-test amendment`）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动。
