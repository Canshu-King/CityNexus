## commander 记账 @2026-09-22T23:41+08 —— **C 交 `e1580de`**（ORD-0217 写入端两层校验落主线）：四格边界形状正确；补丁已发布待仲裁审

### ① 我核的形状（源码读数，不替它跑运行时）

```text
提交     e1580de 23:39 fix(backend): an unwritable constraint rule is refused at the write, under two names (ORD-0219)
改动     capabilities.py +12、main.py +30、replanning/feasibility.py +58、新测试 +273、test_wp01_wp03.py +7
```
四格边界逐格对上仲裁 `5778314066`：
- **两个错误名分开**：`UNKNOWN_RULE_CODE`（词表外）与 `HARD_RULE_NOT_EXECUTABLE`（真码当硬门），注释原话："**'I have never heard of that rule' 与 'that rule is real but a hard trip constraint would be refused later' 是不同的拒绝、不同的修法，把它们合并正是让自由文本溜进来的原因**"；
- **两组集合从 evaluator 派生而非重抄**（"so the write layer cannot drift from the evaluator"）；
- **两条路径都不往 session 里加任何东西**（0 row persisted）；
- 每个拒绝带自己的稳定 `message_key`（`constraint.unknown_rule_code` / `constraint.hard_rule_not_executable`，按 ORD-0055 家族）。

### ② 发布

`evidence/ord0219/bce7269__e1580de.patch` 23,160 B，blob **`3491f64524800461`**（BYTE-LEVEL MATCH）⇒ 请仲裁审（连同 B 的三份，ORD-0219 的材料现在齐了）。

### ③ 主线状态

working tip **`e1580de`（23:39）**——20 分钟内主线连进三笔（B 的 severity、B 的 producer、C 的写入端校验），ORD-0219 的实现主体齐了；剩下：第五步 mutation + E2E（B）、验收（GPT）。
链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
