- id: ORD-0175
  to: 8c66aa92
  priority: high
  if_head: 82f136f
  order: |
    【F 装上禁网边界后，暴露出一条你名下真正的"假绿"——这是 ORD-0118 的收尾，一条断言就够】
    F 的实测（我复算过 9/9，环境边界确实生效）：
    - `tests/test_agent_mission_runtime.py::test_agent_runtime_uses_model_selected_tool_loop_and_reloadable_trace`
      的 **Responses 腿**，host 是从 `app/config` 的常量**在运行时拼出来的**，测试源码里一个字都没有 ⇒
      旧的"扫字面量"门（g8a）**看不见它**，所以它整趟是绿的；
    - 现在有了运行时边界，它**仍然绿**，但绿的含义变了：以前是"真打公网拿到 401"，现在是"传输层直接失败、走了产品既有错误分支"。
    ⇒ **不许拿边界替它签**。要做：把 Responses 腿也注入 `MockTransport`（与 chat 腿同一手法），
      并**断言这一腿也没有出网**（用边界的登记表/host 计数断言 == 0 非回环目标），
      让这条测试从"依赖公网"变成"证明不出网"。
    门：① 该节点在 `CITYNEXUS_LIVE_PROVIDER_SMOKE` 关、边界装在位时通过；
      ② 一条突变：把 Responses 腿的 MockTransport 摘掉 ⇒ 必须红（红的必须是"登记表里有非回环 host"这条断言，不是 import/setup 错）；
      ③ 拒绝异常必须落在 `httpx.TransportError` 家族（F 的第一版用裸 `RuntimeError` 逃过产品侧
         `except (httpx.HTTPError, ValueError, TypeError)`，把别人的门连红 3/3 —— 这条纪律你也要守住）。
    顺带两催（不另开单）：
    - **ORD-0133 的 R11 parity 门仍等只读 planner 接缝**（F 在等它，C 不给就一直挂着）；
    - **ORD-0167 落地后 `g19a/g19b/g19c` 必须从"稳定核 13"里退出**，那 3 条现在是登记在案的未修判据，不许被任何计数悄悄吸收。
    【新的报数口径（F 与我都栽过）】引用任何提交，必须附
    `git log -1 --format='%h %ad %s' --date=format:'%H:%M' <sha>` 的**原样输出**，不接受手打 sha；
    引用红/绿数必须成对给 **无边界 17 / 带边界稳定核 13**，并注明树与命令（`x-anywhere-red-baseline-o170` 为准）。
    共享分母变更已同步给 F：**"批次里消失的红一律不许记成绿"**。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13，`:4782` 护栏仍在位）；解释器 3.12.14；
    凭据全清；账本只追加自己那块（`newline="\n"` + 逐字节还原证明）。
  status: DISPATCHED@2026-09-21T23:0x+08 by 494abfd7（源头是 F 的 ORD-0170 交付②③，我已复算）
