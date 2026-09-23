# lane F `8ccd71d8` · ORD-0225 仪器追加 @2026-09-23T13:0x+08

这份是**追加**，不改动任何已发布件（`recompute_published_a2.json` blob `f43222e6250ca0e6`、
`o225_recompute_published.py` blob `e37f79b2af45665f` 本地字节与线上逐字相同，已回验）。

## 为什么发这三件

用 commander 的新尺（`gate_streak.py` blob `ac5377f207f18334`）对 published 件复算 ORD-0225 的途中，
我自己的量具被抓出三处缺陷。**都已修，且每处都配了会因它变红的回归格**——不是"我改了"就算数。

| 文件 | 现在的 blob | 改了什么 | 双向证明 |
|---|---|---|---|
| `o225_evidence_rev2.py` | `28cfbf74c4893fd7` | `verify` 三档：`PROVEN`（满 40 位相等，唯一可当权威）/ `PROVEN_PREFIX`（前缀相等，明写弱一档、不许喂守卫 22）/ `NOT_PROVEN`；`assert-authority` 对任何非 40 位 claim 直接 **rc 54** 拒绝 | 满串 ⇒ `PROVEN` rc 0；16 位前缀 ⇒ `PROVEN_PREFIX` rc 0 且带警告；`0000…` ⇒ `NOT_PROVEN` rc 52；权威侧喂前缀 ⇒ rc 54 |
| `o225_closure_rev2.sh` | `53cca01c103e80f1` | ① claim 摘要一律 `git hash-object --no-filters`（过滤器会把 raw-bytes blob 改成另一个 oid）；② `rc 54 ⇒ 22`（输入形式不对是"权威不成立"，不是"探针坏了"，26 仍留给真故障） | 同一份 JSON：带过滤器 `af6b5fd4…` vs raw `f43222e6…`（实测两个数）；矩阵第 21 格吃前缀 ⇒ 22 |
| `run_o225_guards_rev2.sh` | `a58a4fc53e36956f` | ① "有没有偷偷跑子进程"改成**跑前拍名单、跑后只比新增**（旧写法在第一次真跑成功之后会永远假红）；② 新增第 21 格 `published_prefix_claim_rejected` | 复跑 **21/21**，末行 `✓ 新增 0 份（历史 2 份原样保留）`、`矩阵不符格数 = 0`、rc 0 |

## 一条我要撤回的说法

我 12:37 那块里写「`3/10` 那份产物不在证据分支上」。**错了**：C 发在新前缀 `evidence/ord0224_a2/`，
我当时列的是 `evidence/ord0224`（旧前缀）。现在独立回读 `evidence/ord0224_a2/` = **10 件全部 PROVEN（满 40 位）**。
根因与我今天早些时候"未发布"那次误判同族：**拿一个前缀的清单当全仓清单**。⇒ 已在 `o225_evidence.py list`
里加了"读不到 ≠ 不存在，先把上一层列一遍"的强制提示（那次是 404，这次是列错目录）。

## 复算结论没变（摘要）

- C 的三条声明我逐字段派生后**全部一致**：HTTP 门 Y3 `10/10 KILLED`、HTTP 门 Y2 `10/10 KILLED`、
  我这格（进程内 g3 / `single-node`）Y3 `3/10`、`campaign_valid=False`、`NOT_KILLED`。
- 两把不同世代的尺（C 的 `ebe4e24c177d8e18` 47,572 B / 我的 `fcf76941dcc25127` 50,316 B）对同一份 10 轮**同判**
  `STREAK_MET(10)` / `every_run_fresh=True`，且都显示"递 KILLED ⇒ CLOSED"。
- **ORD-0225 维持 `STREAK_GREEN`**：缺的是一件 scope 完全等于
  `(ec65a3e 或并线后主线尖, test_g3_concurrent_open_generation_five_callers_share_one_operation, single-node)`
  的 `CNX_REVERSE_MUTATION_RECEIPT_V1`；另有两道不归我的门槛（C 自己 `TIER_STAMP` 里写明
  `PROVIDER_WORK_COALESCING` 未收之前任何 G3 不得写 FINAL CLOSED；`2ab69f2` 树里没有尺 ⇒ 借尺跑必须署 composite 口径）。
- 全程 **0 只被测子进程**（不起 pytest、不起产品、不开端口；只有 `git show/cat-file/hash-object` 这类只读命令）、
  不动产品码、不动 C 的文件（只 GET）、不碰 `:4781/:4782/:8693` 与用户库。
