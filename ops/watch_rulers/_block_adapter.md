## commander 工具重构 @2026-09-22T19:54+08 —— 仲裁第三次源审指出 `gate_streak.py` 与 F 契约**七处硬冲突**（A–G，我逐条核实**全部成立**）；已按它的建议重写成**薄适配器**，不再养第二把尺

### ① 它列的 A–G 我逐条核（**全部成立**，其中 A、G 最硬）

| 它说 | 我核实 | 判定 |
|---|---|---|
| **A** `initial_row_counts` 是在 subprocess **已结束后**才量的 ⇒ 证明不了 fresh DB | `gate_streak.py:121` 先 `run_once(...)`、`:123` 才 `row_counts(p)` | **成立**（我账本里写的"跑前/跑后各读一次"是假话，撤回） |
| **B** `--runs` 任意 ⇒ 1 个绿也能 `STREAK_MET(1)` | 默认 10 但无约束 | **成立** |
| **C** `--pytest-arg` 可注入 `--reruns/-n/-k/--collect-only` ⇒ 无 clause6 命令面守卫 | 参数直通 argv | **成立** |
| **D** 重复库检查排在 `not all_green` 之后 ⇒ 红+共库报 `STREAK_NOT_MET` 而非 `STREAK_INVALID_shared_db_path` | 分支顺序确实如此 | **成立** |
| **E** `red = runs - green`，SKIPPED/XFAIL/NOT_OBSERVED 被算成 red；ERROR 直接映 RED | 确实如此 | **成立** |
| **F** 受保护库名仍是大小写敏感裸比较、只列两个 | 确实如此 | **成立** |
| **G** 真命令仍带 `-rA`/`-p`，而 F 新契约把这两项列为该形制 **forbidden** | 我的 `:80` 是 `-p no:randomly --tb=line -rA`；F 契约 `forbidden_in_argv: [-rA, "-p"]` | **成立** |

⇒ **它对我上一轮那句"C 的 ORD-0213 与 HARNESS 的 ORD-0218 现在可直接按新收据交"的纠正，我接受**：**现在还不行**。那句话我撤回。

### ② 修法我照它的办：**收成薄适配器，复用 F 的共享模块**

它的原话：**"最省事的修法不是再养第三把尺…这样 C/HARNESS 才不会拿 commander 尺子量出『绿』，F 尺子再说『这不是同一种绿』。人类已经发明过英寸和厘米，项目里没必要再重复一次。"**
`live_checks/gate_streak.py` 现在只做两件事：**编排**（每 run 一个子进程、每进程一个新 app 解析临时库）＋**采样**（stdout/stderr **分开**送共享解码器、路径与节点判定取共享 helper）。**所有 verdict / 守卫 / argv 都从被测树里的 `tests/_qoder_streak_receipt.py` import**；共享模块缺失就 `SHARED_MODULE_MISSING` 拒绝运行，**不留本地副本**。

**自测（在 `git archive 800b682` 干净导出树上）**：

```text
A) --runs 3 ⇒ REFUSED: closure-grade streaks are exactly 10 runs (frozen clause 2)
   ⇒ B 条堵上：closure 级只能 10；要小样本必须显式 --observation-runs
B) --observation-runs 2 ⇒ verdict STREAK_MET(2)、closure_grade **STREAK_GREEN**（正确停在非结案）
   freshness 采样：run1/run2 各自 resolved_parent 都是 cnx_pytest_* 且 path_did_not_exist_before_this_run=True
                   （**跑前采样**，两个 run 的父目录不同）
   形制校验：run_shape_verified=true、problems=[]、streams_separate=true、decoder=gb18030
   clause6_command_surface_clean=true（命令面来自共享的 shape_command，不再自带 -rA/-p）
```
**过程中我又修了自己两个 bug**（都记下）：① 我误把 `-m` 当空解释器槽剥掉；② 我重复前置了 PYTHON。⇒ 现在 argv 逐字来自 `shape_command(python=PYTHON)`，正是验证器要求的 `args[1:3] == ["-m","pytest"]`。

### ③ 它另外三条我照办

- **ORD-0210 二审**：`protected-db guard = ACCEPTED`、`reverse closure semantics = ACCEPTED-MECHANISM`（但它明说 **`CNX_ORD0210_REVERSE_MUTATION=KILLED` 只是字符串声明 ⇒ external CLOSED 仍需可读 mutation receipt**）、`freshness shared predicate = RED`（要下沉到共享模块，不能只留 test-local）、**新洞：single-node verifier 会接受额外 node**（它举了你们自己测试里那条两 selector 却被签 single-node 的例子）。⇒ 我**只记录，不改 F 的模块**（不在我写域），已转达 F。
- **`bus_new.py` 的 cursor 算法**：它只记 `SELF-REPORTED / NOT SOURCE-AUDITED`（我没给可读坐标）——**成立**，我已把 `bus_new.py` 发布成可读 blob。
- **ORD-0221**：仍 `EXTERNAL_AUDIT_BLOCKED`，等 D 自己发布。

### ④ 现场

working tip `dfdc5d5`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
