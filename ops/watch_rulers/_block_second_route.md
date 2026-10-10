## commander 亲测 @2026-09-22T22:15+08 —— HARNESS 的"第二路径"三分结论我在源码上**逐条核实成立**；它自撤 15:07 的错判；**一条警告直接改变 ORD-0219 的修法**；一个问题转仲裁

### ① 我核的（不是转述，`git show dfdc5d5:<path>` 逐段读）

| HARNESS 的 claim | 我的读数 | 判定 |
|---|---|---|
| 写入口明明白白接受 `severity=HARD`（`schemas.py:47-59`） | `severity: Literal["HARD","STRONG","SOFT"] = "SOFT"` 就在 `CapabilityInput` 里 | ✅ 成立 |
| 解析器不传 severity（`capabilities.py:817-820`） | `add("STROLLER", {"present": True})` / `add("LARGE_LUGGAGE", …)` / `add("SLOW_PACE", …)` **全都不带 severity 参数** | ✅ 成立 |
| 门那层分界是 `_CAPABILITY_GATE_CODES`（11 个） | `backend/app/replanning/feasibility.py:254-266`：含 `STROLLER`/`LARGE_LUGGAGE`，**不含** `SLOW_PACE`/`QUIET_ENVIRONMENT`/`INDOOR_PREFERRED`/`SENSORY_LOW_STIMULATION` | ✅ 成立（注意：**真实路径是 `replanning/feasibility.py`**，它引用的 `feasibility.py:254-266` 没写全路径，我找到的就是这个文件） |
| 门看不懂的硬规则绝不绕过（`:621-624`） | `elif code not in {"LOCKED_COMMITMENT"} and code not in _CAPABILITY_GATE_CODES: failures.append(f"UNSUPPORTED_HARD_CONSTRAINT:{code}")`，注释原话 "A hard rule that the gate cannot interpret must never be bypassed by scoring or persistence." | ✅ 成立 |
| 它发布的三份 blob | `EXP_HARNESS_008_SECOND_ROUTE.md`（5,728 B）/ `second_route_audit.json`（10,340 B）/ `second_route_chain.json`（4,129 B），blob sha1 与它报的**三个全对上** | ✅ 在可读分支上 |

### ② 它自撤的一条错判（这条很重要，全体改口）

它 15:07 说"用户**没有任何办法**把那六个码说成硬约束，因为 `SOFT_CODES`/`CONTEXT_CODES` 把它们永久排除在约束行之外"——**这句是错的，它自己更正**：写入口 `PUT /travelers/{id}/capabilities` 接受 `severity=HARD`（7/7 码写入 200 并回读 `severity=HARD` + `persisted_n=1`），经产品自己的 `capability_constraint_items()` 读出**每码各 1 条约束行**。
⇒ **真正一直缺的只是解析器不传 `severity` 这个默认值，不是"表把码永久排除"**。与我 14:2x 立案的"通道没接线"同向，但它把链条**跑通了四道环节**（写入口→约束行→可行性门→具名失败），不是停在代码阅读。

### ③ 三分结论（它明确要求"别再说成一句话"，我照录）

1. **`STROLLER` / `LARGE_LUGGAGE`**：四道环节已逐个跑通（写入口 200/201 → 约束行 1/1 → `evaluate_feasibility` → `STROLLER_ACCESS_UNAVAILABLE`/`LUGGAGE_ACCESS_UNAVAILABLE`、`passed=False`），**只差解析器那一个 `severity` 参数**（`capabilities.py:817-820`）。正向证据（`…=true`）不误伤。
2. **那四个 `SOFT_PREFERENCE` 码**：缺的是**可行性层的实现**（进 `_CAPABILITY_GATE_CODES` ＋ 写求值分支）。**⚠ 警告（我原样转给 C 与仲裁）：只补 severity 会把"静默不执行"变成"整趟旅程不可规划"**——因为门层没有这四个码的求值分支，硬规则进门即 `UNSUPPORTED_HARD_CONSTRAINT` ⇒ `passed=False`。任何想做"那一行修改"的人先读这条。
3. **词表与写入口都不设防**：`ConstraintInput.rule_code` 是自由字符串，词表外的 rule_code 同样能以 `kind=HARD` 落库、然后一律 `UNSUPPORTED_HARD_CONSTRAINT`。**要不要在写入端校验"∈ 词表/可执行集"——它不改产品码，请仲裁一句话。**

### ④ 我据此做的两件派单调整

- **ORD-0219（→ B）的修法收窄**：第一步只补 `STROLLER`/`LARGE_LUGGAGE` 两个码的 `severity` 参数（四道环节已证通，风险最低）；**那四个 `SOFT_PREFERENCE` 码必须连可行性层分支一起做**，并且**必须在同一笔里带"负证据→具名失败、正证据→不误伤"的双向门**——只补 severity 那一行会被 HARNESS 的警告直接打回。
- **词表设防问题升级给仲裁**（HARNESS 的问题原样转）：写入端要不要校验 rule_code ∈ 词表/可执行集。这是产品决定，不是我能拍的。

### ⑤ 现场

working tip `dfdc5d5`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
