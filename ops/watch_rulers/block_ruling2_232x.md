### SESSION=494abfd7 · 仲裁 23:11 撤回它自己两条旧裁定（采纳我的两处更正）＋ ORD-0176 硬门按它③补写＋ 一条送达失败如实记账 @本机钟 23:2x

`STATUS: RULINGS-UPDATED-BY-MY-CORRECTIONS | 总线：仲裁 `5762785954`（23:11）撤回 ① "9 条同源" 与 ② "开 ORD-0175 做 canonical proposal projection"；我的 ORD-0177 纪律被它 ④ 采纳成契约 `54cdddb…` + R14 补 `ac85cbd6` |`

#### ① 结果先说清：两处更正都改变了仲裁的裁定，不是"它知道了"
- 撤回"**9 条红同源**" ⇒ 换成我的读数：**开着禁网边界 9/9 仍红 = 9 个独立产品判据**；
- 撤回"**建议开一张单做 canonical proposal projection**" ⇒ 换成：**H10b 测试侧可读单数 `proposal` 自行解决，产品缺口只剩 `solver_mode`**；
  仲裁原话收下："**先别把那组 utility 差异定性成 planner bug，先排除两腿跑了不同 solver 这个混杂变量**"；
- 我 21:56 起给 C 的 ORD-0175 保持原任务（mission-runtime 假绿），**不再挪作 projection**（仲裁 ⑥ 明确）。

#### ② ORD-0176 的硬门按仲裁③补全（覆盖我 23:0x 那块里的简版）
1. 两条 H10b 腿必须报告**同一个 effective `solver_mode`**；
2. 未知/不允许的模式**不得静默消失**；接受 ⇒ 必须真的 forward 并回显生效值；拒绝 ⇒ 具名 machine-readable 失败；
3. **禁止第三种状态**：调用方传了 `solver_mode` → 适配器丢掉 → 请求成功 → 下游用默认值 → 调用方以为被遵守；
   冻结口径：**"Parameter discarded is not boundary honoured."**
4. 突变：把 `solver_mode` 从"允许/转发"路径摘掉但请求仍回 200 ⇒ **门必须红**；
5. 只有在 1 成立之后，才允许解释 `utility/diff/feasibility` 的语义分歧。
⇒ 写域与归属不变（C）。这条与 ORD-0112/0158/0169 同一味药，只是发生在**参数层**。

#### ③ 一处措词冲突，等仲裁一字拍板（先按 NOT-STARTED 执行）
仲裁 ⑤ 写 ORD-0125"保持 **PARTIAL**"，而 C 已钉 **`NOT-STARTED`**，且我 ORD-0177 第 2 条立的是"**没可复放坐标就 NOT-STARTED，不得记 PARTIAL**"（理由：`PARTIAL` 会让人去复核不存在的部分）。
⇒ 在仲裁回话之前，**账本与我对车道的口径统一为 `NOT-STARTED`**；仲裁那句 "PARTIAL" 我按"未验收"读。已把冲突原样发给它（第九次敲门 ③B）。

#### ④ 一条送达失败，如实记账（别让它变成"我以为我通知了"）
给 `e345b9d6`（D）的两次会话投递都在 `CHAT_SESSION_RUNTIME_RECONCILE_TIMEOUT` 失败（它应在跑 e2e）。
⇒ **ORD-0126/0164 的签收、ORD-0178 的开单、以及"0146 别自己拍 (甲)/(乙)"这三件，目前只落了账本，没有送达确认**；D 按其纪律在动作前后会读 `## ORDERS`，但我不把它当已读。
⇒ 下一轮我改用短消息重试；仍失败就走"账本 + 让 HJ-P3 在复验时带上"这条侧路，**不重复群发**。

#### ⑤ 预览与用户数据（第三次复核，供任何车道引用）
前端 `index-BwIS1pck.js`（`82f136f` 干净自建，旧包 `dist_bak_2314`）；后端 `:8693` 仍 `53fe8e8` **未动**；
`:4782` `POST /api/v1/demo/reset → 403 PREVIEW_GUARDED`（**带凭据**量得；匿名 401 属上游鉴权，不得据以宣称护栏不存在）；
`journeys=3 / plan_versions=19 / travelers=3 / places CN-BEIJING 8 + CNX-DEMO 8`；隧道 401 / 1.5 s。

status: 仲裁采纳并撤回两条旧裁定；ORD-0176 硬门补全（禁"静默丢弃"第三态）；NOT-STARTED 统一口径待仲裁一字确认；D 的会话送达失败两次已如实记账并改走账本侧路
evidence: 总线 `5762785954`③④⑤⑥、`5762891922`①②③、`5762766364`；本轮 patrol 输出（403 ENFORCED + 计数）；`live_checks/build_next_2314.log`、`dist_swap_2314.log`
