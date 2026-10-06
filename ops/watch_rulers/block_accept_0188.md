### SESSION=494abfd7 · **ORD-0188 = ACCEPTED / REPRODUCED**（B→C 交接已可用）——关键路径从"等"变成"接线"，我已把接口原样递给 C @01:2x

`STATUS: HANDOFF-VERIFIED-BY-ME | 树 `git archive 44e4ea7` → `v_44e4ea7`（权威树 0 写）| 3.12.14、AI off、凭据清空 | 全 targeted（P5：不跑全量）|`

**我复跑**：`tests/test_qoder_provider_identity.py` → **24 tests collected / 24 passed in 0.40 s**（rc=0，无 skip）。
**测试名本身就是仲裁 ③ 那句硬负例的证明**（逐条我在意过）：
`test_timeout_never_becomes_no_match` · `test_http_refusals_are_runtime_shaped_not_absence` ·
`test_zero_features_reverse_capture_is_a_no_match_not_an_outage` ·
`test_first_endpoint_failing_second_answering_zero_is_no_match` · `test_all_endpoints_failing_stays_runtime_and_keeps_every_attempt`
⇒ **运行性失败与"没这个东西"被拆成两条通路**，且"第一个镜子失败、第二个镜子答了但 0 条 ⇒ NO_MATCH"这种最容易写反的分支被单独钉住。
我 01:1x 提的 **UA 坑已被实现并成门**：`test_the_adapter_pins_an_identifying_user_agent`（`provider_identity.py:201` 合并 `User-Agent`）。
**边界也被门守住**：`test_resolution_exposes_no_product_identity_verdict` ⇒ B 的结果里**不含**"这是否已成为产品 canonical identity"的判断，正是仲裁那句 **"B resolves provider evidence; C decides when that evidence becomes product truth."**

#### 交给 C 的确切接口（`app/integrations/discovery/provider_identity.py`，字段名照抄，不要让 C 去猜）
- `ProviderOutcome(str, Enum)` = `MATCH | AMBIGUOUS | NO_MATCH | RUNTIME_FAILURE`（`:64-68`）
- `ProviderResolution`（`:128`）字段：`outcome / query / normalized_query / candidates / attempts / retryable / reason / answered / provider_replied`
- `ProviderCanonicalCandidate`（`:97`）：`source_provider / source_entity_id / display_name / crs(=WGS84) / admin_level / country_code / admin_area / observed_at / fetched_at / raw_feature`
  ⇒ **`crs` 是显式字段**（我 20:3x 提醒过 `places` 没有 CRS 列，这里补上了，C 不必再自己假定）
- `ProviderAttempt`（`:84`）：`endpoint / answered / http_status / elapsed_ms / reason / retry_after_s / error` ⇒ **每个镜子的每次尝试都留痕**，R14 的"具名运行性失败"有依据可写
- 入口：`PhotonIdentityProvider`（`:206`），可注入 `ProviderTransport`（`:176`）/ `HttpxTransport`（`:184`）⇒ 测试不需要真出网
- 另有 `six_provider_shapes_yield_six_distinct_reason_codes` ⇒ **C 可直接把这些 reason 映射进 `attribution_reason`（R14 §8）**，不必另造词汇

#### 指挥链动作
1. 已把上述接口原文发给 C，并明确"队列让位"：`ORD-0191 > 0158 > 0182 > 0176 > 0175 > 0187 > 0125`。
2. **贡山端到端（ORD-0192）的门槛条件已满足上游部分**：B 侧可给出 typed outcome + provenance；剩下卡在 C 接线与 used-edge 收据（14 项，见 `833d56acb`）。
3. 我不因为"24/24 绿"就宣布链通：**C 的 10 项必证与 14 项 used-edge 收据还没做**；且 `test_qoder_provider_identity.py` 用的是**逐字 fixture 重放**，**没有打真 provider**——真网络那一腿要等 C 接线后由 B 的 canary 补，且不得改主预览配置。

status: ORD-0188 ACCEPTED/REPRODUCED（24/24，硬负例与 UA 与边界三样都有门）；B→C 接口已原文递 C；贡山链上游解锁，下游仍待 C 接线与 used-edge 收据
evidence: `v_44e4ea7/backend` 上 `--collect-only` 24 与 `-q` 24 passed 原样输出 · `provider_identity.py:64-206` 字段行号 · 18 个 test 名清单
