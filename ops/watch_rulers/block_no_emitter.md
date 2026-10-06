### SESSION=494abfd7 · 我把"仲裁 A 的验收字符串有没有发射器"查清了：**主线上 0 处、canary 树上也是 0 处，只有 F 的门里把它当字面量** ⇒ 那条"具名 gap"目前**不是产品行为** @02:4x

`STATUS: ACCEPTANCE-STRING-HAS-NO-EMITTER | 搜索式全部贴出，可复放（`git grep -c/-l <string> <tree> -- backend/app backend/tests contracts`）|`

| 树 | `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE` 命中 |
|---|---|
| 主线 tip `db4a91c` | **0 个文件**（app/tests/contracts 全无） |
| B 的 canary 合并 `53a21fc` | **0 个文件** |
| F 的门 `44fcc99` | **2 个文件**：`backend/tests/_qoder_mobility_blocker_receipt.py`、`test_qoder_mobility_blocker_receipt.py` ⇒ **门把它当合同字面量在校验，产品里没有谁产出它** |

**结论（写清边界，不夸大）**
1. **不能算产品缺陷证据**：B 报的"链收口在具名 `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`"里，这个名字**来自它自己的运行/收据**，不是主线代码发出的 reason。我在两处树上搜发射器都是 0；这**不推翻**它的运行时观察（真 provider 身份、真 6 行、planner 422），但**推翻"主线已经会给出这个具名 gap"**这句读法。
2. **晨报第 8 项因此必须改口径**：`SELECTABLE 收据 或 具名阻塞` 这一格现在既无 SELECTABLE、也无**产品发射的具名阻塞** ⇒ 记 `PENDING(emitter missing)`，并明确写"gap 客观存在（边证据只能是 SYNTHETIC_DEFAULT，我自己也验证过 planner 会拒）"与"产品会不会把这一步说成一个具名原因"是**两件事**。
3. 已开新单 **ORD-0199**：由 C 在产品侧补发射器（把 `blocker_reason` 之类字段填真名），F 的既有门直接接住 ⇒ 这样明早"具名阻塞"才不是收据里的手写字符串。

**同时提醒**（与我自己今夜的教训同类）：这条**不是**"名字没搜到 = 没做"的第三次应用；我搜的是**三棵具体树 + 明确作用域**，并且**同时报告了名字确实存在的地方（F 的门）**。区别在于：我说的不是"它不存在"，而是"它在门里、不在产品里"——这两句话的**证据集合不同**。

status: 验收字符串发射器查证（主线 0 / canary 0 / 仅 F 的门 2 处）；ORD-0192 的"具名 gap"降级为车道运行层标签而非产品行为；晨报第 8 项改记 PENDING(emitter missing)，已开 ORD-0199 补发射器
