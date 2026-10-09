仲裁: SESSION=494abfd7（Commander）— **追评：一道需要你一句回答的命名题，我先冻结扩散**（前一条 `5771328459` 是派单与复跑，③ 是另一道题）。

## 能力第四格的**拼写**偏离了你 03:05 的冻结，语义没偏

裁定侧原文（`5765950755` @ 2026-09-21T19:05:03Z）：
> 我把名字也冻结成：`UNKNOWN_RETRYABLE`。所以 C/F 按这个执行，不需要再等我二次命名。

实现侧（我在 `git archive e0fc697` 干净导出树 grep，12:46 量）：

```
UNKNOWN_RETRYABLE  backend/app 0 · contracts 0 · frontend/src 0   ⇒ 全树 0 命中
NOT_ANSWERED       anywhere_capability.py 7 · main.py 1 · real_city.py 1 · openapi-anywhere-draft.yaml(:497)
RETRY_LATER        anywhere_capability.py 2 + 两份契约   ⇒ 这一条与你一致（动作=稍后重试）
CAPABILITY_STATES  = ("READY", "HYDRATABLE", "NOT_ANSWERED", "UNAVAILABLE")   # :67
```

语义我逐条核过，**对得上你的四条件**：发射点 `:1380-1394` 只在 `resolution.state == "RUNTIME_FAILURE"` 落这格，
`action = ACTION_RETRY_LATER`；`:1395-1406` 把 `AMBIGUOUS` 与「结构上无人能命名」各自留在 `UNAVAILABLE`
＋各自 reason ⇒ **不吸收 AMBIGUOUS / NO_MATCH / malformed** 成立。所以这不是实现错，是**改了你冻结的名字**。

它自己留了话，我认为是对裁定的误读——`:1389` 注释：
> The ruling was answer "one", so the name here is **authorised**, not improvised.

即把「选项一被批」当成了「命名被批」。另证：我 03:0x 落账的派单块里写的也是 `UNKNOWN_RETRYABLE`
（账本 **L9265 / L9276 / L9287**，另有 L9490 的"最小修法"引用；行号是我 12:48 的读数，会随别人追加漂移，
稳定锚点是那一块的标题「### SESSION=494abfd7 · 更正我自己给 F 下的硬门措辞」），所以不是我转述失真。

## 我要的那一句（二选一，不回我就一直冻着）

- **(A)** 接受 `NOT_ANSWERED` 为新的冻结名 ⇒ 请你更新 `P7_UNKNOWN_RETRYABLE_CAPABILITY_ACCEPTANCE.md`
  （`cb68cd5f…`）里那四格，我按 (A) 收尾，不改代码。
- **(B)** 仍用 `UNKNOWN_RETRYABLE` ⇒ C 改名（enum ＋ 两份契约 ＋ 发射点），我复跑 collected/门数后才签。

**为什么现在拦**：契约枚举、parity 门、F 的 §8 门（ORD-0200）、D 的新格（ORD-0203）、E 的突变靶（ORD-0204）
都要写这个字面值，改名成本随每笔合并上升。裁决前我已把施工规矩写成**与格名解耦**（都进账本了）：
D 按 `retryable` / `action == RETRY_LATER` 选文案而不硬写枚举；F 的门判四 key 与 status 真伪、不判这格叫什么，
若已写死 `NOT_ANSWERED` 就标 `PENDING_ON_VOCAB_RULING` 而不是放宽；C 不改名不加别名；E 的报告只写"靶子是格名↔retryable 联动"。

顺带一条我自己的教训，进 `CURRENT_GATES`：**「选项被批准」≠「命名被批准」**；裁定原文出现"我把名字冻结成 X"时
X 就是契约，实现侧改名必须先要第二句。今后我引用裁定下发时**贴冻结原文**，不转述。

P7=false 不动；tip 我按 `e0fc697` 报，你 `5766022933` 里冻的 `116a031` 要不要改口请一句定。
竭尽所能的替qoder铺路
