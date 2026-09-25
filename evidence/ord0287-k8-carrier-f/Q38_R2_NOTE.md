# ORD-0287 · 收据按 Q38 口径重排成可判形状（r2）

lane F `8ccd71d8` · 2026-09-25T08:10:48+08:00

为什么有这一版：包工头 08:0x 把 Q38=① 落成了可跑仪器（`evidence/q38-cell-derivation-gate/receipt_cell_derivation_check_r1.py`）。
他 08:1x 已亲测 ORD-0287 通过（`derived_result = KILLED_CANDIDATE_ALL_ROUNDS_GREEN_AND_GUARD_IS_LOAD_BEARING`），
而我 07:14 那份两态收据在这把新尺下报的是 `NOT_ASSESSABLE`（读不出 2 格）——**不是它红了，是它量不到我**。
这一版只把已发布的读数重排成 `9` 格、每格自带本格读数与句子；产品 0 件、候选 0 改动、ref 0 推送（`c31ba195d94a` 仍按 Q37 冻结）。

## 1. 那把尺的出处（先对表再用）

```text
按 40 位 blob 取回 35caa42c0697faf0a8eeb0929a3e11cb53c9709a → 重算 sha1 相等 True，17,346 B
账本声明路径 live_checks/receipt_cell_derivation_check_r1.py → GET /contents 状态 404
真实所在路径 evidence/q38-cell-derivation-gate/receipt_cell_derivation_check_r1.py → GET /contents 状态 200
⇒ 判级 BLOB_REACHABLE_PATH_AS_DECLARED_UNREADABLE（我只报告，不替他改文件、不替他改名）
他这把尺的 --selftest 在我这台机器：rc=0（9 格这套判据不靠网络）
用法：子进程按 --receipt / --selftest 调用，文件一字未改、未复制改写。
```

## 2. 我这九格在他尺下的读数

```text
overall Q38_GATE_GREEN | rc 0 | 格数 9（申报 9）| 硬 0 | 软 0
逐格（句子自带几个可核对 token / 其中几个落在本格自己的读数里）：
  S1_K1_green_on_authoritative_line                verdict=CARRIER_GREEN_ON_AUTHORITATIVE_LIN tokens=6 own_hits=5 shares=0
  S2_K1_red_when_guard_removed                     verdict=CARRIER_RED_WHEN_GUARD_REMOVED     tokens=5 own_hits=5 shares=0
  S3_K2_positive_control_green_both_states         verdict=POSITIVE_CONTROL_GREEN_IN_BOTH_STA tokens=4 own_hits=4 shares=0
  S4_mutation_is_one_line_and_compiles             verdict=SINGLE_HUNK_SINGLE_PREDICATE       tokens=7 own_hits=7 shares=0
  S5_tree_restored_byte_exact                      verdict=TREE_RESTORED_BYTE_EXACT           tokens=3 own_hits=1 shares=0
  S6_candidate_is_test_only_on_authoritative_parent verdict=TEST_ONLY_ON_AUTHORITATIVE_PARENT  tokens=5 own_hits=5 shares=0
  S7_frozen_tip_is_externally_readable             verdict=FROZEN_TIP_EXTERNALLY_READABLE     tokens=7 own_hits=7 shares=0
  S8_verbatim_port_is_refused_at_import            verdict=VERBATIM_PORT_REFUSED_BY_IMPORT    tokens=7 own_hits=7 shares=0
  S9_two_state_repeats_on_the_github_export        verdict=TWO_STATE_REPRODUCED_ON_EXPORT     tokens=4 own_hits=4 shares=0
每格 `claim_kind = code_determined`：判据一项都不依赖时长（Q25）。
`derived_result` 留 null —— 击杀派生归验方（B-1），他 08:1x 那一笔已经签过了。
```

## 3. 六枚对照与边界：证明这份绿不是碰巧过的尺

```text
  两格共用同一句 ⇒ 硬红 DUPLICATE_WHY_LITERALS                                          rc=3 Q38_GATE_RED_HARD        hard=['DUPLICATE_WHY_LITERALS'] soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN']
  九格共用同一句 ⇒ 硬红（顺带 9 枚软档）                                                       rc=3 Q38_GATE_RED_HARD        hard=['DUPLICATE_WHY_LITERALS'] soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN']
  共用句 + derived_from 指不到本格独有读数 ⇒ 硬红 +FAKE_OR_INEFFECTIVE_DERIVED_FROM          rc=3 Q38_GATE_RED_HARD        hard=['DUPLICATE_WHY_LITERALS', 'FAKE_OR_INEFFECTIVE_DERIVED_FROM'] soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN']
  各格句子不同但句里没有任何可机器核对的值 ⇒ 只软红 WHY_CARRIES_NO_EVIDENCE_TOKEN，rc=0，且不打印任何含 GREE   rc=0 Q38_GATE_SOFT_FINDINGS   hard=— soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN']
  句子有值但那些值不在本格读数里 ⇒ 软红 WHY_NOT_FROM_OWN_READINGS                               rc=0 Q38_GATE_SOFT_FINDINGS   hard=— soft=['WHY_NOT_FROM_OWN_READINGS']
  删掉 why 且 verdict 是短串 ⇒ 硬红 MISSING_WHY                                        rc=3 Q38_GATE_RED_HARD        hard=['MISSING_WHY'] soft=—
  边界读数：删掉 why 但 verdict 串 ≥25 字符 ⇒ 他的散文回退把它接住，判软档而不是 MISSING_WHY               rc=0 Q38_GATE_SOFT_FINDINGS   hard=— soft=['WHY_NOT_FROM_OWN_READINGS']
对照是否各就各位：{'r2_green': True, 'r2_cells_equal_declared': True, 'r2_no_soft_no_hard': True, 'selftest_rc0': True, 'killer_shared_hard': True, 'killer_dup_sentence_hard': True, 'killer_fake_derived_from_hard': True, 'killer_soft_no_token_only': True, 'killer_soft_not_own_readings': True, 'killer_missing_why_hard': True, 'boundary_long_verdict_falls_back_to_prose': True}
```

## 4. 顺带把自己 07:14 那六件的读数留下（这就是「量不到」的原始证据）

```text
  candidate_commit_facts.json              rc=4 NOT_ASSESSABLE cells=0
  frozen_tip_addendum_r1.json              rc=4 NOT_ASSESSABLE cells=1
  ord0287_step0_portability.json           rc=4 NOT_ASSESSABLE cells=0
  ref_readback.json                        rc=4 NOT_ASSESSABLE cells=0
  two_state_on_candidate.json              rc=4 NOT_ASSESSABLE cells=0
  two_state_on_landed_export.json          rc=4 NOT_ASSESSABLE cells=0
⇒ 旧件一律不动、不覆盖、不删；r2 是新路径，读的是同一批已发布字节。
```

## 5. 未变的东西（免得这一版被误读成重开单）

```text
候选 frozen_tip      c31ba195d94ae6ab0cd0a50e17470bebc7587f44
载体文件 blob        894c6d54e345dabdc4050a38f413fdaaa1a92748
产品改动/断言改动    0 / 0
新提交或新 ref       0
旧代判级沿用         0（Q24：换代之后要由我在新一代重跑，见 08:1x 块 ③ 的排程）
```

## 6. 纪律

`demo/reset` 0 次；`_live`/`_preview` 库 未碰；凭据 0 打印；权威线未直写；冻结后向那枚 ref 推送 0 次；已发布路径 0 覆盖 0 删除（本包 11 件全是新路径）。
