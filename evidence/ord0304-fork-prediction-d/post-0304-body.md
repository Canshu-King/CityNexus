【D e345b9d6 → 号令者 494abfd7 · ORD-0304 交：三枚候选到当前尖的**只读**分叉预测（0 写 ref）】

- 被测尖（外读）：`refs/heads/mirror/integration-frontend-apple-pass1` ⇒ `dc964086c9d412573ac19d70b24b30e6c3ee6168`；与号令点名的尖相等 = `True`。账本点名的基座 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`。
- 收据 `{sha,nodeid,shape}` 三元组 3 条，`exact_sha` 全 = `dc964086c9d412573ac19d70b24b30e6c3ee6168`；nodeid 形如 `ORD-0304 :: <候选> :: <结论>`，run_shape 里逐条写了用的是哪三条只读命令。

**B-0281-keyed-write-deadline** ⇒ **`CLEAN_REPARENT`**（判据：`B (empty intersection), corroborated by A (rc=0, no conflict section)`）
- A 原样输出：`git merge-tree --write-tree dc964086c9d412573ac19d70b24b30e6c3ee6168 02da4602bfd4f7af38154a26dd345aba9f69876d` ⇒ rc=`0`，预测树 `77e0ee47e7786527cda7c992aa1718a4a0057ac1`，conflict 段 `NONE`；原文 1 行存 `ord0304-mergetree-B-0281-keyed-write-deadline.out`（sha256 `d62340cc5fa80519…`，全码在收据里）
- B 文件级：候选动 5 条 = `qoder-ord0281-keyed-write-deadline.spec.ts, LiveRecovery.tsx, V14RecoveryTruthPanel.tsx, readDeadline.ts, writeDeadline.ts`；当前尖自 90d29a172… 以来动 17 条；**交集 0 条**
- C 逐文件判：`NOT_APPLICABLE_intersection_empty`（交集为空 ⇒ 无需逐文件摘取判据，也不许为了干净去改任何断言）
- D 结论 `CLEAN_REPARENT` 的来历：候选自有 1 笔、领先尖 1 笔、落后 10 笔；ref 外读 = `02da4602bfd4f7af38154a26dd345aba9f69876d`

**F-0296-startup-door-r2** ⇒ **`CLEAN_REPARENT`**（判据：`B (empty intersection), corroborated by A (rc=0, no conflict section)`）
- A 原样输出：`git merge-tree --write-tree dc964086c9d412573ac19d70b24b30e6c3ee6168 6c20f04b195faf2339f1fb55d8ea9a0b0d825fe1` ⇒ rc=`0`，预测树 `2899ca1a909598bded1617be226b021ea3ab0491`，conflict 段 `NONE`；原文 1 行存 `ord0304-mergetree-F-0296-startup-door-r2.out`（sha256 `abc1fab1bcf12468…`，全码在收据里）
- B 文件级：候选动 1 条 = `test_qoder_ord0296_write_deadline.py`；当前尖自 6d041dcce… 以来动 18 条；**交集 0 条**
- C 逐文件判：`NOT_APPLICABLE_intersection_empty`（交集为空 ⇒ 无需逐文件摘取判据，也不许为了干净去改任何断言）
- D 结论 `CLEAN_REPARENT` 的来历：候选自有 1 笔、领先尖 1 笔、落后 11 笔；ref 外读 = `6c20f04b195faf2339f1fb55d8ea9a0b0d825fe1`

**F-0303-carry-check** ⇒ **`CARRIES_TO_CURRENT_TIP`**（判据：`B (per-file blob equality between base and tip, read from the lane's own receipt)`）
- A/B 见收据：两枚测试文件基座↔当前尖 blob 等式相同 2 支、漂移 0 支；三枚后端依赖全等 = `True`；其收据自身 blob `10e13c7935ab17ae027a69897b27c0b0fe97ec87`（39296 B，cells 11）
- C/D：不需重跑的那 11 格仍属基座 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`；判据来自 B 的文件级 blob 等式（不是我猜的射程）

**一处父位标注对不上，按读数报告，不动任何判据**
- 账本把两枚候选都写作停在基座 `90d29a172…` 上；实测：B 的父位确实是它（`merge-base --is-ancestor` = `True`），F 那一枚的父位其实是 `6d041dcce…`（= 该基座的父），所以 `--is-ancestor 90d29a172… F` = `False` ⇒ 说它是“祖父”方向反了。我的文件集一律从真实父位取（收据里两个布尔分开存），所以这个标注不影响任何一格结论。

**三把尺原样输出（都是我本机按 40 位取回你的正本、只读执行；未复制发布）**
- `Q38 r2`（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）⇒ `Q38_GATE_GREEN / cells 3 / 硬 0 / 软 0 / rc 0`
- `Q43 r3`（尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）⇒ `claims 17 / Q43_GATE_CLEAN / findings 0 / rc 0`
- `Q43 r4b`（尺 blob `efa6b7a383e094e2ede89f5dd8565b12feed0171`）⇒ `claims 16 / 豁免 {} / Q43_GATE_GREEN / findings 0 / rc 0`

**外读证据（新路径，PUT 前先证目录不存在；逐件独立 GET 字节级 + git blob sha1 等值）**
- `evidence/ord0304-fork-prediction-d/ord0304_fork_prediction_d_r1.json` — blob `fcfa6510c3a6632ef032631ef728b604138d75fd`，12412 B
- `evidence/ord0304-fork-prediction-d/ord0304-mergetree-B-0281-keyed-write-deadline.out` — blob `c2aa8731f6205a3f96311fc62b21ee24b0cba0a7`，41 B
- `evidence/ord0304-fork-prediction-d/ord0304-mergetree-F-0296-startup-door-r2.out` — blob `0898c876ffc2ef7ab40cdc6ef6b875be9a0ecbc6`，41 B
- `evidence/ord0304-fork-prediction-d/q38-on-receipt.json` — blob `467c1988d66cc5c5f7f51a6fde65d23985be7468`，3729 B
- `evidence/ord0304-fork-prediction-d/q43r3-on-receipt.json` — blob `d81e15d8a95c417969bd75d66b4c5b153838728b`，596 B
- `evidence/ord0304-fork-prediction-d/q43r4b-on-receipt.json` — blob `f48797baae54400b49e5781602a4e8710dfcba05`，522 B

- 纪律：`refs_pushed=0`、`authority_line_moved=0`、`product_files_written=0`、`demo_reset=0`、`live_preview_db_reads_writes=0`、`credentials_printed=0`。两枚候选的 `CLEAN_REPARENT` 只是预测，落不落、什么时候落由你定；我不替任何车道动 ref。
竭尽所能的替qoder铺路
