### SESSION=494abfd7 · ORD-0176 的"第 0 步"我已经静态做完了：**不是静默丢弃，是 MCP 根本没有这个入口** ⇒ 修法分支已定 @23:4x

`STATUS: PREMISE-RESOLVED-BY-CODE-READ | 依据＝`agent-mcp/citynexus_mcp/server.py:114-121` + `schemas.py:24-72` 原文（权威树 HEAD）| 不必再起服务做实验 |`

- 工具签名：`request_replan(request_id, journey_id, trigger_event_id, candidate_count=3)` ⇒ **签名里没有 `solver_mode`**；
- `SAFE_ARGUMENT_NAMES`（`schemas.py:24`）也没有它；而 `payload()`（`:71`）对未知键是 **`raise ValueError("unknown CityNexus Agent arguments: […]")`，不是静默丢**；
- ⇒ 结论：`solver_mode` 在 MCP 面上**根本不存在入口**（我原先在 ORD-0176 里写的"MCP 白名单静默丢弃"**机制说错了**，方向对了）。
- ⇒ **修法只有一条**（=我原单里的分支"签名处丢"，现改为"无入口"）：给 `request_replan` 工具签名加 `solver_mode`（枚举校验、默认值与产品一致）+ 加入 `SAFE_ARGUMENT_NAMES` + 透传到网关；
  **或**明确声明 MCP 面永远只用默认 solver，并把这一点写进契约、让 H10b **不再声称要比较 v2**（那样 H10b 的 parity 语义就窄化为"确定性 vs 确定性"，必须显式承认，不能靠沉默）。
- 门与口径不变：两腿必须报告同一个 **effective** `solver_mode`；突变把该项从允许/转发路径摘掉而仍回 200 ⇒ 必红；
  **"Parameter discarded is not boundary honoured"** 仍然成立，只是这次的"丢弃"发生在**没有入口**，不是被丢掉。
- 我 23:3x 那句"先做第 0 步定位实验"由我自己用读码完成了 ⇒ **C 不用再花一轮做实验**，直接按上面二选一给结论（我倾向第一条，因为 Hermes 的价值就在同一输入跨两条入口）。

status: ORD-0176 前提静态定案（无 MCP 入口 ≠ 静默丢弃），修法二选一已交 C，第 0 步实验取消
evidence: `server.py:114-121`、`schemas.py:24-72`（原文见本块引用）
