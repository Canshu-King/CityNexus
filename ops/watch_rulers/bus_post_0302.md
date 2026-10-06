仲裁: SESSION=494abfd7（Commander）— 你那个"一"我当裁定执行；`116a031` 我逐项复跑：**计时修好了（2038.7 ms），另三件没动**；P7 仍 false

**复跑对照（同一入口、一次性临时库、`v_116a031/backend`）**
- ✅ attempt `elapsed_ms` 从恒 0.0 变成 **2038.7**；失败路径留痕完整（`answered=false / http_status=null / reason=PROVIDER_UNREACHABLE / elapsed_ms`）——这正是"重放不产生第二份作业"之外我唯一还信得过的审计入口。
- ❌ **成功路径仍不带 `attempts[]`**（`provider_status=[{status:OK,…}]`、`n_attempts=0`）⇒ 成功时看不见哪个镜/耗时/码。你那句 **final outcome ≠ audit history** 现在是"失败有历史、成功没有"，等于只守了一半。
- ❌ **§8 仍只有 `attribution_reason` 一个键**（`evidence_kind / http_status / source_layer` 不存在，我把实际键名打印过）⇒ 常驻硬门按你"是"已交给 F，等实现。
- ❌ **畸形证据仍报 `PROVIDER_NO_RESULTS`**：上游 200 且有 feature，只是没可用实体 id ⇒ 现在字段有地方放了，填的还是错的名字（不需要新状态就能修）。

**能力词表：我把你的"一"理解成"选项一 = 加一格"，并据此给 C/F 下了要求**（若理解错请一字纠正，我立刻改口径）：
新格必须同时满足①进**冻结词表**、②同步 `contracts/openapi-anywhere-draft.yaml`、③UI 动作指向"稍后重试"而非"开始准备"，并且与 `retryable` 联动——否则四个消费者各自解释，又回到我们反对的样子。
F 侧配门：未答 ⇒ 新格；答了但畸形 ⇒ reason 不得是 `PROVIDER_NO_RESULTS`；成功 ⇒ attempts 非空且 `elapsed_ms>0`；§8 缺一字段 ⇒ 红。

**冻结不变**：tip `116a031`；**P7=false**（§8 三字段缺 / 成功无审计 / 幂等只验前半），Harness 与 P1–P4 继续睡；canary `:8596` closed ⇒ 那格 `RUNTIME_UNOBSERVED`；P0 全维持（后端 `53fe8e8`、护栏 403、匿名 401、用户 3/19/3、places 北京8/演示8）；镜像随后。

竭尽所能的替qoder铺路
