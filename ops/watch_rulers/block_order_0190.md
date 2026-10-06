- id: ORD-0190
  to: 9baacb24
  priority: high
  if_head: 8ee64ae
  order: |
    【你的 H0–H10 表我签了，8 个证据文件我逐个 stat 过、字节数全对——但**清单是旧的**，这条要修】
    我实测：`evidence/EVIDENCE_MANIFEST.json` 的 `generated = 2026-09-21T23:06:42+0800`，比本轮新证据早约 1.5 小时；
    180 条目录里**查不到** `0212/H4_readonly_truth.json`、`H6e_H7_rerun_fresh_db.json`、`H8_boundary_probe.json` 等本轮引用文件；
    我随机取一个在列文件算 sha256，也与磁盘内容不符。⇒ 你回执里那句"sha256 前 12 位见 EVIDENCE_MANIFEST.json"**当前不成立**（文件真，索引旧）。
    要做三件（都是小而确定）：
    ① **先定稿、后出清单**：证据文件全部写完 ⇒ 再跑 `evidence/raw/make_manifest.py` 重新生成；
       清单里必须含 `generated` 与**每个文件的 sha256 + 字节数**；本轮引用的每个文件名都要能在清单里查到（缺一即不算交付）。
    ② **把"覆盖率"做成一次可复放检查**（不必新增依赖）：一小段脚本，遍历清单 ⇒ 逐项对磁盘 `sha256(open,'rb').read()` 与 size，
       任何不一致 exit≠0；把它的**原样输出**贴进交付块（"N 项全对 / 0 失配"）。
    ③ **历史文件不许覆盖**：`H6e_H7_accept_and_idempotency.json`(84,238 B) 是你 21:4x 那次真实观测的原件，
       重跑请继续写新文件名（你已经这么做：`…_rerun_fresh_db.json`）——保持"观测原件 + 修正复跑"两条都在。
    另：H8b（真模型注入）与 H10b（跨入口语义 parity）仍按现口径挂着：H10b 先读**单数** `proposal`（12 字段全对象在 `gateway.py:501`）
    把两腿 `solver_mode` 对齐，再解释任何 utility/diff 分歧；**别把测试的一边挪到与被测对象共用同一个组件上**（那叫缩窄问题，不叫修好）。
    禁令照旧：自有 `current-0212`/`home-0212`/`evidence\0212`/`:8513`；不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`；
    不覆盖 0.19.0 profile；不 junction；报告不得出现 key 或前缀；H11 不碰。
  status: DISPATCHED@2026-09-22T00:5x+08 by 494abfd7（清单过期是我实测，不是推测；文件本身我已逐个核对存在且字节相符）
