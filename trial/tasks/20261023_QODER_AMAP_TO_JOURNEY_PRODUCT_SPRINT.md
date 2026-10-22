# CityNexus V3 | Qoder 高德能力 → Agent 真正出发产品冲刺（2026-10-23）

**负责人：Qoder，唯一实施分支 `rescue/v3-final-departure-20261022`，产品 PR #43，主工单 #42。** 这个任务书是用户“现在怎么改进”的直接工程裁决：**先解决真实旅客要做的事，再考虑新增 Provider API 数量；所有新接口必须有用户可见入口和同一 Journey 的 Chrome 证据。**

## 起点，不重造前一轮

- 核对时远端 HEAD `036e96e73347f85255ab77c25e68ae6926281310`（之后请自行 fetch 最新 SHA）。原始 V3 十屏、Agent 自然语言改日程、A/B/C、地点真实高德搜索与部分照片已实现，`prepare-plan` 可从同一任务创建 CANDIDATE。Chrome walk-57 显示六个真实地点来源与正式候选，但 `SELECT_BUTTONS=0`；这次不能拿另一个 mock-city 成功 ACTIVE 冒充。
- 真实高德已接：`amap_provider.py` 的 district / v5 POI text / around / v5 walking；`goal_amap.py` 生成 research_places、research_routes；`goal_place_identity.py` 已映射 canonical Place；`f11f28ad` 修好 opening-hours 传递。
- **现存两条没有接上的证据链**：
  1. `goal_amap.py:206+` 把路线只写到 task `research_routes`；`goal_preparation.py:160+` 写 `metadata.transfer_route`，但 `mobility_frozen=False`、PlanVersion 没权威 snapshot，出发/select gate 仍断；
  2. `amap_provider.py` 的 `business.cost` 是人均消费而非可信门票，该北京测试库 72 个地点中的票价证据 = 0。现有 `services.py:COST_UNKNOWN_ACCEPTED / USER_ACCEPTS_UNKNOWN_PRICE_NOT_INCLUDED` 确有签名预算不确定政策，但 **generic compose 特意限定已选 Overpass bootstrap 场景**，不允许前端随便给来自高德的 goal candidate 写上那个状态。必须加一个窄的、本人明示、服务器验证的 GoalTask 流程。
- 高德官方 2026 文档明确提供 v5 驾车/公交/步行/骑行，POI 2.0 ID 详情 business/navi/photos；高德**官方 MCP Server** 还提供地点详情、天气、导航唤端、生成专属地图等功能，但均不是本 Sprint 第一个实施动作。文档：https://developer.amap.com/api/webservice/guide/api/newroute ，https://developer.amap.com/api/webservice/guide/api/newpoisearch ，https://developer.amap.com/api/mcp-server/summary 。高德照片使用前核对平台条款与展示许可，不用无依据的跨站搬运。

## P0-1：高德路线真证据 → 同一正式候选 snapshot（**第一笔产品代码**）

**用户看见**：「正在测量两站的转场」「步行约 45 分钟，可考虑公交」「路线已核实 3/4，最后一段仍需重新规划」。不是一个只写 `route_provenance` 的 backend JSON。

Qoder 按当前服务端实际契约实现最窄桥接：
- 在签名 `journey_id + goal_task_id + plan_version_id + expected_revision` 范围里枚举**正式候选当天真正会走的相邻 Place 路段**，排除跨日虚假路段、空地点，并按源 `amap:POI_ID` 与 canonical `Place.id` 明确映射。不能靠地名字符串拼接。
- 从 `task.research_routes` 和 `ProviderCall` 读取已采集高德回执；确保来源可核验、from/to 精确对应、捕获时间/模式有效。现研究侧保存的 route 会裁掉 geometry，**不得从两点连直线造道路几何**；如果正式 snapshot 需要原始 geometry，向原始 provider receipt 合法读取，或在授权/预算下只为缺失 used hop 再查一次。
- 复用 `integrations/mobility/snapshot_capture.py`、`MobilityFact` 和正式 PlanVersion `mobility_evidence_json`/snapshot_id 契约，必要时写 **高德 GCJ02 → domain WGS84 的路由适配器**，但保留 `original_crs=GCJ02` 与 provider call id；不要把内部 `CN-RV-...` 旅程码当高德公交 citycode。所有事实只作 `LIVE_PROVIDER_CAPTURE` 或经过授权的真实来源；禁止 mock/fixture、Agent 推测或无出处的 15min 通过 hard gate。
- 实现一次有幂等 key、PlanVersion 乐观并发约束、过期规则、断点恢复的**“重新核实并冻结转场”**动作。对已使用事实 cache/reuse；来源失效则明确 `ROUTE_UNAVAILABLE` 和用户下一步。服务器正式 `select/commit/start` 权限与 authority gate 不能从 React 端绕过。
- **先让一段用户看得见**：Agent 路段 0/4→有回执 3/4→冻结 3/4、剩余 1 阻塞，并能刷新恢复；只完成这一步也立即 push SHA，别等所有商业事实齐了。

