### commander 亲测 @2026-09-21 20:3x —— 我自己先把 #4 那条冷链跑了一遍（**副本库、实时模式**），第一枪打在云和县上，结果正好替仲裁的排序作了证

**读数**（`live_checks/dod4_hydrate_probe.py`，库＝`live_snapshots/dod4_hydrate.db`，`_live.db` 未被触碰；
env：`CITYNEXUS_REAL_CITY_ENABLED=true`、`CITYNEXUS_REAL_CITY_MODE=live`、`TIMEOUT=25`、AI/凭据全清、解释器 3.12.14）
- `capability?query=云和县` → `canonical_destination_id=unresolved:8fccf2bbf123e3df`、`capability=UNAVAILABLE`、
  `reason_code=NO_CANONICAL_IDENTITY`、`recommended_action=CHOOSE_ANOTHER_DESTINATION`；
- `POST /api/v1/catalog-hydrations {"query":"云和县"}` → **202 / 0.03 s**，带 `fingerprint`、
  `catalog_schema_version=catalog-v1`、`readiness_policy_version=…`、`retry_after_ms=1000`、`reused=false`
  ⇒ **R8 的"受理 ≤1s、不绑前台"这一半是达标的**；
- 但作业之后**每 3 秒读一次、连读 76 次（228 s）**始终是
  `state=UNAVAILABLE phase=DISCOVERING_POIS outcome=NO_REGISTERED_SOURCE provider_status=null`；
- 库里 `places` 仍然只有 `CNX-DEMO 8`、`provider_key` 只有 `mock-city` ⇒ **一个真 provider 实体都没长出来**。

**我的判读（写清楚哪些是我证的、哪些是推的）**
- 证到的：**身份未解析 ⇒ 冷链根本没有"注册源"可走**，于是它以 `NO_REGISTERED_SOURCE` 诚实拒绝——
  这是 R10（哈希不是身份）与 #4（真数据长出来）之间**直接的因果链**，不是我原先猜的"provider 打不通"。
- 推的（**待验，别当结论**）：注册源与 canonical id 绑死 ⇒ **R10 不修，贡山以外的大部分县都进不了冷链**；
  但贡山有实测成立的 canonical identity + extent（B 的 ORD-0092/0109 数据），所以仲裁"先贡山、云和县留 CASE4"的排序是对的。
- **我这次的量具错也记一下**：我第一版把 `UNAVAILABLE` 不当终态，傻等了 228 秒——
  它其实就是**终态的诚实拒绝**。所以"作业永不结束"这条**不成立，我撤回**；成立的是"拒绝得早、但 UI 层没人会看到这句话"。
- 顺手暴露的一条实现坑（给 C/F）：`stay_generation_operations` **没有 `operation_id` 列**（我 SQL 直接炸），
  说明响应体里的 `operation_id` 与库内列名不同源——契约对差（ORD-0123）请把它记进去。

**下一步**：同一脚本第二枪打**贡山独龙族怒族自治县**（`live_checks/dod4_gongshan.txt`），
把它当作 B（ORD-0148）的 pre-flight：如果贡山也拒绝，我就把"注册源/身份"这一环直接派回 F/C，
而不是让 B 一个案例一个案例地撞墙。
