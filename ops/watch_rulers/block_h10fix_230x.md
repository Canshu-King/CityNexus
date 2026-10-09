### SESSION=494abfd7 · 更正我自己刚转录的 H10b 结论：**"4 vs 12 fields"是读错了键**，12 字段全对象一直在同一个响应里；真缺的只有 `solver_mode`（被 MCP 白名单**静默丢弃**）@本机钟 23:0x

`STATUS: MY-TRANSCRIBED-CONCLUSION-CORRECTED | 我只核了权威树 HEAD 的代码，没有采信任何自述（包括仲裁 5762383895 ② 那段的转述）| 树 `backend/app/agent/*` + `agent-mcp/citynexus_mcp/schemas.py` |`

#### ① 代码读数（逐条可复放）
- `backend/app/agent/gateway.py:501` → **`"proposal": generated`** = **完整对象**（含 `diff` / `utility_score` / `proposed_plan_version_id` / `base_plan_version_id` / `trigger_event_id` / `score_breakdown`）；
- `:502` → `"proposals": [...]`，其元素来自 **`main.py:7269 def _replan_payload(...)`** = **摘要形状**（`id,status,hard_constraints_passed,locked_commitments_preserved`）；
- 产品自己就用单数键：`guardian.py:435` `proposal_id = str(generated["proposal"]["id"])`；`runtime.py:549` 读的也是 `result.get("proposal")`；
- `gateway.py:459 / :481` 的入参里有 **`solver_mode`**（网关收），但 **`agent-mcp/citynexus_mcp/schemas.py:24 SAFE_ARGUMENT_NAMES`** 不含它，
  `:71 unknown = sorted(set(payload) - SAFE_ARGUMENT_NAMES)` ⇒ **MCP 侧把它丢在门口**，网关拿 `None` → `normalize_solver_mode(None)="deterministic"`。

#### ② 结论：H10b **不是**被投影阻塞，是被**读错的键**阻塞
⇒ "同一个 proposal 产品面 12 fields、agent 面只有 4 fields"这句把**单数全对象**和**复数摘要**当成了两个不同表面的两个真值 —— 它们是**同一响应里的两个键**。
⇒ 因此 H10b 的两半要分开：
 - **(a) 数据可见性：不需要产品改动。** parity 腿改读 `proposal`（单数）即可拿到同一 canonical 对象 ⇒ 车道今天就能做，不必等接缝；
 - **(b) 求解一致性：这是一条真的产品/适配缺口**，但只有"一个字段"那么大：`solver_mode` 不在 MCP 白名单 ⇒ 产品腿传 `v2`、MCP 腿传空 ⇒ **跑的是两个不同 solver**，之前量到的"8 字段 planner 分歧"（`V2_WHOLE_HORIZON` vs `F1_OPTIONAL_REMOVAL`、utility 0.58468 vs 0.697）**是配置不齐，不是语义分歧**。
⇒ 我在 ORD-0173 ③ 里把仲裁的 `BLOCKED_BY_PROJECTION / 二选一关闭方案`原样抄给了车道 —— **那是我转录过快**：车道自己的笔记里已经撤过"读复数键得出的截断结论"，我该先核代码再转。已下 ORD-0176 修那条真缺口，ORD-0173 的 ③ 相应改口径。

#### ③ 顺带一条与 R14 同一味的产品真相
"未知字段被**静默丢弃**"比"被拒绝"更危险：MCP 层丢（FastMCP 按签名绑定）+ 网关 422，两处都在丢/拒，但**调用方看到的是一次成功调用**。
⇒ 全线口径（已写进 ORD-0176）：**参数被丢弃必须说 "parameter discarded"，不得报成"边界已遵守"**；否则一次带 `sql=` 的"成功"调用会被读成"它拒绝了 SQL"，而这正是我们最不该留下的错觉。

status: 更正我转录的 H10b 结论（单数键=12 字段全对象，一直可见）；真缺口收敛为一个字段 `solver_mode`（ORD-0176）；"静默丢弃不得报成已拒绝"提为口径
evidence: `gateway.py:501/502`、`main.py:7269`、`guardian.py:435`、`runtime.py:548-550`、`agent-mcp/citynexus_mcp/schemas.py:24/:71`（权威树 HEAD 直读）

- id: ORD-0176
  to: 8c66aa92
  priority: high
  if_head: 82f136f
  order: |
    【一条只有"一个字段"大的真缺口：`solver_mode` 进不了 MCP，而且**是被静默丢的】
    读数：`agent-mcp/citynexus_mcp/schemas.py:24` 的 `SAFE_ARGUMENT_NAMES` 不含 `solver_mode`，`:71` 把未知字段算出来之后**不报错**；
    而 `backend/app/agent/gateway.py:459/:481` 明确收 `solver_mode`（`POST /journeys/{id}/replans` 可传 `v2`）。
    ⇒ 后果：同一次 parity，产品腿 `v2`、MCP 腿 `None`→`normalize_solver_mode(None)="deterministic"` ⇒ **跑两个 solver**，
      分歧是配置造成的（今天已有一次因此被误读成"8 字段 planner 语义分歧"：`V2_WHOLE_HORIZON` vs `F1_OPTIONAL_REMOVAL`，utility 0.58468 vs 0.697）。
    要做（二选一，**不许**保持"静默丢弃"这第三种状态）：
    (A) 把 `solver_mode` 纳入 allow-list（仍是安全参数：枚举值、不接受任意字符串），MCP 与网关同源校验；或
    (B) 让 MCP 对"未知或被丢的参数"**具名拒绝**（422 + 稳定 reason/message_key），并在响应里回显本次实际生效的 `solver_mode`。
    门：① 同输入两腿必须报告**相同**的 `solver_mode`（回显字段断言）；② 一条突变：把 (A) 的白名单项摘掉 / 把 (B) 的拒绝摘掉 ⇒ 必须红；
      ③ 口径进契约：**"parameter discarded" ≠ "boundary honoured"**，一次携带被丢参数的成功调用不得被报成"边界遵守了它"。
    与别的单不混：这**不是** ORD-0167（身份/解析），也不是 ORD-0158（预算真值）；H10b 的"数据可见性"那半**不需要你动**——
    12 字段全对象在 `gateway.py:501` 的 `"proposal"`（单数）里一直可见，车道改读它即可（我已把 ORD-0173 的 ③ 改成这个口径）。
  status: DISPATCHED@2026-09-21T23:0x+08 by 494abfd7（我自己代码复核后新增，非转述）
