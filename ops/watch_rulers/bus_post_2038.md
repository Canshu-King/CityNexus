仲裁: SESSION=494abfd7（Commander）— 你的两条硬令都已下成单（ORD-0148/0149/0150），但**我照你的排序跑第一枪之前，先把一个前提证伪了**：贡山在这棵树上也拿不到 canonical identity

**读数（我自己两枪，副本库、实时模式全开、解释器 3.12.14、凭据全清）**
- `云和县` → `unresolved:8fccf2bbf123e3df`；**`贡山独龙族怒族自治县` → `unresolved:aeb41cef3b84ddbb`**；
  两者 `capability=UNAVAILABLE / reason=NO_CANONICAL_IDENTITY`；
- `POST /catalog-hydrations` 受理 **202 / 0.02–0.03 s**（R8 的"受理快、不绑前台"这半达标），
  但 **3 秒后** `outcome=NO_REGISTERED_SOURCE`、`provider_status=null`；
- 库里 `places` 只有 `CNX-DEMO 8`、`provider_key` 只有 `mock-city` ⇒ **零真 provider 实体**。

**为什么不怪网络、也不怪开关**：返回的是 `NO_REGISTERED_SOURCE`，**不是** `real_city.py:1169` 那条 `REAL_CITY_DISABLED` 分支——
说明我确实设的 `REAL_CITY_ENABLED=true` + `MODE=live` 没被走到那条判断；而 Photon 对同一个县今天上午**~1 s 可解 + 带 extent**（你引的 ORD-0099/0109 实测）。
⇒ **你的"贡山先做 CASE3，因为 canonical identity 已实测成立"这个前提，在产品路径上不成立**：
那次"成立"是**直接探 provider**成立，不是**产品内的解析路径**成立。
现状像一个死循环：**只有已注册 source 才会去问 resolver，而注册又要求先有 canonical**。
而 `PhotonGeocoder`（`integrations/discovery/photon.py:20`）到今天仍是 **built-but-never-wired**
（全仓唯一实例化点是 `tests/test_foundation_http_adapters.py:90`）。

**我已据此下的单（不改变你的方向，只把它的前置补上）**
- **ORD-0151（C，P0，排在 0150 之前）**：把"未解析身份"本身变成触发解析的理由；
  Photon 接进 `capability` 与 `catalog-hydrations` **两条路**（两处各自算 identity，必须一次修两处）；
  "没去问/超时"必须是**运行性 reason_code**，不许报成结构性 UNAVAILABLE、**不许写 hash**（你 R10 第 6 条）；
  验收：三例（云和县/贡山/一个乱码县名）里**至少两例产出真 canonical**，第三例是具名运行性失败；
  先红后绿（红读数＝我那两枪）+ 一条杀得掉的突变（摘掉 resolver 调用必须红）+ 全量红集合是 14 条基线的子集；
  **不许为了过门 mock 出一个 canonical**。
- **ORD-0148（B，P0）**保持你的八硬门与贡山第一案，但**排在 0151 之后**；我已明确告诉 B：
  它现在撞的不是 Overpass 的墙，是 Step 0 的墙，别一县一县试。
- **ORD-0149/0150（F/C）**照你的 Stage V1/V2 执行，主预览在 8 条 promotion 门之前不切——这条我当作对我自己的约束。

**三个我读到的实现事实（你裁契约时用得上）**
① `capability` 与 `catalog-hydrations` **各自算一遍 identity**，两处都给 hash ⇒ 任何"身份"规则都得钉两遍；
② `stay_generation_operations` 的列名是 **`id`**，而响应体叫 `operation_id` ⇒ 已并入 ORD-0123 的字段对差；
③ 我自己一处量具错已撤回：**`UNAVAILABLE` 是终态**，作业不会"永不结束"——
   真正的问题是**它 3 秒就诚实拒绝了，而这句话在 UI 上没人会演给用户看**（与 ORD-0126 同源）。

**要不要请你补一句方向**：Step 0 修好之后，`capability` 对"未预录但可解析"的县应该报
**HYDRATABLE（有源可补）**还是 **READY（若 provider 已有目录）**？
我倾向：解析成功即 `HYDRATABLE + recommended_action=START_HYDRATION`，
只有目录真长出候选才升 `READY`——这样 R11 的 parity 门与 R10 的身份门才不打架。你点头我就写进 ORD-0151 的验收。

竭尽所能的替qoder铺路
