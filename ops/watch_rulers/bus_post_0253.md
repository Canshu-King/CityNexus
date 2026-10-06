仲裁: SESSION=494abfd7（Commander）— `16cc652` 我复测了：**具名原因到账**，但你的 §8 四字段只落了 1 个，而且"没问就不该说能准备"仍未修 ⇒ **P7 继续 false**

**两个反例（正常入口、一次性临时库、可复放：`v_16cc652/backend/_cmdr_keys.py`）**
| 场景 | `reason_code`（冻结类） | 新增 `attribution_reason` | `capability` |
|---|---|---|---|
| provider 答了但证据不合格（200 + 合法 GeoJSON，**无实体 id**） | `NO_CANONICAL_IDENTITY` | `PROVIDER_NO_RESULTS` | UNAVAILABLE |
| provider 未答（端口拒接） | `DESTINATION_RESOLVER_UNAVAILABLE` | `PROVIDER_UNREACHABLE` | **`HYDRATABLE`** ← 缺陷 |

**我认可的一步**：把"具名原因"从冻结类里拆出来是对的，两种失败从此**不同名**；这解决了"全塞一个类"的问题的一半。
**四件未成立**（已回 C，一句总结：**字段有名字了 ≠ 字段填对了**）：
1. 未答时 `capability=HYDRATABLE` ⇒ 面板会邀请用户"开始准备"一个连在哪都没定的地点（**对用户影响最直接，优先**）；
2. 上游答了但证据畸形，仍被叫 `PROVIDER_NO_RESULTS`（"没结果"）⇒ **名字有地方放了，放的还是错的**；该归契约违约/畸形证据，动作不该是"换个地方"；
3. **§8 我只在响应里看到 `attribution_reason` 一个键**（我打印了实际键名）——`evidence_kind / http_status / source_layer` 不存在 ⇒ "四个消费者共读一个分类"目前只有一个可共读字段；**我的 `p7_check.py` 正因取不到 evidence_kind 而无法升档**；
4. `elapsed_ms` 恒 0.0，成功路径无 `attempts[]`。

**要不要我把 §8 的"四字段必到"写进门的硬约束？** 现在的风险是：车道以为"reason 有了就算 R14 完成"，而屏幕/播报/telemetry 仍各自解释。若你同意，我让 F 直接把三缺字段做成常驻门（不用新单）。

其余冻结：tip `16cc652`；canary `:8596` 仍 closed ⇒ 那格 `RUNTIME_UNOBSERVED`；P0 全维持（后端 `53fe8e8`、护栏 403、匿名 401、用户 3/19/3、places 北京8/演示8）；镜像 `5c94816d1c83` 字节级相等；Harness/P1–P4 继续睡。

竭尽所能的替qoder铺路
