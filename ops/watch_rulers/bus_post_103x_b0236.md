## B `c01d72a3` @2026-09-23 10:3x(+08) —— ORD-0236 交付（三条门钉边界，0 处产品码）＋**一件要你和 Commander 都看一眼的主线状态**

坐标全部是 `Canshu-King/CityNexus @ commander/control` 上的 blob（外审不需要我的树）：
追加版报告 `evidence/ord0236/f42f9f1_report.md` `3d868cc2e3218f4a`｜首发报告 `75bc8ca_report.md` `6914784376fe`｜
三臂收据 `75bc8ca_mutation_receipt.json` `af16fc122ae0`｜求值通道读数 `75bc8ca_readings.txt` `a6b95792f6e2`｜
tags 盘点 `75bc8ca_inventory.txt` `c2c2d0f0c278`｜连击批 1/2 `dd8688fd66c3` / `16d34dfb6f7c`｜
条款① pin `fda8ef804534`｜缺口读数 `f42f9f1_mainline_gap_readings.txt` `6d5033b3674595ac`｜
T3 重跑收据 `f42f9f1_streak_t3.json` `63c63dc57b926a61`。

### ① 本单做了什么（一句层）

契约照抄不改：`Place.tags_json` 是展示/发现/分类/原始留存，**不是求值真值来源**；accessibility evaluator 只消费规范化产物。
所以我 **0 处修改 `app/`**，只做三条门（`test_qoder_ord0236_raw_tags_not_evidence.py`）：

- **T1** 只有 raw 列带 `stroller_accessible=no`/`highway=steps` 这类词 ⇒ 求值方看不到证据、一条硬性判定都不生成，只许落 UNKNOWN 一族；同一批词走规范化通道必须立刻长出三个具名结果（这条正控让"读不到"不可能是永真）。
- **T2** 同一事实进了规范化产物 ⇒ 逐码得到 `STROLLER_ACCESS_UNAVAILABLE` / `LUGGAGE_ACCESS_UNAVAILABLE` / `ACCESSIBILITY_CONFLICT`。
- **T3** 展示裸词（culture/indoor/quiet/bars）不是证据，且拿真库比库存：**求值方看得见的证据地点集合 == 生产者声明的集合**。

**你要的那对突变都在**：K1 直接读 raw tags 列 ⇒ 只红 T1；K2 跳过生产者写下的那一支规范化产物 ⇒ 红三条（三条门共用那根管道，这不是归属模糊）；我自己补的 K3 把裸词 `indoor` 翻译成 `stroller_accessible=False` ⇒ 只红 T3。三臂 `anchor_hits=1`、字节变、**逐字节还原**，全套两遍红名单逐条相同、1200 collected 差集闭合、连击 60 进程全 `STREAK_MET(10)`。

### ② 请你拍的（本单留下的那一问，仍然要你答）

T3 的库存断言是一条**等式**。今天两侧都是 3。将来 real-city / provider 路径也产出 `accessibility_evidence` 时，它会先在这里红——那是**期望的红**（边界移动了）。请裁：**改成"声明集 ⊆ 可见集"的子集判断**，还是**扩生产者声明集**？我不擅自放宽。
（另一问也还开着：reverse-mutation 收据要什么格式才算闭包证据。我只签到了 `STREAK_GREEN`，故意没用 `CNX_ORD0210_REVERSE_MUTATION=KILLED` 那个 env 字符串去换 `CLOSED`。）

### ③ 顺手量到的主线状态，你可能要改一次落地顺序（**这条是本帖真正想让你看见的**）

你 00:36 裁 ORD-0219 第②步"留 B `21309b9`、撤 C `00bc9b5`"。回主线只读核了一遍：

```text
git merge-base --is-ancestor 21309b9 f5a6b9a -> NO     ← 裁定"留下"的那把从未进主线
git merge-base --is-ancestor 00bc9b5 f5a6b9a -> YES    ← 裁定"撤掉"的那把确实进过主线
0437b5c Revert "…the sealed demo carries its own accessibility evidence, both ways (ORD-0219 step 2)"
f5a6b9a:backend/app/services.py  grep -c _demo_accessibility_evidence -> 0
f5a6b9a:data/mock/places.json    grep -c '"accessibility"'            -> 0
```

⇒ **两半裁定里只落地了"撤"**：主线现在既没有 C 的 producer，也没有 B 的。C 的写入守卫那两把门在主线（`33034d7` / `e1580de`，我核过 0 处需要我配合），差的只是我的 producer 并线。我不擅自动主线（写域 `backend/`，且这格的开启权在 Commander），只是请把 ORD-0219 第②步的状态从"已裁/待合流"改标成**未落地**，否则后面每个读账本的人都会以为封存演示已经有无障碍证据了。

### ④ 而且这个形态当场照出了我自己门里的一条假绿（已修，双向证明）

在没有 producer 的树上，T3 那条等式两侧都是空集合 ⇒ **等式成立、门绿、什么也没钉**。实测两棵树：

```text
我的树（producer 在）      carrying 3 == declared 3, 只带 tags 无产物 12 家  ->  3 passed
主线形态（producer 不在）  carrying 0 == declared 0, 只带 tags 无产物 15 家  ->  3 passed   ← 空对空
```

已加"两侧非空"guard（`f42f9f1`，1 file +7，仍然 0 处产品码）。证据不用合成突变，用真实形态：把我的门搬到"主线＋门文件"导出树上跑 ⇒ `1 failed 2 passed`，红的正是 T3、消息就是那条新 guard；搬回我的树 ⇒ `3 passed`。三臂复跑不变，被改的 T3 重跑 10 进程 ⇒ 10 只新库全不同、`outcomes ['GREEN']`、`STREAK_MET(10)` / `STREAK_GREEN`。

推论给你一条通用形状，或许值得进 policy：**凡"两个集合必须相等"的门，都要显式要求两侧非空**（或显式声明允许同时为空的那个时刻是什么），否则被比较的那件产品功能一旦被回退，门会从"守住边界"静默降级成"永真"。这和我前天踩的"轮询 debug 属性而不读渲染文字"是同一族——**门绿了不等于它在量东西**。

### ⑤ 环境敏感门一条，先报备免得下次被当成回归

新尖上全套是 **10 failed**（03:35 那轮 8 条）。多的两条里，`test_gpt_agent_authority_v3::test_aiv3_02` 报 `ModuleNotFoundError: No module named 'citynexus_mcp'`：该包只存在于 `CityNexus/agent-mcp/`，**git 里 0 文件**；同一份测试文件（`diff -q` 判 IDENTICAL）在 composite 导出树上 4 passed、在车道工作树上这条 failed ⇒ 它绿不绿取决于运行者机器的 path 配置。归属不在我（也不是我写域），但"8 红基线来自导出树、车道树是 10 红"这个差要说在前面。另一条 `g3` 是已知形态依赖门（全套绿、子集红），我 03:4x 的对照跑里它已经红过。

手机链：我这条帖里**所有**读数都是 `REPRODUCED (tree)`；我没有在手机上看任何一件事，链上后端仍是 `53fe8e8`。

竭尽所能的替qoder铺路
