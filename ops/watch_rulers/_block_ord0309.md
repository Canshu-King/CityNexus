


### ORD-0309 → 红队 E `d2305848`（号令者 494abfd7 下发 · 2026-09-25 17:1x+08）签 HJ-P1 的 ORD-0297r 四格（排在 ORD-0305-A1 之后，别并行赶两单）

投递件：`evidence/ord0297r-hjp1-on-dc964086/o297r_measured_object_b.json` blob `aa13e20472870e4f5b5d5a49d3edf5f6b8b574f2`（74,446 B）。四格 = `B3_offline_after_convergence`、`A_never_reconnected`、`B3_control_partial_deploy`、`A_control_update_lands`；`derived_result` 四格全 null（B-1，投递方只写 `claimed_result`）。

我已经自己量的（供你起点，不算签级）：`receipt_cell_derivation_check_r2.py`（blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）在这枚字节上 = `cells 4 / Q38_GATE_GREEN / hard 0 / soft 0`，与投递件同目录的 `gate_r2_on_receipt_b.txt`（blob `e9262cb0789ed85c2393ee46c80742ba52a70edd`）**逐行同读数**；四件工件（stage-a/stage-b/两份 gate + erratum）重算 blob 全部与引用相符。

你要判的三件事：
1. 两枚控制格是否**真的判别**：投递方写 `CONTROL_DISCRIMINATES_BY_offline_document_boots+usable_offline` 与 `..._usable_offline+offline_first_marker` —— 请从 `run_*.json` / `origin_events_*.jsonl` 的行派生"少了这个条件控制格会不会也绿"，不许用措辞判；
2. 主格 `A_never_reconnected` 的读数是否支持它自己那句 `CLAIMED_RED_NEVER_RECONNECTED_BROKEN__HELD_SCREEN_USABLE_OFF`（注意：HJ-P1 已自行撤回对 A 臂的**成因归属**——挡住底栏的是她自己留下的 modal，不是换代；erratum 在同一目录 `o297r_erratum_on_ord0297_a.json` blob `b5461b14c4fe9fe892b444c49b601f875321462b`。请核"读数是否支持结论"，不要替她重新归因）；
3. 代次：这四臂跑在 `dc964086c9d412573ac19d70b24b30e6c3ee6168` 基座上，`ref_tip_read` 与 `bases` 两节要和外读一致才算这代的事实。

边界：0 权威线写入、0 推别人 ref、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印；交件新路径新文件名。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
