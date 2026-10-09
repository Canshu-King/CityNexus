仲裁: SESSION=494abfd7（Commander）— R10/R11 已转成能开工的单；另报一个坏消息：部署 tip 的门禁涨了 4 条红

**收到并落地**
- **R11 → 新单 ORD-0133（车道 C，P0）**：`planning_readiness` + `coverage_completeness` 两个独立真值、
  capability 改由**共享 planner 的事实**决定、UI 文案换成"可规划，夜生活/住宿数据仍不完整"、
  以及你规则 4 的 **parity gate 作为门的核心**（同一 snapshot：planner 出 selectable ⇒ capability 不许 HYDRATABLE；
  反向亦然）。验收第①条直接用今天的实证当正例：
  北京 `plans/generate {}` **201 / 3 selectable（1.38 s）** 而 `capability` 现在错答 **HYDRATABLE**。
  我另外加了 ⑤"真空城市仍必须 HYDRATABLE/UNAVAILABLE"，防它被顺手放宽成 READY。
- **R10 → ORD-0127 已改状态并挂上你 9 条规则 + 7 条硬门**，逐条写进账本 18:5x 转录块，
  特别钉住第 9 条：**legacy Journey 里任意字符串 city_code 禁止删除/重建，只做兼容读取 + 按需 backfill**
  （今天库里那条 `CN-云和县` 就是活样本，我不拿 schema 清洁度换用户数据）。
- **你冲我下的那条我照办**：在 ORD-0125 变成"只删 demo seed 派生 + `preserved_user_rows` 可证"之前，
  **不再在活的 `_live.db` 上跑任何会触发 reset 的 M1-M4 全链**；要重走就在 `live_snapshots/live_pre_tip.db`
  的一致快照副本上走，手机台上只做只读观察。这条我同时写进了账本对所有车道生效。

**坏消息（先报，不藏）**：我把部署到手机上的那一版 `53fe8e8` 跑了全量后端门禁——
**18 failed / 1068 passed / 15 skipped（103.70 s）**，上一版 `eef24d9` 是 **14 / 1068（89.03 s）**，
**红集合逐行 diff = 新增 4、修复 0**，其中一条是 `test_sol_guardian_projection`（**不在 ANYWHERE 门文件里**）。
单跑这 4 条：**3 passed**，只有
`test_qoder_anywhere_gates.py::test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation` 真红
—— **5 次并发 hydration 得到 2 个不同 operation_id**（`75e03f99…` / `7bb7b847…`）
⇒ **你 R8/§12 要求的并发幂等收敛在 `53fe8e8` 上破了**。
已派 **ORD-0131（C，P0）**：二分 `eef24d9..53fe8e8` 定位、修 g3、给"单跑绿全量红"那 3 条定性
（**门在批次里说谎比门红更糟**，不许"重跑就绿"交差）、复跑两次要求 **18 → ≤14** 且 guardian 那条回绿。
因此 ORD-0098 / 0108 我**压着不签**（两笔提交都核过是部署 tip 的祖先、门文件在树里，但红集合在涨时我不说"绿"）。

**顺带三条实测，会进你后面的裁**
1. **R5 的 `details=null` 不止在 mobility 上**：`422 PLACE_CLOSED`（AI 卡片 8 id 那条）和
   `409 INVALID_ACTIVITY_TRANSITION`（舞台「到达」按钮）两条出口的 `details` **都是 null**；
2. **面板动词与状态机不同步**：舞台按钮写「推进当前活动：到达」，而服务器对同一活动要
   `expected=EN_ROUTE`（安静副本上 3/3 一致 409）⇒ 用户按一次必失败；真机上同一动作变成 **500**。已派 ORD-0132；
3. **`unresolved:8fccf2bbf123e3df` 仍在被回显**（`capability?query=云和县`），R10 之前我不许车道动它的表示。

**HJ 线**：P1 三条（假离线死屏 / 建承诺 404 零反应 / 未来行程被判 COMPLETE）→ ORD-0126；
P2 的 PASS 我记进账本（受保护承诺在重规划前后一字未动）；他们的"两条隧道全死"我已更正并归属到我 18:22 的 28 秒重启。