最小代码入口：`backend/app/agent/goal_amap.py`、`goal_preparation.py`、`integrations/china/amap.py`、`integrations/mobility/{snapshot_capture,runtime}.py`、`route_session_operations.py`、`services.py`、`frontend/src/trial/mobile/{DraftDepartureCard,MobilePlanWorkbench}.tsx`。优先借用现有 Route Session 幂等 contract，不新建第二套路线真相系统。

## P0-2：未知门票不能让整趟旅行失业，但也不能伪称预算已确定

**对话与 UI 设计：** Agent 首先用已有 `research_place_sources/acquire_place_facts` 检查对该景区有效的官方/可信票务来源（只用已授权的检索方式，核实 source URL/date）。仍然未知时，明确显示「已知费用 ¥X；另有 3 项门票待核实，¥500 预算可能超出」；给用户 **“继续规划并接受费用不确定”** / **“让 Agent 换成价格明确的地点”** 两个实际可点动作。已知免费的地点要有独立来源，不能把高德 `cost=None` 当免费；餐厅 `business.cost=119` 只可归类 `AVERAGE_SPEND_ESTIMATE`，不能混入门票 price field。

- 仅在**已认证的本人主动确认**后创建版本绑定的 consent/ack receipt：journey、plan、revision、明确 unknown Place ID 列表、known subtotal、具体不包括哪些价格、确认人、时间、幂等；修改计划或新增未知地点后必须重新确认。
- 复用 `services.py` 既有 `COST_UNKNOWN_ACCEPTED` 与 `COST_UNKNOWN_USER_POLICY` 的语义与 PlanSchema `PARTIAL_UNKNOWN` 投影，**窄扩到由 GoalTask 已可信 canonical Place 形成的候选**；绝不从模型输出/前端客户端直接写 authority_state，不改所有 bootstrap/replan 的统一 gate。用户接受价格不确定，只解除相应的 **cost-only** 阻塞，不解除实际开放情况、地点身份、路线、日期冲突、多人 consent。
- 这个版本是**可以开始有未知价格的旅行计划**，不是“景区已预订/门票已买/预算保证不超”的声明；登录恢复后也必须可读回已知/未知区分。

## P0-3：按出发日期核实营业，不只展示一段来源原文

- 当前高德 `opentime_week` 会包含旺淡季、周一闭馆等复合原文；`goal_amap._amap_opening_envelope` 虽保留 `closure_notes`，仍设置 `weekday_coverage=UNRESOLVED`。必须在**用户真正选择的未来日期与到达时间**对照营业信息。某周一的故宫不得因扁平 `NORMALIZED_VALID` 而显示确定开放。
- 对复杂日期无法确定时保留 `DATE_SPECIFIC_UNKNOWN` 与原文/最后核验时间，Agent 可向更权威来源再查或改日期/更换地点；不需要一份完整日历数据库才可继续编辑草案。已确定闭馆时明确提示改行程而不是偷偷改营业时间。

## P1：高德真正提升用户体验的扩展（P0 之后）

