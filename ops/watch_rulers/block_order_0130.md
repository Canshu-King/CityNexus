- id: ORD-0130
  to: CMDR-SCOUT（指挥官派出的只读子代理，不占任何车道写域）
  priority: high
  if_head: 53fe8e8
  order: |
    **总线 5758628612（17:56）裁：ORD-0124 拆两阶段**，本单就是拆出来的 **0124-A — OSS UI Donor Scout**。
    与 0124 的关系：**侦察归本单（只读、立即并行）**；**移植（0124-B）HELD**，
    等车道 D 把手机端 P0/P1 可演示性收口后，由**当时的 UI owner（D）**逐组件 port。
    **禁令（仲裁原话）**：不拥有 production frontend 文件、不改 `package.json`、不建 UI commit、
    **不抢 D**（"不能同时写" ≠ "不能同时想"）。
    四个 donor（顺序即优先级）：`stvlynn/OpenTrip`、`clawnify/OpenTripPlanner`、
    `shusingh/michi-planner`、`Serkanbyx/travel-planner`。**AGPL 系只看交互思想，禁止拷代码。**
    必交可执行映射表（列已由仲裁指定，一列不许少）：
    donor repo / exact source path / license / CityNexus target screen / 依赖 /
    状态与 data assumptions / 是否依赖 donor backend / port difficulty / 要改哪些 CityNexus 文件 /
    与 truth contracts 的冲突点 / 360·390·412 移动端风险 / map gesture·safe-area·bottom-nav·sheet collision /
    判决（直接移植 / 借结构重写 / 只参考 / 拒绝）。每个 blocker 只给 1~3 个最高价值候选，不做目录堆砌。
    **必须 source-level**：至少打开仲裁点名的真实文件（OpenTrip: MobileAgentSheet / MobileItinerarySheet /
    MobilePlannerHeader / MobileStopDetailSheet / MobileTabBar / TripMapView / ScheduleBoard /
    ReservationsBoard / BudgetBoard / DayPills / StopCard / PlaceSearch），其余三仓读对应
    itinerary / map / onboarding / DnD / sheet 文件。**README 与截图不算数。**
    交付文件名固定：`UI_DONOR_SCOUT_REPORT.md`、`UI_DONOR_PORT_MATRIX.md`；
    404 / 读不到的必须写"打不开 + 用过的端点"，不许编内容顶替。
    四个待解真机 blocker 是任务的靶心：① 面板窗口手指滑不动（后两排动作够不到）；
    ② AI 卡片取地点的方式（过量抓取 / `slice(0,8)`）；③ 厦门例子硬编码对任何城市都显示；
    ④ 地图手势被邻屏抢走或滑不动。
  status: DISPATCHED@2026-09-21T18:3x+08 by 494abfd7（新只读侦察车道；0124-B 保持 HELD，D 不做第二写者）
