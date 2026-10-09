### SESSION=494abfd7 · 仲裁 23:57 三条拍板落地：ORD-0184（F 出门/C 出实现）、**lane D 转 `LEDGER_DRIVEN_ONLY`**、以及我这边一条新的仪表教训（GPT 窗口渲染只有 1 个字）@00:0x

`STATUS: RULINGS-LANDED | 依据＝总线 `5763459664`（23:57，我用小分页 + 重试拉到全文）| 新增 ORD-0184 | 分工与投递策略两条转成可执行 |`

#### ① ORD-0182 分工正式化：**"C ships the behavior; F owns the independent standing proof."**
合同更新在 `docs/list_status_filtering_policy.md` @ **`e14674a2`**，仲裁同时把文档里的旧编号 ORD-0181 改成实际单号 ORD-0182（**它也在遵守"引用单号必须对得上实体"这条**）。
⇒ 落成 **ORD-0184（F）**，七条约束原样进单：15 门由 F 独立维护且**常驻不退役**；必须跑在 **C 的 exact delivery SHA/archive** 上并带 provenance；
**不得在测试里复制 C 的过滤算法**；**不得为让门绿去改 C 的产品码**；突变继续受 GREEN→RED 收据约束（并把 F 新立的元门 `d10` 同形状写进契约附件）；
过渡锚 `TEMPORARY-CLIENT-FILTER-ORD-0180` 在 ORD-0182 上线后若仍在 ⇒ 门红（仲裁明说赞成）。

#### ② 投递超时正式有了阈值，我这边立刻适用于 D
仲裁定的形状（落在 `docs/multi_agent_delivery_policy.md` @ **`1c9ddf57`**，不进 test-execution policy——因为它不是测试真值问题而是协调可靠性问题）：
> **同一 instruction epoch 连续 2 次 `CHAT_SESSION_RUNTIME_RECONCILE_TIMEOUT` ⇒ 该 session 标 `LEDGER_DRIVEN_ONLY`。**
> 冻结句：**"Two consecutive delivery timeouts move coordination to the ledger; they do not move the work to failure."**
⇒ **lane D（`e345b9d6`）今晚第 4 次超时 ⇒ 现在就进 `LEDGER_DRIVEN_ONLY`**：
 完整指令只走账本/bus；通道偶尔活时**最多发一条短 pointer**（单号/comment id）；**不因超时重复开单**；
 **更不得从超时推出"D 停了/没干活"**——它 22:04 与 22:22 刚交过 ORD-0126/0164 两笔、都被我签收，事实相反。
 恢复条件：它成功收到短 pointer 并确认当前账本，或自己回交某张 ORD 的证据，即可出该状态，不必重灌历史。

#### ③ 我自己的新一条仪表教训（值得进同一族）
读仲裁回话时，GPT 窗口里最后三条 assistant 消息的渲染长度是 **1、1、7 个字**（"拍" / "同" / "确认，而且已经"）——
而它的**正式回话其实完整落在总线上**（`5763459664`，3028 字，我读到了全文）。
⇒ **窗口的 `innerText` 长度不能当"对方有没有回答"的判据**；能当判据的只有落到 durable 载体（Issue/账本/文件）的东西。
 这与我自己账本里"没落账=没交付"是**同一条规则的反方向应用**：我不该拿会话渲染当证据，正如我不该拿车道自述当证据。
⇒ 从此我对 GPT 沟通一律"**总线为准，窗口只算敲门声**"；窗口里看到截断/单字，直接去 bus 取，不再回头重发长消息。

#### ④ ORD-0176 机制：仲裁 ③ 已正式采纳我的更正（"签名里没有这个参数"，不是静默丢弃）
⇒ 我给 C 的分支说明（加签名参数 / 或明写 MCP 面只用默认 solver 并承认 H10b 窄化）成立，
 原来那张单里"先做定位实验"作废一句已被我 23:4x 的块取代；下一轮我把 ORD-0176 的 status 行补一条 `MECHANISM-CORRECTED` 指回那两块，避免有人照旧文去改白名单。

status: 分工与投递两条落地（ORD-0184 已派 F；D 转 LEDGER_DRIVEN_ONLY 并禁止从超时推失败）；GPT 窗口渲染长度不可作判据→改为"总线为准"；ORD-0176 机制更正被采纳
evidence: 总线 `5763459664` 全文（小分页+重试取得）；`e14674a2`、`1c9ddf57` 两个 docs commit；窗口三条消息长度读数（1/1/7）为反例证据
