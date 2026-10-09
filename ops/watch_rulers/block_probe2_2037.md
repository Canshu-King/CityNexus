### commander 亲测 补枪 @2026-09-21 20:3x —— 第二枪打在**贡山**上，结果把仲裁排序的前提问住了：**贡山在这棵树上同样是 `unresolved:`**，冷链在**第 0 步**就断，不是断在 Overpass

同一脚本、同一副本库、同一实时模式（`live_checks/dod4_gongshan.txt`）：
- `capability?query=贡山独龙族怒族自治县` → `canonical_destination_id=`**`unresolved:aeb41cef3b84ddbb`**、
  `destination_resolution=unresolved`、`capability=UNAVAILABLE`、`reason_code=NO_CANONICAL_IDENTITY`；
- `POST /catalog-hydrations` → **202 / 0.02 s**（受理仍然快，R8 那半达标）；
- **3 秒后**作业就是 `state=UNAVAILABLE phase=DISCOVERING_POIS outcome=NO_REGISTERED_SOURCE`，`provider_status=null`；
- 库里 `places` 仍只有 `CNX-DEMO 8`、`provider_key` 仍只有 `mock-city` ⇒ **零真 provider 实体**。

**结论（我能证的部分）**：在这棵 `e9efec6` 上，**两个不同的县都拿不到 canonical identity**，
而 `outcome` 是 `NO_REGISTERED_SOURCE` 而不是 `REAL_CITY_DISABLED`
⇒ 我**不是**没开实时（`CITYNEXUS_REAL_CITY_ENABLED=true`、`_MODE=live` 都设了），
是**能力评估/解析这一步根本没走到 resolver**，或者走到了但结果被丢。
**#4 的堵点在 Step 0（原文→canonical），不在 Step 2（Overpass 冷发现）**——这和我 20:36 那块里的推测一致，现在两例都成立。

**我要更正/请求确认的一件事（不甩锅）**：仲裁 5760530753 建议"贡山先做 CASE3，因为 Photon canonical identity + extent 已实测成立"。
那句"实测成立"是 **ORD-0099/0109 时期对 provider 的直接探测**成立的；
但**产品内的解析路径今天实测不成立**（两例都是 `unresolved:`）。
所以"贡山能绕开 R10 污染"这个前提，在今天的树上不成立 —— 请先修 Step 0，再谈 CASE3/CASE4。

**顺带三条实现事实（给 C/F 省时间）**：
① `capability` 与 `catalog-hydrations` **都各自算了一遍 identity**，两处都给 hash ⇒ 修要一次修两处，别只修表面；
② 作业表 `stay_generation_operations` 的列是 **`id`**（响应体里叫 `operation_id`）——契约对差（ORD-0123）记一笔；
③ 我的量具错已撤回：**`UNAVAILABLE` 就是终态**，作业没有"永不结束"，是**它结束得太早、而没人会把这句话演给人看**。
