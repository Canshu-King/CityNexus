## commander 记账 @2026-09-22T23:52+08 —— C 的 ORD-0219 正式交付块到账（写入端两层校验＋五步①）；它自纠两处量具错；**两格仍红是已知旧账不是它带的**

### ① C 的交付块要点（我按读数引用，不替它复跑）

- **四格行为表**：词表外⇒422 `UNKNOWN_RULE_CODE` 不落库；词表内但不执行＋HARD⇒422 `HARD_RULE_NOT_EXECUTABLE` 不落库；同码 SOFT⇒201 落库；可执行硬码⇒201 且**写入端不预判挡不挡**（由 feasibility 按证据定）。
- **关键取舍**：两个集合都**从求值层派生**（`EXECUTED_HARD_RULE_CODES` = dispatch 真认识的码 ∪ `_CAPABILITY_GATE_CODES`），没有第二份手抄词表 ⇒ 求值层加分支时写入端自动跟上，且 `test_7` 钉这条一致性。
- **五步①**：`STROLLER`/`LARGE_LUGGAGE` 断言式说法=HARD、只提及=STRONG；**故意没**把它们挪进 `HARD_ACCESSIBILITY_CODES`（那会触发"永不过期/不许降级"，是更大的一步）。
- **门禁**：全量 collect 1187/0 error；新门 9 passed；回归批 295 passed / **2 failed（g14a/g14c）**——它用 `git stash push -- <四个改动路径>` 证明这两条红**不是它带的**（stash 后同节点仍红）。
- 它自纠两处量具错：① 把 git blob sha1 当 sha256 比（我发的适配器指纹其实一致）；② 适配器跑 streak 时共享判据取错版本（`9514eb7` 没有 `shape_command`）⇒ 换 `a4079bc` 版一次跑通。**它还确认了产品树里没有放这把判据（未并线），它是在一次性导出里放的——这个纪律对。**

### ② 我这边两个待办提醒

- 那 2 条 g14a/g14c 红**仍是 B 的旧账**（14:2x 就红），B 修完时按"红集合子集"口径收口；
- C 的补丁已发布（`evidence/ord0219/bce7269__e1580de.patch` blob `3491f64524800461`），等 GPT 与 B 的三份一起审。

### ③ 现场

working tip `e1580de`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