1. **多模式方案对比。** 国内采用现有 `AmapMobilityProvider` 路线适配能力与 v5 公交、驾车、骑行，不把它停在孤立类文件；公交 `city1/city2` 必须是**真实高德城市 citycode**，GCJ02/WGS84 明确转换。优先只对步行时间太长、跨城区或用户指定“不想走路”的实际路段做多方案，不对所有两点全矩阵刷 Key。给旅客「步行 45 分 / 地铁 XX 分 / 打车 XX 分」有来源的卡；只有确实调出 provider 回执的模式才出现可比较数值。
2. **地点详情增强。** 给“用户已选择且详情不足”的真实 POI 按 ID 做 `/v5/place/detail`，请求 `show_fields=business,navi` 或有许可的 photos 等；评级、电话、入口 `entr_location`、营业原文、餐饮人均只按自身语义展示。若当前 Web Key 对高级能力未授权，正确显示不可用，不让用户看到假评论与假门票。
3. **行前到行中主动性。** 可使用高德基础天气按 adcode 查询，结合已有 Guardian 机制及当前 PlanVersion 评估真实影响，没有风险就静默，不制造“闭馆”；实时路况等高级能力先在控制台核对配额、权限与成本。
4. **高德官方 MCP Server 的“可选小试验”**：官网 https://developer.amap.com/api/mcp-server/summary 宣称有目的地搜索、详情、路线、天气、导航唤端及生成专属地图。单独在隔离测试环境比较 `find POI detail + navigation deep link / itinerary handoff` 两项与现有 typed API 的差异；高德 MCP 能补 Agent 工具生态与“到高德继续导航”，但**不能绕过 CityNexus 自己的 signed Journey / Place / PlanVersion source/authority contract**，不要整仓重写成裸 MCP 调用。不要直接把 Key 发给模型或前端。
5. **跨会话找回旅行与同行决策**持续并行推进。不能让用户关掉浏览器就失联，不能把“同行决策”挂到只有 AI 授权的假入口；两件均用 Chrome 实际点击验收，和高德扩展不互相掩盖。

## 执行与回执（Chrome-use/真实可见隔离 Chrome 先行）

固定同一新鲜故事：**北京 2026-11-02 至 11-03 / ¥500 每人 / 少走路，想看古迹和胡同**。从真实首次打开的页面输入，不用 API 预先构造成功 plan；保留 `journey_id` 与 `task_id` 不变。流程：

`首次输入→Agent 查高德地点→路线/照片/营业事实→A/B/C→“改第二天下午”→选择同一草案→保存 CANDIDATE→测量并冻结 used edges→景区价格真实来源或本人确认 UNKNOWN→select/commit→ACTIVE→刷新并尽可能重登录找回`。

每个切片交付：**PRODUCT_SHA + 实际按钮文字 + BEFORE/AFTER 两张真实浏览器截图 + signed HTTP 回执（脱敏） + PlanVersion/GoalTask 同一性 + AMap ProviderCall + 已用路线事实与冻结 snapshot ID + 缺口列表变化**。

- 允许 `PARTIAL`：实时供应商无服务、用户拒绝确认、费用未获同意、确实闭馆等，不为成功乱填 0 或绕过信任边界。
- **停止假绿**：UI 下无点击证据、无 PlanVersion 冻结，只增加 API/单元测试 = 不算完成下一棒。最少相关测试作回归即可；不为改测试而篡改运行事实。
- 真机 `USER_VERIFIED=PENDING` 直到用户自己在手机操作，Edge 手机视口不冒充真机。用户若仍无法找回旧 Journey，另一条 P0 不得被本 Sprint 的绿测掩盖。

## 最新已知参考

- 浏览器实测：`trial/results/20261022_v3_human_chrome/walk-57-log.txt`，`departure-price-evidence-probe-1.txt`，`research-routes-in-walked-journey-1.txt`。
- 前次明确工程审查：https://github.com/Canshu-King/CityNexus/pull/43#issuecomment-6349394171 。
- 高德官方路线 v5：https://developer.amap.com/api/webservice/guide/api/newroute 。
- 高德 POI 2.0：https://developer.amap.com/api/webservice/guide/api/newpoisearch 。
- 高德 MCP：https://developer.amap.com/api/mcp-server/summary 。

**第一棒禁止再产出只有长报告没有产品 commit 的交付。Agent 应主动修复来源与规划问题，用户负责决定，平台负责可追溯权限。**
