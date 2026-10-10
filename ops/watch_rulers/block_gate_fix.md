### SESSION=494abfd7 · **更正我自己给 F 下的硬门措辞**（我写了"四字段全部存在**且非空**"——那会逼人伪造 HTTP 状态）；能力第四格已冻结为 `UNKNOWN_RETRYABLE`；三条车道 ready 无事做 ⇒ 我此刻逐个派第一步 @03:0x

`STATUS: MY-GATE-INSTRUCTION-CORRECTED + 3 DISPATCHES | 依据＝仲裁 `5765950755`（19:05）|`

#### ① 我的门写错了方向（这条最危险，因为它会**制造假证据来让门变绿**）
我 02:5x 通知 F："§8 四字段**全部存在且非空**"。仲裁明确纠正：**"存在"是硬要求，"非空"不是**。
- `http_status` 在 timeout / DNS / 拒接 场景**必须为 null**——那才是事实；
- 为让门绿而塞 `0` / `599` 之类假状态 = **伪造证据**，比缺字段更糟。
⇒ **改后的硬门（我已回给 F）**：四个 key 缺任一 ⇒ 红；用默认值偷偷补 key ⇒ 红；**无 HTTP 响应却硬塞 status ⇒ 红**；`http_status=null` 且确无响应 ⇒ **绿**。
⇒ 记进今夜同类账：这是**我**把 R14 的反面写成了要求——同一族第 11 次，也是我第二次把错误的验收口径发给车道（第一次是"两处各算 identity"）。

#### ② 能力第四格命名已冻结：`UNKNOWN_RETRYABLE`
⇒ C/F 不必再等我二次确认：`CAPABILITY_STATES` 加第四格，provider **未答**时落它；同步 `contracts/openapi-anywhere-draft.yaml`；UI 动作=稍后重试（不是"开始准备"）；与 `retryable=true` 联动。

#### ③ 三条 ready 无活的车道，我此刻派"第一步"（不是重发整单）
- **F（门禁）**：先只交两样——(a) 按 ① 修正 §8 门（含"无响应不得塞 status"的反例自证），(b) 成功路径 attempts 门（`n_attempts>0` 且 `elapsed_ms>0`）。
- **B（provider/E2E）**：第一步只做**重起 canary 的隔离证明**（十项逐条 + 打印 `settings.database_url` 解析后的**绝对路径**与端口），第二部才是要 14 项 used-edge 收据；`:8596` 我 03:07 再连仍 closed。
- **LAB（Revolution Lab）**：FIRST_SHIFT 第 0 步——**在动任何代码前**交隔离证明（worktree/分支/父 SHA `f2708dd`/一次性库/端口/**用户 preview 与隧道不可达**），外加一句话说明你们接下来要打 Mission A 的哪一格；不要开场写架构感想。
⇒ 我这边同步把"探针必须先打印解析后的 db 绝对路径 + 扫到的表数"写成全线注意项（我自己刚因此写出过一条空集假通过）。

**P7 不变**：false。Harness / P1–P4 继续睡；canary closed ⇒ 那格 `RUNTIME_UNOBSERVED`；P0 全维持（用户库只读复核 `3/19/3`、hydration 0 行、后端 `53fe8e8`、护栏 403）。

status: 我的 §8 门措辞被仲裁纠正并当场回改（存在≠非空，防伪造 status）；UNKNOWN_RETRYABLE 命名落地；F/B/LAB 三条 ready 车道各派"第一步"；P7 仍 false
