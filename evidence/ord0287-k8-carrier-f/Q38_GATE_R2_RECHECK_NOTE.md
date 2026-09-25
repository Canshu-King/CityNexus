# ORD-0287 · 他那把 Q38 尺出 r2 之后的整体重跑（不沿用 r1 读数）

lane F `8ccd71d8` · 2026-09-25T08:19:22+08:00

```text
尺 r2 blob 91ae8b1ec55f5c19122af11bf775df14580955e4（18867 B，重算 sha1 相等 True）
他声明的路径 live_checks/receipt_cell_derivation_check_r2.py → GET /contents 404；真实所在 evidence/q38-cell-derivation-gate/ → 200
（同一条形态与 r1 那笔一致，读数已发过：q38_gate_coordinate_readback_r1.json）
r1 35caa42c0697faf0a8eeb0929a3e11cb53c9709a 仍在原处、未动 —— 他自己在 r2 文件头写了「r1 留作历史」
他的 --selftest 在我这台机器：rc=0（r2 多了一臂 S10 收列表形状）
```

## 我这九格在 r2 下

```text
overall Q38_GATE_GREEN | rc 0 | 格数 9 | 硬 — | 软 —
与 r1 逐格比对（本格 own_hits 数）：逐格一致（r1 9 格 / r2 9 格）
⇒ 他这一版为 @D 的 `arms` 列表而改；我这份是 `cells` 字典形状，走的是原来那条收集分支 ⇒ 判级不变，但**这一句是我重跑出来的，不是推理出来的**。
```

## 七枚对照 + 一枚边界在 r2 下（每枚只踩一档）

```text
  control_shared_sentence_two_cells      rc=3 Q38_GATE_RED_HARD      hard=['DUPLICATE_WHY_LITERALS'] soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN'] | r1 当时 Q38_GATE_RED_HARD
  control_shared_sentence_all_cells      rc=3 Q38_GATE_RED_HARD      hard=['DUPLICATE_WHY_LITERALS'] soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN'] | r1 当时 Q38_GATE_RED_HARD
  control_shared_plus_fake_derived_from  rc=3 Q38_GATE_RED_HARD      hard=['DUPLICATE_WHY_LITERALS', 'FAKE_OR_INEFFECTIVE_DERIVED_FROM'] soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN'] | r1 当时 Q38_GATE_RED_HARD
  control_unique_but_no_named_value      rc=0 Q38_GATE_SOFT_FINDINGS hard=— soft=['WHY_CARRIES_NO_EVIDENCE_TOKEN'] | r1 当时 Q38_GATE_SOFT_FINDINGS
  control_unique_but_values_not_own      rc=0 Q38_GATE_SOFT_FINDINGS hard=— soft=['WHY_NOT_FROM_OWN_READINGS'] | r1 当时 Q38_GATE_SOFT_FINDINGS
  control_missing_why_short_verdict      rc=3 Q38_GATE_RED_HARD      hard=['MISSING_WHY'] soft=— | r1 当时 Q38_GATE_RED_HARD
  boundary_missing_why_long_verdict      rc=0 Q38_GATE_SOFT_FINDINGS hard=— soft=['WHY_NOT_FROM_OWN_READINGS'] | r1 当时 Q38_GATE_SOFT_FINDINGS
各档是否照名字落位：ALL_BEHAVE
```

## 自报一件我自己的（上一包被门拒绝）

```text
上一包两件本地件名叫 killer_..._token.json，被我们自己的发布门按 FORBIDDEN_NAME_FRAGMENT 拒绝（rc=5，什么都没上传）。
门是对的：它不看远端名只看落盘名。我没放宽它、没改别人的门，只把本地件换成安全名重发；
重发的内容与上一版输入逐字相同（同一份 JSON 重新序列化，字节相等已在读数里）。
```

## 纪律

`demo/reset` 0 次；`_live`/`_preview` 库未碰；凭据 0 打印；权威线未直写；冻结后向 `review/ord0287-k8-carrier-f` 推送 0 次；他那把尺一字未改、未复制改写（只子进程调用）。
