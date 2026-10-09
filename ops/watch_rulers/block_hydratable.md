### SESSION=494abfd7 · **我自己复现了"第一次真 HYDRATABLE"**（不是车道报的那次，是我在隔离实例上打真 Photon 得到的）；同时抓到两处**很小但要修**的审计缺口 @02:4x

`STATUS: HYDRATABLE-REPRODUCED-BY-ME + 2 AUDIT FINDINGS | 树 `git archive db4a91c` → `v_db4a91c/backend`，venv **3.12.14**，一次性临时库，`CITYNEXUS_ANYWHERE_RESOLVER=photon`，AI off、凭据清空；正常入口 `GET /api/v1/destinations/capability` |`

#### ① 我亲眼看到的（原样）
```
q=贡山县            → canonical=OSM:R:2729765   resolution=provider   capability=HYDRATABLE
                       reason=COVERAGE_INCOMPLETE  action=START_HYDRATION
                       provenance: source_provider=photon, source_entity_id=R:2729765,
                                   coordinate_system=WGS84, centroid=(27.7444, 98.6672),
                                   extent=98.132,27.495 – 98.918,28.397, observed_at=…
                       raw="贡山县" / normalized="贡山县" / fidelity=EXACT_RAW
q=zzxq-不存在县      → canonical=null  resolution=provider_no_match  capability=UNAVAILABLE
                       raw="zzxq-不存在县" normalized="zzxq不存在县"（**两栏确实不同**）fidelity=EXACT_RAW
                       provider_status=[{OK, stage=resolving_destination, reason=PROVIDER_NO_RESULTS,
                                         answered=true, provider_replied=true,
                                         attempts=[{endpoint=https://photon.komoot.io/api/, answered=true,
                                                    http_status=200, elapsed_ms=0.0}]}]
q=北京              → provider_status=null（本地目录已含 ⇒ 未走 provider）
```
⇒ **今晚 A 里程碑的"链跑到真实产品语义"这一环，我这边成立**：**未预录县 → 真 provider 身份 + WGS84 + extent → HYDRATABLE → START_HYDRATION**，且**没有 hash 冒充**（对比我 02:2x 在部署侧看到的 `unresolved:8fccf2bbf123e3df`）。
⇒ **`provider_no_match` 与 `unresolved` 是两个不同的 resolution 值** ⇒ R10/R14 最怕的那次塌缩，在这里**没有发生**。

#### ② 两处审计缺口（小而具体，已回给 C）
1. **成功路径没有 attempts**：`q=贡山县` 的 `provider_status=[{status:OK, stage:resolving_destination}]` —— **没有 `attempts` 数组**；只有"问了但为空"那条才有。⇒ 正是仲裁那句 **"final outcome ≠ audit history"** 的反面：成功时我看不到是哪个镜、多少毫秒、什么 HTTP 答的。**修法**：成功分支同样填 `attempts[]`。
2. **`elapsed_ms=0.0`**：一次真打 photon.komoot.io 的往返被记成 0 ms ⇒ 计时没接上（`http_status=200/answered=true` 倒是真的）。⇒ 修法：把 client 侧耗时写进 attempt。

#### ③ P7 判定（诚实版）
- 行为已验：条件 1（未预录原文走正常入口）/ 3（raw 与 normalized 分栏且取值不同）/ 5（provider_no_match 保持 null）/ 7（无 pending/raw 冒充身份，`destination_pending_key` 另存）⇒ **PASS(行为)**
- 未验：AMBIGUOUS（我没能自然构造出多候选同名）、RUNTIME_FAILURE（我这次 provider 可达）、条件 4 的"缺 source id 必须具名 malformed"（需反例）、条件 6（重放幂等需 durable operation 层复跑）
⇒ **P7 仍 false，Harness / P1–P4 继续睡**；但**贡山那一格从 `RUNTIME_UNOBSERVED` 升为 `REPRODUCED(我的隔离实例)`** —— 注意：这**不等于**车道那台 canary 被复现，两件事分开写。

status: 我在隔离实例上复现"未预录县→真 provider 身份+WGS84+extent→HYDRATABLE→START_HYDRATION"，并确认 provider_no_match/unresolved 不塌缩；抓到两处审计缺口（成功路径缺 attempts、elapsed_ms=0.0）；P7 仍 false（AMBIGUOUS/RUNTIME/malformed/幂等未验），贡山格升 REPRODUCED(自有实例)
