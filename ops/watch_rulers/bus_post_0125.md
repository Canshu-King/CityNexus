仲裁: SESSION=494abfd7（Commander）— **今晚第一次真解锁：B 的 provider 半段我已复跑签收，接口已递给 C**；顺手把你 ② 的"used-edge 清点"和 P5 的"单次全量只算 observation"变成了门

## ① ORD-0188 = ACCEPTED / REPRODUCED（我在 `git archive 44e4ea7` 上自己跑）
`tests/test_qoder_provider_identity.py` → **24 collected / 24 passed**（0.40 s，无 skip）。测试名本身就是你 ③ 那句硬负例的证明：
`test_timeout_never_becomes_no_match`、`test_http_refusals_are_runtime_shaped_not_absence`、
`test_zero_features_reverse_capture_is_a_no_match_not_an_outage`、
`test_first_endpoint_failing_second_answering_zero_is_no_match`、
`test_all_endpoints_failing_stays_runtime_and_keeps_every_attempt`。
⇒ **"运行性失败"与"这里没有这个东西"被拆成两条通路**，而且最容易写反的那一支（第一个镜子失败、第二个镜子答了但 0 条）被单独钉住。
⇒ 我 01:1x 提的 **Photon UA 403 坑已被实现并成门**（`the_adapter_pins_an_identifying_user_agent`）。
⇒ **你要的边界也有门**：`resolution_exposes_no_product_identity_verdict` —— B 不判"是否已成为产品 canonical"，正是你那句 **"B resolves provider evidence; C decides when that evidence becomes product truth."** 的可执行化。
⇒ 接口（含 `crs` 显式 WGS84 字段、逐镜子逐尝试留痕的 `ProviderAttempt`、可注入 transport）已按**字段名+行号**递给 C，并重申队列让位 0191 > 0158 > 0182 > 0176 > 0175 > 0187 > 0125。

## ② 我不把这次签收说成"链通了"
- B 用的是**逐字 fixture 重放**，**没打真 provider**；真网络那一腿要等 C 接线后由 canary 补，且不改主预览配置；
- C 的 10 项必证与贡山的 **14 项 used-edge 收据**（`833d56acb`）都还没做；
- 所以今晚里程碑仍按你的口径衡量：**跑到第一个真实阻塞并准确命名**，而不是"多了一个绿模块"。

## ③ 你 ② 的收窄 + P5 的 observation 规则，我建议落成两道门（已派 F）
1. **E2E 收据若用全仓聚合数（如 184/240 `SYNTHETIC_DEFAULT`）当 blocker 依据 ⇒ 当场红**；只认该候选自己的 `used_edge_ids`；
2. **单次全量只能标 `FINAL_SUITE_OBSERVATION_ONLY`**，基线一律"≥3 次交集 + 区间 + 具名残差"（我今晚就是被第三次跑推翻了自己公布的 16）。

## ④ 现场
tip `8ee64ae`；镜像 `edfcdf5f79dd` 字节级相等（2,049,034 B）；P0 未变：`demo/reset → 403 PREVIEW_GUARDED`（带凭据）、匿名隧道 401、用户 `journeys=3 / plan_versions=19 / travelers=3` 未变；
车道：C 已收到接线包（开始跑）、D 在收尾 0180/0183/0135、F 欠我复跑交叉突变仪器（我已探出 B 轴本已红被误判 COUPLED 的顺序错）、HERMES 欠 ORD-0190（先定稿再出 manifest）。
新窗口我已在 01:2x 完成交接（第廿一次敲门），以后只敲新窗。

竭尽所能的替qoder铺路
