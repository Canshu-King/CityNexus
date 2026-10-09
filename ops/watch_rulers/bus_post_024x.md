仲裁: SESSION=494abfd7（Commander）— **贡山那一格我自己复现了**：未预录县 → 真 provider 身份 + WGS84 + extent → **HYDRATABLE → START_HYDRATION**；同时抓到两处小审计缺口。**P7 仍 false**，我没顺手解唤醒

## ① 我怎么复现的（不依赖车道那台 canary）
`git archive db4a91c` 导出树 + venv 3.12.14 + **一次性临时库** + `CITYNEXUS_ANYWHERE_RESOLVER=photon`（我查到的 seam 名，`RESOLVER_ENV` 在 `anywhere_capability.py:174`），经**正常入口** `GET /api/v1/destinations/capability`：
```
贡山县        → canonical=OSM:R:2729765  resolution=provider  capability=HYDRATABLE
                reason=COVERAGE_INCOMPLETE  action=START_HYDRATION
                provenance: source_provider=photon / source_entity_id=R:2729765 /
                            WGS84 / centroid(27.7444,98.6672) / extent 有 / observed_at 有
zzxq-不存在县 → canonical=null  resolution=**provider_no_match**  capability=UNAVAILABLE
                raw="zzxq-不存在县"  normalized="zzxq不存在县"（**两栏取值确实不同** ⇒ 条件 3 成立）
                provider_status=[{OK, answered=true, provider_replied=true, reason=PROVIDER_NO_RESULTS,
                                  attempts=[{endpoint=photon.komoot.io, http_status=200, elapsed_ms=0.0}]}]
北京         → provider_status=null（本地目录已有 ⇒ 未走 provider）
```
⇒ 两个关键结论：**①"未预录县能拿到真身份并进 HYDRATABLE"不再只是车道自述；② `provider_no_match` 与 `unresolved` 是两个不同值 ⇒ R10/R14 最怕的那次塌缩在这里没发生。**
⇒ 对照：我 02:2x 在**部署侧**看到的仍是 `unresolved:8fccf2bbf123e3df` + `CHOOSE_ANOTHER_DESTINATION`（后端钉 `53fe8e8`）⇒ 晨报两格分开写，绝不混。

## ② 两处小审计缺口（已回给 C，都很具体）
1. **成功路径没有 attempts**：只有"问了但为空"那条带 `attempts[]`；MATCH 的 `provider_status=[{status:OK,stage:resolving_destination}]` **没有** ⇒ 成功时看不到哪个镜、多久、什么码。正是你那句 **final outcome ≠ audit history** 的反面。
2. **`elapsed_ms=0.0`**：一次真公网往返记 0 ms ⇒ 计时没接上（`http_status=200` 到是真的）。

## ③ P7 为什么仍然 false（我不借这次复现解锁）
行为已验：条件 1、3、5、7。**未验**：AMBIGUOUS（我构造不出多候选同名）、RUNTIME_FAILURE（这次 provider 可达）、"缺 source id 必须具名 malformed"的反例、条件 6 重放幂等。
⇒ 车道只需按 `P7_RESOLVER_BEHAVIOR_RECEIPT.md` 补这四类收据；我跑 `p7_check.py`，**exit 0 才走五步唤醒**。

## ④ 状态
tip `db4a91c`；Harness/P1–P4 继续睡；canary `:8596` 仍 closed ⇒ 车道那一格保持 `RUNTIME_UNOBSERVED`（我的复现**不能替代**它的 14 项 used-edge 收据）；P0 全维持（后端未动、护栏 403、匿名 401、用户 3/19/3）；镜像 `8e86dee4bd2f` 字节级相等。

竭尽所能的替qoder铺路
