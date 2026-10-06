- id: ORD-0131
  to: 8ccd71d8
  priority: P0-critical
  if_head: 53fe8e8
  order: |
    **部署到手机上的那个 tip 变红了 4 条**，我亲测两轮，分母如下（同一棵树 `53fe8e8`、同一解释器
    `CityNexus/.venv` 3.12.14、AI 关闭 + key 置空、`-p no:cacheprovider`，日志 `raw/suite_53fe8e8.txt`）：
    - 全量：**18 failed / 1068 passed / 15 skipped（103.70 s）**；上一轮 `eef24d9` 是 **14 / 1068 / 15（89.03 s）**；
    - 逐行 diff 红集合：**新增 4、修复 0**（不守"只允许少不允许多"）：
      1. `test_qoder_anywhere_gates.py::test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation`
      2. `test_qoder_catalog_hydration.py::test_a_job_stopped_before_its_worker_starts_still_closes_itself`
      3. `test_qoder_catalog_hydration.py::test_nothing_leaves_the_process_while_the_deterministic_plane_answers`
      4. `test_sol_guardian_projection.py::test_a_preventive_run_carries_the_fields_the_panel_selects_on`
      **（第 4 条不在 ANYWHERE 门文件里 ⇒ 它不是"新门还没绿"，是别的区域被碰到）**
    - **单跑那 4 条**：3 passed / **只有 ① 真红**，读数：5 次并发 hydration 拿到 **2 个不同 operation_id**
      （`75e03f99…`, `7bb7b847…`）⇒ **幂等收敛破了**，两个 operation 会各灌一份目录。
    要你做的，按顺序：
    ① 二分 `eef24d9..53fe8e8`（本地树，**不许 push**）定位是哪一笔让 ① 变红，给"红→绿"的 sha 与失败断言原文；
    ② 修 ①：同一 destination 的并发 hydration 必须**收敛到一个** nonterminal operation（0110/0109 已有的 durable 指纹口径），
      409/202 的分布也要如实报（现在是 5 次里有 1 次 409 被测试过滤掉再数 id）；
    ③ 把 ②③④ 定性清楚：**单跑绿、全量红**说明它们与前面的测试**共享状态/库**——
      要么各自建自己的库，要么显式声明依赖顺序；**门在批次里说谎比门红更糟**，
      这条必须给结论，不许用"重跑就绿"交差；
    ④ 复跑全量两次，报"两次红集合是否逐行相同"，且要求 **18 → ≤14**、且 `test_sol_guardian_projection` 回绿。
    禁令：不许 skip、不许放宽断言、不许把 ① 的期望从"1 个 operation"改成"1 或 2 个"。
  status: DISPATCHED@2026-09-21T18:4x+08 by 494abfd7

- id: ORD-0132
  to: 8c66aa92
  priority: P0-critical
  if_head: 53fe8e8
  order: |
    HJ-P2（d4b04a0f）真机交两条，我在 `53fe8e8` + **活的库的一致快照**上量过，两件事都成立、但要分开修：
    **A. 舞台那颗「推进当前活动：到达」按钮与服务器的状态机不同步**
    - 面板给的动词是"到达"（我在 18:28 的新包上仍然看到按钮 `推进当前活动：到达`）；
    - 服务器对同一活动 `3a58c470…`（状态 `PLANNED`，`start_at 2026-10-10T09:00+08`）
      三次一致回答 **409 `INVALID_ACTIVITY_TRANSITION:PLANNED->ARRIVED; expected=EN_ROUTE`**（安静副本、无并发，
      `live_checks/arrive_repro.py`，探针只写副本）；
    - ⇒ **按一次必然失败**：面板该给"出发/前往(EN_ROUTE)"，或者按钮文案由服务器投影决定。
      这条是**真机可演示性**缺陷（老师 demo 第二步就会点它），不是并发问题。
      顺带：这条 409 的 `details` 又是 **null**（R5 已定性，别再新增 null 的出口）。
    **B. 同一动作在真机预览上是 500，不是 409**
    - 旧 `:8693` 访问日志里 `POST /journeys/22222222/activities/3a58c470…/arrive → 500` **恰好 3 次**，
      同刻 `GET …/experience → 500` **3 次**，`booking-slots → 500` 1 次；新进程（tip）日志里
      `database is locked` **9 次**、500 **0 次**；
    - ⇒ 与 **ORD-0112 / ORD-0057** 同族（读时写 + 锁竞争把 500 当默认回答）。
      要求照 0112 的口径收口：**任何锁竞争不得变成 500**，必须是具名可重试的 409/429 + 屏幕有下一步；
      `GET /experience` 的读时写要么去掉，要么失败不影响读。
    **C. 「我的」屏当着用户说假话**（P2 原话）：已确认的预订存在时，屏幕写"已确认的预订：还没有"。
      给一条门：钱包/我的屏的"有没有"必须来自同一投影，不得各自数各自的。
    验收：① 面板动词与状态机一致（按一次就成功，或按钮写"出发"）；② 锁竞争下无 500（并发打它，报分母）；
    ③ 「我的」屏不再假空态；④ 全量红集合逐行 diff **只允许少不允许多**（现在 18 条红，见 ORD-0131）。
    排在 ORD-0111 之后、ORD-0125 之前（B 与 0112 合做可以，但两条验收都要各自交数）。
  status: DISPATCHED@2026-09-21T18:4x+08 by 494abfd7（HJ-P2 的 PASS 结论也记：受保护承诺在重规划前后一字未动）
