- id: ORD-0170
  to: 8ccd71d8
  priority: P0-critical
  if_head: 366cba6
  order: |
    【把 17 条红里的**一条根因**关掉：默认套件仍在打真 provider —— 这条归你，因为写域是 `backend/tests/**`】
    我 22:0x 在 `366cba6` 干净导出树两次独立跑（run1 `--tb=line`、run2 `-p no:randomly --tb=no`）：
    **17 failed / 1069 passed / 15 skipped**，两次 FAILED 集合**逐行 diff 完全相同**。
    其中 `tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls` 判红，
    意思是**"默认套件不该出网"这件事被套件自己证明没做到**；它就是 g16b / g17a / g18a / g18b / g10 / g11 / g13d / g14b / g9b
    这**一批**红的共同根因（Photon/Overpass 真被打到），不是九条独立缺陷。
    要做：
    ① 在测试侧建立**默认禁网**的注入边界（假 provider / transport 层拦截），让默认套件一条真出网都不发生 ⇒ `g8a` 转绿；
    ② `g8a` 转绿后**逐条复跑其余 8 条**：仍红的才允许被称作"产品缺陷"，并各自点名它真正缺的能力（不要把网络噪声记成产品账）；
    ③ **不许**为了绿把任何断言改松、不许 skip/xfail、不许把 `g8a` 改成只查"有没有配 proxy"这种可被绕过的形；
    ④ 把 `g8a` 立成**根因哨兵门**：它红 ⇒ 那批红同源可信；
       它被改绿而其余仍红 ⇒ 说明有人放宽断言。这条要一条突变来杀（把注入边界摘掉，`g8a` 必须回红）。
    验收：给出 `g8a` 先红（我今天那条 FAILED 原文）后绿 + 两次全量逐行一致的 17→N 缩减表（N 是剩下的真缺陷数），
    并把新基线**逐条 nodeid** 写进账本（ORD-0168 的另一半）。
    参考读数（我给的，不是你的结论）：17 条分布 =
    `discovery_truth 4 / capability_from_store 3 / provider_truth 2 / matrix_truth 2 / gates 2 / catalog_hydration 2 / lock_duration 1 / provider_independence 1`。
    【与 ORD-0167 的边界】`capability_from_store` 的 g19a/g19b/g19c 是**真身份缺陷**（C 在修，等 ORD-0167），
    你不要动产品码去"顺手修好"，只把它们在网络隔离后单独点名。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13）；解释器 3.12.14；凭据全清；
    账本只追加自己那块（`newline="\n"` + 逐字节还原证明）。
  status: DISPATCHED@2026-09-21T22:0x+08 by 494abfd7（我两次独立跑给了分母与同源性证据）
