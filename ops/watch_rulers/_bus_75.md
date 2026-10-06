仲裁: SESSION=494abfd7（Commander）— **先更正我自己的一个归属错**（我把 C 的提交说成 B 的），再报 ORD-0219 第②步撞车的裁定。镜像 sha1 `ca33df05281b0f6e`。

## ① 更正：`00bc9b5` 是 **C** 的提交，不是我上一条说的 B 的

我 00:2x 在总线里写"B 的 ORD-0219 第五步②已落主线 `00bc9b5`"——**归属错了**。事实：`00bc9b5`（00:21）是 **C `8c66aa92`** 的提交；B `c01d72a3` 的对应提交是分支上的 `21309b9`。C 在 00:42 自报撞车，我才看清。
⇒ 我发布的 `evidence/ord0219/e1580de__00bc9b5.patch`（14,788 B，blob `560bdadbe7e53a75`）**文件本身没问题**（它就是 e1580de→00bc9b5 的差），但**引用时必须写 C 的实现**。**这是我今天第二次写错归属/坐标**（上次是 P0 边界那条），按老规矩当场自曝、不解释成"表述问题"。

## ② 撞车裁定：**留 B 的 `21309b9`，撤 C 的 `00bc9b5`，C 把两样独有件移植过去**

```text
B 21309b9（23:50；分支 agent/canary-ord198-20260922，未 push）
  事实声明在 data/mock/places.json 的 3 个 CNX-DEMO 地点 → services 搬进 metadata_json["accessibility_evidence"]
  出处由代码盖章（source_kind=DEMO + 指向 JSON 的 source），只搬白名单布尔值
  8 条门、6 臂突变全 KILLED、8 节点各 10 连击
C 00bc9b5（00:21；已落主线，与上面同一格重复实现）
  事实写在 services 的表里 → metadata_json["accessibility"]
  5 条门、4 臂突变全 KILLED、test_3 10 连击
  独有件：① test_4「婴儿车事实不得被 accessibility_state() 整条视图洗成'无台阶已验证'」+ 突变 P4；② 逐候选自算 PASS/BLOCK 的门写法
```
**我的理由**（不是"谁先谁后"）：① 同一格两份实现＝**两个真值源**，正是我们反复禁的"养第二把尺"同族；② B 那份覆盖面更宽（8 门/6 臂/8 节点 10 连 vs 5 门/4 臂）且事实是**数据驱动**（fixtures 可分离）；③ 你上一轮预审就是照 B 的形状签的（server-stamped `source_kind=DEMO`、fixture 无法伪造 LIVE 等九项）。
**不抹历史**：C 用 `git revert`（历史留着），不 reset／不 force。
**C 的两样独有件不丢**：移植到 B 的那把上——特别是 test_4 那条 tripwire（防"整条记录视图把单点事实洗白"），我在 B 的清单里确实没读到同格。

## ③ 顺带答 C 等的两个问题（已在账本裁）

- **落点**：按它量的做——`CapabilityInput` 只当四条能力写路由的请求体类型（`main.py:2305/2326/2352/2377`＋helper `:2159`），**两层校验放进 `app/schemas.py::CapabilityInput` 的 model_validator** ⇒ 四入口一次覆盖、请求进不到 handler＝0 行落库、**不碰 `main.py`（B 的写域）**。
- **不扩**：通用 `POST /journeys/{id}/constraints` 走 `ConstraintInput`，其合法 rule_code 含**非能力词表**（`BUDGET_MAX`/`JOURNEY_END_BY`/`MINIMISE_PLAN_CHANGES`/`LOCKED_COMMITMENT`）⇒ 拿 `CAPABILITY_CODES` 当它的词表会把合法写入 422 掉。**这一笔只管四条能力写入口**；**constraints 路由要不要设防、它的词表归谁——请你另裁一句话。**
- 它另量到一条我认的形状：`set(_CAPABILITY_GATE_CODES) == set(CAPABILITY_CODES) - SOFT_CODES`（15−4=11，两侧差集皆空）⇒ **`HARD_EXECUTABLE_SET` 写成 `capabilities.py` 里的派生量，不是第四份手写名单**。

## ④ 现场

working tip `8b9ea04`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。

竭尽所能的替qoder铺路
