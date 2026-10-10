### commander 裁定 @2026-09-21 19:1x —— 收 ORD-0118 / ORD-0106；外呼绊线归属我定了；另外**我叙述里的车道字母串了三位，以此表为准**

**1) ORD-0118 ACCEPTED**（你 18:56 那块）。理由：`g8a` 从"有一条实时外呼混进默认套件"升级成了**一个具名节点 + 一条机制**：
`tests/test_agent_mission_runtime.py::test_agent_runtime_uses_model_selected_tool_loop_and_reloadable_trace`
→ `POST https://api.deepseek.com/responses`，实测对端 **401**（占位 key ⇒ 无费用、无凭据外泄），
而**该节点自己是绿的**；产品栈 `main.py:1056 → main.py:10154 → integrations/ai/semantic_compiler.py:315 → integrations/ai/responses.py:306`，
机制是 `tests/test_agent_mission_runtime.py:106` **只 stub 了 chat-completions 客户端**。
`test_qoder_catalog_hydration.py:388` 在同一次运行里**零条出网记录** ⇒ 它是形状违规、今天不真出网。
**门一个字没放宽、没 skip、没 deselect**，分母 **14 failed / 1062 passed / 15 skipped / 131.21 s** 与我自己的两轮一致
（我在部署 tip `53fe8e8` 上是 **18 / 1068**，多出的 4 条就是我派回给你的 ORD-0131）。

**2) 外呼绊线归属——我定，不再悬着**：
- **仓库内**（你的活，**新单 ORD-0136，P1**）：把那个节点的 stub 补成**两个客户端都 stub**
  （chat-completions **与** responses），并加一条**不需要网络的"零出网"门**：
  断言默认套件运行期间 `getaddrinfo`/`socket.connect` 对**外部主机**的调用次数为 **0**，
  本地回环与测试内 fake transport 白名单要显式列出、不许整类放行。先红后绿 + 一条杀得掉的突变。
- **仓库外常驻**（**不进默认套件**）：`D:/moodle/_qoder_f_run/egress_tripwire.py` 保持为**可选审计工具**，
  由 **Harness 线（d291c9dc，ORD-0128）每轮实验各跑一次**并把"出网节点清单"附在报告里。
  理由：**没有网络的 CI 必须还能跑**——把网络审计变成默认硬门，等于让离线机器全线红，
  那是用一种不诚实换另一种不诚实。**要防的是"默认套件偷偷出网"，不是"我们必须联网才能验收"。**

**3) ORD-0106 ACCEPTED（五轮全交）**：`c421d68`/`9283195`（契约 + 七门）→ `3ff11e7`/`351dd31`（几何/失败码/数量）
→ `31b2a4f`（矩阵单位 + cells≤100 预检 + 直线距离，§9 N≤20）→ `4922f6f`（TTL 读侧 + 发现范围 + 分类塌缩）
→ `eef24d9`（G19 北京 8 行却被"北京市"问成零覆盖）。附件 `0.94-annex.4` 的
`x-matrix-bound`、`x-server-truth-fields`（provider_budget / discovery_area）与 **12 条红门台账（kind/owner/cause/rerun）**
我收下，直接当 ORD-0131/0133 的起点。**注意**：你 G19 那三条红与我 18:4x 的 18 条红**不重合**，
所以 ORD-0131 的验收里我加了"两次全量红集合逐行 diff 是否相同"这一条，别拿单跑绿交差。

**4) 我自己的错，写死在这儿**：这几轮我在**叙述/消息里**把车道字母用串了三位（单子里的 `to:` 会话 id 都是对的，没有派错人）：

| 会话 id | 正确车道 | 我误称过 |
| --- | --- | --- |
| `8c66aa92` | **C 后端** | E |
| `8ccd71d8` | **F 契约与门禁** | C |
| `c01d72a3` | **B 外部数据实测** | F |
| `dc19d662` | **E 红队** | （正确） |
| `e345b9d6` | **D 前端** | （正确） |
| `d291c9dc` / `1a986a24` 等 | Harness / HJ-P1…P4 | （正确） |

**从现在起以 ORDERS 条目的 `to:` 会话 id 为准**，谁因为字母说"这不是我的单"我都算违令。
ORD-0131/0133 是 F（`8ccd71d8`）的，ORD-0132 是 C（`8c66aa92`）的，ORD-0127 是 B（`c01d72a3`）的。
