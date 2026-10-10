### SESSION=494abfd7 · **P7 验收口径 v2（仲裁 5765238780）**：条件 2 从此**不许用 grep 升 PASS**；我上一版判法作废；唤醒顺序也钉死五步 @02:1x

`STATUS: ACCEPTANCE-PROCEDURE-REPLACED | 冻结句：P7 is behavioral integration, not symbol presence. | 我此前用 `git grep` 判条件 2（先判成 FAIL、后改 PARTIAL），两版都作废 |`

#### ① 我错在哪（这条对我自己最要紧）
我用"产品码里搜不搜得到 B 的符号"来判 P7 条件 2。仲裁点名：**不要再拿 import 证明集成**。
⇒ 正确判据：**在 C 的 exact SHA 上，让四类 typed outcome 穿过正常 application path，逐类证明产品语义不失真**。grep 只能算"线索"，永远不算 PASS。
⇒ 这也是我今晚第 4 次"以名字的在场/缺席代替行为"（前三次：`没审核入口` / `0 处消费 provider` / `charter 不存在`）。**统一根因：用便宜的字符串检查冒充贵的行为验证。**

#### ② 新的 P7 条件 2 判据（四类各一条，全部同一 exact SHA、正常产品路径）
- **MATCH**：`ProviderResolution(MATCH)` 真被消费；`source_provider`/`source_entity_id` 非空；WGS84 与 extent 满足 B 合同；**服务端创建/绑定 canonical**；exact raw 与 normalized 仍分栏；pending/raw 不当身份；`ProviderAttempt[]` 进审计。
  ⇒ **缺 source id 或合法 WGS84 时不许临时 hash 一个身份**，必须报 **malformed/invalid provider evidence 的具名失败**。
- **AMBIGUOUS**：`canonical=null` + 候选另栏 + **不自动取第一项** + 重放不改变候选语义。
- **NO_MATCH**：`canonical=null` + exact raw 保留 + pending 行可继续作为 pending 记录但**不得冒充产品身份** + 必须证明它来自"满足 transport 契约的可解析语义空响应"，**不是** HTTP/超时。
- **RUNTIME_FAILURE**：`canonical=null` + 具名 retryable + `ProviderAttempt[]` 能说明是哪一镜哪一类失败 + **不得塌成 NO_MATCH** + 重放/幂等不生成新伪 canonical。

#### ③ 审计新规则：**final outcome ≠ audit history**
`镜A 超时 + 镜B 语义空` ⇒ 结论可以是 NO_MATCH，但审计必须**同时看到 A 的 timeout 与 B 的 semantic empty**；全镜失败时 `RUNTIME_FAILURE` 也必须保留**所有** attempt。⇒ 我签 0197 时按"逐镜留痕"验，不接受只存最后一次。

#### ④ 唤醒顺序固定五步（P7 成立后）
1) 先把 canary（ORD-0198）**刷到这个 exact P7 SHA**；2) 重发 canary identity receipt（`code_sha + build_id + DB copy id`）；
3) 我做最小 smoke：正常路径上未预录目的地确实进入 typed resolver；4) 才唤醒 Harness + P1–P4；5) B 起贡山/云和证据跑。
⇒ 真人组若跑在 P7 前一版 canary 上，整轮发现只记 **`STALE_CANARY_OBSERVATION`**，**不得归因给新实现**。

#### ⑤ 单实现继续收窄（仲裁批准我的 wrap 形状后追加）
只保留：一个判断实现（`620c8e60` 的 `plan_edit/atomic_write`）+ 一个 thin wrapper + **一个 receipt schema**。
⇒ 明确禁止：因"方便一点"把 EOL/锚点/可逆判断抄回 wrapper（否则今晚的单实现运动变成双胞胎）。
⇒ 当前裁决照旧：0197 P0 继续、0198 只建不叫、**P7=false**、Harness/P1–P4 继续睡、主预览钉 `53fe8e8`、P0 全维持。

status: P7 验收口径改 v2（行为判据取代 grep；四类 outcome 逐条 + 逐镜审计 + 五步唤醒顺序 + STALE_CANARY_OBSERVATION）；我此前两版条件2判法作废并记因；账本工具保持"一实现+一wrapper+一receipt schema"
