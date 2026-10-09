- id: ORD-0136
  to: 8ccd71d8
  priority: high
  if_head: 53fe8e8
  order: |
    接 ORD-0118 的结论落两件仓库内的活（外部的 egress 绊线按我 19:1x 裁定**不进默认套件**，
    改由 Harness 线每轮实验各跑一次并附出网节点清单；理由：没网的 CI 必须还能跑）：
    ① 把 `tests/test_agent_mission_runtime.py:106` 的 stub 补全：chat-completions **与** responses
      两个客户端都要 stub（机制你已定位：`main.py:1056 → main.py:10154 →
      integrations/ai/semantic_compiler.py:315 → integrations/ai/responses.py:306` 走的是 responses 那条）；
    ② 加一条**不需要网络的"零出网"门**：默认套件运行期间对外部主机的
      `getaddrinfo` / `socket.connect` 调用次数必须为 **0**；
      本地回环与测试内 fake transport 要**显式白名单**，不许按类别整类放行（那就是把门变成装饰）。
    验收：① 先红后绿（今天 `test_agent_runtime_uses_model_selected_tool_loop_and_reloadable_trace` 就是红基线，
      实测对端 **401**，节点自己绿 ⇒ "绿着出网"正是门的靶子）；② 一条杀得掉的突变
      （把 responses 客户端的 stub 摘掉，门必须红）；③ 断言里要能区分"出网"与"被 stub 的假传输"，
      贴出两次的节点计数；④ 全量红集合逐行 diff **只允许少不允许多**（现在部署 tip 是 18 条红，见 ORD-0131）。
    禁令：不许 `skip`/`deselect` 该节点、不许给它挂网络标记绕过、不许把 `api.deepseek.com` 加进任何 allow-list、
    不许在测试里用真凭据（本轮对端 401 已是"占位 key"的证据，保持）。
  status: DISPATCHED@2026-09-21T19:1x+08 by 494abfd7（排在 ORD-0131 之后）
