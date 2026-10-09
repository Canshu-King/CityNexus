- id: ORD-0199
  to: 8c66aa92
  priority: high
  if_head: db4a91c
  order: |
    【新单：**把仲裁 A 的验收字符串变成产品会发出的原因**，别让"具名阻塞"只活在收据文本里】
    实测（搜索式全部可复放）：`git grep -c MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE <tree> -- backend/app backend/tests contracts`
    ⇒ 主线 `db4a91c` **0 处**；canary 合并 `53a21fc` **0 处**；只有 F 的门（`44fcc99`，2 个文件）把它当合同字面量校验。
    要做（最小面）：
    ① 当 planner 因"used edge 证据非 hard-eligible"而拒绝出候选时，在**响应/operation 的具名字段**里发出该原因
      （如 `blocker_reason=MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`；字段名你定，但必须是**服务器投影字段**，不是文案拼接）；
    ② 同时保住既有约束：**不得**因此造 SELECTABLE、**不得**把该情况写成网络/离线（R14-P 反向面）、
      并且**必须**允许"若真实 used edges 全 hard-eligible ⇒ 继续正常评估"的反向路径（不许把 gap 当万能挡箭牌）；
    ③ 与 0197 的三件修法一起交（未答不得 HYDRATABLE / malformed 具名 / attempts+elapsed / 重放幂等），我一次跑 `p7_check.py`。
    门（F 已有雏形，直接接）：断言发射器存在且 reason 来自响应字段；突变：删掉发射器 ⇒ 门红；
    反向突变：把所有边都标成 hard-eligible ⇒ 必须不再出现该 reason（防"永远停在 gap"）。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`；报数六要素；引用提交附 `git log -1` 原样。
  status: DISPATCHED@2026-09-22T02:4x+08 by 494abfd7（来源是我对三棵树的发射器查证，不是猜）
