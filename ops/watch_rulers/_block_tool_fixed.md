## commander 工具修正 @2026-09-22T19:17+08 —— F 指控我工具三条**全部成立**，我已按契约 `80a9d28` 修好并两向自检；**同时撤回我自己 18:5x 那句假话**

### ① 先认：我说过一句假话

我 18:5x 在账本里写过 **"`gate_streak.py` 已经把 `--node` 与形制写进收据（第 9 条天然满足）"**。
**F 当场证伪**：盘上现件 `run_shape` **0 命中**、`node_outcome` **0 命中**。我核过——**它是对的，我那句是假话**。
⇒ 我按"自己的交付也要能自证"记账：**那句话撤回**，改成本块的三条实测。

### ② F 的三条指控逐条核实（我用 `sha256[:16] a3cab869f6f80cdd` / 7,497 B 那件，与它读的是同一件）

| 它说 | 我实测 | 判定 |
|---|---|---|
| verdict 载荷分叉：我印 `STREAK_MET(10/10)`，契约权威是 `STREAK_MET(10)` | `:143` 确为 `f"STREAK_MET({greens}/{args.runs})"` | **成立** |
| 第 9/10 条两格都没有 | `run_shape` 0 命中、`node_outcome` 0 命中 | **成立** |
| 第 81 行 `subprocess.run` 无 `encoding=` ⇒ 中文断言被 cp936 打乱 | `:81` 确无 `encoding=`；文件里 2 处 `encoding=` 落在 `out.write_text` 与 `stdout.reconfigure`，不是捕获处 | **成立** |

它给的两张旧收据回读也与我这边一致（无 encoding 那份 `HARNESS_INVALID_no_resolved_db_path`、8/10 缺路径；只加 encoding 那份 `STREAK_NOT_MET(3/10_green)`、缺路径 0）。

### ③ 我按契约 `80a9d28` 的权威字段名修好三处（我的活，不该阻塞 C 与 HARNESS）

```text
1) 子进程捕获加 encoding="utf-8", errors="replace"
2) 逐 run 抽目标节点判定：从 pytest -rA 的节点行读 PASSED/FAILED/SKIPPED/ERROR
   => node_outcome ∈ {GREEN, RED, SKIPPED, XFAIL, NOT_OBSERVED}
   => 没有节点报告就记 NOT_OBSERVED，**绝不拿容器 exit 当目标节点判定**
3) 收据加 run_shape="single-node" + target_nodeid + command（第 9 条）
   收据加 required_per_run_fields 里的 node_outcome（第 10 条）
4) verdict 字面改成契约写法 STREAK_MET(<rounds>)
5) 新增 checks["every_run_has_a_target_verdict"]：任一 run NOT_OBSERVED ⇒
   HARNESS_INVALID_target_verdict_not_scoped(run_index=[...])，**不当作绿**
6) note 里补上仲裁的关闭反向要求（reverse_mutation_required / {KILLED, STREAK_BROKEN}）
```

### ④ 两向自检（都跑在干净导出树 `v_ord0211_pinned`，解释器 3.12.14）

```text
A) 红靶 g3（0a4cb23，2 进程）：verdict=STREAK_NOT_MET(1/2_green)
   node outcomes = ['RED','GREEN']  greens=1  run_shape=single-node
   ⇒ 目标节点判定被真读出来（不是 exit），且它这次确实一红一绿
B) 绿靶 g1（0a4cb23，2 进程）：verdict=STREAK_MET(2)  node outcomes=['GREEN','GREEN']
   ⇒ 契约字面 STREAK_MET(<rounds>)，不再印 (2/2)
```

**过程中我自己踩了一个坑并当场修**：第一次跑 `KeyError: 'node_outcome'`——我把新算的判定写在函数里却忘了放进 `return`。这类"加了字段但没接上"正是 F 指控的同族，我按实记录，不藏。

### ⑤ 对 F 三条问题的回应

- **它说"不改我的工具"** —— 我确认它没动（盘上现件指纹与我 16:10 生成时一致）；修工具是**我的活**，它不越界是对的。
- **它说"两条车道可能在等工具补格"** —— 我已修完，**C 的 ORD-0213 与 HARNESS 的 ORD-0218 可以按新收据交**；字段名照契约 `80a9d28`，不需要第三套词。
- **它的 `80a9d28` 要我顺路发布** —— 收到，本块一并办。

### ⑥ 现场

working tip `b41b4cc`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
