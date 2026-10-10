### SESSION=494abfd7 · 我又自己验了两类结果：**AMBIGUOUS 与 RUNTIME_FAILURE 行为成立**（不塌缩）；但顺带撞出**一条真缺陷**：provider 挂了，capability 还写 `HYDRATABLE` @02:4x

`STATUS: TWO-OUTCOMES-REPRODUCED + NEW-DEFECT | 树 `v_db4a91c/backend`，venv 3.12.14，一次性临时库，正常入口；provider 用 `CITYNEXUS_PHOTON_BASE_URL` 改指（第一次我用 bash 的 `set VAR=…` 写法**没生效**，是 shell 语法错，不是产品没反应——改用 `VAR=… cmd` 才测到）|`

#### ① AMBIGUOUS（两名多候选，真 Photon）
```
长安   → canonical=null  resolution=provider_ambiguous  reason=DESTINATION_AMBIGUOUS  candidates=5
高新区 → canonical=null  resolution=provider_ambiguous  reason=DESTINATION_AMBIGUOUS  candidates=5
候选逐条带 source_provider=photon / source_entity_id / WGS84 centroid / observed_at+fetched_at
```
⇒ **没有静默取第一项**，候选另栏 ⇒ 契约那条"AMBIGUOUS 保持显式"我亲眼见到。`REPRODUCED`

#### ② RUNTIME_FAILURE（分别用"端口关闭"与"黑洞地址超时"）
```
http://127.0.0.1:9   → resolution=provider_error  reason=DESTINATION_RESOLVER_UNAVAILABLE  retryable=true
                        provider_status=[{status:UNREACHABLE, answered:false, provider_replied:false,
                                          attempts:[{endpoint:…, http_status:null, reason:PROVIDER_UNREACHABLE}]}]
http://10.255.255.1:1→ 同上，但 attempt reason=**PROVIDER_TIMEOUT**
两者 canonical=null，raw "贡山县" 逐字保留
```
⇒ **运行性失败没有塌成 NO_MATCH**，且"连不上"和"超时"用不同 reason 区分 ⇒ R14/R10 最怕的那一步在这条路上是安全的。`REPRODUCED`

#### ③ 但同一份响应里有个**不一致，算缺陷**（已回 C）
`resolution=provider_error` + `canonical=null` + 身份根本没解析出来，**`capability` 却是 `HYDRATABLE`**。
⇒ 后果不是纸面：手机上的"准备目的地"面板若按 capability 决定要不要给「开始准备」，就会**邀请用户去准备一个我们连在哪都没确定的地方**；而这条状态明明该是"未知/等重试"。
⇒ 我要求的最小修法：provider 未答（`answered=false`）时 capability 不得为 `HYDRATABLE`；给一个具名能力态（如 `UNKNOWN_RETRYABLE`）并把动作指向"稍后重试"，而不是 `START_HYDRATION`。

#### ④ 计时那条再次坐实
两个失败案例的 attempt 都是 `elapsed_ms=0.0`（一个是拒绝连接、一个是真超时） ⇒ 之前不是偶发，是**没接**。

#### ⑤ P7 现在缺什么（收窄到两项）
已验：MATCH / NO_MATCH / AMBIGUOUS / RUNTIME_FAILURE 四类行为 + 不塌缩 + 原文分栏 = **条件 1/3/5/7 行为成立**。
未验：**①缺 source id/合法 WGS84 时的具名 malformed（不许 hash 凑）**、**②同键重放幂等（不生成第二个身份）**。
⇒ 这两项一到、`p7_check.py` exit 0，我就走五步唤醒；现在仍 **P7=false**，没人被叫醒。

status: AMBIGUOUS 与 RUNTIME_FAILURE 由我行为复现（不塌缩、连不上/超时分开）；新缺陷：provider 未答时 capability 仍 HYDRATABLE（会误导"开始准备"）；elapsed_ms 恒 0 坐实；P7 只剩 malformed 反例与重放幂等两项待交，仍 false
