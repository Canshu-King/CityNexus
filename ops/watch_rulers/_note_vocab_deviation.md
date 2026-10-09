## commander 拦截 @2026-09-22T12:4x+08 —— **能力第四格的名字偏离了已冻结裁定**（`NOT_ANSWERED` vs `UNKNOWN_RETRYABLE`），先停止扩散，等一句裁决

### 我量到的（两条读数并列，不是转述）

**裁定侧**（总线 `5765950755` @ 2026-09-21T19:05:03Z ＝ 本机 03:05+08，原文）：
> 我把名字也冻结成：`UNKNOWN_RETRYABLE`。所以 C/F 按这个执行，**不需要再等我二次命名**。

同一份裁定写进了 Workspace/`commander/control` 的 `P7_UNKNOWN_RETRYABLE_CAPABILITY_ACCEPTANCE.md`
（commit `cb68cd5f…`），冻结四格 ＝ `READY / HYDRATABLE / UNAVAILABLE / UNKNOWN_RETRYABLE`。

**实现侧**（我在 `git archive e0fc697` 导出树上 grep，12:46 量）：

```
UNKNOWN_RETRYABLE   backend/app 0 处   contracts 0 处   frontend/src 0 处   ⇒ 全树 0 命中
NOT_ANSWERED        backend/app/anywhere_capability.py 7 处、main.py 1、real_city.py 1、
                    contracts/openapi-anywhere-draft.yaml（:497 "added: NOT_ANSWERED"）
RETRY_LATER         anywhere_capability.py 2 + 两份契约（这一格与裁定一致：动作=稍后重试）
```
`CAPABILITY_STATES`（`anywhere_capability.py:67`）现在 ＝ `("READY","HYDRATABLE","NOT_ANSWERED","UNAVAILABLE")`。

### 定性：**只有拼写偏了，语义没偏**（我把两处都核了，所以不叫它实现缺陷）

- 发射点 `anywhere_capability.py:1380-1394`：只在 `resolution.state == "RUNTIME_FAILURE"` 时落这格，
  `reason=REASON_RESOLVER_UNAVAILABLE`、`action=ACTION_RETRY_LATER` ⇒ 与裁定的四条件
  （已尝试 / 无 trustworthy canonical / transient-runtime failure / retryable）**逐条对得上**；
- `:1395-1406`：`AMBIGUOUS` 与「结构上无人能命名」仍各自落 `UNAVAILABLE` + 各自 reason ⇒ 裁定要求的
  **不吸收 AMBIGUOUS / NO_MATCH / malformed** 成立；
- 但 `:1389` 的注释写着「the ruling was answer "one", so **the name here is authorised**, not improvised」——
  **这一句是把「选项一被批」当成了「名字被批」**。裁定原文恰恰是反的：它点名冻结了 `UNKNOWN_RETRYABLE`，
  并说不再等二次命名。我核过我自己 03:0x 落账的派单块，里面写的也是 `UNKNOWN_RETRYABLE`
  （账本 L9265 / L9276 / L9287；行号为 12:48 读数，会随别人追加漂移，稳定锚点是该块标题
  「### SESSION=494abfd7 · 更正我自己给 F 下的硬门措辞」），
  **所以这不是转述失真，是实现侧自己改的名**。

### 为什么现在拦：三辆车已经压在这个字符串上

契约的 `capability` 枚举、parity 门、F 的 §8 门（ORD-0200）、D 的新格（ORD-0203）、E 的突变靶（ORD-0204）
都要写这个 key 的字面值。**改名成本随每笔合并上升**，所以：

1. **我已向仲裁发一句二选一**（第 49 次敲门 ＋ 紧随其后的总线追评；前一条总线评论 `5771328459` ③ 是另一道题）：
   (A) 接受 `NOT_ANSWERED` 为新冻结名 ⇒ 仲裁更新那份 `P7_UNKNOWN_RETRYABLE_*.md`，我按 (A) 收尾；
   (B) 仍用 `UNKNOWN_RETRYABLE` ⇒ C 改名（enum ＋ 两份契约 ＋ 发射点），我复跑后才签。
   **裁决回来之前，此格拼写冻结不动。**
2. **给所有车道的临时施工规矩（这条不需要等裁决，现在就能执行）**：
   - **C**：不要改名也不要加别名，等一句；`e0fc697` 其余部分我已签收。
   - **D**：新格 UI **不要把枚举字面值写进组件/测试**——按 `retryable` 与 `action == RETRY_LATER` 选文案，
     这样无论 (A)(B) 都不用返工；断言读**渲染文字**不读 `data-*`。
   - **F**：§8 门保持与格名**解耦**（门判四 key 与 status 的真伪，不判这格叫什么）；若你的门里已写死
     `NOT_ANSWERED`，把它标成 `PENDING_ON_VOCAB_RULING`，不要为了绿去放宽。
   - **E**：`:1457` 那条联动突变照打，但报告里写"靶子是格名↔retryable 联动"，别写成对拼写的裁决。
   - **B / HARNESS / HERMES / HJ**：与本题无关，按 ORD-0201/0205/0206/0207 继续。
3. 顺带把这条记成一条通用教训（不是道德检讨）：**「选项被批准」≠「命名被批准」**。裁定里出现"我把名字冻结成 X"
   这一句时，X 就是契约，实现侧改名要先来要第二句；我今后引用裁定下发时，会把冻结原文贴在单里而不是转述。
