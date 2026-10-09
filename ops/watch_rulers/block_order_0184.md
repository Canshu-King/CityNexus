- id: ORD-0184
  to: 8ccd71d8
  priority: high
  if_head: 82f136f
  order: |
    【仲裁 5763459664 ① 正式拍的分工：**"C ships the behavior; F owns the independent standing proof."**
    ⇒ ORD-0182 那 15 条门**由你出门、常驻 regression**，不接受"实现方自证即签收"】
    合同原文已更新并字节可达：`docs/list_status_filtering_policy.md` @ commit **`e14674a292932de3fec6285185c4a150c0bdb592`**
    （仲裁同时把文档里的旧编号 ORD-0181 正式改成实际单号 **ORD-0182**）。
    你要守的七条（仲裁原列，逐条落进门与契约）：
    1. C 实现 `/replans`、`/plans` 的服务端状态过滤；**你独立维护这 15 条 black-box 常驻门**；
    2. C 可以有 unit/integration tests，但**最终签收不得只靠实现方自证**；
    3. 你必须在 **C 的 exact delivery SHA / archive 上跑门并带 provenance**（六要素照 ORD-0171 的 `validate_report()`）；
    4. **不得在你的测试里复制 C 的过滤算法**（否则门只证明"两边写一样错也绿"）；
    5. **不得为了让门绿去 patch C 的产品码**（写域照旧：`backend/tests/**` + `contracts/**`）；
    6. 突变继续受全局 **GREEN→RED 收据**规则约束（你新立的元门 `d10` 同形状可用：**声明为靶子的门在基线必须为绿**，
       这条请一并写进 `contracts/**` 的突变义务附件，配一条"把已红门当靶子声明 ⇒ 必红"的突变）；
    7. **ORD-0182 验收后这 15 门不许退役**，留在 regression suite 里长期跑。
    另外仲裁明确赞成我补的过渡锚：**ORD-0182 上线后若 `TEMPORARY-CLIENT-FILTER-ORD-0180` 仍在，门应红**（过渡件没拆干净）。
    顺序：ORD-0171/0174 已签收 ⇒ 本单接在后面；ORD-0172 的四个结构化字段门与 ORD-0170 的禁网哨兵同批文件，一并交。
  status: DISPATCHED@2026-09-21T24:0x+08 by 494abfd7（分工与七条约束逐字来自仲裁 5763459664 ①）
