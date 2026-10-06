### SESSION=494abfd7 · 交叉突变仪器：**我七组复跑全对 → 升 REPRODUCED**（`44fcc99`）；顺带记录一件事的坐标差别（车道 worktree ≠ 权威树）@02:2x

`STATUS: ACCEPTED-REPRODUCED-BY-ME | 树 `D:/moodle/_qoder_f_o156_20260921` @ `44fcc99`（只读 import 其 `tests/_qoder_mutation_receipts.py`，未改任何文件）| 权威 integration 树**没有**这份仪器 ⇒ 见 ③ |`

**① 我原先抓到那个错，现在是这个行为**
```
真独立      G/R/G/G  -> INDEPENDENT            假独立(耦合)  G/R/G/R  -> COUPLED
靶子本已红   R/R/G/G  -> INCONCLUSIVE           没撬动        G/G/G/G  -> INCONCLUSIVE
B 本来就红   G/R/R/R  -> INCONCLUSIVE   ← 我 01:3x 报的是 COUPLED，**已修**
B 已红且没撬动 G/G/R/R -> INCONCLUSIVE          非绿非红      …UNKNOWN… -> INVALID_MUTATION_EVIDENCE
```
⇒ 7/7 与我上一版给的第六组期望一致 ⇒ **ORD-0189 的仪器部分升 `REPRODUCED`**（时间优先判定顺序：先验 A_before、再验 B_before、才看 A_after、最后才看 B_after）。
⇒ 车道从"我报出问题"到"修好 + 把第六组补进自证 + 顺手把'聚合数当 blocker'也做成门"（`2bbd69a`→`44fcc99`→`28c2fb9`）用了约 25 分钟，方向没有一项跑偏。

**② 同一棵 worktree 里还有一条我已核过形状的**：`44fcc99` 一并加了"聚合数 blocker 判红"的门 ⇒ 与仲裁 `94b4d904` 的 `blocker_basis=USED_EDGE_INVENTORY` 对得上；这条我算**契约+门都到位**，只等 B 真交 14 项收据来验行为。

**③ 一条我自己的操作错（差点误判成"没做"）**：我先在**权威树**里找这份仪器 ⇒ `ModuleNotFoundError`，几乎要写"仪器不在交付面里"。
实际它在 F 自己的 worktree（车道分支未并入权威树），是我找错了地方，不是它没做。
⇒ 这正是我今天第 5 次"搜索面选错 → 得出假缺失"。**新规矩（也写进车道口径）**：判"某文件不存在"之前，必须同时报 **仓库/树路径 + ref + 搜索式**；权威树缺席 ≠ 交付缺席（车道未 push 是今晚常态）。

**④ 权威树侧的新事实**：`306f153`（02:13）只动 `review/mutate_ord191_leg.py`（+128），是 C 对"四类结果要各自可断"的响应 ⇒ **仍是测试面，不是产品行为收据**；ORD-0197 按 v2 仍需四类穿过正常产品路径的证据，**不能就此判通**。

status: 仪器 7/7 复跑通过 → REPRODUCED（@44fcc99，含我报的第六组）；聚合数 blocker 门同步到位；我自纠"在权威树找不到"= 搜索面选错（第 5 次同类），已立"报缺失必附树+ref+搜索式"；306f153 只是测试面，0197 未过
