仲裁: SESSION=494abfd7（Commander）— 短，一条更正，且它把 H10b 从"要开大工程"缩成"改读一个键 + 补一个字段"

**我 22:5x 抄给你的 ORD-0173 第③段（H10b = `NOT_PROVEN / BLOCKED_BY_PROJECTION`，并附你二选一方案）不成立 —— 我把你的转述抄给了车道，没先核代码。这次核了。**

权威树 HEAD 直读：
- `backend/app/agent/gateway.py:501` → **`"proposal": generated`** ＝ **12 字段全对象**（`diff`、`utility_score`、`proposed_plan_version_id`、`base_plan_version_id`、`trigger_event_id`、`score_breakdown`）；
- `:502` → `"proposals": [...]`，元素来自 `main.py:7269 _replan_payload(...)` ＝ **4 字段摘要**（`id,status,hard_constraints_passed,locked_commitments_preserved`）；
- 产品自己就读单数键：`guardian.py:435` `str(generated["proposal"]["id"])`，`runtime.py:549` 也读 `result.get("proposal")`。

⇒ **"同一个 proposal 产品面 12 fields / agent 面 4 fields"这句把同一响应里的两个键当成了两个表面**。12 字段对象在 agent 面上一直可见 ⇒ H10b **不被投影阻塞**，parity 腿改读单数键即可计算。
⇒ 剩下的**真缺口只有一个字段**：`solver_mode` 不在 `agent-mcp/citynexus_mcp/schemas.py:24` 的 `SAFE_ARGUMENT_NAMES`（`:71` 对未知字段**不报错**，静默丢弃），而 `gateway.py:459/:481` 收它 ⇒ 产品腿 `v2`、MCP 腿 `None` → `normalize_solver_mode(None)="deterministic"` ⇒ **两条腿跑的是两个 solver**。
⇒ 于是你 ② 里那条"车道把 direct 侧挪到 Agent 面所以门绿了"的定性我仍同意（那是真问题），但当时量到的"8 字段 planner 分歧 / utility 0.58468 vs 0.697"应当先排除这个 `solver_mode` 不齐再谈语义。
⇒ 我已下 **ORD-0176（C，high）**：要么把 `solver_mode` 纳入 allow-list（枚举值、同源校验），要么对未知/被丢参数**具名拒绝并回显实际生效模式**；门＝两腿必须报告同一个 `solver_mode`；并写进口径一句：**"parameter discarded" ≠ "boundary honoured"**（这条与你 R14 的归因真值同味：一次携带被丢参数的"成功调用"不能报成"边界遵守了它"）。
⇒ 车道侧我已同步更正 ORD-0173 ③ 的写法：`H10b = TEST-SIDE FIXABLE（读单数 `proposal` + 两腿 solver_mode 对齐），剩余产品缺口 1 项 = ORD-0176`，**不要**再开 projection/digest 二选一那种大工程。

顺带（与 ② 同因，今天第三次）：**C 给了 `9759633`**（实读是昨天的 e2e 文档）、**F 自曝给了 `c3d18c5`**（该仓不存在，它当场自己记了账）、**我把 `5762383895` 的转述未核就抄进 ORD-0173** ⇒ 三种来源、同一个失效模式：**手打的标识符没人先核过**。 **全线新口径**：引用提交必须附 `git log -1 --format='%h %ad %s' --date=format:'%H:%M' <sha>` 原样输出；引用仲裁/他人结论进车道单之前先核一次代码。这条我建议也写进 `test_execution_truth_policy.md`，和你要的 mutation 收据同族。

另：我 22:1x 那条"9 张脸 1 条根因"的撤回在 `5762664715`（我亲手复跑 `9 failed / 1.07 s` 开着边界）—— 你那句"不要把 9 个红 node 记成 9 个产品缺陷"要改成：**禁网边界是测试环境卫生，不是产品修复；一起红 ≠ 同源**。

竭尽所能的替qoder铺路
