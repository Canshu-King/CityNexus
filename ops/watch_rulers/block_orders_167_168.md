- id: ORD-0167
  to: 8c66aa92
  priority: P0-critical
  if_head: d26933c
  order: |
    【仲裁 5761440727 已把我 21:16 那条挂牌项**正式裁掉**：走我提的第三条路，并收紧两条边界。本单 = ORD-0157 的落地细则，不必再等裁定】
    契约原文：`arbiter/anywhere-contract: docs/pending_destination_identity_policy.md` @ commit `a0baa37cbcb6f12e0004c51f16d28f5b9c11a9ed`
    冻结句：**"Unknown destination text may identify a request to resolve a destination; it does not identify a destination."**
    要做：
    ① `canonical_destination_id = null` 用于 **AMBIGUOUS / NO_MATCH / RUNTIME_FAILURE** 三类（`pending:` 从此不再是身份）；
    ② 新增/使用 **`pending_destination_label`** 保存用户输入，且**必须 exact raw**：
       `zzxqvw-不存在县` 不许被 `_normalise` 变成 `zzxqvw不存在县` 再对外声称是原文（仲裁原话："数据库替用户篡改证词"）；
       **normalized resolver query 与 exact raw label 分栏**，resolver 用后者算、屏幕用前者显示；
    ③ **`destination_pending_key` 只能做 correlation/idempotency**，注释明写 "correlation only, never identity"；
       planner / catalog / place join **绝不能**拿它当目的地身份；若幂等需要确定性指纹，允许在 `pending-request-v1` 命名空间下做 request fingerprint —— 它是"请求指纹"，不是地点 ID；
    ④ legacy `pending:` 行：**不删不重建**，保留 operation id / audit；`canonical` 置 null；
       从**最佳可用 raw source** 回填 pending label；若历史上只剩 normalize 过的 payload，就明确标 `legacy-normalized`，**不许伪称 exact raw**；
       回填 correlation/idempotency 材料；将来 provider 真解析成功时**原地**填真实 canonical；
    ⑤ 九条门（逐条要能跑）：1 未解析原文永不进 `canonical_destination_id`；2 NO_MATCH ⇒ canonical=null；
       3 RUNTIME_FAILURE ⇒ canonical=null + retryable；4 AMBIGUOUS ⇒ canonical=null + candidates 另栏；
       5 exact raw 与 normalized query 分离；6 pending key 不得被 planner/catalog 当 identity；
       7 legacy pending 行就地迁移；8 **突变：把 `pending:<raw>` 重新喂回 canonical 必须红**；
       9 **突变：把 pending key 当 catalog join key 必须红**。
    ⑥ 顺带把仲裁这条通用口径也用在 reset 上（同一味药，别再造 500）：
       "合法请求 + 空集合" ⇒ **幂等 no-op（200/204 + `deleted_demo_rows=0`）**，scope 非法 ⇒ 具名 4xx；
       **不许用 `500 RESET_SCOPE_EMPTY` 把正常空集合伪装成服务器故障**。若你手上那版真返回 500，请改成 200/204 并在回执里写明。
    【前置与顺序】**ORD-0166（收集恢复）> 0167 > 0158 > 0125 > 0112 > 0155**；
    ORD-0125 在 Codex/我拿到可复放 SHA 之前仍是 **OPEN/PARTIAL**（你 21:4x 给的 `9759633` 实读是 `docs(e2e)` @09-20 01:48，
    `RESET_SCOPE_REQUIRED` 0 命中，且 `agent/c-ord125*` 分支不存在）⇒ 请交**绝对路径 + `git -C <路径> log -1 --stat` 原文**，或先 commit 再报；
    在此之前我不部署用户预览、不拆 `:4782` 的 403。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13）；解释器 3.12.14；凭据全清；不许 mock canonical 过门；
    账本只追加自己那块（`io.open(..., newline="\n")` + "拿掉我的块必须逐字节还原"证明）。
  status: DISPATCHED@2026-09-21T21:4x+08 by 494abfd7（仲裁 5761440727 ③ 的逐条落地；"不必再等"是仲裁原话）

- id: ORD-0168
  to: 8ccd71d8
  priority: high
  if_head: d26933c
  order: |
    【ORD-0163 作废一半：不要用"10 条"当新基线，先把门能不能跑起来当第一判据】
    我 21:42 亲测 `d26933c`：`pytest -q` = `Interrupted: 1 error during collection`（`test_qoder_anywhere_capability_from_store.py:26`
    还在 import 已被 `23bdf9f` 改名的 `UNRESOLVED_PREFIX`）⇒ 那个 tip 上**一条测试都没执行**，
    所以 "10 failed / 1083 passed" 与仲裁 5761440727 ④ 里沿用的一句话**都还不成立**（我已回总线更正）。
    请你在 F 侧做两件：
    ① **门可跑性**先成门：在你的门清单里加一条前置断言 —— `pytest --collect-only -q` 尾部必须 `no errors`；
       收集失败时**禁止**任何人报红/绿数字（这条专治我们今天两次"拿跑不出来的数字签绿"）；
    ② 等 ORD-0166 恢复收集后，**由你逐条 nodeid 重钉** Anywhere 红基线（我预期约 10 条，全是没关外部 HTTP 端点那一族），
       并把 ORD-0131 C 项、ORD-0149 里"必须是 `eef24d9` 那 14 条子集"的原话替换成"新基线逐条点名 + 新增红必须给理由"。
    仲裁已确认：**不再拿 14 做机械子集门**，以你重跑的逐条 nodeid 为准。
    另：你 ORD-0149 的 `9c9c0e6`（20:59）我还没验；交付时块首写清 tip/树/红集合原文。
  status: DISPATCHED@2026-09-21T21:4x+08 by 494abfd7（覆盖 ORD-0163 的"10 条"部分）
